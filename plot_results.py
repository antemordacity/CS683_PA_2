import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

configs = ["lru", "rrip", "irrip_v1", "irrip_v2", "irrip_v3"]
traces = ["Trace1", "Trace2", "Trace3"]

def parse(path):
    t = open(path).read()
    ipc  = float(re.search(r"CPU 0 cumulative IPC: ([\d.]+)", t).group(1))
    load = float(re.search(r"L2C LOAD\s+ACCESS:.*?MPKI:\s*([\d.]+)", t).group(1))
    data = float(re.search(r"L2C DATA LOAD MPKI: ([\d.]+)", t).group(1))
    inst = float(re.search(r"L2C INSTRUCTION LOAD MPKI: ([\d.]+)", t).group(1))
    return ipc, load, data, inst

R = {c: {t: parse(f"results/{c}_{t}.txt") for t in traces} for c in configs}

def bars(title, ylabel, fn, fname, baseline_line=None):
    w = 0.16
    plt.figure(figsize=(8, 4.5))
    for i, c in enumerate(configs):
        vals = [fn(c, t) for t in traces]
        plt.bar([x + i * w for x in range(len(traces))], vals, w, label=c)
    plt.xticks([x + 2 * w for x in range(len(traces))], traces)
    if baseline_line is not None:
        plt.axhline(baseline_line, color="red", ls="--", lw=0.8)
    plt.title(title); plt.ylabel(ylabel); plt.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(fname, dpi=150); plt.close()

bars("Speedup over LRU (L2C replacement)", "Speedup", lambda c, t: R[c][t][0] / R["lru"][t][0], "results/plot_speedup.png", 1.0)
bars("L2C load MPKI", "MPKI", lambda c, t: R[c][t][1], "results/plot_l2c_mpki.png")
bars("L2 instruction load MPKI", "MPKI", lambda c, t: R[c][t][3], "results/plot_l2_instr_mpki.png")
bars("L2 data load MPKI", "MPKI", lambda c, t: R[c][t][2], "results/plot_l2_data_mpki.png")
print("saved 4 plots in results/")