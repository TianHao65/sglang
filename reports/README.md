# Per-start benchmark and validation reports

These reports supplement the native screenshots and complete original model
traces at immutable evidence commit `d16bdf05a3d00de8bf5288e5fc185fccff193d94`.
Image and model-trace links in the PR remain pinned to that commit.

- [Independent final audit](node19/final-audit.json): nine complete model starts,
  eighteen formal workload cases, source/model/runtime identity, statistical
  definitions, measurement dates, trace coverage and owned cleanup.
- [Producer summary](node19/summary.json) and [formal audit](node19/formal-audit.json).
- [Final cleanup](node19/cleanup.json), [container state](node19/container-final.json),
  [runtime](node19/runtime.json), [resume runtime](node19/runtime-resume.json) and
  [safe config identity](node19/config-identity.json).
- Per-start files under `node19/runs/`: aggregate metrics, request length/timing
  arrays, actual concurrency, commands, source hashes, dispatch, quality probe
  summaries, normalized server identity and shutdown verification.
- [Original alias-guard reproduction](validation/guard-original-reproduction.json),
  [CPU/output validation](validation/output-validation.json),
  [GPU validation](validation/output-gpu.json) and
  [complete original output operator trace](validation/output-gpu-original.trace.json).
- Micro reports and complete original operator traces under `micro/{port,gemv,direct}/`.
- Original stopped attempt on52 under `attempt1-52/`, including the resource guard
  and separate owned-cleanup assessment; its conservative raw cleanup result is
  preserved rather than rewritten.
- [Source publication verification](source-publication.json).
- [Artifact provenance and original hashes](artifact-provenance.json).

## Data preservation and exclusions

`*-request-metrics.jsonl` retains each original JSONL record's scalar benchmark
fields and unmodified `input_lens`, `output_lens`, `ttfts` and `itls` arrays.
Original line indexes and source-file SHA256 are recorded. Generated text, embedded
full server configuration and error text are omitted; empty-error flags and counts
are retained. Numeric timing units remain those of the original benchmark fields;
no new per-request latency formula or score is introduced.

Per-start `metrics.json` retains original aggregate fields without repeating raw
request arrays or generated text. `server-identity.json` and `config-identity.json`
are explicit noncredential setting subsets, not claims of complete untouched raw
configuration. Original input-file hashes and transformations are listed in the
provenance manifest.

Quality records retain output-token counts and finish/latency metadata, but omit
raw text and output token IDs. They are smoke diagnostics and do not establish
GSM8K or Taobao acceptance. Numerical API/micro results do not imply model ETE or
default model-path copy removal. No customer inputs, credential files, full server
logs or user sessions are published in this package.
