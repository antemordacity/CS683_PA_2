#!/usr/bin/env python3
"""Record callback plumbing and consistency of the original table."""
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from parse_results import read_stats

def main():
    out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=False)
    sites=[]
    for file in ['src/cache.cc','src/ooo_cpu.cc']:
        for n,line in enumerate((ROOT/file).read_text().splitlines(),1):
            if 'update_replacement_state)' in line or '.update_replacement_state(' in line:
                if file=='src/cache.cc': assert re.search(r'\.instruction\);\s*$',line),line
                else: assert re.search(r', 0\);\s*$',line),line
                sites.append(dict(file=file,line=n,code=line.strip()))
    assert len(sites)==11,sites
    definitions=[]
    for p in [ROOT/'inc/cache.h',*sorted((ROOT/'replacement').iterdir())]:
        if not p.is_file(): continue
        for signature in re.findall(r'update_replacement_state\)?\([^;{}]*?\)', p.read_text(), re.S):
            if 'uint32_t' in signature:
                assert 'uint8_t isInstruction' in signature, str(p)+signature
                definitions.append(str(p.relative_to(ROOT)))
    checked=0
    for line in (ROOT/'results/task2a_table.txt').read_text().splitlines()[1:]:
        tr,config,ipc,speed,load,data,inst=line.split()
        r=read_stats(ROOT/f'results/{config}_{tr}.txt')
        baseline=read_stats(ROOT/f'results/lru_{tr}.txt')['ipc']
        actual=[f"{r['ipc']:.6f}",f"{r['ipc']/baseline:.4f}",f"{r['load_mpki']:.3f}",f"{r['data_mpki']:.3f}",f"{r['instr_mpki']:.3f}"]
        assert actual==[ipc,speed,load,data,inst],(line,actual)
        checked+=1
    # Original artifacts must still equal committed bytes.
    protected=['Summary.html','Summary.pdf','plot_results.py','make_summary.py']
    protected += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'results').iterdir() if p.is_file()]
    for path in protected:
        original=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
        assert original== (ROOT/path).read_bytes() or original.replace(b'\r\n',b'\n')==(ROOT/path).read_bytes().replace(b'\r\n',b'\n'),path
    result={'callback_sites':sites,'declarations_and_definitions_checked':len(definitions),'historical_table_rows_verified':checked,'preserved_artifacts':protected}
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS {len(sites)} callbacks, {len(definitions)} signatures, {checked} table rows, {len(protected)} original artifacts')

if __name__=='__main__': main()
