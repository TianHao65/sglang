#!/usr/bin/env python3
"""TP1 frozen851 full-model operator profile pair; separate from TP4 performance or CI scores."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request

import profile_support_tp1 as safe

HOST_ROOT = Path('/raid/hatian/pr107_full_tgemm_20261116/tp1')
CONTAINER_ROOT = '/full_tgemm_tp1'
PORT = 19863
ENUM_LIMIT = 16 * 1024 ** 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_bytes(value):
    if value is None:
        return None
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|KB|MB|GB)?\s*', str(value), re.I)
    if not match:
        return None
    factors = {'b': 1, 'kib': 1024, 'mib': 1024**2, 'gib': 1024**3,
               'kb': 1000, 'mb': 1000**2, 'gb': 1000**3}
    return float(match[1]) * factors.get((match[2] or 'b').lower(), 1)


class ResourceGuard:
    """Permit recorded low-memory enumeration; refuse active selected-GPU peers."""
    def __init__(self, path, gpus):
        self.path, self.gpus = path, set(gpus)
        self.offset, self.pending = 0, b''
        self.samples = []
        self.enumeration_baseline = {}
        self.allowed_enumeration = []
        self.active_peer_events = []
        self.preflight = True
        self.release_mode = False
        self.owned_generations = set()
        self.consecutive_idle_samples = 0

    def poll(self):
        if not self.path.exists():
            return
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            self.pending += stream.read()
            self.offset = stream.tell()
        rows = self.pending.split(b'\n')
        self.pending = rows.pop()
        for line in rows:
            row = json.loads(line)
            if row.get('event') != 'sample':
                continue
            self.samples.append(row)
            idle = True
            if self.preflight:
                unavailable = False
                for card in row['gpu']['cards']:
                    if card['gpu'] not in self.gpus:
                        continue
                    metrics = card['metrics']
                    if metrics['util_percent'] != 0 or metrics['vram_used_bytes'] is None or metrics['vram_used_bytes'] >= 1024**3:
                        idle = False
                if row['owners'].get('complete') is not True:
                    idle = False
            for owner in row.get('owners', {}).get('owners', []):
                process = owner.get('process') or {}
                generation = (owner.get('pid'), str(process.get('start_ticks')))
                if process.get('in_own_container') is True and process.get('start_ticks') is not None:
                    self.owned_generations.add(generation)
                if generation in self.owned_generations:
                    continue
                if owner.get('gpu') not in self.gpus or process.get('alive') is False or process.get('in_own_container') is True:
                    continue
                values, has_queue = [], False
                for evidence in owner.get('evidence', []):
                    if evidence.get('source') == 'kfd_queue':
                        has_queue = True
                    if evidence.get('source') == 'kfd_stats_directory':
                        vram = evidence.get('vram') or {}
                        if vram.get('ok'):
                            values.append(memory_bytes(vram.get('value')))
                    if evidence.get('source') == 'drm_fd':
                        for key, value in (evidence.get('fdinfo') or {}).items():
                            if key.startswith('drm-memory-vram'):
                                values.append(memory_bytes(value))
                known = [value for value in values if value is not None]
                used = max(known) if known else None
                key = (owner.get('pid'), str(process.get('start_ticks')), owner.get('gpu'))
                growth = key in self.enumeration_baseline and used is not None and used > ENUM_LIMIT
                if has_queue or used is None or used > ENUM_LIMIT or growth or owner.get('mapping_verified') is not True:
                    event = {'sample_index': row.get('sample_index'), 'clock': row.get('wall_utc'),
                             'owner': owner, 'known_memory_bytes': used, 'has_kfd_queue': has_queue, 'memory_growth': growth}
                    self.active_peer_events.append(event)
                    raise RuntimeError('active or unresolved selected-GPU peer; cancel only owned server')
                self.enumeration_baseline.setdefault(key, used)
                self.allowed_enumeration.append({'sample_index': row.get('sample_index'), 'pid': owner.get('pid'),
                                                 'gpu': owner.get('gpu'), 'start_ticks': process.get('start_ticks'), 'bytes': used})
            if self.preflight:
                self.consecutive_idle_samples = self.consecutive_idle_samples + 1 if idle else 0


def http(path, body, guard, timeout=300):
    """Profile endpoints return text; poll telemetry while native HTTP is pending."""
    results = queue.Queue()
    def request():
        try:
            req = urllib.request.Request('http://127.0.0.1:{}{}'.format(PORT, path),
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                results.put((response.status, response.read().decode(), None))
        except Exception as exc:
            results.put((None, None, exc))
    threading.Thread(target=request, daemon=True).start()
    while True:
        guard.poll()
        try:
            status, text, error = results.get(timeout=.2)
            if error:
                raise error
            return {'status': status, 'text': text}
        except queue.Empty:
            pass


def server_command(gpus, arm, pidfile):
    suffix = 'base' if arm == 'before' else 'accepted'
    env = dict(safe.ENV, HIP_VISIBLE_DEVICES=','.join(map(str, gpus)), PYTHONPATH='/ci/sglang/python',
               SGLANG_PROFILE_V2='0', SGLANG_PROFILE_RECORD_SHAPES='1',
               AITER_CONFIG_GEMM_A8W8_BPRESHUFFLE=CONTAINER_ROOT + '/configs/ck_' + suffix + '.csv',
               AITER_CONFIG_GEMM_BF16=CONTAINER_ROOT + '/configs/tgemm_' + suffix + '.csv')
    command = ['-m', 'sglang.launch_server', '--host', '127.0.0.1', '--port', str(PORT),
        '--served-model-name', 'full-tgemm-profile', '--model-path', safe.MODEL, '--tp-size', '1',
        '--reasoning-parser', 'qwen3', '--tool-call-parser', 'qwen3_coder', '--enable-multimodal',
        '--trust-remote-code', '--chunked-prefill-size', '32768', '--mem-fraction-static', '0.9',
        '--max-prefill-tokens', '32768', '--max-running-requests', '128', '--cuda-graph-max-bs-decode', '128',
        '--attention-backend', 'aiter', '--mm-attention-backend', 'aiter_attn', '--enable-strict-thinking',
        '--kv-cache-dtype', 'fp8_e4m3', '--disable-radix-cache', '--watchdog-timeout', '1200',
        '--random-seed', '42', '--max-total-tokens', '262144']
    return safe.docker_args(env) + ['python3', '-u', '-c', safe.SERVER_BOOT, pidfile, json.dumps(command)], env


def tokenize_input(args):
    common = args.root / 'common'
    common.mkdir(exist_ok=False)
    container_common = CONTAINER_ROOT + '/common'
    safe.command(safe.docker_args() + ['python3', '-c', 'from pathlib import Path; Path(' + repr(container_common) + ').mkdir(exist_ok=False)'])
    program = r'''
import hashlib,json,pathlib
from transformers import AutoTokenizer
root=pathlib.Path('/full_tgemm_tp1/common'); model=pathlib.Path('/models/Qwen3.5-35B-A3B-PTPC-FP8')
tokenizer=AutoTokenizer.from_pretrained(str(model),trust_remote_code=True,local_files_only=True)
paragraph='Matrix multiplication combines rows and columns to form an output. Numerical scaling keeps low precision values in range. Careful measurements distinguish model latency from individual kernel time. '
suffix=tokenizer.encode('\nSummarize the passage briefly in English.\nAnswer:',add_special_tokens=False)
body=tokenizer.encode(paragraph*2000,add_special_tokens=False)
ids=body[:8000-len(suffix)]+suffix
assert len(ids)==8000 and all(isinstance(x,int) for x in ids)
payload=json.dumps(ids,separators=(',',':'));(root/'input_ids.json').write_text(payload+'\n')
files={name:hashlib.sha256((model/name).read_bytes()).hexdigest() for name in ['config.json','tokenizer.json','tokenizer_config.json','model.safetensors.index.json']}
config=json.loads((model/'config.json').read_text())
metadata={'input_tokens':len(ids),'input_ids_sha256':hashlib.sha256(payload.encode()).hexdigest(),'tokenizer_class':type(tokenizer).__name__,'model_metadata_sha256':files,'quant_method':config.get('quantization_config',{}).get('quant_method'),'main_shards':len(list(model.glob('*.safetensors'))),'source':'CPU tokenizer fixed repeated real English text plus instruction; same input_ids reused for both arms'}
(root/'input_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
'''
    safe.command(safe.docker_args({'HIP_VISIBLE_DEVICES': '', 'ROCR_VISIBLE_DEVICES': ''}) + ['python3', '-c', program], timeout=120)
    for name in ['input_ids.json', 'input_manifest.json']:
        safe.command(['docker', 'cp', safe.OWN_CONTAINER + ':' + container_common + '/' + name, str(common / name)])
    metadata = json.loads((common / 'input_manifest.json').read_text())
    assert metadata['model_metadata_sha256']['config.json'] == safe.MODEL_CONFIG_SHA and metadata['quant_method'] == 'quark' and metadata['main_shards'] == 14
    return json.loads((common / 'input_ids.json').read_text()), metadata


def capture_arm(args, arm, ids, input_manifest):
    output = args.root / 'results' / ('profile_' + arm)
    output.mkdir(parents=True, exist_ok=False)
    container_output = CONTAINER_ROOT + '/results/profile_' + arm
    pidfile = container_output + '/server_process.json'
    guard = ResourceGuard(output / 'telemetry.jsonl', args.gpus)
    result = {'side': arm, 'scope': 'New2026-11-16 TP1 prototype full-model operator profiling of frozen851 source pair; separate from TP4 performance, not finalPRhead or CIscore', 'tensor_parallel_size': 1,
              'input_manifest': input_manifest, 'physical_gpus': args.gpus, 'rank_to_physical_gpu': dict(enumerate(args.gpus)),
              'profiling_workload': {'input_tokens': 8000, 'output_tokens': 64, 'concurrency': 1, 'temperature': 0.0,
                                      'ignore_eos': True, 'warmup_requests': 2, 'radix_cache': False}}
    telemetry = server = None
    try:
        result['container'] = safe.require_sleep_container()
        safe.command(safe.docker_args() + ['python3', '-c', 'from pathlib import Path; Path(' + repr(container_output + '/traces') + ').mkdir(parents=True,exist_ok=False)'])
        telemetry = subprocess.Popen(['sudo', '-n', sys.executable, str(args.telemetry_script), '--output', str(guard.path),
                  '--gpus', ','.join(map(str, args.gpus)), '--container-id', result['container']['id'], '--interval', '1'],
                  stdout=(output / 'telemetry.stdout.log').open('w'), stderr=(output / 'telemetry.stderr.log').open('w'))
        deadline = time.monotonic() + 45
        while guard.consecutive_idle_samples < 2:
            guard.poll()
            if telemetry.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('two verified preflight samples unavailable')
            time.sleep(.2)
        result['preflight_samples'] = guard.samples[-2:]
        result['telemetry_process_identity'] = safe.identify_telemetry(args, output)
        assert result['telemetry_process_identity'] is not None
        result['source'] = json.loads(safe.command(safe.docker_args() + ['python3', CONTAINER_ROOT + '/scripts/setup_arm_tp1.py', arm]))
        safe.write_json(output / 'source.json', result['source'])
        guard.preflight = False
        command, env = server_command(args.gpus, arm, pidfile)
        result.update(server_command=command, environment=env)
        server = subprocess.Popen(command, stdout=(output / 'server.log').open('w'), stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            guard.poll()
            if server.poll() is not None or telemetry.poll() is not None:
                raise RuntimeError('owned server/telemetry exited before readiness')
            try:
                info = json.loads(http('/server_info', None, guard, timeout=2)['text'])
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(1)
        else:
            raise RuntimeError('server readiness timeout')
        result['server_info'] = info
        safe.write_json(output / 'server_info.json', info)
        assert safe.find_field(info, 'random_seed') == 42 and safe.find_field(info, 'tp_size') == 1
        assert safe.find_field(info, 'max_total_tokens') == 262144 and safe.find_field(info, 'max_total_num_tokens') == 262144
        assert safe.find_field(info, 'disable_radix_cache') is True
        runtime_program = "import importlib.metadata as m,json,subprocess; print(json.dumps({'sglang_head':subprocess.check_output(['git','rev-parse','HEAD'],universal_newlines=True).strip(),'packages':{n:m.version(n) for n in ['sglang','torch','amd-aiter','triton','pyhip']}}))"
        result['runtime'] = json.loads(safe.command(safe.docker_args() + ['python3', '-c', runtime_program]))
        safe.write_json(output / 'runtime.json', result['runtime'])
        safe.write_json(output / 'input_manifest.json', input_manifest)
        payload = {'input_ids': ids, 'sampling_params': {'temperature': 0.0, 'max_new_tokens': 64, 'ignore_eos': True}, 'stream': False}
        safe.write_json(output / 'request.json', payload)
        result['warmup'] = [json.loads(http('/generate', payload, guard)['text']) for _ in range(2)]
        result['flush'] = http('/flush_cache?timeout=60', {}, guard)
        request = {'output_dir': container_output + '/traces', 'profile_prefix': 'full-tgemm-' + arm,
                   'profile_id': arm, 'activities': ['CPU', 'GPU'], 'record_shapes': True,
                   'with_stack': False, 'profile_by_stage': False, 'merge_profiles': False}
        result['profile_request'] = request
        safe.write_json(output / 'profile_request.json', request)
        result['start_profile'] = http('/start_profile', request, guard)
        result['capture_start_epoch'] = time.time()
        result['response'] = json.loads(http('/generate', payload, guard)['text'])
        safe.write_json(output / 'response.json', result['response'])
        result['capture_end_epoch'] = time.time()
        meta = result['response'].get('meta_info') or {}
        result['actual_request_dimensions'] = {'prompt_tokens': meta.get('prompt_tokens'), 'completion_tokens': meta.get('completion_tokens')}
        safe.write_json(output / 'actual_dims.json', result['actual_request_dimensions'])
        assert meta.get('prompt_tokens') == 8000 and meta.get('completion_tokens') == 64
        result['stop_profile'] = http('/stop_profile', {}, guard)
        safe.command(['docker', 'cp', safe.OWN_CONTAINER + ':' + container_output + '/traces', str(output / 'traces')], timeout=180)
        traces = sorted((output / 'traces').glob('*.trace.json.gz'))
        assert {int(re.search(r'-TP-(\d+)\.trace', p.name)[1]) for p in traces} == {0}
        result['original_traces'] = []
        for trace in traces:
            with gzip.open(trace, 'rt') as stream:
                original = json.load(stream)
            assert original.get('traceEvents')
            result['original_traces'].append({'path': str(trace), 'bytes': trace.stat().st_size, 'sha256': sha(trace),
                'trace_event_count': len(original['traceEvents']), 'baseTimeNanoseconds': original.get('baseTimeNanoseconds'),
                'kernel_event_count': sum(event.get('cat') == 'kernel' for event in original['traceEvents'])})
        result['status'] = 'captured_complete_originals'
    except BaseException as exc:
        result.update(status='failed', error='{}: {}'.format(type(exc).__name__, exc))
        raise
    finally:
        if server is not None:
            try:
                result['server_cleanup'] = json.loads(safe.command(safe.docker_args() + ['python3', '-c', safe.SERVER_STOP, pidfile], timeout=20))
                server.wait(timeout=15)
                # Consume pending loaded samples, then verify driver release before next startup.
                guard.poll()
                guard.preflight = True
                guard.release_mode = True
                guard.consecutive_idle_samples = 0
                deadline = time.monotonic() + 45
                while guard.consecutive_idle_samples < 2:
                    guard.poll()
                    if time.monotonic() > deadline:
                        raise RuntimeError('selected GPU release not verified')
                    time.sleep(.2)
                result['released_samples'] = guard.samples[-2:]
            except Exception as exc:
                result['cleanup_error'] = str(exc)
                result['status'] = 'failed'
        if telemetry is not None:
            try:
                result['telemetry_cleanup'] = safe.stop_telemetry(args, output, result.get('telemetry_process_identity'))
                telemetry.wait(timeout=5)
            except Exception as exc:
                result['telemetry_cleanup_error'] = str(exc)
                result['status'] = 'failed'
        if not (output / 'traces').exists():
            try:
                safe.command(['docker', 'cp', safe.OWN_CONTAINER + ':' + container_output + '/traces', str(output / 'traces')], timeout=180)
            except Exception as exc:
                result['partial_trace_copy_error'] = str(exc)
        result['resource_guard'] = {'samples': len(guard.samples), 'incomplete_owner_samples': sum(s['owners'].get('complete') is not True for s in guard.samples),
            'allowed_enumeration': guard.allowed_enumeration, 'active_peer_events': guard.active_peer_events}
        result['artifact_sha256'] = {p.name: sha(p) for p in output.glob('*.json')}
        result['scripts_sha256'] = {'capture_full_profiles_tp1.py': sha(Path(__file__)), 'profile_support_tp1.py': sha(Path(safe.__file__)),
                                    'telemetry.py': sha(args.telemetry_script)}
        safe.write_json(output / 'capture_manifest.json', result)
    if result['status'] != 'captured_complete_originals':
        raise RuntimeError('capture/cleanup failed; retained capture_manifest and raw traces')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=HOST_ROOT)
    parser.add_argument('--gpus', default='6')
    parser.add_argument('--telemetry-script', type=Path)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    args.gpus = [int(x) for x in args.gpus.split(',')]
    if len(set(args.gpus)) != 1 or any(x < 0 or x > 7 for x in args.gpus):
        parser.error('one physical GPU required')
    args.telemetry_script = args.telemetry_script or args.root / 'scripts/telemetry.py'
    if args.plan_only:
        print(json.dumps({'sides': ['before', 'after'], 'gpus': args.gpus, 'input_tokens': 8000, 'output_tokens': 64,
            'warmup_each': 2, 'full_original_ranks_each': [0], 'performance_matrix': False,
            'server_plans': {arm: server_command(args.gpus, arm, CONTAINER_ROOT + '/results/profile_' + arm + '/server_process.json') for arm in ['before', 'after']}}))
        return
    safe.require_sleep_container()
    ids, manifest = tokenize_input(args)
    results = [capture_arm(args, arm, ids, manifest) for arm in ['before', 'after']]
    safe.write_json(args.root / 'results/full_profile_manifest.json', {'input_manifest': manifest, 'captures': results,
        'original_trace_bytes_preserved': True, 'source_scope': 'frozen851 prototype, not final PR head',
        'profiling_workload_is_separate_from_performance_scores': True, 'tensor_parallel_size': 1,
        'evidence_scope': 'TP1 paired operator profiles, separate from TP4 performance and TP4 before trace appendix'})


if __name__ == '__main__':
    main()
