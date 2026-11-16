"""Owned-process helpers reused verbatim from frozen Nov16 runner v2; no benchmark flow."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

OWN_CONTAINER = 'hatian-pr63-full-ci-host52-20261112'

MODEL = '/models/Qwen3.5-35B-A3B-PTPC-FP8'

MODEL_CONFIG_SHA = '187335f1c79ce1d340be9f7a0b3dea86710a8bba77f996d0bc3066814dbf97fb'

ENV = {
    'PYTHONUNBUFFERED': '1', 'HF_HUB_OFFLINE': '1', 'AITER_USE_SYSTEM_TRITON': '1',
    'SGLANG_DISABLE_CUDNN_CHECK': '1', 'SGLANG_USE_CUDA_IPC_TRANSPORT': '1',
    'SGLANG_VLM_CACHE_SIZE_MB': '8192', 'SGLANG_USE_AITER': '1',
    'SGLANG_ROCM_USE_AITER_LINEAR_SHUFFLE': '1', 'SGLANG_ROCM_USE_AITER_LINEAR_FP8HIPB': '1',
    'SGLANG_USE_AITER_NEW_CA': 'false', 'SGLANG_USE_IPC_POOL_HANDLE_CACHE': '1',
    'AITER_QUICK_REDUCE_QUANTIZATION': 'INT6', 'USE_AITER_COMM': '1',
    'TVM_FFI_DISABLE_TORCH_C_DLPACK': '1',
}

SERVER_BOOT = r'''
import json,os,pathlib,sys,time
path=pathlib.Path(sys.argv[1]); command=json.loads(sys.argv[2])
if os.getpgrp()!=os.getpid(): os.setsid()
stat=pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
with path.open('x') as f: json.dump({'pid':os.getpid(),'pgid':os.getpgrp(),'start_ticks':stat[19]},f)
os.execv(sys.executable,[sys.executable]+command)
'''

SERVER_STOP = r'''
import json,os,pathlib,signal,sys,time
p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text()) if p.exists() else None
if d is None: print(json.dumps({'no_pid_file':True})); sys.exit(0)
proc=pathlib.Path('/proc')/str(d['pid'])
if proc.exists():
 stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
 if stat[19]!=d['start_ticks'] or os.getpgid(d['pid'])!=d['pgid']: raise RuntimeError('server PID identity changed')
for sig in [signal.SIGTERM,signal.SIGKILL]:
 try: os.killpg(d['pgid'],sig)
 except ProcessLookupError: break
 if sig==signal.SIGTERM: time.sleep(8)
print(json.dumps({'target_server_group':d,'cleanup_signals_sent':True}))
'''

TELEMETRY_CONTROL = r'''
import json,os,pathlib,select,signal,sys
spec=json.loads(sys.argv[1]); script=pathlib.Path(spec['script']).resolve(); output=pathlib.Path(spec['output']).resolve()
def identity(pid):
 p=pathlib.Path('/proc')/str(pid)
 try:
  if p.stat().st_uid!=0: return None
  raw_stat=(p/'stat').read_text()
  if not raw_stat[raw_stat.find('(')+1:raw_stat.rfind(')')].startswith('python'): return None
  stat=raw_stat.rsplit(')',1)[1].split()
  argv=(p/'cmdline').read_bytes().split(b'\0'); argv=[x.decode() for x in argv if x]
  if len(argv)<2 or pathlib.Path(argv[1]).resolve()!=script: return None
  if '--output' not in argv or pathlib.Path(argv[argv.index('--output')+1]).resolve()!=output: return None
  return {'pid':pid,'uid':0,'state':stat[0],'ppid':int(stat[1]),'start_ticks':stat[19],'script':str(script),'output':str(output)}
 except (OSError,ValueError,IndexError,UnicodeError): return None
if spec['action']=='identify':
 pids=[spec['pid']] if spec.get('pid') else [int(p.name) for p in pathlib.Path('/proc').iterdir() if p.name.isdigit()]
 candidates=[x for x in (identity(pid) for pid in pids) if x]
 if len(candidates)>1: raise RuntimeError('multiple exact telemetry identities; refuse signalling')
 print(json.dumps({'identity':candidates[0] if candidates else None})); sys.exit(0)
expected=spec.get('identity')
if not expected: raise RuntimeError('verified telemetry identity required')
current=identity(expected['pid'])
if current is None:
 proc=pathlib.Path('/proc')/str(expected['pid'])
 if not proc.exists(): print(json.dumps({'already_gone':True}));sys.exit(0)
 stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
 if proc.stat().st_uid==0 and stat[19]==expected['start_ticks'] and stat[0].upper() in ('Z','X'): print(json.dumps({'already_nonlive':True}));sys.exit(0)
 raise RuntimeError('telemetry target identity no longer matches; refuse signalling')
if current['start_ticks']!=expected['start_ticks']: raise RuntimeError('telemetry PID generation changed')
if current['state'].upper() in ('Z','X'): print(json.dumps({'already_nonlive':True,'identity':current}));sys.exit(0)
if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'): raise RuntimeError('pidfd API unavailable; refuse race-prone PID signalling')
try: fd=os.pidfd_open(current['pid'],0)
except ProcessLookupError: print(json.dumps({'already_gone':True}));sys.exit(0)
try:
 verified=identity(current['pid'])
 if verified is None or verified['start_ticks']!=expected['start_ticks']: raise RuntimeError('telemetry generation changed after pidfd open')
 signals=[]
 for sig,seconds in [(signal.SIGTERM,6),(signal.SIGKILL,2)]:
  try: signal.pidfd_send_signal(fd,sig,None,0)
  except ProcessLookupError: break
  signals.append(int(sig))
  if select.select([fd],[],[],seconds)[0]: break
 else: raise RuntimeError('verified telemetry Python did not exit')
 print(json.dumps({'identity':verified,'pidfd_signals':signals,'target_exited':True}))
finally: os.close(fd)
'''

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def command(argv, timeout=30):
    return subprocess.check_output(argv, stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)

def docker_args(env=None, workdir='/ci/sglang'):
    argv = ['docker', 'exec', '-w', workdir]
    for name, value in (env or {}).items():
        argv.extend(['-e', '{}={}'.format(name, value)])
    return argv + [OWN_CONTAINER]

def require_sleep_container():
    data = json.loads(command(['docker', 'inspect', OWN_CONTAINER]))[0]
    if not data['State']['Running']:
        raise RuntimeError('root must start the existing prepared sleep container before this runner')
    rows = command(['docker', 'top', OWN_CONTAINER, '-eo', 'pid,comm']).splitlines()[1:]
    if any(row.split()[-1] not in ('sleep', 'sh', 'bash') for row in rows):
        raise RuntimeError('prepared container has non-sleep processes; do not reset its source')
    return {'id': data['Id'], 'image': data['Image'], 'name': OWN_CONTAINER}

def identify_telemetry(args, output):
    candidate_pid = None
    path = output / 'telemetry.jsonl'
    if path.exists():
        try:
            first = json.loads(path.open('rb').readline())
            if first.get('event') == 'start':
                candidate_pid = first.get('pid')
        except (OSError, ValueError):
            pass
    spec = {'action': 'identify', 'pid': candidate_pid, 'script': str(args.telemetry_script),
            'output': str(path)}
    return json.loads(command(['sudo', '-n', sys.executable, '-c', TELEMETRY_CONTROL, json.dumps(spec)], timeout=10))['identity']

def stop_telemetry(args, output, identity):
    identity = identity or identify_telemetry(args, output)
    if identity is None:
        return {'no_exact_live_helper_found': True}
    spec = {'action': 'terminate', 'identity': identity, 'script': str(args.telemetry_script),
            'output': str(output / 'telemetry.jsonl')}
    return json.loads(command(['sudo', '-n', sys.executable, '-c', TELEMETRY_CONTROL, json.dumps(spec)], timeout=12))

def find_field(value, name):
    """Handle flattened args as well as nested internal_states/model_worker_info."""
    if isinstance(value, dict):
        if value.get(name) is not None:
            return value[name]
        for child in value.values():
            found = find_field(child, name)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_field(child, name)
            if found is not None:
                return found
    return None
