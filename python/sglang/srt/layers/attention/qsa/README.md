# QSA decode on ROCm

This directory contains the Qwen3.8 QSA indexer and sparse-attention path. On
gfx942/MI308X, the supported decode configuration uses the CUDA implementation
as its semantic reference while replacing CUDA-only kernels with HIP-capable
JIT or Triton kernels.

## Selected decode path

For the validated Qwen configuration (BF16, 12 query heads, one KV head,
head dimension 256, compression ratio 4, and block top-k 512), the GPU path is:

```text
index projection GEMM
-> qsa_index_q_prep_kernel
-> qsa_index_k_compress_kernel
-> _triton_qsa_mqa_decode_kernel.kd
-> fast_topk_kernel<512, false>
-> _expand_qsa_block_indices_kernel.kd
-> _sparse_gqa_chunk_prefill.kd
```

The final sparse-attention kernel is a direct-paged, one-CTA-per-row decode
kernel. It is launched before the generic compact-KV fallback and reads the
full K/V cache through the indexer's existing page table.

## Operator replacements

| Previous work | Current implementation | Notes |
|---|---|---|
| Torch paged-cache gather, FP32 einsum/GEMM, ReLU, head reduction, scaling, and tail masking | `_triton_qsa_mqa_decode_kernel.kd` | Reads compressed K pages directly and produces the MQA logits in one Triton kernel. |
| Allocating/filling a zero `row_starts` tensor before decode FastTopK | `fast_topk(..., row_starts=None)` | Decode rows always start at zero; the FastTopK kernel itself is unchanged. |
| Work on complete logits-tail CTAs | Device-side early return in `_triton_qsa_mqa_decode_kernel.kd` | Internal FastTopK receives the valid compressed lengths, so untouched tail CTAs are not consumed. |
| Valid-count, prefix-sum, compact-KV, and relative-index preparation before sparse attention | Direct logical-index to physical-page mapping inside `_sparse_gqa_chunk_prefill.kd` | The supported path does not materialize a compact K/V buffer. |
| Experimental split-K stage plus merge | One `_sparse_gqa_chunk_prefill.kd` launch | No partial-output, LSE, merge, or effective-length scratch is present in the selected product path. |

The following kernels are retained rather than replaced:

- `qsa_index_q_prep_kernel`: normalizes/rotates the current index query and
  updates the pending index-K ring.
- `qsa_index_k_compress_kernel`: writes a completed four-token compressed key;
  inactive graph rows return through a device-side slot-zero sentinel.
- `fast_topk_kernel<512, false>`: selects 512 compressed blocks.
- `_expand_qsa_block_indices_kernel.kd`: expands each selected compressed block
  to four raw-token indices and appends up to three tokens from the incomplete
  compression group. Its output width is therefore `2048 + 3 = 2051`.

## MQA equivalence

`_triton_qsa_mqa_decode_kernel` and `tilelang_qsa_mqa_decode` implement the
same expression for every visible compressed key:

```text
logit[key] = sum_over_heads(relu(dot(query[head], key))) / sqrt(head_dim)
```

Both read the paged compressed-K cache and mask positions outside the device
context length. The Triton implementation handles the native four query heads
directly; the TileLang implementation pads the head dimension used by its MMA
layout.

The normal test suite uses `torch_qsa_mqa_decode` as the portable numerical
oracle. It covers short rows, page crossings, invalid page IDs, and graph
replay with growing and shrinking context lengths. The accepted tolerance is
`rtol=2e-2, atol=2e-2`; standalone 12K/16K measurements observed maximum
absolute errors between `9.54e-7` and `1.91e-6`.

An optional test also compares Triton directly with TileLang when TileLang is
installed on gfx942. The independent bring-up measurement found identical
finite/negative-infinity masks and maximum absolute error `9.54e-7` in eager
execution and HIP graph replay. On the same MI308X, the complete calls measured
about 14.90 us for Triton and 30.01 us for TileLang, including TileLang's
padding/fill wrappers.

## Tests

The relevant tests are:

- `test_qsa_decode_mqa_prefers_triton_over_tilelang_on_gfx942`
- `test_qsa_decode_mqa_four_heads_gpu`
- `test_qsa_triton_decode_mqa_short_and_cross_page_matches_reference_on_rocm`
- `test_qsa_triton_decode_mqa_rejects_out_of_range_pages_on_rocm`
- `test_qsa_triton_decode_mqa_supports_rocm_graph_replay`
- `test_qsa_triton_decode_mqa_matches_tilelang_when_available`
- `test_qsa_same_named_chunk_prefill_kernels_do_not_collide_in_one_process`
- `test_qsa_fast_topk_expand_dispatches_direct_paged_one_cta`
- `test_qsa_backend_direct_paged_one_cta_graph_replay`
- `test_qsa_backend_direct_paged_one_cta_two_layers_do_not_alias`

The direct-paged backend tests make the compact-KV helpers fail if they are
reached, compare outputs with an FP32 reference, and inspect profiler events to
require `_sparse_gqa_chunk_prefill.kd` while rejecting split-K or merge names.

## Performance trade-off

The single-CTA sparse topology is retained intentionally. At 12K and batch 1,
it measured about 295 us per layer versus about 35 us for the removed 16-way
split-K plus merge implementation. The full-model comparison showed mean TPOT
12.8622 ms -> 16.0727 ms. This commit therefore records the requested
CUDA-aligned single-kernel topology; it does not claim that this sparse stage
is faster than the excluded split-K implementation.
