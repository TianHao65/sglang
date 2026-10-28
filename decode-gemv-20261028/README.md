# Decode swizzled GEMV: complete original model traces

These four native Perfetto screenshots directly open the complete untouched
TP0 model traces for pure PR8 ddccab6e0d (before) and a8cd545783 (after).
Model: Qwen3.5-397B-A17B-PTPC-FP8, TP8, MI308X, ROCm7.2.0/Torch2.9.1.
Captured2026-10-26, input8000/output500/c1, profiler configured33steps.
The original files contain CPU EXTEND8000 and32DECODE annotations, with the
original captured GPU prefill/decode work. No trace event is extracted,
reconstructed, shifted, relabeled, filtered or repaired.

The selected BA projection has BF16 input/weight, N16/K4096. Prefill is
identified via original CPU shapes/external ID and GPU launch correlation.
Decode is identified via the matched original stream7 kernel sequence,
30th GDN BA call (layer38), with six identical neighboring kernel names.
Prefill still uses hipBLASLt; Decode switches to allocating _swizzled_gemv.
Current model BA callers use apply, so these model figures do not prove the
optional caller-owned output API or its no-copy benefit. That API is measured
separately by the original numerical/operator experiments.

Each screenshot preserves native blue Area Selection and duration, with
Current Selection > Slices and native names/count/wall/self/average below.
Same scale per phase: Prefill100microseconds, Decode40microseconds.
Perfetto v59.1 reports36overlapping-complete-event diagnostics already in
each original trace; they are preserved. Selected kernel timestamp/duration
are checked against the original JSON. Overlapping phase annotations in the
native table must not be summed into GPU kernel duration.

Original trace SHA256 and selection/UI checks are in manifest/. Each trace
file here is byte-identical to the recorded original compressed file.
