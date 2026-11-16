import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
import aiter
from aiter.tuned_gemm import tgemm
from compressed_tensors.quantization import QuantizationStrategy
from sglang.srt.environ import envs
from sglang.srt.layers.quantization import unquant
from sglang.srt.layers.quantization.compressed_tensors.schemes.compressed_tensors_w8a8_fp8 import CompressedTensorsW8A8Fp8

ROOT = Path('/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110')
torch.manual_seed(42)
rows = []


def check(out, ref):
    assert out.shape == ref.shape and out.dtype == torch.bfloat16
    assert torch.isfinite(out).all()
    error = float((out.float() - ref.float()).norm() / ref.float().norm().clamp_min(1e-8))
    assert error < 0.015, error
    return error


with torch.inference_mode(), envs.SGLANG_ROCM_USE_AITER_LINEAR_FP8HIPB.override(True):
    for n, k in [(8192, 2560), (2560, 3072), (6656, 2560)]:
        method = CompressedTensorsW8A8Fp8(
            SimpleNamespace(strategy=QuantizationStrategy.CHANNEL, block_structure=None), False)
        layer = torch.nn.Module()
        layer.weight = torch.nn.Parameter(torch.randn(n, k, device='cuda').to(torch.float8_e4m3fn), False)
        layer.weight_scale = torch.nn.Parameter(torch.linspace(0.01, 0.03, n, device='cuda').view(-1, 1), False)
        canonical = layer.weight.float() * layer.weight_scale
        method.process_weights_after_loading(layer)
        assert layer.weight.is_shuffled
        for m in [1, 4, 16, 32, 7103, 8191, 8193]:
            x = torch.randn(m, k, device='cuda', dtype=torch.bfloat16)
            bias = torch.randn(n, device='cuda', dtype=torch.bfloat16)

            def reference(z):
                q, s = aiter.per_token_quant_hip(z, quant_dtype=aiter.dtypes.fp8)
                return (q.float() * s) @ canonical.t() + bias.float()

            real = tgemm.mm
            calls = []

            def tracked(*args, **kwargs):
                calls.append(args[0].shape[0])
                return real(*args, **kwargs)

            with patch.object(tgemm, 'mm', tracked):
                out = method.apply_weights(layer, x, bias)
            assert bool(calls) == (m > 16), (m, calls)
            error = check(out, reference(x))
            q, s = aiter.per_token_quant_hip(x, quant_dtype=aiter.dtypes.fp8)
            if m == 4:
                fused = (q.view(2, 2, k), s, torch.bfloat16)
                expected = reference(x).view(2, 2, n)
            else:
                fused = (q, s, torch.bfloat16)
                expected = reference(x)
            check(method.apply_weights(layer, fused, bias), expected)
            method.apply_weights(layer, x, bias)
            torch.cuda.synchronize()
            graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph):
                result = method.apply_weights(layer, x, bias)
            errors = []
            for _ in range(2):
                x.copy_(torch.randn_like(x))
                graph.replay()
                errors.append(check(result, reference(x)))
            rows.append(dict(dtype='fp8', M=m, N=n, K=k, tgemm=bool(calls),
                             relative_l2=error, graph_relative_l2=errors))
            print(rows[-1], flush=True)

    for n, k in [(1728, 1152), (2152, 1152), (1152, 2152), (1152, 576)]:
        method = unquant.UnquantizedLinearMethod()
        layer = torch.nn.Module()
        layer.weight = torch.nn.Parameter(torch.randn(n, k, device='cuda', dtype=torch.bfloat16), False)
        canonical = layer.weight.detach().clone()
        method.process_weights_after_loading(layer)
        assert torch.equal(layer.weight, canonical)
        for m in [4, 256]:
            x = torch.randn(m, k, device='cuda', dtype=torch.bfloat16)
            bias = torch.randn(n, device='cuda', dtype=torch.bfloat16)
            reference = lambda z: z.float() @ canonical.float().t() + bias.float()
            error = check(method.apply(layer, x, bias), reference(x))
            method.apply(layer, x, bias)
            torch.cuda.synchronize()
            graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph):
                result = method.apply(layer, x, bias)
            errors = []
            for _ in range(2):
                x.copy_(torch.randn_like(x))
                graph.replay()
                errors.append(check(result, reference(x)))
            rows.append(dict(dtype='bf16', M=m, N=n, K=k, relative_l2=error,
                             graph_relative_l2=errors))
            print(rows[-1], flush=True)

(ROOT / 'results/sglang_validation.json').write_text(json.dumps(rows, indent=2))
print('PASS', len(rows), 'SGLang cases;', 2 * len(rows), 'changed-input graph replays', flush=True)
