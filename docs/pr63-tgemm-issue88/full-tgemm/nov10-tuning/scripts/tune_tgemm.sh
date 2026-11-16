#!/usr/bin/env bash
set -euo pipefail
unset ROCR_VISIBLE_DEVICES
export HIP_VISIBLE_DEVICES=1
export CUDA_VISIBLE_DEVICES=1
cd /opt/aiter
python3 csrc/gemm_a16w16/gemm_a16w16_tune.py \
  -i /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/tgemm_shapes.csv \
  -o /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/tgemm_tuned.csv \
  --profile_file /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/results/tgemm_candidates.csv \
  --libtype hipblaslt,asm,torch \
  --with-hipblaslt \
  --mp 1 \
  --errRatio 0.01
