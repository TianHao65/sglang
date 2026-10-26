# PR #63: screenshots from complete original model traces

These four images replace the earlier screenshots made from extracted events.
Each image opens the complete, untouched TP0 model trace in Perfetto. Only
native viewport zoom, track expansion, Area Selection, dark theme and column
widths are changed. No extraction, timestamp translation, PID/TID replacement,
kernel renaming, track relabeling, duration editing or event reconstruction is
performed. Adjacent original kernels and original phase scopes remain visible.
The blue area and the Current Selection > Slices table are native Perfetto UI.
The table includes enclosing phase scopes as imported on the original stream;
their clipped durations overlap the kernels and must not be added to GPU time.

Historical workload: Qwen3.5-397B-A17B-PTPC-FP8, TP8, MI308X, 512 input /
256 output, concurrency 1; official v0.5.21 baseline e00930c54 vs original
PR #8 port 0bcf65b8f, collected 2026-10-20, TP0, layer-call 30.
These captures precede the new Decode follow-up commits in PR #63.

The traces in traces/ are byte-identical to the saved original .json.gz files.
The original-trace-manifest.json records SHA256, original events, imported
slice IDs/timestamps/durations, full event counts, viewport and UI checks.
full-original-links.json links to these same complete original bytes in Perfetto.
scripts/capture.py reproduces screenshots by opening the original local file
through Perfetto's Open trace file action. It reads originals without writing them.

Perfetto v59.1 reports slice_spill_overlapping_complete_event for overlapping
complete events already in the original model traces; these are not repaired or
filtered. Selected kernel timestamps and durations are verified against the
original JSON. The import diagnostic is recorded in each capture manifest.
