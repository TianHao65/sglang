#!/usr/bin/env python3
"""Read-only, standard-library host telemetry for the Quark35 TP4 experiment.

Run on the host, outside the model container. GPU numbers refer to rocm-smi
device indices. A sysfs ordinal fallback is explicitly unverified until a
rocm-smi PCI identity has been observed. No environment or command lines are read.
"""

import argparse
import datetime
import errno
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time


SCHEMA_VERSION = 1
COMMAND_TIMEOUT_SECONDS = 0.8
OWNER_SCAN_BUDGET_SECONDS = 0.7
ERROR_EXAMPLE_LIMIT = 8
KFD_PROC_ROOTS = ("/sys/class/kfd/kfd/proc", "/sys/kernel/debug/kfd/proc")
PCI_RE = re.compile(r"(?:[0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]")


def clock():
    epoch = time.time()
    return {
        "wall_utc": datetime.datetime.fromtimestamp(
            epoch, datetime.timezone.utc
        ).isoformat(),
        "epoch_seconds": epoch,
        "monotonic_seconds": time.monotonic(),
    }


def error_record(exc, path=None):
    result = {"type": type(exc).__name__, "message": str(exc)}
    if path is not None:
        result["path"] = str(path)
    if getattr(exc, "errno", None) is not None:
        result["errno"] = exc.errno
    return result


def read_text(path):
    try:
        return {"ok": True, "value": Path(path).read_bytes().decode("utf-8", "replace")}
    except OSError as exc:
        return {"ok": False, "error": error_record(exc, path)}


def list_names(path):
    try:
        return {"ok": True, "names": os.listdir(str(path))}
    except OSError as exc:
        return {"ok": False, "error": error_record(exc, path)}


