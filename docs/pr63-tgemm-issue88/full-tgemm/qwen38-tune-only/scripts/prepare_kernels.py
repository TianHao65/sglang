import json
import os
import subprocess
from pathlib import Path

os.environ.pop('ROCR_VISIBLE_DEVICES', None)
import torch
import aiter
import aiter.jit.core as core
from aiter.ops.shuffle import shuffle_weight
from aiter.ops.gemm_op_a8w8 import gemm_a8w8_bpreshuffle_ck, gemm_a8w8_bpreshuffle_cktile

assert subprocess.check_output(['git', '-C', '/opt/aiter', 'rev-parse', 'HEAD'], text=True).strip() == '514c166e9abad59acde74309923c2d923a89eee0'
assert not subprocess.check_output(['git', '-C', '/opt/aiter', 'status', '--short'], text=True)
core.AITER_REBUILD = 1
with torch.inference_mode():
    x = torch.ones(4, 3072, device='cuda', dtype=torch.bfloat16).to(aiter.dtypes.fp8)
    w = shuffle_weight(torch.ones(2560, 3072, device='cuda', dtype=torch.bfloat16).to(aiter.dtypes.fp8), (16, 16))
    sx = torch.ones(4, 1, device='cuda')
    sw = torch.ones(2560, 1, device='cuda')
    out = torch.empty(4, 2560, device='cuda', dtype=torch.bfloat16)
    for fn in [gemm_a8w8_bpreshuffle_ck, gemm_a8w8_bpreshuffle_cktile]:
        fn(x, w, sx, sw, out, 0)
        torch.cuda.synchronize()
        assert torch.all(out == 3072), fn.__name__
    aiter.hipb_create_extension()
print('Prepared CK, CKTile and hipBLASLt from the same AITER source.', flush=True)
