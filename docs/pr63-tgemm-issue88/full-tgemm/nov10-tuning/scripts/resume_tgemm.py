import json
import runpy
import sys
from pathlib import Path

import pandas as pd

ROOT = Path('/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110')
sys.path.insert(0, '/opt/aiter/gradlib/gradlib')
from GemmTuner import Gemm

checkpoint = json.loads((ROOT / 'configs/fp8_fast_checkpoint.json').read_text())
original_fast = Gemm.run_fast_solutions
original_best = Gemm.run_best_solutions
completed = []


def resume_fast(self):
    key = ','.join(map(str, [self.m, self.n, self.k, self.indtype]))
    if key in checkpoint:
        self.hipb_gtimedf = pd.DataFrame(checkpoint[key])
        print('Reusing 20 completed fast-search candidates:', key, flush=True)
    else:
        original_fast(self)


def save_best(self):
    result = original_best(self)
    completed.append(dict(M=int(self.m), N=int(self.n), K=int(self.k),
                          dtype=str(self.indtype), bias=self.has_bias,
                          bpreshuffle=self.is_shuffle, results=result))
    (ROOT / 'results/tgemm_validated_checkpoint.json').write_text(
        json.dumps(completed, indent=2, default=str))
    return result


if __name__ == '__main__':
    Gemm.run_fast_solutions = resume_fast
    Gemm.run_best_solutions = save_best
    sys.argv = [
        '/opt/aiter/csrc/gemm_a16w16/gemm_a16w16_tune.py',
        '-i', str(ROOT / 'configs/tgemm_shapes.csv'),
        '-o', str(ROOT / 'configs/tgemm_tuned.csv'),
        '--profile_file', str(ROOT / 'results/tgemm_candidates_resumed.csv'),
        '--libtype', 'hipblaslt,asm,torch',
        '--with-hipblaslt',
        '--mp', '2',
        '--timeout', '180',
        '--errRatio', '0.01',
    ]
    runpy.run_path(sys.argv[0], run_name='__main__')
