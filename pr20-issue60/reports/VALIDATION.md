# PR20 shared-expert gate follow-up: issue60 port evidence

Source port: `61f3cb41145e1a8c465b6cf07cc6f9297d64793d`.
CI parent: `0be1aabf5bae3da58bd268fcdad2001a74c4c2b8`, the adopted PR63/76 snapshot.
Target: `apinge/sglang:qwen4_v0.5.21` at `91cdd01da750004559b94f2ceede50d88f516a59`.
Related issue: https://github.com/apinge/sglang/issues/60
Original optimization: https://github.com/apinge/sglang/pull/20

The target already contains the fused Triton shared-expert gate and model support.
This port preserves the previously adopted native HIP follow-up: BF16 H=4096,
M>=256, EXTEND/SPLIT_PREFILL, AITER enabled, no gate bias, supported contiguous
layouts and one fused shared expert. It combines gate GEMV, sigmoid, EP scale and
top-k append. Unsupported inputs and decode retain the existing fused Triton path.
ForwardBatch propagates through router, dual-stream and MegaMoE callers.
Qwen3.8 model evaluation is outstanding; this contribution covers part of issue60.

## Exact-source checks on November 3

One feature commit, three files, +216/-6 relative to the CI parent. All three blob
identities and the full tree outside the CI dependencies match tested candidate
`51565668154dd51530c225b5f221bc631ec034eb`. CI files match the adopted CI parent;
no PR8/PR63/PR76 linear changes are included. Author and author date preserved;
issue/source references were appended to the commit message.

21 CI CPU tests and 10 evaluation shell syntax checks passed. The first local
CPU attempt used an empty HIP_VISIBLE_DEVICES, which changes the CI CLI's default
--gpus argument and caused a validation-order expectation failure. The final run
omitted this variable while retaining empty CUDA_VISIBLE_DEVICES and
ROCR_VISIBLE_DEVICES; no GPU or model work ran and no code changed.

## Historical full-model data: October 30

The following data was measured on baseline `e04b1a37e8118cb7323b2cb30a6d0c29259479cc`
and candidate `51565668154dd51530c225b5f221bc631ec034eb`, before rebasing CI to 0be1.
These are same-implementation historical results, not fresh measurements of 61f3.

Same-node **TP4**, 4×MI308X, Qwen3.5-397B-A17B-PTPC-FP8. Main pairs r1/r2 use GPUs0–3/NUMA0; the last pair uses GPUs4–7/NUMA1 after two external GPU0 contexts interrupted startup before any formal samples. Each A/B pair uses the same GPU set. The original three-start protocol on one fixed GPU set was not completed.

| Workload / scope | c | Output tok/s before → after | TTFT ms before → after | TPOT ms before → after | ETE ms before → after |
|---|---:|---:|---:|---:|---:|
| 8000/500, GPUs0–3, two starts/side | 1 | 82.722 → 82.908 (+0.22%) | 595.788 → 594.443 (-0.23%) | 10.915 → 10.891 (-0.22%) | 6042.514 → 6028.996 (-0.22%) |
| 8000/500, GPUs4–7, one start/side | 1 | 82.810 → 82.633 (-0.21%) | 595.656 → 595.591 (-0.01%) | 10.903 → 10.928 (+0.24%) | 6036.038 → 6048.888 (+0.21%) |
| 512/256, GPUs0–3, one start/side | 1 | 85.685 → 86.212 (+0.62%) | 216.879 → 204.376 (-5.77%) | 10.861 → 10.839 (-0.20%) | 2986.355 → 2968.215 (-0.61%) |
| 512/256, GPUs0–3, one start/side | 8 | 437.179 → 439.622 (+0.56%) | 486.124 → 453.107 (-6.79%) | 16.451 → 16.475 (+0.14%) | 4681.171 → 4654.224 (-0.58%) |
| 512/256, GPUs0–3, one start/side | 16 | 695.914 → 694.473 (-0.21%) | 703.505 → 713.910 (+1.48%) | 20.297 → 20.305 (+0.04%) | 5879.348 → 5891.665 (+0.21%) |

