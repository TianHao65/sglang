# Complete tgemm work: original evidence index

This directory preserves the completed integration, tuning and model experiments.
Copied records are byte-identical to their originals; SHA256SUMS and MANIFEST.json
record original paths, file hashes and scope. No trace/log content or slow request
was rewritten. Root-level complete configuration snapshots are reused rather than
duplicated here. Native Perfetto captures remain in [profiling/tp1](../../../profiling/tp1).

| Evidence | Source / comparison | Completeness |
|---|---|---|
| [Nov9 matrix](nov09/matrix/RESULTS.md) | Image4d63dea baseline / PR63 port / tgemm adapter | 14/24 planned starts,1792/3072 formal requests; all measured128 records retained |
| [Nov10 tuning](nov10-tuning/RESULTS.md) | Native defaults → selected configuration | All16 GEMMs;29 SGLang callers /58 changed-input graph replays |
| [Qwen3.8 tune-only](qwen38-tune-only/RESULTS.md) | Same4d63dea tgemm source, base → accepted tables | 2 starts/arm;512 formal plus64 discarded requests |
| [Tuning support/recovery](nov10-tuning/review) | Two temporary AITER search patches, fast-search checkpoint recovery | Original AITER restored before production validation |
| [Source-kit checks](source-kit-validation/scope_audit.json) | Source05cd615, validated overlays and complete-table merge | 10 stdlib CPU tests; exact generated accepted hashes verified |

## Nov9 measured and unmeasured scope

The [whole summary](nov09/matrix/summary.csv), [14-run table](nov09/matrix/rounds.csv)
and [status](nov09/matrix/CURRENT_STATUS.json) retain all implementations. Valid
raw records and runtime/smoke/resource metadata are under `nov09/matrix/results/`.
Qwen3.8 TP2 has two starts for each implementation. Qwen3.5-35B TP4 also has two
starts each: mean ETE2197.886 /2262.247 /2218.759ms for baseline /PR63 /tgemm.
Qwen3.5-397B TP8 has one baseline and one PR63 start:3475.193 /3554.254ms.
Its tgemm arm has **no measurement**. Qwen3.8 TP4 and other planned startup slots
also remain unmeasured; blank results are not zero performance.

Qwen3.8 uses the customer11K/350 mean workload, sigma4, prefix0.35, MTP/radix on.
The Qwen3.5 cases use standard8K/500, con1, MTP/radix off. These comparisons are
separate from later six-model CI and final-source profiling.

## Nov10 tuning and model result

The two delta CSVs contain only one CK and four tgemm accepted rows. Complete
[base/accepted tables](../../../configs) are already at evidence root. Failed and
unselected search records are retained as search history, not adopted defaults.
Initial operator measurements used image/prebuilt defaults versus rebuilt tuned
kernels; unchanged-case variation is visible in the full16-row table. The later
model comparison prepared both arms from original AITER source.

The Qwen3.8 TP2 table-only comparison measured ETE2226.815 →2076.229ms (−6.76%),
TPOT5.032 →4.598ms (−8.62%), and TTFT476.562 →479.689ms (+0.66%). Each startup has
16 discarded and128 timed requests. The original customer-client format keeps
**two additional untimed warmup input/error entries**: formal input/error arrays
have130 entries while output/timing arrays have128; discarded arrays18 versus16.
No original array was trimmed. Every error entry is empty, and measured length
arrays match across all four starts.

Historical scripts keep their original mount paths to document the actual run.
Portable validated-overlay application and native comparison/CI entry points are
in PR107's `benchmark/rocm_tgemm/`; they do not vendor AITER or automatically apply
tuning-support patches to an installed shared runtime.

## Scope and integrity

AITER `tgemm` and native kernels are existing library code. Our work is caller
integration, safe packed/canonical ownership, validated configuration deltas and
verification. The BF16 no-scaling and unsupported-solution patches were temporary
search helpers; restored source hashes and clean AITER status are retained.

The recorded source05cd615 kit passed10 CPU tests. Preparation from the recorded
base snapshots reproduces exact accepted-file hashes: CK131424a… and tgemm6f2203…,
2943 /3233 runtime rows. This is a CPU merge/hash check, not a new GPU tuning run.

Later six-model CI, controlled35B ABBA/original-pool observations, final-head native
boundary checks and the matched full-model traces retain their own source/runtime
labels. Do not treat image4d63dea or851108 prototype timing as final-head timing.
The original35B late interval remains reported; the specific historical trigger
has not been established by later controls.
