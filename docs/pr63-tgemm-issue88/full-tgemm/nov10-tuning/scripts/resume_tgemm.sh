#!/usr/bin/env bash
set -euo pipefail
unset ROCR_VISIBLE_DEVICES
export HIP_VISIBLE_DEVICES=1,3
export CUDA_VISIBLE_DEVICES=1,3
cd /opt/aiter
python3 /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/scripts/resume_tgemm.py
