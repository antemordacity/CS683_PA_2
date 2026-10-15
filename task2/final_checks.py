#!/usr/bin/env python3
"""Check a selected full run and the current tools without historical datasets."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'task2'))
from run import find_traces


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',required=True,help='Completed full-run directory')
    p.add_argument('--output',required=True,help='New directory for check logs and outputs')
    a=p.parse_args()
    result=Path(a.run_dir).resolve()
    out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=False)
    with (out/'checks.txt').open('x') as f:
        def check(command):
            f.write('$ '+' '.join(command)+'\n'); f.flush()
            proc=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            f.write('exit='+str(proc.returncode)+'\n'); f.flush()
            assert proc.returncode==0, command
        check(['bash','-n','run_task2.sh'])
        check(['git','-c','core.autocrlf=true','diff','--check'])
        check([sys.executable,'task2/test.py','--output',str(out/'tests')])
        check([sys.executable,'task2/audit.py','--run-dir',str(result),'--output',str(out/'audit')])
        check([sys.executable,'task2/analyze.py','--input',str(result/'logs'),'--output',str(out/'analysis'),'--expected','25000000'])
        assert len(list((out/'analysis').glob('*.png')))==10
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for n in range(1,4): (d/f'tRaCe{n}.champsimtrace.gz').touch()
            assert len(find_traces(d))==3
            (d/'Trace1.xz').touch()
            for target in [d,d/'missing']:
                try: find_traces(target)
                except ValueError: pass
                else: raise AssertionError('ambiguous/missing traces accepted')
        f.write('PASS trace discovery and ambiguity/missing rejection\nALL FINAL CHECKS PASSED\n')
    print('PASS final checks:',out/'checks.txt')

if __name__=='__main__': main()