The descriptive three-pair aggregate is 82.752→82.817 tok/s (+0.08%) and ETE6040.355→6035.626 ms (−0.08%); ETE sample SD is 6.088/11.514 ms across starts and GPU groups. Paired ETE changes are −0.289%, −0.158%, +0.213%. These results do not establish a stable full-model performance improvement.

Full GSM8K:1288/1319 (97.6497%)→1283/1319 (97.2707%), **−5 answers / −0.3791 percentage points**. Both sides completed the original protocol once with zero request errors; each retained one length cutoff at id119 in the denominator. One answer became correct and six became incorrect; no no-regression or equivalence claim. Taobao's original n=1 case passed the seven accepted automatic rules on both sides, HTTP200/stop. Different default-thinking output lengths make its durations unsuitable as a performance comparison. Both formal quality evaluations used GPUs0–3; GPUs4–7 ran only the final performance pair and short diagnostics.


## Workload and runtime

Six valid benchmark starts, 12 formal rounds, 2368 requests, 248 discarded warmups;
each formal round >=60 seconds. Main 8000/500 c1: 8 warmups + 32 formal requests per
start, A/B then B/A then A/B. The last pair changed physical GPU set due to foreign
GPU0 contexts during startup; those interrupted starts produced no formal samples.
The original three-start protocol on one fixed GPU set was not completed.
Supplemental 512/256 c1/c8/c16: one independent start per side, formal counts
64/512/512. Seed and individual-start raw metrics are retained in
[performance-comparison.json](performance-comparison.json).

Non-speculative, radix disabled. Actual KV capacity262144, request limit64,
Mamba cache128, decode graph32, effective memory fraction0.765. AITER full attention,
Triton GDN, NHD/page1, FP8 KV. Torch2.12, ROCm7.14.60850, Triton3.8, AITER b7aed05.
Runtime image content identity:
`21d84755a0bdd941beebfcecbd1d0d8734c6a8bcaf2ff162088a83f6a2f74834`.
Generated package metadata was retained and does not identify loaded source;
loaded source files/import paths were checked separately.

GSM8K: original full1319/train5/chat/c8/thinkingFalse/seed2311/max4096/greedy
protocol, one run per side. Errors and cutoffs stay in the denominator. Original
raw score hashes, correct IDs, flips and protocol/request hashes are retained in
[quality-comparison.json](quality-comparison.json). Taobao is one original case,
seven automatic rules, with semantic review pending; it is not dataset accuracy.
Quality runs used GPUs0-3 only.

## Historical numerical and profiling evidence

Actual ROCm7.14: 8 numerical cases, 25 guards, 30 phase/EP checks, 3 changed-input
CUDA-graph replays, 2 operator profiles passed; max absolute error7.7486e-7.
Earlier real-class lightweight caller tests used mocked expert/distributed work;
these do not prove distributed or full-model correctness.

Matched profiling workload: 8000 input /20 output, concurrency1, TP4, rank0.
Complete original files are under ../traces. The prefill screenshots select
chronological gate call30 on each side. Rank0 prefill gate median61.800->56.4985us,
60-call sum3708.234->3380.566us: local GPU work, not TTFT/ETE attribution.
Candidate EXTEND records60 HIP gates/rank; candidate DECODE records60 original
Triton gates/rank. Baseline EXTEND records60 Triton gates/rank. Baseline DECODE
is partial:48/38/41/49 gates, with missing other operator families too.
Decode screenshots show the first recorded gate as reachability examples; they
are not matched-layer timing comparisons. Candidate TP1 prefill TopK has59
auxiliary events; complete auxiliary coverage is not claimed.

Original trace bytes, timestamps, events, names and tracks are preserved.
Native Perfetto importer diagnostics are recorded in ../capture; they are not
hidden by editing traces. Screenshot capture on November3 changes UI state only.

No six-model GPU CI or Qwen3.8 quality test was run for this source revision.
All October30 task-owned test services/containers were stopped and cleanup
verified; unrelated services were retained. No new model server or GPU test was
started for this publication.
