GEMM tuning on hjbog-srdc-34.amd.com / MI308X / gfx942 / 80 CUs, 2026-11-10.
Qwen3.8 TP2 rank-local FP8 and BF16 ViT shapes; measurements use GPU 2.
Before: default image configuration. Final: selected tuned configuration and rebuilt kernels.
Image base SGLang 4d63dea with the local tgemm candidate; original AITER 514c166 restored for verification.
Five eager and three graph samples per shape, 16 rotating tensor sets.
All 16 GEMMs and 29 SGLang caller cases passed numerical and changed-input graph checks.
These are operator timings, not end-to-end model TTFT/TPOT or GSM8K results.

| Family | M / N / K | Eager us before → final | Graph us before → final | Eager Δ | Graph Δ | Config |
|---|---|---:|---:|---:|---:|---|
| ck_decode | 1 / 8192 / 2560 | 9.003 → 9.396 | 10.365 → 10.786 | +4.4% | +4.1% | base |
| ck_decode | 4 / 8192 / 2560 | 9.631 → 9.177 | 10.989 → 10.518 | -4.7% | -4.3% | base |
| ck_decode | 16 / 8192 / 2560 | 9.342 → 9.911 | 11.052 → 10.908 | +6.1% | -1.3% | base |
| ck_decode | 1 / 2560 / 3072 | 6.107 → 5.981 | 7.469 → 7.450 | -2.1% | -0.3% | base |
| ck_decode | 4 / 2560 / 3072 | 29.230 → 6.155 | 29.255 → 7.526 | -78.9% | -74.3% | tuned |
| ck_decode | 16 / 2560 / 3072 | 5.484 → 5.425 | 6.615 → 6.564 | -1.1% | -0.8% | base |
| ck_decode | 1 / 6656 / 2560 | 8.129 → 8.394 | 9.621 → 9.781 | +3.3% | +1.7% | base |
| ck_decode | 4 / 6656 / 2560 | 8.286 → 8.602 | 9.986 → 9.914 | +3.8% | -0.7% | base |
| ck_decode | 16 / 6656 / 2560 | 8.465 → 8.641 | 10.005 → 9.532 | +2.1% | -4.7% | base |
| tgemm | 8192 / 8192 / 2560 | 783.408 → 693.392 | 784.318 → 697.227 | -11.5% | -11.1% | tuned |
| tgemm | 8192 / 2560 / 3072 | 281.701 → 281.616 | 283.162 → 282.396 | -0.0% | -0.3% | base |
| tgemm | 8192 / 6656 / 2560 | 633.880 → 563.051 | 634.934 → 564.700 | -11.2% | -11.1% | tuned |
| tgemm | 256 / 1728 / 1152 | 12.036 → 12.049 | 15.067 → 15.077 | +0.1% | +0.1% | base |
| tgemm | 256 / 2152 / 1152 | 15.781 → 15.738 | 16.251 → 18.074 | -0.3% | +11.2% | base |
| tgemm | 256 / 1152 / 2152 | 17.754 → 16.019 | 19.607 → 17.687 | -9.8% | -9.8% | tuned |
| tgemm | 256 / 1152 / 576 | 7.965 → 5.758 | 9.565 → 6.723 | -27.7% | -29.7% | tuned |
