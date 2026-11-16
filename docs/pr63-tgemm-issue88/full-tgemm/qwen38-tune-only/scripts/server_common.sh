#!/usr/bin/env bash
set -euo pipefail
export AITER_REBUILD=0

export HSA_NO_SCRATCH_RECLAIM=1
export HSA_COREDUMP_PATTERN=/dev/null
export HIP_FORCE_DEV_KERNARG=1
export PYTHONUNBUFFERED=1
export SGLANG_USE_AITER=1
export SGLANG_ROCM_USE_AITER_LINEAR_FP8HIPB=1
export SGLANG_ROCM_USE_AITER_LINEAR_SHUFFLE=1
export AITER_MOE_PADDING_SIZE=64
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
unset ROCR_VISIBLE_DEVICES
export HIP_VISIBLE_DEVICES=2,3
export CUDA_VISIBLE_DEVICES=2,3
export SGLANG_GR_READ_FLYDSL=1
export SGLANG_USE_PYHIP_QSA=1
export SGLANG_QWEN4_SEQ_PARALLEL=1
export SGLANG_QWEN4_SEQ_PARALLEL_MIN_TOKENS=2048
export SGLANG_ENABLE_ROCM_LM_HEAD_GEMV=1
export PYTHONPATH=/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/sources/tgemm/python

exec python3 -m sglang.launch_server \
  --model-path /models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16 \
  --served-model-name /models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16 \
  --host 127.0.0.1 \
  --port 19838 \
  --tp-size 2 \
  --speculative-algorithm EAGLE \
  --speculative-num-steps 3 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 4 \
  --speculative-moe-runner-backend triton \
  --attention-backend aiter \
  --moe-runner-backend aiter \
  --linear-attn-backend triton \
  --linear-attn-decode-backend triton \
  --linear-attn-prefill-backend aiter \
  --linear-attn-verify-backend triton \
  --kv-cache-dtype auto \
  --chunked-prefill-size 16384 \
  --watchdog-timeout 1200 \
  --mem-fraction-static 0.95 \
  --max-running-requests 32 \
  --cuda-graph-max-bs-decode 32 \
  --mamba-ssm-dtype float32 \
  --mm-feature-transport cuda_ipc \
  --enable-cache-report \
  --mamba-radix-cache-strategy extra_buffer \
  --no-ple-offload-embedding \
  --log-requests \
  --log-requests-level 1 \
  --max-total-tokens 262144 \
  --random-seed 42
