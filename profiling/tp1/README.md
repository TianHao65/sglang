# Paired complete-model operator profiles

These are new 2026-11-16 operator traces of the previously measured PR63 `8511084989b4` before / tgemm prototype after, not final-head CI. Both independent startups use the same Quark14 Qwen3.5-35B model, PTL52 / MI308X physical GPU6, TP1/rank0, 8000 identical input IDs / 64 output tokens, con1, two discarded warmups, seed42, fixed token pool262144, radix disabled and full decode graph. The performance tables use their original TP2/TP4/TP8 protocols separately.

The profiler exports complete CPU+GPU original JSON.gz files, with input shapes recorded and Python stacks disabled. Both capture endpoints returned200; all requests verified8000/64, and both captures/owned-server cleanup passed. Telemetry recorded113 before /87 after samples, no active selected-GPU peers, and zero incomplete owner samples. Capture summaries record exact source/config/script hashes; complete original traces are copied byte-for-byte.

| phase / same caller | M/N/K | sampled GPU µs before → after | attribution |
|---|---|---|---|
| Prefill, GDN layer0 in_proj_qkvz | 8000/12288/2048 | 1169.323 → 853.602 | CPU Input Dims + exact External id; layer0 from source order; CK2lds → tgemm-selected hipBLASLt FP8 |
| First decode graph, GDN layer0 in_proj_ba | 1/64/2048 | 9.199 → 4.959 | BF16 HIPBLASLt → AITER wv_splitk_small; graph replay shape inferred from caller/neighbor sequence, corroborated by the same prefill projection dimensions |

Layer0 attribution follows the original source order; prefill matrix shapes have direct CPU/GPU matching. [Independent raw selection audit](capture/trace-selection-audit.md) verifies all four selections.

The decode samples are the fifth kernel in the first graph replay, selected by its runtime `hipGraphLaunch` correlation (before7014 / after6210), **sorted by original GPU timestamp**. Both have FP8 CK before them and `fused_qkvzba_split_reshape_cat_contiguous_kernel` after them. Raw trace-event file ordering is not GPU execution order. FP8 small-M decode remains CK; this BF16 sample demonstrates the dense tgemm dispatcher choosing its skinny kernel.

These are individual-call observations, not statistical kernel speedup estimates, cumulative GPU work or model ETE. Enclosing scopes overlap in the native Slices table: use the GPU kernel row, not the sum across scopes. Importer diagnostics are preserved in all four native screenshots. No events, timestamps, rank/PID labels or tracks were changed. The two phases each use a matching before/after viewport width (1.4ms prefill,60µs decode).

- [Complete originals and SHA256](MANIFEST.json)
- [Screenshot positions](screenshot-manifest.json)
- [Native UI capture records](capture/)
- [Frozen source snapshots](sources/) and [source hash manifest](review/MANIFEST.json)

Profiling scripts retain the tested host/container paths. Full baseline/accepted configs are reused from [../../configs](../../configs/); the separate source tuning kit provides portable table-merge and native benchmark/CI entrypoints. The earlier TP4 before trace and its cleanup failure are preserved locally with a supplementary review; they are not mixed into this matched TP1 pair. The first TP1 staging failure occurred before model startup and is also retained locally.
