#!/usr/bin/env bash
set -euo pipefail
unset ROCR_VISIBLE_DEVICES
export HIP_VISIBLE_DEVICES=2
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/sources/tgemm/python
export SGLANG_USE_AITER=1
export SGLANG_ROCM_USE_AITER_LINEAR_FP8HIPB=1
export SGLANG_ROCM_USE_AITER_LINEAR_SHUFFLE=1
export AITER_LOG_TUNED_CONFIG=1
export AITER_CONFIG_GEMM_A8W8_BPRESHUFFLE=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/ck_accepted.csv
export AITER_CONFIG_GEMM_BF16=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/configs/tgemm_accepted.csv
export AITER_REBUILD=1
python3 /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/scripts/validate_sglang.py
