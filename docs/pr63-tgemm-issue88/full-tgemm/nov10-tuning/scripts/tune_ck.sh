#!/usr/bin/env bash
set -euo pipefail
cd /opt/aiter
python3 csrc/ck_gemm_a8w8_bpreshuffle/gemm_a8w8_bpreshuffle_tune.py \
  -i /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/ck_decode_shapes.csv \
  -o /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/ck_decode_tuned.csv \
  --profile_file /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/results/ck_candidates.csv \
  --libtype ck \
  --splitK \
  --mp 1 \
  --warmup 10 \
  --iters 101 \
  --errRatio 0.01
