#!/usr/bin/env python3
"""Isolated builds using the source selections in build_champsim.sh.
Never overwrites the repository's generated .cc files or existing build outputs.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
POLICIES = {'lru': ('lru', None), 'rrip': ('rrip', None),
            'irrip_v1': ('irrip', 1), 'irrip_v2': ('irrip', 2),
            'irrip_v3': ('irrip', 3), 'dyn_irrip': ('dyn_irrip', None)}


def build(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    stage = out / 'source'
    stage.mkdir()
    hashes = {}
    for folder in ('inc', 'src', 'branch', 'replacement', 'prefetcher'):
        shutil.copytree(ROOT / folder, stage / folder)
        for p in (ROOT / folder).iterdir():
            if p.is_file():
                hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    shutil.copyfile(stage/'branch/hashed_perceptron.bpred', stage/'branch/branch_predictor.cc')
    for level in ('l1i', 'l1d', 'l2c', 'llc', 'itlb', 'dtlb', 'stlb'):
        shutil.copyfile(stage/f'prefetcher/no.{level}_pref', stage/f'prefetcher/{level}_prefetcher.cc')
    for level in ('btb', 'l1i', 'l1d', 'l2c', 'llc', 'itlb', 'dtlb', 'stlb'):
        shutil.copyfile(stage/f'replacement/lru.{level}_repl', stage/f'replacement/{level}_replacement.cc')
    cxx = os.environ.get('CXX', 'g++')
    flags = ['-Wall', '-g', '-std=c++11', '-O3', '-I'+str(stage/'inc')]
    (out/'obj').mkdir()
    (out/'bin').mkdir()
    commands = []
    def compile_source(source, name, extra=()):
        obj = out/'obj'/f'{name}.o'
        cmd = [cxx, *flags, *extra, '-x', 'c++', '-c', str(source), '-o', str(obj)]
        commands.append(cmd)
        with (out/f'{name}.log').open('w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        return obj
    sources = sorted(p for folder in ('src', 'branch', 'replacement', 'prefetcher')
                     for p in (stage/folder).glob('*.cc') if p.name != 'l2c_replacement.cc')
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('TASK2_JOBS', '2'))) as pool:
            objects = list(pool.map(lambda p: compile_source(p, p.parent.name+'_'+p.stem), sources))
        for name, (policy, version) in POLICIES.items():
            extra = ['-DIRRIP_VERSION='+str(version)] if version else []
            obj = compile_source(stage/f'replacement/{policy}.l2c_repl', name, extra)
            cmd = [cxx, *map(str, objects), str(obj), '-static', '-o', str(out/'bin'/name)]
            commands.append(cmd)
            with (out/f'{name}_link.log').open('w') as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
            print('Built', name, flush=True)
    finally:
        (out/'manifest.json').write_text(json.dumps({
            'compiler': subprocess.check_output([cxx, '--version'], text=True).splitlines()[0],
            'flags': flags, 'source_sha256': hashes, 'commands': commands,
            'configuration': '1 CPU, hashed_perceptron, all prefetchers no, all other replacements LRU'
        }, indent=2)+'\n')
    return out/'bin'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    build(args.output)
