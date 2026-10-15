#!/usr/bin/env python3
"""Validate logs and generate tables plus all five comparison/sensitivity plots."""
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parse_results import read_stats

STATIC = ['lru', 'rrip', 'irrip_v1', 'irrip_v2', 'irrip_v3']
THRESHOLDS = ['0.10', '0.20', '0.25', '0.35', '0.50']
CONFIGS = STATIC + ['dyn_'+t for t in THRESHOLDS]
METRICS = {'ipc': 'IPC', 'speedup': 'Speedup relative to LRU', 'load_mpki': 'L2C load MPKI',
           'instr_mpki': 'L2 instruction load MPKI', 'data_mpki': 'L2 data load MPKI'}


def analyze(input_dir, output_dir, historical=False, expected=None, synthetic=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source, out = Path(input_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    configs = STATIC if historical else CONFIGS
    rows = []
    for trace in ['Trace1', 'Trace2', 'Trace3']:
        baseline = read_stats(source/f'lru_{trace}.txt')['ipc']
        for config in configs:
            path = source/f'{config}_{trace}.txt'
            r = read_stats(path)
            if expected and (r['warmup'] != expected or r['requested'] != expected):
                raise ValueError(f'{path}: expected {expected} warmup and ROI instructions')
            if config.startswith('dyn_'):
                if 'dynamic' not in r or float(r['dynamic']['threshold']) != float(config[4:]):
                    raise ValueError(f'{path}: missing/mismatched threshold diagnostics')
            r.update(trace=trace, config=config, speedup=r['ipc']/baseline,
                     provenance='SYNTHETIC TEST ONLY' if synthetic else ('historical logs; newly validated' if historical else 'new run'), source=str(path))
            rows.append(r)
    budgets = {(r['warmup'], r['requested']) for r in rows}
    if len(budgets) != 1: raise ValueError('Mixed instruction budgets')
    (out/'validated.json').write_text(json.dumps(rows, indent=2)+'\n')
    fields = ['trace', 'config', *METRICS, 'instructions', 'cycles', 'accesses', 'hits', 'misses', 'warmup', 'requested', 'provenance', 'source']
    with (out/'metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
    label = 'Historical logs (newly validated)' if historical else f'New runs ({next(iter(budgets))[1]:,} ROI instructions)'
    if synthetic: label = 'SYNTHETIC TEST ONLY - ' + label
    lines = [f'# {label}', '', '| Trace | Policy | IPC | Speedup / LRU | L2C load MPKI | Instruction MPKI | Data MPKI |',
             '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['trace']} | {r['config']} | {r['ipc']:.6f} | {r['speedup']:.6f} | {r['load_mpki']:.5f} | {r['instr_mpki']:.5f} | {r['data_mpki']:.5f} |")
    lines += ['', 'Speedup uses the reported IPC. Counts independently validate IPC and MPKI within simulator printing precision.']
    if historical:
        for tr in ['Trace1', 'Trace2', 'Trace3']:
            a, b = read_stats(source/f'lru_{tr}.txt'), read_stats(source/f'lru_check_{tr}.txt')
            if a != b: raise ValueError(f'{tr}: historical LRU rerun differs')
        lines += ['', 'Historical LRU and lru_check statistics match on all three traces.',
                  'Dynamic measurements are unavailable in this historical dataset; no threshold plot is inferred.']
    else:
        lines += ['', '## Dynamic diagnostics', '', '| Trace | Threshold | Metric | Switches | Follower RRIP updates | Follower I-RRIP updates |', '|---|---:|---:|---:|---:|---:|']
        for r in rows:
            if 'dynamic' in r:
                d = r['dynamic']
                lines.append(f"| {r['trace']} | {d['threshold']} | {d['metric']} | {d['switches']} | {d['follower_rrip_updates']} | {d['follower_irrip_updates']} |")
        lines += ['', '## Threshold sensitivity', '',
                  'Each comparison uses the same trace and instruction budget. These observations do not establish a universal best threshold.']
        for tr in ['Trace1','Trace2','Trace3']:
            subset = [r for r in rows if r['trace']==tr]
            dynamic = [r for r in subset if 'dynamic' in r]
            best = max(dynamic, key=lambda r:r['ipc'])
            worst = min(dynamic, key=lambda r:r['ipc'])
            tied = [r['config'][4:] for r in dynamic if r['ipc']==best['ipc']]
            rrip = next(r for r in subset if r['config']=='rrip')
            static = next(r for r in subset if r['config']=='irrip_v3')
            lines += ['', f"- {tr}: dynamic IPC spans {worst['ipc']:.6f} to {best['ipc']:.6f}; highest reported IPC at threshold(s) {', '.join(tied)}. Best dynamic IPC / RRIP = {best['ipc']/rrip['ipc']:.6f}; best dynamic IPC / static V3 = {best['ipc']/static['ipc']:.6f}."]
        lines += ['', 'A tie at printed precision does not prove all internal behavior is identical. Read the switch counts and follower update counts above.']
    (out/'TABLES.md').write_text('\n'.join(lines)+'\n')
    for metric, ylabel in METRICS.items():
        fig, ax = plt.subplots(figsize=(12, 5))
        width = 0.8/len(configs)
        for i, config in enumerate(configs):
            values = [next(r[metric] for r in rows if r['config']==config and r['trace']==tr) for tr in ['Trace1','Trace2','Trace3']]
            ax.bar([x-0.4+width*(i+0.5) for x in range(3)], values, width, label=config)
        ax.set_xticks(range(3), ['Trace1', 'Trace2', 'Trace3'])
        ax.set_ylabel(ylabel); ax.set_title(label); ax.legend(fontsize=8, ncol=3)
        if metric == 'speedup': ax.axhline(1, color='black', linewidth=.7)
        fig.tight_layout(); fig.savefig(out/f'{metric}.png', dpi=160); plt.close(fig)
        if not historical:
            fig, axes = plt.subplots(1, 3, figsize=(15, 4))
            for ax, tr in zip(axes, ['Trace1','Trace2','Trace3']):
                subset = {r['config']:r for r in rows if r['trace']==tr}
                ax.plot([float(t) for t in THRESHOLDS], [subset['dyn_'+t][metric] for t in THRESHOLDS], 'o-', label='Dynamic I-RRIP')
                for config, color, style in [('lru','black',':'), ('rrip','tab:orange','--'), ('irrip_v3','tab:green','-.')]:
                    ax.axhline(subset[config][metric], color=color, linestyle=style, label=config)
                ax.set_title(tr); ax.set_xlabel('Threshold'); ax.set_ylabel(ylabel); ax.legend(fontsize=8)
            fig.suptitle(label); fig.tight_layout(); fig.savefig(out/f'sensitivity_{metric}.png', dpi=160); plt.close(fig)
    print(f'Validated {len(rows)} logs; tables and plots: {out}')
    report = lines + ['', '## Plots', '']
    for metric, ylabel in METRICS.items():
        report += [f'![{ylabel}]({metric}.png)', '']
        if not historical:
            report += [f'![Threshold sensitivity: {ylabel}](sensitivity_{metric}.png)', '']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True); p.add_argument('--output', required=True)
    p.add_argument('--historical', action='store_true'); p.add_argument('--expected', type=int)
    p.add_argument('--synthetic', action='store_true', help='Label every output as synthetic test data')
    args = p.parse_args()
    analyze(args.input, args.output, args.historical, args.expected, args.synthetic)
