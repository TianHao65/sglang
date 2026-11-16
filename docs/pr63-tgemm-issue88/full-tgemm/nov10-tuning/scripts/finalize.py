import csv
import json
import statistics
from pathlib import Path

ROOT = Path('/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110')
before = json.loads((ROOT / 'results/before.json').read_text())
final = json.loads((ROOT / 'results/accepted.json').read_text())
selection = json.loads((ROOT / 'results/comparison.json').read_text())
validation = json.loads((ROOT / 'results/sglang_validation.json').read_text())
key = lambda d: (d['family'], d['M'], d['N'], d['K'], d['dtype'], d['bias'], d['packed'])
assert len(before) == len(final) == len(selection) == 16
assert len(validation) == 29
assert [key(d) for d in before] == [key(d) for d in final]
rows = []
lines = ['GEMM tuning on hjbog-srdc-34.amd.com / MI308X / gfx942 / 80 CUs, 2026-11-10.',
         'Qwen3.8 TP2 rank-local FP8 and BF16 ViT shapes; measurements use GPU 2.',
         'Before: default image configuration. Final: selected tuned configuration and rebuilt kernels.',
         'Image base SGLang 4d63dea with the local tgemm candidate; original AITER 514c166 restored for verification.',
         'Five eager and three graph samples per shape, 16 rotating tensor sets.',
         'All 16 GEMMs and 29 SGLang caller cases passed numerical and changed-input graph checks.',
         'These are operator timings, not end-to-end model TTFT/TPOT or GSM8K results.', '',
         '| Family | M / N / K | Eager us before → final | Graph us before → final | Eager Δ | Graph Δ | Config |',
         '|---|---|---:|---:|---:|---:|---|']
weak = []
for b, a, s in zip(before, final, selection):
    bm, am = statistics.median(b['us']), statistics.median(a['us'])
    bg, ag = statistics.median(b['graph_us']), statistics.median(a['graph_us'])
    eager, graph = 100 * (am / bm - 1), 100 * (ag / bg - 1)
    selected = s['accepted']
    if selected and (eager > -3 or graph > -3):
        weak.append((a['family'], a['M'], a['N'], a['K'], eager, graph))
    row = dict(family=a['family'], M=a['M'], N=a['N'], K=a['K'], dtype=a['dtype'],
               bias=a['bias'], packed=a['packed'], before_us=bm, final_us=am,
               eager_change_pct=eager, before_graph_us=bg, final_graph_us=ag,
               graph_change_pct=graph, selected=selected,
               libtype=a['config'].get('libtype') if a['config'] else 'default')
    rows.append(row)
    lines.append(f"| {a['family']} | {a['M']} / {a['N']} / {a['K']} | {bm:.3f} → {am:.3f} | {bg:.3f} → {ag:.3f} | {eager:+.1f}% | {graph:+.1f}% | {'tuned' if selected else 'base'} |")
assert not weak, ('Selected configurations require review', weak)
with (ROOT / 'results/final_comparison.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
(ROOT / 'results/final_comparison.json').write_text(json.dumps(rows, indent=2))
(ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
print(json.dumps([d for d in rows if d['selected']], indent=2))
