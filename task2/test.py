#!/usr/bin/env python3
"""Actual policy source tests and parser rejection tests, no benchmark claims."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parse_results import read_stats

class ParserTests(unittest.TestCase):
    def test_historical_all(self):
        for path in (ROOT/'results').glob('*_Trace*.txt'):
            read_stats(path)
    def test_reject_corruption(self):
        original = (ROOT/'results/lru_Trace1.txt').read_text()
        changes = [original.replace('ChampSim completed all CPUs','incomplete'),
                   original.replace('CPU 0 cumulative IPC: 0.232345', 'CPU 0 cumulative IPC: 0.9'),
                   original.replace('L2C DATA LOAD MPKI:', 'missing data:'),
                   original.replace('Simulation Instructions: 25000000', 'Simulation Instructions: 1')]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'bad.txt'
            for text in changes:
                path.write_text(text)
                with self.assertRaises(ValueError): read_stats(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True)
    args=parser.parse_args(); out=Path(args.output).resolve(); out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy(); env['TASK2_THRESHOLD']='0.25'
    results=[]
    for policy,version,name in [(0,0,'lru'),(1,0,'rrip'),(2,1,'irrip_v1'),(2,2,'irrip_v2'),(2,3,'irrip_v3'),(3,0,'dynamic')]:
        binary=out/name
        command=[os.environ.get('CXX','g++'),'-std=c++11','-O1','-g','-fsanitize=undefined',
                 '-fno-sanitize-recover=all','-I'+str(ROOT/'task2/tests'),'-DTEST_POLICY='+str(policy)]
        if version: command+=['-DIRRIP_VERSION='+str(version)]
        command += [str(ROOT/'task2/tests/policies.cc'),'-o',str(binary)]
        subprocess.run(command,check=True)
        first=subprocess.check_output([str(binary)],env=env,text=True)
        second=subprocess.check_output([str(binary)],env=env,text=True)
        assert first==second, name+' not reproducible'
        (out/f'{name}.txt').write_text(first)
        results.append({'name':name,'passed':True,'repeated_identically':True,'compiler_command':command})
        print('PASS',name,flush=True)
    for value in ('nan','inf','-0.1','1.1','abc','0.25junk',''):
        env['TASK2_THRESHOLD']=value
        p=subprocess.run([str(out/'dynamic')],env=env,text=True,capture_output=True)
        assert p.returncode!=0 and 'must be a finite number' in p.stderr
    env['TASK2_THRESHOLD']='0.25'
    equivalence={}
    for name,policy,mode in [('rrip',1,0),('dynamic_rrip',3,0),('irrip3',2,1),('dynamic_irrip3',3,1)]:
        binary=out/('equivalence_'+name)
        subprocess.run([os.environ.get('CXX','g++'),'-std=c++11','-O1',
                        '-fsanitize=undefined','-fno-sanitize-recover=all',
                        '-I'+str(ROOT/'task2/tests'),'-DTEST_POLICY='+str(policy),
                        '-DIRRIP_VERSION=3','-DEQUIVALENCE_MODE='+str(mode),
                        str(ROOT/'task2/tests/policies.cc'),'-o',str(binary)],check=True)
        output=subprocess.check_output([str(binary)],env=env,text=True)
        equivalence[name]=re.search(r'DIGEST (\d+)',output).group(1)
    assert equivalence['rrip']==equivalence['dynamic_rrip']
    assert equivalence['irrip3']==equivalence['dynamic_irrip3']
    print('PASS static/dynamic equivalence over 10000 events per mode')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ParserTests)
    with (out/'parser.txt').open('w') as log:
        success=unittest.TextTestRunner(stream=log,verbosity=2).run(suite).wasSuccessful()
    assert success, 'parser tests failed'
    (out/'summary.json').write_text(json.dumps({'policies':results,'equivalence_digests':equivalence,'invalid_threshold_cases':7,'parser_tests':2,'passed':True},indent=2)+'\n')
    print('PASS invalid thresholds and parser tests')

if __name__=='__main__': main()
