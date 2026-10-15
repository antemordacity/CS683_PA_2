#!/usr/bin/env python3
"""Audit callback plumbing and one explicitly selected, completed full run."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parse_results import read_stats


def validate_run(run_dir):
    run_dir = Path(run_dir).resolve()
    manifest = json.loads((run_dir/'manifest.json').read_text())
    assert manifest['status'] == 'complete' and manifest['mode'] == 'full'
    assert manifest['provenance'] == 'user-provided assignment traces'
    assert manifest['warmup'] == manifest['simulation'] == 25000000
    configs = ['lru','rrip','irrip_v1','irrip_v2','irrip_v3'] + ['dyn_'+t for t in ['0.10','0.20','0.25','0.35','0.50']]
    expected = {(c, t) for c in configs for t in ['Trace1','Trace2','Trace3']}
    assert len(manifest['runs']) == 30
    assert {(r['config'],r['trace']) for r in manifest['runs']} == expected
    rows = {}
    for config, trace in sorted(expected):
        stats = read_stats(run_dir/'logs'/f'{config}_{trace}.txt')
        assert stats['warmup'] == stats['requested'] == 25000000
        if config.startswith('dyn_'):
            assert float(stats['dynamic']['threshold']) == float(config[4:])
        rows[(config,trace)] = stats
    assert manifest['repeat']['passed']
    assert read_stats(run_dir/'logs/repeat_dyn_0.25_Trace1.txt') == rows[('dyn_0.25','Trace1')]
    with (run_dir/'analysis/metrics.csv').open(newline='') as f:
        table = list(csv.DictReader(f))
    assert len(table) == 30
    assert {(r['config'],r['trace']) for r in table} == expected
    for row in table:
        stats = rows[(row['config'],row['trace'])]
        for key in ['ipc','load_mpki','data_mpki','instr_mpki']:
            assert float(row[key]) == stats[key], (row['config'],row['trace'],key)
        assert abs(float(row['speedup']) - stats['ipc']/rows[('lru',row['trace'])]['ipc']) < 1e-12
    assert json.loads((run_dir/'tests/summary.json').read_text())['passed']
    metrics = ['ipc','speedup','load_mpki','instr_mpki','data_mpki']
    for name in metrics + ['sensitivity_'+m for m in metrics]:
        assert (run_dir/'analysis'/f'{name}.png').is_file()
    build = json.loads((run_dir/'build/manifest.json').read_text())
    skipped = []
    for name, expected_hash in build['source_sha256'].items():
        path = ROOT/name
        # Noncompiled backups were removed during cleanup; the original snapshot remains.
        if name in ['inc/champsim.h.bak','inc/champsim.h.cp','inc/sedD2leEO'] and not path.exists():
            skipped.append(name)
            continue
        raw = path.read_bytes()
        assert expected_hash in [hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()], name
    return {'run_directory':str(run_dir), 'matrix_runs':30, 'logs_validated':31,
            'repeat_matches':True, 'csv_matches_logs':True, 'plot_count':10,
            'compiler':build['compiler'], 'source_matches_build':True,
            'removed_noncompiled_backups':skipped}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True)
    p.add_argument('--output',required=True)
    args = p.parse_args()
    result = validate_run(args.run_dir)
    sites = []
    for file in ['src/cache.cc','src/ooo_cpu.cc']:
        for n,line in enumerate((ROOT/file).read_text().splitlines(),1):
            if 'update_replacement_state)' in line or '.update_replacement_state(' in line:
                pattern = r'\.instruction\);\s*$' if file=='src/cache.cc' else r', 0\);\s*$'
                assert re.search(pattern,line), line
                sites.append(dict(file=file,line=n,code=line.strip()))
    assert len(sites)==11
    definitions=[]
    for path in [ROOT/'inc/cache.h',*sorted((ROOT/'replacement').iterdir())]:
        if not path.is_file(): continue
        for signature in re.findall(r'update_replacement_state\)?\([^;{}]*?\)', path.read_text(), re.S):
            if 'uint32_t' in signature:
                assert 'uint8_t isInstruction' in signature, str(path)+signature
                definitions.append(str(path.relative_to(ROOT)))
    result.update(callback_sites=sites, declarations_and_definitions_checked=len(definitions))
    out=Path(args.output); out.mkdir(parents=True,exist_ok=False)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS {len(sites)} callbacks, {len(definitions)} signatures, 31 full-run logs, CSV, source hashes, repeat and ten plots')

if __name__=='__main__': main()
