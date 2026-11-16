import csv
import json
import statistics
from pathlib import Path

ROOT = Path('/home/hatian/workspace/projects/Qwen3.8/experiments/pr63_tgemm_ete_11k350_host34_20261110')
outcomes = [json.loads(p.read_text()) for p in sorted((ROOT / 'results').glob('*/OUTCOME.json'))]
assert len(outcomes) == 4
assert {(x['arm'], x['cycle']) for x in outcomes} == {('before', 1), ('before', 2), ('after', 1), ('after', 2)}
for key in ['input_lens_sha256', 'output_lens_sha256']:
    assert len({x['metrics'][key] for x in outcomes}) == 1, key
assert len({json.dumps(x['effective'], sort_keys=True) for x in outcomes}) == 1
rows = []
for x in outcomes:
    m = x['metrics']
    rows.append(dict(arm=x['arm'], cycle=x['cycle'], completed=m['completed'],
                     TTFT_ms=m['mean_ttft_ms'], TPOT_ms=m['mean_tpot_ms'], ETE_ms=m['mean_e2el_ms'],
                     output_tokens_s=m['output_throughput'], QPS=1000 / m['mean_e2el_ms'],
                     QPS_per_GPU=500 / m['mean_e2el_ms'], actual_input_mean=m['mean_input_len'],
                     actual_output_mean=m['mean_output_len']))
with (ROOT / 'results/rounds.csv').open('w') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
fields = ['TTFT_ms', 'TPOT_ms', 'ETE_ms', 'output_tokens_s', 'QPS', 'QPS_per_GPU']
summary = {}
for arm in ['before', 'after']:
    selected = [x for x in rows if x['arm'] == arm]
    summary[arm] = {key: statistics.mean(x[key] for x in selected) for key in fields}
    summary[arm]['ETE_range_ms'] = [min(x['ETE_ms'] for x in selected), max(x['ETE_ms'] for x in selected)]
summary['change_pct'] = {key: 100 * (summary['after'][key] / summary['before'][key] - 1) for key in fields}
summary['completed_formal_requests'] = sum(x['completed'] for x in rows)
summary['workload'] = json.loads((ROOT / 'review/MANIFEST.json').read_text())['workload']
(ROOT / 'results/SUMMARY.json').write_text(json.dumps(summary, indent=2))
lines = ['Qwen3.8 TP2 tgemm ETE comparison, hjbog-srdc-34.amd.com (PTL), GPUs 2/3, 2026-11-10.',
         '11K/350 means, sigma=4, prefix=0.35, con1, one worker, MTP/radix enabled.',
         'Same local tgemm SGLang 4d63dea snapshot / AITER 514c166. Before uses base tables; after uses selected tuned tables.',
         'Two independent startups per arm; before/after/after/before; discarded repetition before each 128-request formal round.',
         'All 512 formal requests completed without client errors. Generated actual input/output length arrays match across all rounds.', '',
         '| Arm | TTFT ms | TPOT ms | ETE ms | Output tok/s | QPS | QPS/GPU |',
         '|---|---:|---:|---:|---:|---:|---:|']
for arm in ['before', 'after']:
    m = summary[arm]
    lines.append(f"| {arm} | {m['TTFT_ms']:.3f} | {m['TPOT_ms']:.3f} | {m['ETE_ms']:.3f} | {m['output_tokens_s']:.3f} | {m['QPS']:.4f} | {m['QPS_per_GPU']:.5f} |")
lines += ['', 'Changes are after / before - 1; negative latency changes mean lower latency.',
          json.dumps(summary['change_pct'], indent=2), '',
          'Per-start ETE ranges (two starts are not a confidence interval):',
          json.dumps({a: summary[a]['ETE_range_ms'] for a in ['before', 'after']}, indent=2), '',
          'Lengths are generator means; text decoding/re-tokenization changes server input lengths, and prefix ratio is not a fixed per-request hit ratio.',
          'QPS here is con1 / mean ETE seconds. Raw client collector throughput is preserved separately.',
          'Arithmetic smoke checks passed; this is not a full GSM8K assessment. No PR was updated.',
          '[Per-round CSV](results/rounds.csv) · [Summary JSON](results/SUMMARY.json)']
(ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(summary, indent=2))
