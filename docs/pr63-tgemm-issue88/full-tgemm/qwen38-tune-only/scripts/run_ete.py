import datetime
import fcntl
import hashlib
import json
import math
import re
import shlex
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path('/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110')
CROOT = Path('/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110')
MODEL = '/models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16'
CONTAINERS = {'before': 'hatian-pr63-ete-before-20261110', 'after': 'hatian-pr63-ete-after-20261110'}
PLAN = [('before', 1), ('after', 1), ('after', 2), ('before', 2)]
STATE = {'status': 'running', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'active': None, 'completed': []}
STATE['completed'] = [json.loads(p.read_text()) for p in sorted((ROOT / 'results').glob('*/OUTCOME.json'))]


def save():
    STATE['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p = ROOT / 'results/STATE.tmp'
    p.write_text(json.dumps(STATE, indent=2))
    p.replace(ROOT / 'results/STATE.json')


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def snapshot():
    cards = json.loads(subprocess.check_output(['sudo', '-n', 'rocm-smi', '--showuse', '--showmeminfo', 'vram', '--json'], universal_newlines=True))
    mapping = subprocess.check_output(['sudo', '-n', 'rocm-smi', '--showpidgpus'], universal_newlines=True)
    owners = []
    lines = mapping.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'PID (\d+) is using .*:', line)
        if m and i + 1 < len(lines):
            for gpu in lines[i + 1].split():
                if gpu.isdigit():
                    owners.append({'pid': int(m[1]), 'gpu': int(gpu)})
    return {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'cards': cards, 'owners': owners}


def idle(s):
    return all(int(s['cards'][f'card{i}']['GPU use (%)']) == 0
               and int(s['cards'][f'card{i}']['VRAM Total Used Memory (B)']) < 1024**3
               and not any(p['gpu'] == i for p in s['owners']) for i in [2, 3])


def foreign(container):
    s = snapshot()
    owned = {int(line.split()[0]) for line in subprocess.check_output(
        ['docker', 'top', container, '-eo', 'pid'], universal_newlines=True).splitlines()[1:] if line.strip()}
    return [p for p in s['owners'] if p['gpu'] in [2, 3] and p['pid'] not in owned]


def request(path, body=None, timeout=15):
    req = urllib.request.Request('http://127.0.0.1:19838' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
        return json.loads(data) if data else {'status': response.status}


def validate(info):
    a = info.get('server_args', info)
    expected = {'model_path': MODEL, 'tp_size': 2, 'disable_radix_cache': False,
        'max_total_tokens': 262144, 'random_seed': 42, 'speculative_algorithm': 'EAGLE',
        'speculative_num_steps': 3, 'speculative_num_draft_tokens': 4,
        'attention_backend': 'aiter', 'linear_attn_prefill_backend': 'aiter',
        'mm_feature_transport': 'cuda_ipc', 'mamba_radix_cache_strategy': 'extra_buffer'}
    for k, v in expected.items():
        assert a.get(k) == v, (k, a.get(k), v)
    assert info['max_total_num_tokens'] == 262144
    return {k: a.get(k) for k in [*expected, 'mem_fraction_static', 'max_running_requests',
                                'kv_cache_dtype', 'speculative_attention_mode']}


def quality(d):
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': 'What is 17 plus 25? Answer with only the number.'}],
            'temperature': 0, 'top_p': 1, 'max_tokens': 128,
            'chat_template_kwargs': {'enable_thinking': False}}
    response = request('/v1/chat/completions', body, timeout=300)
    (d / 'quality.json').write_text(json.dumps({'request': body, 'response': response}, indent=2))
    assert '42' in response['choices'][0]['message']['content'], response


