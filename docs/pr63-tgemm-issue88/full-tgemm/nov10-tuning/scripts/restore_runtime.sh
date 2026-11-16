#!/usr/bin/env bash
set -euo pipefail
cp /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/review/hipbsolgemm_original.cu /opt/aiter/gradlib/csrc/hipbsolgemm.cu
cp /workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110/review/GemmTuner_original.py /opt/aiter/gradlib/gradlib/GemmTuner.py
