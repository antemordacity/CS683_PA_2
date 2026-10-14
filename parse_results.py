import re, sys

def parse(path):
    t = open(path).read()
    ipc  = float(re.search(r"CPU 0 cumulative IPC: ([\d.]+)", t).group(1))
    load = float(re.search(r"L2C LOAD\s+ACCESS:.*?MPKI:\s*([\d.]+)", t).group(1))
    data = float(re.search(r"L2C DATA LOAD MPKI: ([\d.]+)", t).group(1))
    inst = float(re.search(r"L2C INSTRUCTION LOAD MPKI: ([\d.]+)", t).group(1))
    return ipc, load, data, inst

# usage: python3 parse_results.py lru irrip_v1 irrip_v2 irrip_v3   (first = baseline)
configs = sys.argv[1:]
print(f"{'trace':7}{'config':10}{'IPC':>10}{'speedup':>9}{'L2C':>9}{'L2 Data':>9}{'L2 Instr':>9}")
for tr in ["Trace1", "Trace2", "Trace3"]:
    base = parse(f"results/{configs[0]}_{tr}.txt")[0]
    for c in configs:
        ipc, load, data, inst = parse(f"results/{c}_{tr}.txt")
        print(f"{tr:7}{c:10}{ipc:10.6f}{ipc/base:9.4f}{load:9.3f}{data:9.3f}{inst:9.3f}")