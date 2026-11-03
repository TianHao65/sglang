# Qwen3.5 DFlash five-dataset measurements

Measured source: `720f8ad566a97069c10069ad1a76d39bb460e951`, directly on `TianHao65:qwen4-ci-base@0be1aabf5b`.

See [RESULTS.md](RESULTS.md) for the table, [manifest.json](manifest.json) for software/configuration/hashes, and [workloads.json](workloads.json) for each client configuration. `data/` contains all five frozen public datasets; `results/<dataset>/` contains summaries and original measured responses compressed with gzip.

GSM8K reuses the complete first run on this exact source; the other four datasets ran subsequently at concurrency32 with the same weights, backends and sampling. Each workload excludes one warmup batch. All truncated responses and scorer failures remain in the data.

Single-request probes were malformed on this stack. These results cover the listed concurrency32/64 configurations and do not establish single-request numerical correctness. MT-Bench is first-turn performance only.

Owned services were stopped and all eight MI308X GPUs released after execution.
