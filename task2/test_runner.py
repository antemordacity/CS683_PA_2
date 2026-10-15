#!/usr/bin/env python3
"""Exercise the complete smoke workflow on explicitly labeled generated input."""
import argparse
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--trace',default=str(ROOT/'results/task2_audit/synthetic/synthetic.champsimtrace.gz'))
p.add_argument('--output',required=True,help='New directory for fixture aliases and the runner log')
a=p.parse_args()
trace=Path(a.trace).resolve()
if not trace.is_file(): raise SystemExit('Generate the synthetic trace with integration_test.py first')
out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=False)
fixture=out/'inputs'; fixture.mkdir()
(fixture/'.SYNTHETIC_TEST_ONLY').write_text('Generated fixture, NOT the assignment Trace1/Trace2/Trace3.\n')
for n in range(1,4):
    (fixture/f'Trace{n}.gz').symlink_to(trace)
with (out/'runner.log').open('w') as log:
    subprocess.run(['bash',str(ROOT/'run_task2.sh'),'--trace-dir',str(fixture),'--mode','smoke'],stdout=log,stderr=subprocess.STDOUT,check=True)
print('PASS complete smoke runner on labeled synthetic inputs; see',out/'runner.log')
