import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path('/full_tgemm_tp1')
TARGET = Path('/ci/sglang')
FILES = [
    'python/sglang/srt/layers/quantization/unquant.py',
    'python/sglang/srt/layers/quantization/fp8_utils.py',
    'python/sglang/srt/layers/quantization/compressed_tensors/schemes/compressed_tensors_w8a8_fp8.py',
]

arm = sys.argv[1]
assert arm in ('before', 'after', 'bf16_only', 'fp8_prefill_only')
manifest = json.loads((ROOT / 'review/MANIFEST.json').read_text())
hashes = {}
for name in FILES:
    source_arm = 'after' if arm == 'after' or (arm == 'bf16_only' and name.endswith('/unquant.py')) else 'before'
    source = ROOT / 'sources' / source_arm / name
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest['files'][source_arm + '/' + name]
    target = TARGET / name
    shutil.copyfile(source, target)
    for cache in (target.parent / '__pycache__').glob(target.stem + '.*.pyc'):
        cache.unlink()
    hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
if arm == 'fp8_prefill_only':
    import subprocess
    subprocess.run(['git', 'apply', str(ROOT / 'review/dispatch/fp8_prefill_only.patch')], cwd=TARGET, check=True)
    hashes[FILES[1]] = hashlib.sha256((TARGET / FILES[1]).read_bytes()).hexdigest()
print(json.dumps({'arm': arm, 'source_sha256': hashes}), flush=True)
