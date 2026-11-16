#!/usr/bin/env bash
set -euo pipefail
export AITER_CONFIG_GEMM_A8W8_BPRESHUFFLE=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/configs/ck_accepted.csv
export AITER_CONFIG_GEMM_BF16=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/configs/tgemm_accepted.csv
source /workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/scripts/server_common.sh
