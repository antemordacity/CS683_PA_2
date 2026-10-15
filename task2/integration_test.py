#!/usr/bin/env python3
"""End-to-end synthetic fixture checks. These are NOT Trace1/2/3 benchmarks."""
import argparse
import gzip
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from parse_results import read_stats


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=False)
    trace=out/'synthetic.champsimtrace.gz'
    # input_instr: 8-byte IP, 8 byte flags/registers, six 8-byte addresses.
    record=struct.Struct('<Q8B6Q'); assert record.size==64
    with gzip.GzipFile(filename=str(trace),mode='wb',mtime=0) as f:
        for i in range(350000):
            # Phase changes exercise both instruction and data pressure.
            phase=(i//20000)%3
            ip=0x400000+(i % (32768 if phase==0 else 512))*64
            data=0x10000000+(i % (65536 if phase==1 else 2048))*64
            f.write(record.pack(ip,0,0,1,0,1,0,0,0,0,0,data if i%3==0 else 0,0,0,0))
    configs=['lru','rrip','irrip_v1','irrip_v2','irrip_v3']+['dyn_'+t for t in ['0.00','0.10','0.20','0.25','0.35','0.50','1.00']]
    rows=[]; bins=Path(a.build).resolve()/'bin'
    for config in configs+['repeat_dyn_0.25']:
        actual=config.replace('repeat_','')
        env=os.environ.copy(); env.pop('TASK2_THRESHOLD',None)
        if actual.startswith('dyn_'): env['TASK2_THRESHOLD']=actual[4:]
        binary=bins/('dyn_irrip' if actual.startswith('dyn_') else actual)
        cmd=[str(binary),'-warmup_instructions','100000','-simulation_instructions','100000','-traces',str(trace)]
        log=out/f'{config}.txt'
        with log.open('w') as f:
            subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
        stats=read_stats(log)
        rows.append(dict(config=config,statistics=stats,command=cmd))
        print('PASS synthetic',config,flush=True)
    assert rows[-1]['statistics']==next(r['statistics'] for r in rows if r['config']=='dyn_0.25')
    for r in rows:
        if r['config'].startswith('dyn_'):
            d=r['statistics']['dynamic']
            assert float(d['threshold'])==float(r['config'][4:])
    assert any(int(r['statistics'].get('dynamic',{}).get('switches',0))>0 for r in rows)
    # RRIP endpoint never enables I-RRIP once there is non-instruction traffic.
    d=next(r['statistics']['dynamic'] for r in rows if r['config']=='dyn_1.00')
    assert d['mode']=='RRIP'
    (out/'summary.json').write_text(json.dumps({'provenance':'SYNTHETIC TEST ONLY, not assignment traces','passed':True,'runs':rows},indent=2)+'\n')

if __name__=='__main__': main()
