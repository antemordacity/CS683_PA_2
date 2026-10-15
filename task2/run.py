#!/usr/bin/env python3
"""Run Task 2 without overwriting any previous results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from build import build, ROOT
from analyze import analyze, CONFIGS
sys.path.insert(0, str(ROOT))
from parse_results import read_stats


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def find_traces(directory):
    directory = Path(directory).expanduser().resolve()
    traces = {}
    for n in range(1,4):
        accepted = {f'trace{n}{middle}.{ext}' for middle in ('', '.champsimtrace') for ext in ('gz', 'xz')}
        matches = sorted(p for p in directory.iterdir() if p.is_file() and p.name.lower() in accepted) if directory.is_dir() else []
        if len(matches) != 1:
            raise ValueError(f'{directory}: need exactly one Trace{n}.gz/.xz or trace{n}.champsimtrace.gz/.xz; found {len(matches)}')
        traces[f'Trace{n}'] = matches[0]
    return traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-dir', required=True)
    parser.add_argument('--mode', required=True, choices=['smoke', 'full'])
    args = parser.parse_args()
    traces = find_traces(args.trace_dir)  # Fail before expensive compilation.
    synthetic = (Path(args.trace_dir).expanduser()/'.SYNTHETIC_TEST_ONLY').exists()
    for command in [os.environ.get('CXX','g++'), 'gzip', 'xz']:
        if not shutil.which(command): raise ValueError(f'Missing command: {command}; see TASK2_README.md')
    import matplotlib  # Fail early with an actionable package name.
    budget = 100000 if args.mode == 'smoke' else 25000000
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = Path(tempfile.mkdtemp(prefix=f'task2_{args.mode}_{stamp}_', dir=ROOT/'results'))
    print('Results:', out, flush=True)
    # ChampSim invokes a shell with an unquoted trace path. Use safe absolute
    # aliases and a stable third-from-last token (the simulator's seed input).
    aliases = Path(tempfile.mkdtemp(prefix='cs683_task2_', dir='/tmp'))
    manifest = {'mode':args.mode, 'warmup':budget, 'simulation':budget,
                'provenance':'SYNTHETIC TEST ONLY' if synthetic else 'user-provided assignment traces',
                'trace_alias_directory':str(aliases), 'traces':{}, 'runs':[], 'status':'running'}
    def save_manifest():
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    save_manifest()
    try:
        for tr, path in traces.items():
            alias = aliases/f'{tr}.champsimtrace{path.suffix.lower()}'
            alias.symlink_to(path)
            subprocess.run(['gzip' if path.suffix.lower()=='.gz' else 'xz', '-t', str(path)], check=True)
            manifest['traces'][tr] = {'source':str(path), 'alias':str(alias), 'sha256':digest(path), 'seed_token':tr}
        bins = build(out/'build')
        subprocess.run([sys.executable, str(ROOT/'task2/test.py'), '--output', str(out/'tests')], check=True)
        logs = out/'logs'; logs.mkdir()
        for config in CONFIGS:
            for tr in traces:
                binary = bins/('dyn_irrip' if config.startswith('dyn_') else config)
                command = [str(binary), '-warmup_instructions', str(budget), '-simulation_instructions', str(budget), '-traces', manifest['traces'][tr]['alias']]
                env = os.environ.copy(); env.pop('TASK2_THRESHOLD', None)
                if config.startswith('dyn_'): env['TASK2_THRESHOLD'] = config[4:]
                run = {'config':config, 'trace':tr, 'command':command, 'threshold':env.get('TASK2_THRESHOLD'), 'binary_sha256':digest(binary)}
                manifest['runs'].append(run)
                save_manifest()
                print('Running', config, tr, flush=True)
                with (logs/f'{config}_{tr}.txt').open('w') as f:
                    subprocess.run(command, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
                read_stats(logs/f'{config}_{tr}.txt')
        # Repeat exactly the same dynamic configuration and compare all parsed
        # counts, metrics, decisions and switch totals; wall-clock text may differ.
        repeat = next(r for r in manifest['runs'] if r['config']=='dyn_0.25' and r['trace']=='Trace1')
        env = os.environ.copy(); env['TASK2_THRESHOLD']='0.25'
        with (logs/'repeat_dyn_0.25_Trace1.txt').open('w') as f:
            subprocess.run(repeat['command'], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
        if read_stats(logs/'repeat_dyn_0.25_Trace1.txt') != read_stats(logs/'dyn_0.25_Trace1.txt'):
            raise ValueError('Reproducibility check failed for dynamic 0.25 Trace1')
        manifest['repeat'] = dict(repeat, passed=True)
        analyze(logs, out/'analysis', expected=budget, synthetic=synthetic)
        manifest['status']='complete'
        print('Completed:', out/'analysis/TABLES.md', flush=True)
    except BaseException:
        manifest['status']='failed_or_interrupted'
        raise
    finally:
        save_manifest()

if __name__ == '__main__':
    try:
        main()
    except (ValueError, ImportError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Task 2 failed: {error}')