def benchmark(container, d, phase):
    dest = d / phase
    dest.mkdir()
    script = 'client_discard.sh' if phase == 'discard' else 'client.sh'
    cmd = ['docker', 'exec', '-w', str(CROOT / dest.relative_to(ROOT)),
           '-e', 'PYTHONUNBUFFERED=1', '-e', 'HF_HUB_OFFLINE=1', '-e', 'TRANSFORMERS_OFFLINE=1',
           container, 'bash', str(CROOT / 'scripts' / script)]
    with (dest / 'client.log').open('w') as log:
        process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 1800
            while process.poll() is None:
                if time.monotonic() > deadline:
                    raise TimeoutError('Client timeout')
                intruders = foreign(container)
                if intruders:
                    raise RuntimeError(f'Foreign GPU ownership overlap: {intruders}')
                time.sleep(10)
            assert process.returncode == 0, process.returncode
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
    result = json.loads((dest / 'concurrency_benchmark_conc1_iter1.json').read_text())
    count = 16 if phase == 'discard' else 128
    assert result['completed'] == count and not any(result['errors'])
    assert result['max_concurrency'] == 1 and result['mean_expect_input_len'] == 11000
    for key in ['mean_ttft_ms', 'mean_tpot_ms', 'mean_e2el_ms', 'output_throughput']:
        assert math.isfinite(result[key]) and result[key] > 0
    commands = re.findall(r'Command: (.*)', (dest / 'client.log').read_text())
    assert commands
    argv = shlex.split(commands[-1])
    pairs = {argv[i]: argv[i + 1] for i in range(len(argv) - 1)
             if argv[i].startswith('--') and not argv[i + 1].startswith('--')}
    for key, value in {'--random-input-len': '11000', '--random-output-len': '350',
                       '--custom-output-len': '350', '--random-prefix-len': '3849',
                       '--max-concurrency': '1', '--num-prompts': str(count), '--seed': '1'}.items():
        assert pairs.get(key) == value, (key, pairs.get(key), value)
    (dest / 'ACTUAL_COMMAND.json').write_text(json.dumps({'argv': argv, 'values': pairs,
        'sigma': 4, 'prefix_ratio': 0.35, 'mtp': True, 'radix': True}, indent=2))
    metrics = {k: result.get(k) for k in ['completed', 'mean_ttft_ms', 'mean_tpot_ms',
        'mean_e2el_ms', 'output_throughput', 'request_throughput', 'mean_expect_input_len',
        'mean_req_input_len', 'mean_input_len', 'mean_output_len']}
    for key in ['input_lens', 'output_lens']:
        metrics[key + '_sha256'] = hashlib.sha256(json.dumps(result[key]).encode()).hexdigest()
    return metrics


lock = open(ROOT / 'runtime/controller.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
save()
try:
    for arm, cycle in PLAN:
        if any(d['arm'] == arm and d['cycle'] == cycle for d in STATE['completed']):
            continue
        container = CONTAINERS[arm]
        STATE['active'] = {'arm': arm, 'cycle': cycle, 'stage': 'waiting_resources'}
        save()
        deadline = time.monotonic() + 1800
        while True:
            s = snapshot()
            if idle(s):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('GPU 2/3 remained occupied')
            time.sleep(15)
        d = ROOT / 'results' / f'{arm}_r{cycle}'
        attempt = 1
        while d.exists():
            attempt += 1
            d = ROOT / 'results' / f'{arm}_r{cycle}_attempt{attempt}'
        d.mkdir()
        (d / 'resources_before.json').write_text(json.dumps(s, indent=2))
        run(['docker', 'start', container], stdout=subprocess.DEVNULL)
        STATE['active']['stage'] = 'startup'
        save()
        with (d / 'server.log').open('w') as log:
            server = subprocess.Popen(['docker', 'exec', container, 'bash', str(CROOT / 'scripts' / f'server_{arm}.sh')], stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 1800
                while True:
                    if server.poll() is not None:
                        raise RuntimeError(f'Server exited {server.returncode}; {d}/server.log')
                    if foreign(container):
                        raise RuntimeError('Foreign GPU owner appeared during startup')
                    try:
                        info = request('/server_info')
                        request('/health')
                        break
                    except Exception:
                        if time.monotonic() > deadline:
                            raise TimeoutError('Readiness timeout')
                        time.sleep(5)
                (d / 'server_info_before.json').write_text(json.dumps(info, indent=2))
                effective = validate(info)
                STATE['active']['stage'] = 'quality'
                save()
                quality(d)
                STATE['active']['stage'] = 'discard'
                save()
                benchmark(container, d, 'discard')
                STATE['active']['stage'] = 'measured'
                save()
                metrics = benchmark(container, d, 'measured')
                (d / 'server_info_after.json').write_text(json.dumps(request('/server_info'), indent=2))
            finally:
                STATE['active']['stage'] = 'cleanup'
                save()
                run(['docker', 'stop', '-t', '5', container], stdout=subprocess.DEVNULL)
                server.wait(timeout=60)
        for _ in range(20):
            s = snapshot()
            if idle(s):
                break
            time.sleep(3)
        else:
            raise RuntimeError('GPU resources not released')
        (d / 'resources_after.json').write_text(json.dumps(s, indent=2))
        outcome = {'arm': arm, 'cycle': cycle, 'effective': effective, 'metrics': metrics}
        (d / 'OUTCOME.json').write_text(json.dumps(outcome, indent=2))
        STATE['completed'].append(outcome)
        STATE['active'] = None
        save()
        print(json.dumps(outcome), flush=True)
    STATE['status'] = 'complete'
    save()
except BaseException as e:
    STATE['status'] = 'failed'
    STATE['error'] = repr(e)
    save()
    raise
finally:
    for container in CONTAINERS.values():
        subprocess.run(['docker', 'stop', '-t', '5', container], stdout=subprocess.DEVNULL)
    (ROOT / 'results/final_resources.json').write_text(json.dumps(snapshot(), indent=2))
    fcntl.flock(lock, fcntl.LOCK_UN)
