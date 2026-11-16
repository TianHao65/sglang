# PR107 complete tgemm scope audit

Reference: PR107 `f315e8da2e3e9bed6e948fd5a835aeae165b5921`, based on apinge `9ac4ebe`. This audit covers the completed Nov9/10/12 tgemm integration, tuning, reproduction and validation work, plus the Nov16 followup. It does not interpret “all tgemm work” as vendoring AITER. Frozen experiments and the seven published runtime/test files were not modified. The newly authorized benchmark kit is implemented separately in the current source checkout; root owns review, commit and publication.

## Conclusion

The production implementation is already present in f315: FP8 large-M tgemm, small-M CK, BF16 canonical-plus-packed-prefill storage, Quark and CompressedTensors callers, DFlash layout safety, flags, and the new scalar/FP16 tuple correction. There is no missing tgemm kernel library to copy into SGLang.

The prior PR scope was incomplete as a delivery of the **whole completed work**: it provided no source-side way to apply the accepted tuning deltas, foregrounded only 35B in its data section, omitted the Qwen3.8 tune-only model experiment and complete operator-tuning results, and still lacked four matched native full-model Perfetto images. These are integration/reproduction/evidence gaps rather than an absent GEMM algorithm.

## Production coverage and historical variants

| Completed item | f315 location / status |
|---|---|
| gfx942 PTPC FP8 large-M selector, BF16 output, per-token/channel scales | `fp8_utils.apply_fp8_ptpc_linear`; flag and `M>16` guards present |
| CK decode (`M<=16`) | retained in direct PTPC and actual Quark shared caller |
| Quark FP8 prefill adapter | Nov9 `quark_w8a8_fp8.py` adapter was superseded by `apply_fp8_linear` integration; marked `[N,K]` packed transpose retained; do not append the older adapter and re-quantize again |
| BF16 ViT / linear packing | `unquant.py`: canonical parameter preserved, aligned gfx942 packed prefill copy, dense small-M fallback |
| fused input / leading dimensions / dtype | CompressedTensors tag and tuple-aware PTPC dispatcher, new scalar broadcast and FP16 CK handling |
| DFlash KV slicing | layout-aware guard retained; canonical weights permit KV-only fast path |
| default-off experiment flags | two EnvBool definitions; existing global-AITER dense BF16 tgemm off path preserved |
| regressions | linear config/layout tests and existing DFlash tests plus canonical/prefill-copy case |

The old direct `AiterHipblaslt`/`rocm_aiter_swizzle_hipb_*` helper is unused in the alternative and was correctly excluded from f315. The Nov9 `unsupported_54ad` snapshots and the separate native397B-MTP checkpoint setup are compatibility/model-experiment history, not extra tgemm production code.

## Existing AITER versus our contribution

AITER `514c166` already supplied `tgemm.mm`, configuration selection, CK/CKTile, hipBLASLt, ASM and skinny implementations. Our contribution is SGLang caller/layout integration, accepted configuration deltas, verification and experiment entry points. No full `aiter/tuned_gemm.py` or kernel-library copy is necessary.

Two AITER files were temporarily patched during tuning: BF16 `scaleAB=False` generated no scales; unsupported hipBLASLt solutions raised rather than killing workers. Those small tuning-support patches and recovered fast-search checkpoint belong to the full evidence/reproduction record. They were restored before production verification, and AITER Git status was clean. They must not silently become installed-library mutations or be described as the production runtime used for measurements.

## Source-side tuning kit implemented

Only validated deltas and the recorded input shapes were copied byte-for-byte:

| New source asset | Origin | Size / data rows |
|---|---|---|
| `benchmark/rocm_tgemm/configs/ck_accepted_rows.csv` | Nov10 accepted CK delta | 249 B / 1 |
| `benchmark/rocm_tgemm/configs/tgemm_accepted_rows.csv` | Nov10 accepted tgemm delta | 3217 B / 4 |
| `benchmark/rocm_tgemm/configs/ck_decode_shapes.csv` | recorded decode sweep | 9 |
| `benchmark/rocm_tgemm/configs/tgemm_shapes.csv` | FP8 prefill + BF16 ViT sweep | 7 |

The five selected keys/backend choices are:

| Family | M / N / K | Selected backend / identifier |
|---|---|---|
| FP8 decode | 4 / 2560 / 3072 | CK kernelId10 / splitK0 |
| FP8 prefill | 8192 / 8192 / 2560 | hipBLASLt169251 |
| FP8 prefill | 8192 / 6656 / 2560 | hipBLASLt169251 |
| BF16 ViT | 256 / 1152 / 2152 | hipBLASLt82636, bias, dense |
| BF16 ViT | 256 / 1152 / 576 | ASM5 / splitK1, bias, packed |

`prepare_configs.py` uses the original compare-script keys: CK `(gfx,cu_num,M,N,K,q_dtype_w)`; tgemm additionally includes bias/dtype/outdtype/scaleAB/bpreshuffle. It removes only matched base keys and appends the validated rows, preserving unmatched entries. It produces complete baseline/accepted runtime files in a requested fresh directory, records hashes, rejects duplicate shapes/schema failures and refuses input/output overwrites. A bare delta must never be assigned as the complete AITER config file.

