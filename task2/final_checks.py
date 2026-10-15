#!/usr/bin/env python3
"""Final independent metadata/automation checks; preserves existing evidence."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'task2'))
from parse_results import read_stats
from run import find_traces
import run as runner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',required=True,help='New directory for check logs and outputs')
args=p.parse_args()
out=Path(args.output).resolve(); out.mkdir(parents=True,exist_ok=False)
log=out/'checks.txt'
with log.open('x') as f:
    def check(command):
        f.write('$ '+' '.join(command)+'\n'); f.flush()
        result=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        f.write('exit='+str(result.returncode)+'\n'); f.flush()
        assert result.returncode==0, command
    check(['bash','-n','run_task2.sh'])
    # Match the Windows checkout's newline conversion without changing Git config.
    check(['git','-c','core.autocrlf=true','diff','--check'])
    check([sys.executable,'task2/test.py','--output',str(out/'tests')])
    check([sys.executable,'task2/audit.py',str(out/'source')])
    check([sys.executable,'task2/analyze.py','--input','results','--output',str(out/'historical'),'--historical','--expected','25000000'])
    result=ROOT/'results/task2_smoke_20261014T234839Z_n_l4t8zf'
    check([sys.executable,'task2/analyze.py','--input',str(result/'logs'),'--output',str(out/'synthetic_analysis'),'--expected','100000','--synthetic'])
    manifest=json.loads((result/'manifest.json').read_text())
    assert manifest['status']=='complete' and manifest['repeat']['passed']
    assert len(manifest['runs'])==30 and manifest['provenance']=='SYNTHETIC TEST ONLY'
    assert len(list((out/'synthetic_analysis').glob('*.png')))==10
    # Verify every build artifact still corresponds to the final simulator source.
    import hashlib
    built=json.loads((ROOT/'results/task2_audit/build/manifest.json').read_text())
    for path,sha in built['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    f.write('PASS build hashes match final simulator source; runner matrix, provenance, repeat and ten plots\n')
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp)
        for n in range(1,4): (d/f'tRaCe{n}.champsimtrace.gz').touch()
        assert len(find_traces(d))==3
        (d/'Trace1.xz').touch()
        try: find_traces(d)
        except ValueError: pass
        else: raise AssertionError('ambiguous traces accepted')
        try: find_traces(d/'missing')
        except ValueError: pass
        else: raise AssertionError('missing traces accepted')
    # Exercise the runner's failure manifest without invoking a second build:
    # use the real synthetic inputs and raise a deliberate build exception.
    created=[]
    original=tempfile.mkdtemp
    def record_directory(*args,**kwargs):
        path=original(*args,**kwargs)
        if kwargs.get('dir')==ROOT/'results': created.append(Path(path))
        return path
    args=['run.py','--trace-dir',str(ROOT/'results/task2_audit/synthetic_runner_inputs'),'--mode','smoke']
    with patch.object(sys,'argv',args), patch.object(runner,'build',side_effect=RuntimeError('injected test failure')), patch.object(runner.tempfile,'mkdtemp',side_effect=record_directory):
        try: runner.main()
        except RuntimeError as error: assert str(error)=='injected test failure'
        else: raise AssertionError('injected failure lost')
    assert json.loads((created[0]/'manifest.json').read_text())['status']=='failed_or_interrupted'
    f.write('PASS trace discovery, ambiguity/missing rejection, and retained failed-run manifest\n')
    f.write('ALL FINAL CHECKS PASSED\n')
print('PASS final checks:',log)
