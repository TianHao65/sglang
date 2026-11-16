#!/usr/bin/env bash
set -euo pipefail

source /workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/scripts/reset_client_env.sh
export LLM_BENCH_BACKEND=sglang
export LLM_INFER_FRAMEWORK=sglang
export LLM_API_MODEL=/models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16
export LLM_LOCAL_TOKENIZER_PATH=/models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16
export LLM_API_URL=http://127.0.0.1:19838/v1/completions
export LLM_AUTO_DATASET_CONF=tk_in:11000,tk_out:350
export LLM_INPUT_LEN=11000
export LLM_OUTPUT_LEN=350
export LLM_MIN_CONCURRENT=1
export LLM_NUM_WORKERS=1
export LLM_PROMPT_NUM_FACTOR=16
export LLM_BENCH_MAX_ITERS=1
export LLM_AUTO_SEQ_SIGMA=4
export LLM_PROMPT_PREFIX_RATIO=0.35
export LLM_IGNORE_EOS=True
export LLM_PICK_REAL_DS=False
export LLM_LOOP_FOREVER=False
export LLM_ENABLE_WARMUP=True
export LLM_FLUSH_CACHE_BETWEEN_ROUNDS=True
export LLM_FIXED_DATASET_SEED=True
export LLM_FIXED_BENCH_SEED=True
export LLM_BENCH_SEED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1

exec python3 /workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110/client_v4/benchmark_serving_wrapper.py \
  --trust-remote-code \
  --ignore-eos \
  --model /models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16 \
  --tokenizer /models/Qwen3.8-Flash-Next-PTPC-FP8-PLE-BF16 \
  --backend sglang \
  --host 127.0.0.1 \
  --port 19838 \
  --endpoint /v1/completions \
  --dataset-name primus_random \
  --random-input-len 11000 \
  --random-output-len 350 \
  --custom-output-len 350 \
  --random-range-ratio 0.2 \
  --random-prefix-len 3849 \
  --temperature 0.800000011920929 \
  --top-p 0.9 \
  --disable-tqdm \
  --save-result \
  --save-prompt \
  --start-concurrency 1 \
  --burstiness 1 \
  --num-workers 1 \
  --max-iterations 1 \
  --enable-warmup \
  --result-dir .