`benchmark_gemm.py` reuses the completed 16-shape method: five eager / three graph samples, warmup10/iterations101, 16 rotating tensor sets, independent FP32 reference and two changed-input graph replays. No new algorithm or tuning data was added. Its CLI namespace/kernel-argument name collision was corrected during review; config existence and record-output paths were checked. Current adaptation was not GPU-run by this audit agent and should not be called a new performance measurement.

The source README includes existing AITER tuner commands, the exact recorded stack, accepted-only scope and the temporary-search-fix boundary. It never copies complete default tables, old controllers, personal SSH/container paths or benchmark-library dependency trees into source.

Ten standard-library CPU tests passed, with the registry recognizing `base-a-test-cpu`. Isort, Ruff, syntax and diff checks passed. Offline preparation using the frozen base files produced **2943 CK / 3233 tgemm rows**, with every runtime-key/backend/identifier/kernel-name value matching the frozen accepted files; originals were unchanged. Complete base snapshots stay in the evidence branch.

## Reproduction details to retain

1. **All-six CI with tuning enabled.** The existing small `run_ci_before.py` / `run_ci_after.py` wrappers inject both flags and config paths into `MODEL_PATH` server environments. Native `qwen4_ci.clean_environment` strips outer AITER/SGLANG exports. Therefore “export configs then invoke native CI” alone does not reproduce the tuned experiment. The new `run_ci.py` now reuses that thin wrapper, passes all native CLI options through and injects only the server environment. Two extra stdlib tests verify server injection, unchanged client environment and preserved original extras/GPU mask. README names the explicit six-case invocation; no stale controllers/state were copied.
2. **Qwen3.8 tune-only ETE.** Retain the already tested before/after/common server and client/discarded-client constants. Preserve 11000/350 in both environment and CLI, sigma4, prefix0.35, nominal prefix3849, client seed1/server seed42, MTP EAGLE3/4, radix, and fixed pool262144. This experiment discarded **16**, not128, requests before each128 formal round. The customer-V4 client is an existing benchmark dependency; do not substitute another client/distribution and claim identical methodology. Review any dependency-copy scope separately rather than blindly copying the entire legacy client stack.
3. **Search reruns.** The exact BF16/unsupported-solution patches and fast-search recovery checkpoint should remain accessible with hashes. Use an isolated AITER checkout for the historical search; restore original AITER before runtime checks. New tuner output is not automatically accepted. The current source kit safely applies the already accepted rows and runs the recorded native comparison.

## Complete evidence required in the separate branch

The current published evidence commit `2157e3` already contains four complete configuration snapshots, six-model CI JSON, controlled35B JSON, final-head boundary validation and two scientific latency figures. Those figures are not Perfetto screenshots. Extend the independent evidence branch with:

- **Full Nov10 tuning result**, all16 cases and the five selected overlays, raw before/accepted samples, 29-caller numerical/graph checks and restored-source identity. Include unchanged cases; one unchanged graph result varied +11.2%, and the initial operator comparison used default/prebuilt versus rebuilt kernels. These are operator measurements, not model TTFT/TPOT.
- **Qwen3.8 TP2 tune-only model results** from the same4d63dea prototype with base versus accepted tables: TTFT476.562→479.689ms(+0.66%), TPOT5.032→4.598ms(−8.62%), ETE2226.815→2076.229ms(−6.76%), output156.941→168.326tok/s(+7.25%). Two starts/arm,512 formal requests. Actual length arrays and source/client hashes belong with the report. Prefix ratio is not a guaranteed per-request cache-hit rate.
- **All six Nov12 CI cases and tradeoffs**, not just their pass status. Keep every128 performance request and200 GSM8K examples per side, the Qwen3.8 flag supplementation, accepted length and min gates. The35B+10.3% mean remains reported with its late21 diagnostics; the clean Nov16 repeats are a separate protocol and do not replace those requests.
- **Nov16 controlled35B ABBA and original-pool sensitivity**, retaining failed/no-measurement attempt provenance, exact client latencies and telemetry. Source/runtime/protocol differ from the Nov10 tune-only comparison; these are independent tables.
- **Matched complete original Perfetto traces, four native images and direct operator-position links**, with source revisions, workload and hashes. Root's fixed-skill capture workflow owns this item. Do not relabel historical PR8/PR63 screenshots or scientific request-index plots as new native profiling evidence.
- **f315/final-head CPU/native boundary results**, distinct from the image4d/851 prototype’s whole-model performance. Full final-head CI remains a separate claim if not rerun.

A compact PR body can use three explicitly labelled data groups: (a) same-prototype default→tuned Qwen3.8 results; (b)851→tgemm six-model regular CI; (c)controlled35B repeat/sensitivity results. Grouping by source/workload prevents the visually similar before/after labels from conflating different comparisons.

## Suggested reviewable commit split

- Runtime/layout/tests: existing f315 production changes.
- Validated tuning/reproduction: the new small benchmark kit and config CPU tests, plus any reviewed thin model/CI reproduction entry required by root.
- Evidence branch: complete operator/model records, search-support provenance and the four native original-trace Perfetto images/links.

This covers the completed work without introducing a new GEMM algorithm, vendoring AITER defaults/library code, adopting failed candidates, overwriting model/runtime inputs, or hiding adverse measurements. Exact file hashes and inventory are in `scope_audit.json`.
