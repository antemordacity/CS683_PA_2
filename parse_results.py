"""Parse ROI statistics; reject incomplete or internally inconsistent logs."""
import math
import argparse
from pathlib import Path
import re
import sys


def read_stats(path):
    text = Path(path).read_text(errors='replace')
    def one(pattern, source=text):
        matches = re.findall(pattern, source, re.M)
        if len(matches) != 1:
            raise ValueError(f'{path}: expected one {pattern!r}, found {len(matches)}')
        return matches[0]
    if 'ChampSim completed all CPUs' not in text:
        raise ValueError(f'{path}: simulation did not complete')
    roi = text.split('Region of Interest Statistics')
    if len(roi) != 2:
        raise ValueError(f'{path}: missing/duplicate ROI')
    ipc, instructions, cycles = one(r'^CPU 0 cumulative IPC: ([\d.eE+-]+) instructions: (\d+) cycles: (\d+)', roi[1])
    ipc, instructions, cycles = float(ipc), int(instructions), int(cycles)
    if cycles <= 0 or instructions <= 0 or not math.isclose(ipc, instructions/cycles, rel_tol=6e-6):
        raise ValueError(f'{path}: IPC disagrees with instruction/cycle counts')
    access, hit, miss, load = one(r'^L2C LOAD\s+ACCESS:\s*(\d+)\s+HIT:\s*(\d+)\s+MISS:\s*(\d+).*?MPKI:\s*([\d.eE+-]+)', roi[1])
    access, hit, miss, load = int(access), int(hit), int(miss), float(load)
    data = float(one(r'^L2C DATA LOAD MPKI: ([\d.eE+-]+)', roi[1]))
    inst = float(one(r'^L2C INSTRUCTION LOAD MPKI: ([\d.eE+-]+)', roi[1]))
    if access != hit + miss:
        raise ValueError(f'{path}: access != hit + miss')
    # Simulator uses six significant digits, so accommodate printing rounding.
    tolerance = max(0.00002, load*1.2e-5)
    if min(load, data, inst) < 0 or abs(load-miss*1000/instructions) > tolerance or abs(load-data-inst) > tolerance:
        raise ValueError(f'{path}: inconsistent load/instruction/data MPKI')
    warmup = int(one(r'^Warmup Instructions: (\d+)'))
    requested = int(one(r'^Simulation Instructions: (\d+)'))
    # RETIRE_WIDTH is 4: the final retirement batch can overshoot by at most 3.
    if not requested <= instructions <= requested+3:
        raise ValueError(f'{path}: ROI instruction budget mismatch')
    stats = dict(ipc=ipc, load_mpki=load, data_mpki=data, instr_mpki=inst,
                 instructions=instructions, cycles=cycles, accesses=access,
                 hits=hit, misses=miss, warmup=warmup, requested=requested)
    dynamic = re.findall(r'^DYN_STATS (.*)$', text, re.M)
    if dynamic:
        if len(dynamic) != 1: raise ValueError(f'{path}: duplicate dynamic diagnostics')
        d = dict(item.split('=', 1) for item in dynamic[0].split())
        ia, im, da, dm = (int(d[k]) for k in ('ia','im','da','dm'))
        denominator = ia+im+da+dm
        metric = (ia+im)/denominator if denominator else 0
        expected_mode = 'IRRIP3' if denominator and metric >= float(d['threshold']) else 'RRIP'
        if min(ia, im, da, dm) < 0 or im > ia or dm > da or ia+da != int(d['leader_updates']):
            raise ValueError(f'{path}: invalid leader counters')
        if abs(metric-float(d['metric'])) > 1e-10 or expected_mode != d['mode']:
            raise ValueError(f'{path}: invalid dynamic metric or mode')
        stats['dynamic'] = d
    return stats


def parse(path):
    r = read_stats(path)
    return r['ipc'], r['load_mpki'], r['data_mpki'], r['instr_mpki']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='Directory containing the selected run logs')
    parser.add_argument('configs', nargs='+', help='Policy names; first policy is the speedup baseline')
    args = parser.parse_args()
    configs = args.configs
    print(f"{'trace':7}{'config':12}{'IPC':>10}{'speedup':>9}{'L2C':>9}{'L2 Data':>9}{'L2 Instr':>9}")
    for tr in ['Trace1', 'Trace2', 'Trace3']:
        base = parse(args.input/f'{configs[0]}_{tr}.txt')[0]
        for c in configs:
            ipc, load, data, inst = parse(args.input/f'{c}_{tr}.txt')
            print(f'{tr:7}{c:12}{ipc:10.6f}{ipc/base:9.4f}{load:9.3f}{data:9.3f}{inst:9.3f}')

if __name__ == '__main__':
    main()
