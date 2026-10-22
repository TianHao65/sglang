# PR #63 Perfetto screenshots

Original Qwen3.5-397B PTPC-FP8 model traces, official SGLang v0.5.21,
TP8, 8x MI308X, ROCm 7.2.0. Diagnostic workload: 512 input / 256 output,
concurrency 1, captured after the 512/256 c16/c64/c128 benchmark.
Baseline e00930c54 vs port 0bcf65b8f. Not an exact qwen4_v0.5.21 runtime rerun.

Each screenshot contains two adjacent original GPU kernels at layer-call 30:
one FP8 projection and its following BF16 projection. Kernel names, durations,
order and spacing are unchanged; the time origin is translated to 2 us and
lanes are labeled by dtype. Prefill before/after and decode before/after are
separate screenshots. Trace fragments and their provenance are included.

These are sampled operator times, not ETE measurements. Images are real
Perfetto browser screenshots. This evidence branch is separate from the
five-file source PR.
