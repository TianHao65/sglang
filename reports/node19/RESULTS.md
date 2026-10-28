# Decode follow-up: fresh three-version experiment

Qwen3.5-397B-A17B-PTPC-FP8, MI308X, TP8; exact source trees and fixed KV capacity.

8000/500 c1: three independent startups per variant. 512/256 c16/64/128: first-start comparison. Each formal round >=60s, with a separate discarded warmup.

The direct version contains the corrected overlap safety guard. The model caller is unchanged; apply_into benefits are API/operator evidence, not proof of model-level copy removal.

| case | version | output tok/s | TTFT ms | TPOT ms | ETE ms | starts | ETE startup std ms |
|---|---|---:|---:|---:|---:|---:|---:|
| c1_8k500 | port | 94.480 | 385.408 | 9.829 | 5290.246 | 3 | 10.504 |
| c1_8k500 | gemv | 96.537 | 385.126 | 9.604 | 5177.504 | 3 | 15.790 |
| c1_8k500 | direct | 96.395 | 385.396 | 9.619 | 5185.094 | 3 | 9.828 |
| c16_512256 | port | 905.819 | 524.934 | 15.651 | 4515.914 | 1 | n/a |
| c16_512256 | gemv | 912.204 | 519.064 | 15.550 | 4484.223 | 1 | n/a |
| c16_512256 | direct | 911.573 | 523.791 | 15.544 | 4487.433 | 1 | n/a |
| c64_512256 | port | 1755.636 | 1557.251 | 30.411 | 9312.090 | 1 | n/a |
| c64_512256 | gemv | 1755.546 | 1553.229 | 30.429 | 9312.652 | 1 | n/a |
| c64_512256 | direct | 1753.193 | 1570.293 | 30.413 | 9325.662 | 1 | n/a |
| c128_512256 | port | 2519.461 | 2329.419 | 41.721 | 12968.287 | 1 | n/a |
| c128_512256 | gemv | 2512.215 | 2306.384 | 41.907 | 12992.623 | 1 | n/a |
| c128_512256 | direct | 2517.346 | 2304.255 | 41.783 | 12958.868 | 1 | n/a |

| case | change | output tok/s change | ETE change |
|---|---|---:|---:|
| c1_8k500 | port → gemv | +2.18% | -2.13% |
| c1_8k500 | gemv → direct | -0.15% | +0.15% |
| c1_8k500 | port → direct | +2.03% | -1.99% |
| c16_512256 | port → gemv | +0.70% | -0.70% |
| c16_512256 | gemv → direct | -0.07% | +0.07% |
| c16_512256 | port → direct | +0.64% | -0.63% |
| c64_512256 | port → gemv | -0.01% | +0.01% |
| c64_512256 | gemv → direct | -0.13% | +0.14% |
| c64_512256 | port → direct | -0.14% | +0.15% |
| c128_512256 | port → gemv | -0.29% | +0.19% |
| c128_512256 | gemv → direct | +0.20% | -0.26% |
| c128_512256 | port → direct | -0.08% | -0.07% |

## Single-operator measurements

BF16 N16/K4096; actual quantization-method entrypoints; GPU microseconds per call.

| M | version | apply µs | apply_into µs | max relative L2 error |
|---:|---|---:|---:|---:|
| 1 | port | 7.491 | 9.962 | 0.001472 |
| 1 | gemv | 2.837 | 5.490 | 0.001472 |
| 1 | direct | 2.902 | 2.865 | 0.001472 |
| 8 | port | 7.400 | 10.009 | 0.001653 |
| 8 | gemv | 3.672 | 6.224 | 0.001653 |
| 8 | direct | 3.656 | 3.628 | 0.001653 |
| 16 | port | 7.254 | 9.834 | 0.001650 |
| 16 | gemv | 4.442 | 7.002 | 0.001650 |
| 16 | direct | 4.492 | 4.476 | 0.001650 |
| 32 | port | 7.598 | 10.199 | 0.001523 |
| 32 | gemv | 6.286 | 8.861 | 0.001523 |
| 32 | direct | 6.294 | 6.276 | 0.001523 |

Microbenchmarks in results/micro use actual apply/apply_into methods, captured graphs of 50 operations and medians of five GPU-event samples. They measure per-call GPU time and must be interpreted separately from ETE.

The direct output validator covers 15 GPU output/graph cases, 10 distinct-storage DLPack overlap rejections, and a complete original operator trace with no copy.

Original full-model traces are in results/<version>_r1/traces. dispatch.json records new GEMV and GEMM kernel counts across all eight ranks; GEMV alone does not prove apply_into model activation.

Short-answer quality probes are saved for every startup in quality.json. Random-token latency measurements do not establish generation quality or GSM8K accuracy.

| version | repetition | probes | length stops |
|---|---:|---:|---:|
| port | 1 | 3 | 3 |
| port | 2 | 3 | 3 |
| port | 3 | 3 | 3 |
| gemv | 1 | 3 | 3 |
| gemv | 2 | 3 | 3 |
| gemv | 3 | 3 | 3 |
| direct | 1 | 3 | 3 |
| direct | 2 | 3 | 3 |
| direct | 3 | 3 | 3 |
