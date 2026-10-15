import re, sys, os
d = sys.argv[1] if len(sys.argv) > 1 else "results/task3_full"
tags = ["lru", "dyn", "spp", "spp_dyn", "spp_dyn_aware"]
def num(p, t):
    m = re.search(p, t, re.M); return float(m.group(1)) if m else None
rows = {}
for tag in tags:
    for tr in (1, 2, 3):
        f = os.path.join(d, f"{tag}_Trace{tr}.txt")
        if not os.path.exists(f): continue
        t = open(f).read()
        rows[tag, tr] = dict(
            ipc=num(r"CPU 0 cumulative IPC: ([\d.]+) instructions", t),
            l1d=num(r"^L1D LOAD .*MPKI:\s+([\d.]+)", t),
            l2c=num(r"^L2C LOAD\s+ACCESS.*MPKI:\s+([\d.]+)", t),
            l2i=num(r"L2C INSTRUCTION LOAD MPKI:\s+([\d.]+)", t),
            l2d=num(r"L2C DATA LOAD MPKI:\s+([\d.]+)", t),
            acc=num(r"resolved accuracy:\s+([\d.]+)%", t),
            uf=num(r"^L1D PREFETCH\s+REQUESTED.*USEFUL:\s+(\d+)", t),
            iss=num(r"^L1D PREFETCH\s+REQUESTED.*ISSUED:\s+(\d+)", t))
print("trace,config,ipc,speedup_vs_lru,l1d_load_mpki,l2c_load_mpki,l2_instr_mpki,l2_data_mpki,spp_resolved_acc_pct,l1d_useful,l1d_issued,sum_check")
f = lambda x: "" if x is None else x
for (tag, tr), r in rows.items():
    b = rows.get(("lru", tr), {}).get("ipc")
    sp = round(r["ipc"]/b, 6) if b and r["ipc"] else ""
    ok = "ok" if None not in (r["l2c"], r["l2i"], r["l2d"]) and abs(r["l2i"]+r["l2d"]-r["l2c"]) < 0.01 else "CHECK"
    print(f"Trace{tr},{tag},{f(r['ipc'])},{sp},{f(r['l1d'])},{f(r['l2c'])},{f(r['l2i'])},{f(r['l2d'])},{f(r['acc'])},{f(r['uf'])},{f(r['iss'])},{ok}")
