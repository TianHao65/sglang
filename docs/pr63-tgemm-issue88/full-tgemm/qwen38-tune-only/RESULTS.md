Qwen3.8 TP2 tgemm ETE comparison, hjbog-srdc-34.amd.com (PTL), GPUs 2/3, 2026-11-10.
11K/350 means, sigma=4, prefix=0.35, con1, one worker, MTP/radix enabled.
Same local tgemm SGLang 4d63dea snapshot / AITER 514c166. Before uses base tables; after uses selected tuned tables.
Two independent startups per arm; before/after/after/before; discarded repetition before each 128-request formal round.
All 512 formal requests completed without client errors. Generated actual input/output length arrays match across all rounds.

| Arm | TTFT ms | TPOT ms | ETE ms | Output tok/s | QPS | QPS/GPU |
|---|---:|---:|---:|---:|---:|---:|
| before | 476.562 | 5.032 | 2226.815 | 156.941 | 0.4491 | 0.22454 |
| after | 479.689 | 4.598 | 2076.229 | 168.326 | 0.4817 | 0.24083 |

Changes are after / before - 1; negative latency changes mean lower latency.
{
  "TTFT_ms": 0.6562139341635964,
  "TPOT_ms": -8.61927672646794,
  "ETE_ms": -6.762365979031215,
  "output_tokens_s": 7.254384588336449,
  "QPS": 7.254384588336471,
  "QPS_per_GPU": 7.254384588336471
}

Per-start ETE ranges (two starts are not a confidence interval):
{
  "before": [
    2223.162241812588,
    2230.4668385704645
  ],
  "after": [
    2067.6195805863244,
    2084.838802032664
  ]
}

Lengths are generator means; text decoding/re-tokenization changes server input lengths, and prefix ratio is not a fixed per-request hit ratio.
QPS here is con1 / mean ETE seconds. Raw client collector throughput is preserved separately.
Arithmetic smoke checks passed; this is not a full GSM8K assessment. No PR was updated.
[Per-round CSV](results/rounds.csv) · [Summary JSON](results/SUMMARY.json)