def numeric(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
        if match:
            result = float(match.group())
            return result if math.isfinite(result) else None
    return None


def parse_key_values(text):
    result = {}
    for line in text.split("\n"):
        parts = line.replace(":", " ", 1).split()
        if len(parts) >= 2:
            try:
                result[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return result


def command(args, timeout):
    started = time.monotonic()
    result = {"command": args, "timeout_seconds": timeout}
    try:
        completed = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=timeout,
        )
        result.update({
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
    except subprocess.TimeoutExpired as exc:
        def decoded(value):
            return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
        result.update({
            "ok": False, "error": error_record(exc),
            "stdout": decoded(exc.stdout), "stderr": decoded(exc.stderr),
        })
    except OSError as exc:
        result.update({"ok": False, "error": error_record(exc)})
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def canonical_pci(value):
    match = PCI_RE.search(str(value))
    if not match:
        return None
    pci = match.group().lower()
    return pci if len(pci.split(":")) == 3 else "0000:" + pci


def parse_rocm_card(card):
    result = {"util_percent": None, "vram_used_bytes": None,
              "vram_total_bytes": None, "temperatures_c": {},
              "powers_w": {}, "clocks_mhz": {}, "pci": None}
    for key, value in card.items():
        lower = key.lower()
        number = numeric(value)
        if "pci" in lower and "bus" in lower:
            result["pci"] = canonical_pci(value)
        elif "gpu use" in lower or "gpu utilization" in lower:
            result["util_percent"] = number
        elif "vram" in lower and "used" in lower and "memory" in lower:
            result["vram_used_bytes"] = number
        elif "vram" in lower and "total" in lower and "memory" in lower:
            result["vram_total_bytes"] = number
        elif "temperature" in lower and number is not None:
            result["temperatures_c"][key] = number
        elif "power" in lower and "(w)" in lower and number is not None:
            result["powers_w"][key] = number
        elif "clock" in lower and number is not None:
            mhz = re.search(r"(\d+(?:\.\d+)?)\s*mhz", str(value), re.I)
            if mhz or "mhz" in lower:
                result["clocks_mhz"][key] = float(mhz.group(1)) if mhz else number
    return result


def discover_drm():
    listing = list_names("/sys/class/drm")
    result = {"ok": listing["ok"], "devices": [], "errors": []}
    if not listing["ok"]:
        result["errors"].append(listing["error"])
        return result
    for name in sorted(listing["names"]):
        if not re.fullmatch(r"card\d+", name):
            continue
        base = Path("/sys/class/drm") / name / "device"
        vendor = read_text(base / "vendor")
        if not vendor["ok"]:
            result["errors"].append(vendor["error"])
            continue
        if vendor["value"].strip().lower() != "0x1002":
            continue
        try:
            pci = canonical_pci(base.resolve(strict=True).name)
        except OSError as exc:
            result["errors"].append(error_record(exc, base))
            continue
        children = list_names(base / "drm")
        result["devices"].append({
            "card": name, "pci": pci, "device_path": str(base),
            "nodes": children.get("names", [name]),
            "nodes_error": children.get("error"),
        })
    result["devices"].sort(key=lambda item: int(item["card"][4:]))
    return result


def sysfs_gpu(device):
    base = Path(device["device_path"])
    result = {"util_percent": None, "vram_used_bytes": None,
              "vram_total_bytes": None, "temperatures_c": {},
              "powers_w": {}, "clocks_mhz": {}, "errors": []}
    for name, field in [("gpu_busy_percent", "util_percent"),
                        ("mem_info_vram_used", "vram_used_bytes"),
                        ("mem_info_vram_total", "vram_total_bytes")]:
        value = read_text(base / name)
        if value["ok"]:
            result[field] = numeric(value["value"])
        else:
            result["errors"].append(value["error"])
    hwmons = list_names(base / "hwmon")
    if not hwmons["ok"]:
        result["errors"].append(hwmons["error"])
    for hwmon in hwmons.get("names", []):
        directory = base / "hwmon" / hwmon
        files = list_names(directory)
        if not files["ok"]:
            result["errors"].append(files["error"])
            continue
        for name in files["names"]:
            match = re.fullmatch(r"(temp\d+)_input|(power\d+)_(average|input)|(freq\d+)_input", name)
            if not match:
                continue
            value = read_text(directory / name)
            if not value["ok"]:
                result["errors"].append(value["error"])
                continue
            number = numeric(value["value"])
            if number is None:
                continue
            stem = name.rsplit("_", 1)[0]
            label = read_text(directory / (stem + "_label"))
            key = hwmon + "/" + (label["value"].strip() if label["ok"] else name)
            if name.startswith("temp"):
                result["temperatures_c"][key] = number / 1000.0
            elif name.startswith("power"):
                result["powers_w"][key] = number / 1000000.0
            else:
                result["clocks_mhz"][key] = number / 1000000.0
    for name in ["pp_dpm_sclk", "pp_dpm_mclk"]:
        value = read_text(base / name)
        if not value["ok"]:
            result["errors"].append(value["error"])
            continue
        for line in value["value"].split("\n"):
            match = re.search(r"(\d+(?:\.\d+)?)\s*mhz.*\*", line, re.I)
            if match:
                result["clocks_mhz"][name] = float(match.group(1))
    return result


def collect_gpu(gpus, executable, timeout, cached_pci):
    args = ([executable, "--device"] + [str(gpu) for gpu in gpus] +
            ["--showuse", "--showmeminfo", "vram", "--showtemp", "--showpower",
             "--showclocks", "--showbus", "--json"])
    rocm = command(args, timeout) if executable else {
        "ok": False, "error": {"type": "ExecutableUnavailable", "message": "rocm-smi not found"}
    }
    payload = {}
    if rocm["ok"]:
        try:
            payload = json.loads(rocm["stdout"])
            if not isinstance(payload, dict):
                raise ValueError("rocm-smi JSON is not an object")
            rocm["payload"] = payload
        except (ValueError, TypeError) as exc:
            rocm["ok"] = False
            rocm["parse_error"] = error_record(exc)
    drm = discover_drm()
    cards = []
    mappings = {}
    for gpu in gpus:
        raw = payload.get("card" + str(gpu), {})
        metrics = parse_rocm_card(raw) if isinstance(raw, dict) else parse_rocm_card({})
        pci = metrics.pop("pci")
        identity_source = "rocm-smi --showbus"
        if pci:
            cached_pci[gpu] = pci
        else:
            pci = cached_pci.get(gpu)
            identity_source = "cached rocm-smi --showbus" if pci else "unverified sorted AMD DRM ordinal"
        device = next((item for item in drm["devices"] if item["pci"] == pci), None) if pci else None
        verified = device is not None and pci is not None
        if device is None and gpu < len(drm["devices"]):
            device = drm["devices"][gpu]
        identity = {"mapping_verified": verified, "source": identity_source,
                    "rocm_pci": pci, "candidate_drm_device": device}
        fallback = sysfs_gpu(device) if device else {
            "errors": [{"type": "MappingUnavailable", "message": "No candidate AMD DRM device"}]
        }
        sources = {}
        for key in ["util_percent", "vram_used_bytes", "vram_total_bytes",
                    "temperatures_c", "powers_w", "clocks_mhz"]:
            if metrics[key] is not None and metrics[key] != {}:
                sources[key] = "rocm-smi"
            elif fallback.get(key) is not None and fallback.get(key) != {}:
                metrics[key] = fallback[key]
                sources[key] = "sysfs" if verified else "sysfs candidate; mapping unverified"
            else:
                sources[key] = "unavailable"
        cards.append({"gpu": gpu, "identity": identity, "metrics": metrics,
                      "metric_sources": sources, "rocm_raw": raw, "sysfs": fallback})
        mappings[gpu] = identity
    return {"rocm_smi": rocm, "drm_discovery": drm, "cards": cards}, mappings


def parse_cpu_stat(text):
    for line in text.split("\n"):
        if line.startswith("cpu "):
            return [int(value) for value in line.split()[1:]]
    raise ValueError("Aggregate cpu row absent in /proc/stat")


def cpu_delta(current, previous):
    if previous is None:
        return None
    values = [a - b for a, b in zip(current[:8], previous[:8])]
    total = sum(values)
    if total <= 0 or any(value < 0 for value in values):
        return {"ok": False, "reason": "CPU tick counter reset or no positive delta", "ticks": values}
    idle = values[3] if len(values) > 3 else 0
    iowait = values[4] if len(values) > 4 else 0
    return {"ok": True, "ticks": values, "total_ticks": total,
            "busy_percent": 100.0 * (total - idle - iowait) / total,
            "iowait_percent": 100.0 * iowait / total}


def collect_host(previous_cpu):
    result = {}
    stat = read_text("/proc/stat")
    current = None
    if stat["ok"]:
        try:
            current = parse_cpu_stat(stat["value"])
            result["cpu"] = {"ok": True, "aggregate_ticks": current,
                             "interval_delta": cpu_delta(current, previous_cpu)}
        except ValueError as exc:
            result["cpu"] = {"ok": False, "error": error_record(exc)}
    else:
        result["cpu"] = stat
    load = read_text("/proc/loadavg")
    if load["ok"]:
        try:
            values = load["value"].split()
            runnable, processes = values[3].split("/")
            result["loadavg"] = {"ok": True, "load1": float(values[0]),
                                 "load5": float(values[1]), "load15": float(values[2]),
                                 "runnable": int(runnable), "processes": int(processes)}
        except (ValueError, IndexError) as exc:
            result["loadavg"] = {"ok": False, "error": error_record(exc)}
    else:
        result["loadavg"] = load
    mem = read_text("/proc/meminfo")
    if mem["ok"]:
        fields = {}
        for line in mem["value"].split("\n"):
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            parts = raw.split()
            if parts:
                try:
                    fields[key] = {"value": int(parts[0]), "unit": parts[1] if len(parts) > 1 else "count"}
                except ValueError:
                    pass
        result["meminfo"] = {"ok": True, "fields": fields,
                             "values_kb": {key: value["value"] for key, value in fields.items() if value["unit"] == "kB"}}
    else:
        result["meminfo"] = mem
    return result, current


def unescape_mount(value):
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), value)


def parse_mountinfo(text):
    mounts = []
    for line in text.split("\n"):
        if " - " not in line:
            continue
        left, right = line.split(" - ", 1)
        before, after = left.split(), right.split()
        if len(before) >= 5 and len(after) >= 3 and after[0] in ("cgroup", "cgroup2"):
            mounts.append({"root": unescape_mount(before[3]),
                           "mountpoint": unescape_mount(before[4]),
                           "type": after[0], "controllers": after[2].split(",")})
    return mounts


def resolve_cgroup(container_id, timeout):
    inspected = command(["docker", "inspect", "--format", "{{.State.Pid}}", container_id], timeout)
    result = {"ok": False, "container_id": container_id, "docker_inspect": inspected}
    if not inspected["ok"]:
        return result
    try:
        pid = int(inspected["stdout"].strip())
        if pid <= 0:
            raise ValueError("Container has no positive host PID")
    except ValueError as exc:
        result["error"] = error_record(exc)
        return result
    cgroups, mountinfo = read_text("/proc/{}/cgroup".format(pid)), read_text("/proc/self/mountinfo")
    result.update({"host_init_pid": pid, "cgroup_read": cgroups, "mountinfo_ok": mountinfo["ok"]})
    if not cgroups["ok"] or not mountinfo["ok"]:
        result["mountinfo_error"] = mountinfo.get("error")
        return result
    mounts = parse_mountinfo(mountinfo["value"])
    paths = {}
    for line in cgroups["value"].split("\n"):
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        controllers, path = parts[1].split(","), parts[2]
        for mount in mounts:
            v2 = mount["type"] == "cgroup2" and parts[0] == "0"
            matching = v2 or bool(set(controllers) & set(mount["controllers"]))
            relative = os.path.relpath(path, mount["root"])
            if not matching or relative == ".." or relative.startswith("../"):
                continue
            full = str(Path(mount["mountpoint"]) / relative)
            for key in (["unified"] if v2 else controllers):
                paths[key] = full
    result.update({"ok": bool(paths), "paths": paths})
    if not paths:
        result["error"] = {"type": "CgroupMappingUnavailable", "message": "No applicable host cgroup mount"}
    return result


def collect_cgroup(resolved, previous, monotonic_now):
    result = {"resolved": resolved, "files": {}, "cpu_interval": None}
    if not resolved.get("ok"):
        result["ok"] = False
        return result, None
    paths = resolved["paths"]
    usage_seconds = None
    if "unified" in paths:
        base = Path(paths["unified"])
        names = ["cpu.stat", "cpu.max", "memory.current", "memory.max",
                 "memory.events", "memory.stat", "pids.current"]
        for name in names:
            value = read_text(base / name)
            result["files"][name] = value
        stat = result["files"]["cpu.stat"]
        if stat["ok"]:
            usage = parse_key_values(stat["value"]).get("usage_usec")
            usage_seconds = usage / 1000000.0 if usage is not None else None
        result["version"] = 2
    else:
        targets = [("cpuacct", "cpuacct.usage"), ("cpuacct", "cpuacct.stat"),
                   ("cpu", "cpu.stat"), ("cpu", "cpu.cfs_quota_us"),
                   ("cpu", "cpu.cfs_period_us"), ("memory", "memory.usage_in_bytes"),
                   ("memory", "memory.limit_in_bytes"), ("memory", "memory.stat"),
                   ("memory", "memory.failcnt"), ("memory", "memory.oom_control")]
        for controller, name in targets:
            if controller in paths:
                result["files"][name] = read_text(Path(paths[controller]) / name)
            else:
                result["files"][name] = {"ok": False, "error": {
                    "type": "ControllerUnavailable", "message": controller}}
        usage = result["files"].get("cpuacct.usage", {})
        if usage.get("ok"):
            value = numeric(usage["value"])
            usage_seconds = value / 1000000000.0 if value is not None else None
        result["version"] = 1
    identity = json.dumps(paths, sort_keys=True)
    if previous and usage_seconds is not None and previous[2] == identity:
        elapsed, consumed = monotonic_now - previous[0], usage_seconds - previous[1]
        if elapsed > 0 and consumed >= 0:
            result["cpu_interval"] = {"elapsed_seconds": elapsed,
                                      "cpu_seconds": consumed,
                                      "cpu_percent_one_core": 100.0 * consumed / elapsed}
    result["ok"] = all(item["ok"] for item in result["files"].values())
    result["cpu_usage_seconds"] = usage_seconds
    return result, ((monotonic_now, usage_seconds, identity) if usage_seconds is not None else None)


def parse_process_stat(text):
    close = text.rfind(")")
    if close < 0:
        raise ValueError("Malformed /proc/PID/stat")
    fields = text[close + 1:].split()
    return {"name": text[text.find("(") + 1:close], "state": fields[0],
            "ppid": int(fields[1]), "alive": fields[0] not in ("Z", "X"),
            "start_ticks": int(fields[19])}


def process_identity(pid, container_id):
    base = Path("/proc") / str(pid)
    result = {"pid": pid, "name": None, "uid": None, "start_ticks": None,
              "state": None, "ppid": None, "alive": None,
              "in_own_container": None, "errors": []}
    stat = read_text(base / "stat")
    if stat["ok"]:
        try:
            result.update(parse_process_stat(stat["value"]))
        except (ValueError, IndexError) as exc:
            result["errors"].append(error_record(exc, base / "stat"))
    else:
        if stat["error"].get("errno") in (errno.ENOENT, errno.ESRCH):
            result["alive"] = False
        result["errors"].append(stat["error"])
    status = read_text(base / "status")
    if status["ok"]:
        for line in status["value"].split("\n"):
            if line.startswith("Uid:"):
                try:
                    result["uid"] = int(line.split()[1])
                except (ValueError, IndexError):
                    pass
    else:
        result["errors"].append(status["error"])
    cgroup = read_text(base / "cgroup")
    if cgroup["ok"]:
        result["in_own_container"] = container_id in cgroup["value"]
    else:
        result["errors"].append(cgroup["error"])
    return result


def collect_owners(mappings, container_id, budget, stop):
    started = time.monotonic()
    result = {"ok": False, "complete": False, "owners": [], "sources": {},
              "errors": [], "error_count": 0, "vanished_count": 0,
              "proc_entries": 0, "proc_scanned": 0, "scan_budget_seconds": budget}
    owners = {}
    def record_error(value):
        if value.get("errno") in (errno.ENOENT, errno.ESRCH):
            result["vanished_count"] += 1
            return
        result["error_count"] += 1
        if len(result["errors"]) < ERROR_EXAMPLE_LIMIT:
            result["errors"].append(value)
    node_gpus, pci_gpus = {}, {}
    for gpu, mapping in mappings.items():
        device = mapping.get("candidate_drm_device")
        if device:
            if device["pci"] is not None:
                pci_gpus.setdefault(device["pci"], []).append(gpu)
            for node in device.get("nodes", []):
                node_gpus.setdefault(node, []).append(gpu)
    topology = list_names("/sys/class/kfd/kfd/topology/nodes")
    gpu_id_gpus = {}
    if topology["ok"]:
        for node in topology["names"]:
            base = Path("/sys/class/kfd/kfd/topology/nodes") / node
            gpu_id, properties = read_text(base / "gpu_id"), read_text(base / "properties")
            if gpu_id["ok"] and properties["ok"]:
                minor = parse_key_values(properties["value"]).get("drm_render_minor")
                if minor is not None:
                    gpu_id_gpus[gpu_id["value"].strip()] = node_gpus.get("renderD" + str(minor), [])
            else:
                record_error(gpu_id.get("error", properties.get("error")))
    else:
        record_error(topology["error"])
    def add(pid, gpu, evidence):
        entry = owners.setdefault((pid, gpu), {"pid": pid, "gpu": gpu, "evidence": []})
        entry["evidence"].append(evidence)
    for root in KFD_PROC_ROOTS:
        listing = list_names(root)
        source = {"readable": listing["ok"], "processes_scanned": 0}
        result["sources"][root] = source
        if not listing["ok"]:
            source["error"] = listing["error"]
            continue
        for pid_text in listing["names"]:
            if not pid_text.isdigit():
                continue
            pid, base = int(pid_text), Path(root) / pid_text
            source["processes_scanned"] += 1
            children = list_names(base)
            if not children["ok"]:
                record_error(children["error"])
                continue
            for name in children["names"]:
                if name.startswith("stats_"):
                    gpu_id = name[len("stats_"):]
                    vram = read_text(base / name / "vram")
                    if not vram["ok"]:
                        record_error(vram["error"])
                    for gpu in gpu_id_gpus.get(gpu_id, []):
                        add(pid, gpu, {"source": "kfd_stats_directory", "gpu_id": gpu_id,
                                       "vram": vram, "meaning": "registered KFD device, not utilization"})
            queues = list_names(base / "queues")
            if not queues["ok"]:
                record_error(queues["error"])
                continue
            for queue in queues["names"]:
                for attribute in ["gpuid", "gpu_id"]:
                    value = read_text(base / "queues" / queue / attribute)
                    if value["ok"]:
                        for gpu in gpu_id_gpus.get(value["value"].strip(), []):
                            add(pid, gpu, {"source": "kfd_queue", "queue": queue,
                                           "gpu_id": value["value"].strip()})
                        break
                    if value["error"].get("errno") != errno.ENOENT:
                        record_error(value["error"])
        if stop.is_set():
            break
    processes = list_names("/proc")
    drm_complete = False
    result["sources"]["proc_drm_fds"] = {"readable": processes["ok"]}
    if processes["ok"]:
        pids = sorted(int(name) for name in processes["names"] if name.isdigit())
        result["proc_entries"] = len(pids)
        for pid in pids:
            if stop.is_set() or time.monotonic() - started >= budget:
                result["budget_exhausted_or_stopped"] = True
                break
            result["proc_scanned"] += 1
            base = Path("/proc") / str(pid)
            fds = list_names(base / "fd")
            if not fds["ok"]:
                record_error(fds["error"])
                continue
            for fd in fds["names"]:
                if stop.is_set() or time.monotonic() - started >= budget:
                    result["budget_exhausted_or_stopped"] = True
                    break
                try:
                    target = os.readlink(str(base / "fd" / fd))
                except OSError as exc:
                    record_error(error_record(exc, base / "fd" / fd))
                    continue
                if not target.startswith("/dev/dri/"):
                    continue
                node = Path(target).name
                info = read_text(base / "fdinfo" / fd)
                fields = {}
                if info["ok"]:
                    for line in info["value"].split("\n"):
                        if line.startswith(("drm-pdev:", "drm-client-id:", "drm-memory-", "drm-engine-")):
                            key, value = line.split(":", 1)
                            fields[key] = value.strip()
                else:
                    record_error(info["error"])
                pci = canonical_pci(fields.get("drm-pdev", ""))
                selected = pci_gpus.get(pci, node_gpus.get(node, []))
                for gpu in selected:
                    add(pid, gpu, {"source": "drm_fd", "fd": fd,
                                   "device_node": target, "fdinfo": fields,
                                   "fdinfo_error": info.get("error")})
            if result.get("budget_exhausted_or_stopped"):
                break
            if result["proc_scanned"] == len(pids):
                drm_complete = True
    else:
        record_error(processes["error"])
    for (pid, gpu), entry in sorted(owners.items()):
        entry["process"] = process_identity(pid, container_id)
        entry["mapping_verified"] = mappings[gpu]["mapping_verified"]
        for value in entry["process"]["errors"]:
            record_error(value)
        result["owners"].append(entry)
    verified = all(item["mapping_verified"] for item in mappings.values())
    kfd_readable = any(result["sources"][root]["readable"] for root in KFD_PROC_ROOTS if root in result["sources"])
    result["kfd_proc_readable"] = kfd_readable
    result["sources"]["proc_drm_fds"]["complete"] = drm_complete
    result["mapping_verified_all_selected"] = verified
    result["complete"] = (drm_complete and kfd_readable and topology["ok"]
                          and result["error_count"] == 0 and verified)
    result["ok"] = result["complete"]
    result["status"] = "complete" if result["complete"] else "incomplete; empty owners does not establish no owner"
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def parse_gpus(value):
    try:
        result = [int(item.strip()) for item in value.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError("GPU indices must be comma-separated integers")
    if not result or any(item < 0 for item in result) or len(set(result)) != len(result):
        raise argparse.ArgumentTypeError("GPU indices must be distinct nonnegative integers")
    return result


def self_test():
    """Synthetic-only checks: no commands, proc/sysfs reads, or files are written."""
    from unittest.mock import patch
    assert parse_gpus("0,1,2,3") == [0, 1, 2, 3]
    synthetic = {"GPU use (%)": "87", "VRAM Total Used Memory (B)": "123456789",
                 "VRAM Total Memory (B)": "206141652992", "PCI Bus": "0000:41:00.0",
                 "Temperature (Sensor junction) (C)": "71.5", "Average Graphics Package Power (W)": "303.25",
                 "sclk clock speed (Mhz)": "1500Mhz"}
    card = parse_rocm_card(synthetic)
    assert card["util_percent"] == 87 and card["vram_used_bytes"] == 123456789
    assert card["pci"] == "0000:41:00.0" and card["clocks_mhz"]["sclk clock speed (Mhz)"] == 1500
    assert card["temperatures_c"] and card["powers_w"]
    delta = cpu_delta([20, 0, 10, 50, 20, 0, 0, 0], [10, 0, 0, 0, 0, 0, 0, 0])
    assert abs(delta["busy_percent"] - 100.0 * 20 / 90) < 1e-9
    mounts = parse_mountinfo("29 23 0:26 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n")
    assert mounts[0]["type"] == "cgroup2"
    stat = "42 (worker with spaces) " + " ".join(["S"] + ["0"] * 18 + ["987654"])
    assert parse_process_stat(stat)["start_ticks"] == 987654
    denied = {"ok": False, "error": {"type": "PermissionError", "errno": errno.EACCES,
                                       "message": "synthetic permission denied"}}
    with patch(__name__ + ".list_names", return_value=denied):
        owner = collect_owners({0: {"mapping_verified": True, "candidate_drm_device": None}},
                               "a" * 64, 0.01, threading.Event())
    assert owner["owners"] == [] and not owner["complete"] and owner["error_count"] > 0
    with patch(__name__ + ".subprocess.run", side_effect=subprocess.TimeoutExpired(["fake"], 0.1, output=b"partial")):
        timed_out = command(["fake"], 0.1)
    assert not timed_out["ok"] and timed_out["stdout"] == "partial"
    json.dumps({"card": card, "owner": owner, "timeout": timed_out}, allow_nan=False)
    print("self-test passed: synthetic parsing, CPU delta, cgroup mount, PID identity, permissions, timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="New JSONL file; existing files are not overwritten")
    parser.add_argument("--gpus", type=parse_gpus, default=parse_gpus("0,1,2,3"))
    parser.add_argument("--container-id", help="Own Docker container ID, used for cgroup and PID attribution")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.output or not args.container_id:
        parser.error("--output and --container-id are required for telemetry")
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a positive finite number")
    if not re.fullmatch(r"[0-9a-fA-F]{12,64}", args.container_id):
        parser.error("--container-id must be a Docker ID of 12 to 64 hexadecimal characters")
    stop = threading.Event()
    termination = {"reason": "running", "signal": None}
    def on_signal(signum, frame):
        termination.update({"reason": "signal", "signal": signum})
        stop.set()
    for signum in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(signum, on_signal)
    executable = shutil.which("rocm-smi")
    timeout = min(COMMAND_TIMEOUT_SECONDS, max(0.05, args.interval * 0.75))
    owner_budget = min(OWNER_SCAN_BUDGET_SECONDS, max(0.02, args.interval * 0.7))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    count, skipped = 0, 0
    previous_cpu, previous_cgroup, cached_pci = None, None, {}
    started = time.monotonic()
    fatal = None
    with output.open("x", encoding="utf-8", buffering=1) as stream:
        def emit(event):
            stream.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        emit(dict(clock(), event="start", schema_version=SCHEMA_VERSION,
                  pid=os.getpid(), python_version=sys.version.split()[0],
                  gpus=args.gpus, container_id=args.container_id, interval_seconds=args.interval,
                  command_timeout_seconds=timeout, owner_scan_budget_seconds=owner_budget,
                  rocm_smi_path=executable,
                  owner_note="Permission failures, time budget, and unverified mappings prevent absence claims"))
        deadline = time.monotonic()
        resolved = None
        try:
            while not stop.is_set():
                if stop.wait(max(0.0, deadline - time.monotonic())):
                    break
                sample_start = clock()
                collection_start = sample_start["monotonic_seconds"]
                if resolved is None or count % 30 == 0:
                    resolved = resolve_cgroup(args.container_id, timeout)
                gpu, mappings = collect_gpu(args.gpus, executable, timeout, cached_pci)
                host, previous_cpu = collect_host(previous_cpu)
                cgroup, previous_cgroup = collect_cgroup(resolved, previous_cgroup, time.monotonic())
                remaining = args.interval - (time.monotonic() - collection_start)
                sample_owner_budget = min(owner_budget, max(0.02, remaining - 0.02))
                owners = collect_owners(mappings, args.container_id, sample_owner_budget, stop)
                finished = clock()
                emit(dict(sample_start, event="sample", schema_version=SCHEMA_VERSION,
                          sample_index=count, scheduled_monotonic_seconds=deadline,
                          schedule_lag_seconds=max(0.0, collection_start - deadline),
                          collection_elapsed_seconds=finished["monotonic_seconds"] - collection_start,
                          collection_end=finished, gpu=gpu, host=host, container=cgroup, owners=owners))
                count += 1
                deadline += args.interval
                if deadline < time.monotonic():
                    missed = int((time.monotonic() - deadline) // args.interval) + 1
                    skipped += missed
                    deadline += missed * args.interval
        except Exception as exc:
            fatal = error_record(exc)
            termination["reason"] = "error"
        finally:
            emit(dict(clock(), event="end", schema_version=SCHEMA_VERSION,
                      samples=count, skipped_schedule_slots=skipped,
                      elapsed_seconds=time.monotonic() - started,
                      termination=termination, error=fatal))
    if fatal:
        print("telemetry error: " + json.dumps(fatal), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
