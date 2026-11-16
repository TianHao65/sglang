import csv
import json
import statistics
from pathlib import Path

import pandas as pd

ROOT = Path('/workspace/projects/Qwen3.8/experiments/pr63_tgemm_tuning_host34_20261110')
before = json.loads((ROOT / 'results/before.json').read_text())
after = json.loads((ROOT / 'results/after.json').read_text())
key = lambda d: (d['family'], d['M'], d['N'], d['K'], d['dtype'], d['bias'], d['packed'])
assert len(before) == len(after) == 16
assert [key(d) for d in before] == [key(d) for d in after]
rows = []
accepted = {'ck_decode': [], 'tgemm': []}
lines = ['Kernel measurements on 34 / GPU 2; 16 rotating tensor sets.',
         'Five eager and three graph measurements per shape. Changes are after / before - 1.',
         'Candidate acceptance requires at least 3% lower median latency in both measurements.',
         'These are kernel timings, not model TTFT/TPOT or GSM8K results.', '',
         '| Family | M / N / K | Eager us before → after | Graph us before → after | Eager Δ | Graph Δ | Keep |',
         '|---|---|---:|---:|---:|---:|---|']
for b, a in zip(before, after):
    bm, am = statistics.median(b['us']), statistics.median(a['us'])
    bg, ag = statistics.median(b['graph_us']), statistics.median(a['graph_us'])
    eager_change, graph_change = 100 * (am / bm - 1), 100 * (ag / bg - 1)
    keep = eager_change <= -3 and graph_change <= -3
    if keep:
        accepted[a['family']].append(a)
    row = dict(family=a['family'], M=a['M'], N=a['N'], K=a['K'], dtype=a['dtype'],
               bias=a['bias'], packed=a['packed'], before_us=bm, after_us=am,
               eager_change_pct=eager_change, before_graph_us=bg, after_graph_us=ag,
               graph_change_pct=graph_change, libtype=a['config'].get('libtype') if a['config'] else None,
               accepted=keep)
    rows.append(row)
    lines.append(f"| {a['family']} | {a['M']} / {a['N']} / {a['K']} | {bm:.3f} → {am:.3f} | {bg:.3f} → {ag:.3f} | {eager_change:+.1f}% | {graph_change:+.1f}% | {'yes' if keep else 'base'} |")

with (ROOT / 'results/comparison.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
(ROOT / 'results/comparison.json').write_text(json.dumps(rows, indent=2))
(ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')

for family, selection, keys in [
    ('ck', 'ck_decode', ['gfx', 'cu_num', 'M', 'N', 'K', 'q_dtype_w']),
    ('tgemm', 'tgemm', ['gfx', 'cu_num', 'M', 'N', 'K', 'bias', 'dtype', 'outdtype', 'scaleAB', 'bpreshuffle']),
]:
    base = pd.read_csv(ROOT / 'configs' / (family + '_base.csv'))
    candidates = pd.read_csv(ROOT / 'configs' / (family + '_candidate.csv'))
    selected = []
    for d in accepted[selection]:
        mask = ((candidates.gfx == 'gfx942') & (candidates.cu_num == 80)
                & (candidates.M == d['M']) & (candidates.N == d['N']) & (candidates.K == d['K']))
        if family == 'ck':
            mask &= candidates.q_dtype_w == d['dtype']
        else:
            mask &= ((candidates.dtype == d['dtype']) & (candidates.bias == d['bias'])
                     & (candidates.bpreshuffle == d['packed']) & (candidates.outdtype == 'torch.bfloat16')
                     & (candidates.scaleAB == ('float8' in d['dtype'])))
        part = candidates.loc[mask]
        assert len(part) == 1, (d, part)
        selected.append(part)
    supplement = pd.concat(selected, ignore_index=True) if selected else candidates.iloc[:0]
    supplement.to_csv(ROOT / 'configs' / (family + '_accepted_rows.csv'), index=False)
    merged = pd.concat([base, supplement], ignore_index=True).drop_duplicates(keys, keep='last')
    merged.to_csv(ROOT / 'configs' / (family + '_accepted.csv'), index=False)
    print(family, 'accepted', len(supplement), flush=True)
