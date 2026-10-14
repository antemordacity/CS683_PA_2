#!/usr/bin/env python3
"""
make_summary.py - builds Summary.html (and Summary.pdf if a Chrome/Chromium binary is found)
for CS683 PA2, Task 2A (I-RRIP).

Run from the repo root (the folder that contains results/):
    python3 make_summary.py

Reads   : results/{lru,rrip,irrip_v1,irrip_v2,irrip_v3}_{Trace1,Trace2,Trace3}.txt  (ChampSim outputs)
Writes  : results/plot_*.png, results/task2a_table.txt, Summary.html, Summary.pdf
Needs   : python3 + matplotlib (pip3 install matplotlib)
"""
import base64
import io
import re
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------------------
# FILL THESE IN
TEAM = "TeamName"
LDAPS = "LDAP1, LDAP2"
# ----------------------------------------------------------------------------------------

TRACES = ["Trace1", "Trace2", "Trace3"]
CONFIGS = ["lru", "rrip", "irrip_v1", "irrip_v2", "irrip_v3"]
LABEL = {
    "lru": "LRU (baseline)",
    "rrip": "RRIP (SRRIP)",
    "irrip_v1": "I-RRIP V1",
    "irrip_v2": "I-RRIP V2",
    "irrip_v3": "I-RRIP V3 (final)",
}


def parse(path):
    t = open(path).read()
    ipc = float(re.search(r"CPU 0 cumulative IPC: ([\d.]+)", t).group(1))
    load = float(re.search(r"L2C LOAD\s+ACCESS:.*?MPKI:\s*([\d.]+)", t).group(1))
    data = float(re.search(r"L2C DATA LOAD MPKI: ([\d.]+)", t).group(1))
    inst = float(re.search(r"L2C INSTRUCTION LOAD MPKI: ([\d.]+)", t).group(1))
    return {"ipc": ipc, "l2c": load, "data": data, "inst": inst}


R = {c: {t: parse("results/%s_%s.txt" % (c, t)) for t in TRACES} for c in CONFIGS}


def speedup(c, t, base="lru"):
    return R[c][t]["ipc"] / R[base][t]["ipc"]


def pct(a, b):
    """percent change from a to b"""
    return (b - a) / a * 100.0


def signed(x, nd=1, suffix="%"):
    return ("%+." + str(nd) + "f%s") % (x, suffix)


# ---------------------------------------------------------------------------- tables
def html_table(header, rows, left_cols=1):
    out = "<table><tr>" + "".join("<th>%s</th>" % h for h in header) + "</tr>"
    for r in rows:
        out += "<tr>"
        for i, c in enumerate(r):
            cls = ' class="l"' if i < left_cols else ""
            out += "<td%s>%s</td>" % (cls, c)
        out += "</tr>"
    return out + "</table>"


# main results table (also written as plain text for the repo)
main_rows, txt_lines = [], []
txt_lines.append("trace  config           IPC  speedup      L2C  L2 Data L2 Instr")
for t in TRACES:
    for c in CONFIGS:
        r = R[c][t]
        sp = speedup(c, t)
        main_rows.append([t, LABEL[c], "%.6f" % r["ipc"], "%.4f" % sp,
                          "%.3f" % r["l2c"], "%.3f" % r["data"], "%.3f" % r["inst"]])
        txt_lines.append("%-6s %-10s %10.6f %8.4f %8.3f %8.3f %8.3f" %
                         (t, c, r["ipc"], sp, r["l2c"], r["data"], r["inst"]))
open("results/task2a_table.txt", "w").write("\n".join(txt_lines) + "\n")

main_table = html_table(
    ["Trace", "Policy", "IPC", "Speedup vs LRU", "L2C load MPKI", "L2 data load MPKI", "L2 instr load MPKI"],
    main_rows, left_cols=2)

# mean speedup row
mean_rows = []
for c in CONFIGS:
    mean_rows.append([LABEL[c]] + ["%.4f" % speedup(c, t) for t in TRACES] +
                     ["%.4f" % (sum(speedup(c, t) for t in TRACES) / len(TRACES))])
mean_table = html_table(["Policy"] + TRACES + ["Mean"], mean_rows)

# V3 vs LRU and V3 vs RRIP tables
def delta_rows(base):
    rows = []
    for t in TRACES:
        a, b = R[base][t], R["irrip_v3"][t]
        rows.append([t,
                     "%.4f" % speedup("irrip_v3", t, base),
                     "%.3f -> %.3f (%s)" % (a["inst"], b["inst"], signed(pct(a["inst"], b["inst"]))),
                     "%.3f -> %.3f (%s)" % (a["data"], b["data"], signed(pct(a["data"], b["data"]))),
                     "%.3f -> %.3f (%s)" % (a["l2c"], b["l2c"], signed(pct(a["l2c"], b["l2c"])))])
    return rows

hdr_delta = ["Trace", "Speedup", "L2 instr load MPKI", "L2 data load MPKI", "L2C load MPKI"]
tbl_vs_lru = html_table(hdr_delta, delta_rows("lru"))
tbl_vs_rrip = html_table(hdr_delta, delta_rows("rrip"))

# ladder (marginal) table
ladder_rows = []
steps = [("lru", "irrip_v1", "Insertion (LRU -> V1)"),
         ("irrip_v1", "irrip_v2", "+ Promotion (V1 -> V2)"),
         ("irrip_v2", "irrip_v3", "+ Eviction (V2 -> V3)")]
for t in TRACES:
    for a, b, name in steps:
        ra, rb = R[a][t], R[b][t]
        d_ipc = (rb["ipc"] - ra["ipc"]) / R["lru"][t]["ipc"] * 100.0
        d_inst = rb["inst"] - ra["inst"]
        d_data = rb["data"] - ra["data"]
        ratio = "%.2f" % (d_data / -d_inst) if d_inst < -1e-9 else "n/a"
        ladder_rows.append([t, name, signed(d_ipc, 2, " pts"), "%+.3f" % d_inst, "%+.3f" % d_data, ratio])
tbl_ladder = html_table(
    ["Trace", "Step", "Speedup change", "dInstr MPKI", "dData MPKI", "Data misses added per instr miss saved"],
    ladder_rows, left_cols=2)


# ---------------------------------------------------------------------------- plots
def make_plot(title, ylabel, fn, fname, hline=None, ylim=None):
    w = 0.16
    fig = plt.figure(figsize=(7.5, 4.2))
    for i, c in enumerate(CONFIGS):
        vals = [fn(c, t) for t in TRACES]
        plt.bar([x + i * w for x in range(len(TRACES))], vals, w, label=LABEL[c])
    plt.xticks([x + 2 * w for x in range(len(TRACES))], TRACES)
    if hline is not None:
        plt.axhline(hline, color="red", ls="--", lw=0.8)
    if ylim is not None:
        plt.ylim(*ylim)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.legend(fontsize=7)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    fig.savefig("results/" + fname, dpi=150)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


PLOTS = [
    ("Speedup over LRU (axis zoomed to 0.995-1.025)", "Speedup", lambda c, t: speedup(c, t), "plot_speedup.png", 1.0, (0.995, 1.025)),
    ("L2C load MPKI", "MPKI", lambda c, t: R[c][t]["l2c"], "plot_l2c_mpki.png", None),
    ("L2 instruction load MPKI", "MPKI", lambda c, t: R[c][t]["inst"], "plot_l2_instr_mpki.png", None),
    ("L2 data load MPKI", "MPKI", lambda c, t: R[c][t]["data"], "plot_l2_data_mpki.png", None),
]
plots_html = ""
for title, ylabel, fn, fname, hl, *yl in PLOTS:
    src = make_plot(title, ylabel, fn, fname, hl, yl[0] if yl else None)
    plots_html += '<figure><img src="%s"><figcaption>%s</figcaption></figure>' % (src, title)

# a few numbers used in the prose
t2 = R["irrip_v3"]["Trace2"]
l2 = R["lru"]["Trace2"]
mean_v = {c: sum(speedup(c, t) for t in TRACES) / len(TRACES) for c in CONFIGS}

# ---------------------------------------------------------------------------- the document
CSS = """
body{font-family:Arial,Helvetica,sans-serif;max-width:920px;margin:28px auto;padding:0 14px;font-size:12.5px;line-height:1.5;color:#111}
h1{font-size:21px;margin-bottom:2px} h2{font-size:16px;margin-top:26px;border-bottom:1px solid #bbb;padding-bottom:3px}
h3{font-size:13.5px;margin-bottom:3px}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:11.5px}
th,td{border:1px solid #999;padding:3px 6px;text-align:right} th{background:#eee}
td.l{text-align:left} th:first-child{text-align:left}
figure{display:inline-block;width:48%;margin:4px 0.5%;text-align:center;vertical-align:top} figure img{width:100%}
figcaption{font-size:11px;color:#444}
code,pre{font-family:Consolas,Menlo,monospace;font-size:11px;background:#f4f4f4}
pre{padding:8px;white-space:pre-wrap;border:1px solid #ddd}
.box{border-left:4px solid #4a7;padding:2px 10px;background:#f2faf5;margin:8px 0}
@media print{h2{page-break-after:avoid} table,figure,pre{page-break-inside:avoid}}
"""

BODY = """
<h1>CS683 PA2 &ndash; Task 2A: Instruction-Conscious L2 Replacement (I-RRIP)</h1>
<div>Team: @@TEAM@@ (@@LDAPS@@) &nbsp;|&nbsp; Simulator: ChampSim &nbsp;|&nbsp; 25M warmup + 25M simulated instructions per trace</div>

<h2>1. Summary of the work</h2>
<div class="box">
<p><b>What was built.</b> An instruction-conscious replacement policy for the L2 cache (<code>replacement/irrip.l2c_repl</code>), derived from 2-bit SRRIP.
The policy receives an <code>isInstruction</code> flag with every insertion/promotion and favours instruction lines in insertion, promotion and eviction.</p>
<p><b>Headline result.</b> L2 instruction load MPKI decreased on all three traces. On the instruction-dominated Trace2 it fell from
@@T2_LRU_INST@@ to @@T2_V3_INST@@ (@@T2_INST_PCT@@), total L2C load MPKI fell by @@T2_L2C_PCT@@ and IPC improved by @@T2_SPEEDUP_PCT@@
(speedup @@T2_SPEEDUP@@). Trace1 is neutral and Trace3 flat. The price is higher L2 <i>data</i> load MPKI on every trace, which is the
motivation for the dynamic policy of Task 2B.</p>
</div>

<h2>2. Work log (what was done, in order)</h2>
<ol>
<li><b>Build environment.</b> The first build (Ubuntu 22.04, default GCC 11.4) compiled but crashed at run time
(segmentation fault inside <code>O3_CPU::execute_instruction</code> with an invalid <code>this</code> pointer). The build log showed the warning
<i>"control reaches end of non-void function"</i> for <code>PAGE_TABLE_WALKER::handle_page_fault</code> in <code>src/page_table_walker.cc</code>:
the function is declared to return <code>uint64_t</code> but has no <code>return</code>. This is undefined behaviour that older compilers (the README asks for GCC 7)
tolerated and GCC 11 does not. All three call sites ignore the return value, so a <code>return 0;</code> was added at the end of the function (no change in
simulated behaviour), and the simulator is built with GCC 9 (<code>CXX=g++-9 ./build_champsim.sh ...</code>).</li>
<li><b>Baseline.</b> LRU L2C, no prefetcher, run on Trace1&ndash;3 (25M warmup, 25M simulation). The trace files are given as <code>.gz</code>, which ChampSim reads directly.</li>
<li><b>Plumbing.</b> <code>update_replacement_state</code> was extended with a final <code>uint8_t isInstruction</code> parameter: function-pointer type and declarations
in <code>inc/cache.h</code>; definitions in <code>base_replacement.cc</code> and all <code>lru.*_repl</code> files and <code>rrip.l2c_repl</code>; 8 call sites in
<code>src/cache.cc</code> (passing the packet's <code>.instruction</code> field from the MSHR/WQ/RQ/PQ entry) and 3 BTB call sites in <code>src/ooo_cpu.cc</code> (passing 0).
<b>Verification:</b> the LRU baseline was rebuilt after the change and re-run; IPC and all L2C load MPKI lines were identical to the pre-change run on all three traces.</li>
<li><b>I-RRIP.</b> Implemented in one file with a compile-time switch <code>IRRIP_VERSION</code> (1, 2, 3), so every change could be measured on its own.</li>
<li><b>Experiments.</b> LRU, plain RRIP, and I-RRIP V1/V2/V3 on all three traces; results below. A helper script (<code>run_ladder.sh</code>) rebuilt and ran each version.</li>
</ol>

<h2>3. The policy and its versions</h2>
<p>Background: RRIP keeps a 2-bit re-reference prediction value (RRPV) per line: 0 = expected to be reused soon, 3 = evict next. SRRIP inserts at RRPV 2,
promotes a hit line to 0, and evicts a line at RRPV 3 (ageing all lines when none is at 3). Server-style code does not fit in L1I, so L2 hits
for instruction fetches matter for front-end throughput; I-RRIP gives instruction lines preferential treatment. The three versions are cumulative.</p>
<table>
<tr><th>Version</th><th>Insertion (fill)</th><th>Promotion (hit)</th><th>Eviction (victim choice)</th></tr>
<tr><td class="l">RRIP (reference)</td><td class="l">all lines at RRPV 2</td><td class="l">all hits to RRPV 0</td><td class="l">first line at RRPV 3, age if none</td></tr>
<tr><td class="l"><b>V1</b></td><td class="l"><b>instruction at RRPV 0</b>, data at RRPV 2</td><td class="l">unchanged (to 0)</td><td class="l">unchanged</td></tr>
<tr><td class="l"><b>V2</b></td><td class="l">as V1</td><td class="l"><b>instruction hit to 0; data hit decremented by one step</b></td><td class="l">unchanged</td></tr>
<tr><td class="l"><b>V3</b> (final)</td><td class="l">as V1</td><td class="l">as V2</td><td class="l"><b>among lines at RRPV 3, evict a data line first</b>; otherwise any line at 3; age if none</td></tr>
</table>

<h3>Why each change</h3>
<p><b>Insertion (V1).</b> A line brought in by an instruction fetch is placed at the most-protected position (RRPV 0), so it survives longer than the data fills that
compete for the same set. Data fills keep the baseline RRPV 2 ("long re-reference" prediction), so streaming data still ages out quickly and is not given extra protection.
This is the cheapest change and is expected to give most of the instruction-miss reduction.</p>
<p><b>Promotion (V2).</b> An instruction line that is hit again is promoted fully (to 0), while a data line hit moves down only one step. A data line therefore needs
repeated reuse to reach the protected state, and instruction lines that proved useful are hard to displace. The risk is that genuinely reused data lines are protected less well.</p>
<p><b>Eviction (V3).</b> When several lines are at the eviction value, a data line is chosen before an instruction line (read from <code>block[set][way].instruction</code>,
which the cache sets at fill time). If no data line is at RRPV 3 the normal RRIP search and ageing loop is used, so the ageing mechanism is unchanged.
This only changes the tie-break, which keeps the modification small and easy to reason about.</p>
<p><b>Implementation notes.</b> The policy uses only the existing 2-bit RRPV per line plus the per-block instruction bit already present in the cache, i.e. no additional storage.
Prefetch packets are not treated specially here (that is Task 3).</p>

<h2>4. Results</h2>
<p>All numbers are from the ROI of each run (25M instructions after a 25M warmup). Speedup = IPC / IPC of LRU. MPKI values are L2C <i>load</i> misses per 1000 instructions;
"instr" and "data" split the load misses by request type.</p>
@@MAIN_TABLE@@
<h3>Mean speedup over LRU</h3>
@@MEAN_TABLE@@
<h3>Plots</h3>
@@PLOTS@@

<h3>I-RRIP V3 compared with LRU</h3>
@@TBL_VS_LRU@@
<h3>I-RRIP V3 compared with plain RRIP</h3>
@@TBL_VS_RRIP@@
<h3>Contribution of each change (marginal, per step)</h3>
<p>"Speedup change" is in percentage points of the LRU IPC; the last column is how many extra data load misses (MPKI) each step adds per instruction load miss (MPKI) it removes.</p>
@@TBL_LADDER@@

<h2>5. Explanation of the results</h2>
<p><b>Trace2 &ndash; large gain.</b> This trace is instruction-bound: its L1I MPKI is about 40 and instruction loads cause roughly two thirds of L2 load misses under LRU.
Every step helps: V1 / V2 / V3 give speedups of @@T2_V1@@ / @@T2_V2@@ / @@T2_V3@@. The code footprint also exceeds the L2 (under LRU, instruction fills evict other instruction lines
about 300 thousand times), so protecting instruction lines changes which code survives and substantially reduces instruction misses. Against plain RRIP the gain is larger still
(@@T2_VS_RRIP@@), showing the improvement comes from the instruction-aware changes and not from using RRIP.</p>
<p><b>Trace1 &ndash; neutral.</b> Instruction misses fall at every step (@@T1_INST@@), but data misses rise by almost the same amount (@@T1_DATA@@), so total L2C load MPKI and IPC stay flat
(speedup @@T1_V3@@). This suggests that instruction and data lines compete about equally for the L2 on this trace, so favouring one side mostly moves misses from one type to the other (an interpretation of the numbers; it was not tested separately).</p>
<p><b>Trace3 &ndash; flat.</b> Instruction pressure is low (L1I MPKI about 2.1, L2 instruction MPKI about 1.1), so there is little for an instruction-aware policy to gain; instruction MPKI
still falls (@@T3_INST@@) while data MPKI rises slightly, and IPC is unchanged.</p>
<p><b>Cost-effectiveness of the three changes.</b> On Trace2, insertion removes the most instruction misses for the fewest added data misses (about @@R_INS@@ per instruction miss saved);
eviction costs @@R_EVI@@ and promotion @@R_PRO@@. Promotion is therefore the least cost-effective change, most likely because slowing data promotion reduces the protection of reused data lines (not tested in isolation).
V3 nevertheless has the best mean speedup (@@MEAN_V1@@ for V1, @@MEAN_V2@@ for V2, @@MEAN_V3@@ for V3) and the best result on the trace where the policy matters most.</p>

<h2>6. Why this design</h2>
<ul>
<li>The task goal is to reduce L2 instruction load MPKI. V3 achieves the lowest instruction MPKI on every trace among the variants tested, and the highest speedup on Trace2 and highest mean speedup.</li>
<li>It is simple and cheap: no extra state beyond what the cache already holds, and RRIP's ageing logic is preserved.</li>
<li>The incremental ladder gives evidence for each decision rather than assuming all three changes are needed; it also shows which one is least efficient (promotion).</li>
<li>The data-MPKI increase and the neutral Trace1 result are the honest limits of a static policy: it helps when instruction pressure is high and costs data misses when it is not.
A policy that switches itself on only when instruction pressure is high (set dueling, Task 2B) is the natural fix.</li>
</ul>

<h2>7. Limitations and possible follow-ups</h2>
<ul>
<li>Gains are modest (at most about 2%) and measured on one 25M-instruction window per trace, without variance estimates.</li>
<li>Untested variants: instruction insertion at RRPV 1 instead of 0 (less aggressive), leaving data promotion unchanged while keeping the eviction change, or limiting instruction protection per set.</li>
<li>Only three traces were used; behaviour on other workloads (especially data-heavy ones, like Trace3) is expected to be neutral-to-negative for a static policy.</li>
</ul>

<h2>8. How to reproduce</h2>
<pre>
# build (GCC 9) and run, e.g. I-RRIP V3
CXX=g++-9 ./build_champsim.sh irrip
./bin/hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-irrip-lru-lru-lru-lru-1core-irrip \\
    -warmup_instructions 25000000 -simulation_instructions 25000000 -traces ~/traces/Trace1.gz > results/irrip_v3_Trace1.txt
# IRRIP_VERSION (1, 2 or 3) is the #define at the top of replacement/irrip.l2c_repl; run_ladder.sh &lt;v&gt; rebuilds and runs all traces
# baseline: CXX=g++-9 ./build_champsim.sh baseline ;  plain RRIP: CXX=g++-9 ./build_champsim.sh rrip
python3 make_summary.py     # regenerates tables, plots and this document
</pre>
<p>Files: <code>replacement/irrip.l2c_repl</code> (policy), <code>inc/cache.h</code>, <code>src/cache.cc</code>, <code>src/ooo_cpu.cc</code>, <code>replacement/*.l2c_repl</code> and other policy files (signature change),
<code>src/page_table_walker.cc</code> (missing return fix), <code>results/</code> (raw ChampSim outputs, table, plots), <code>run3.sh</code>, <code>run_ladder.sh</code>, <code>make_summary.py</code>.</p>
"""

def inst_range(t):
    a, b = R["lru"][t]["inst"], R["irrip_v1"][t]["inst"]
    c = R["irrip_v3"][t]["inst"]
    return "%.2f to %.2f" % (a, c)

def data_range(t):
    return "%.2f to %.2f" % (R["lru"][t]["data"], R["irrip_v3"][t]["data"])

def ratio(t, a, b):
    d_inst = R[b][t]["inst"] - R[a][t]["inst"]
    d_data = R[b][t]["data"] - R[a][t]["data"]
    return "%.2f" % (d_data / -d_inst)

subs = {
    "@@TEAM@@": TEAM, "@@LDAPS@@": LDAPS,
    "@@T2_LRU_INST@@": "%.2f" % l2["inst"], "@@T2_V3_INST@@": "%.2f" % t2["inst"],
    "@@T2_INST_PCT@@": signed(pct(l2["inst"], t2["inst"]), 0),
    "@@T2_L2C_PCT@@": "%.0f%%" % -pct(l2["l2c"], t2["l2c"]),
    "@@T2_SPEEDUP_PCT@@": "%.1f%%" % ((speedup("irrip_v3", "Trace2") - 1) * 100),
    "@@T2_SPEEDUP@@": "%.3f" % speedup("irrip_v3", "Trace2"),
    "@@T2_V1@@": "%.4f" % speedup("irrip_v1", "Trace2"),
    "@@T2_V2@@": "%.4f" % speedup("irrip_v2", "Trace2"),
    "@@T2_V3@@": "%.4f" % speedup("irrip_v3", "Trace2"),
    "@@T2_VS_RRIP@@": "speedup %.4f over RRIP, instruction MPKI %s" % (
        speedup("irrip_v3", "Trace2", "rrip"), signed(pct(R["rrip"]["Trace2"]["inst"], t2["inst"]))),
    "@@T1_INST@@": "MPKI %s" % inst_range("Trace1"),
    "@@T1_DATA@@": "MPKI %s" % data_range("Trace1"),
    "@@T1_V3@@": "%.4f" % speedup("irrip_v3", "Trace1"),
    "@@T3_INST@@": "MPKI %s" % inst_range("Trace3"),
    "@@R_INS@@": ratio("Trace2", "lru", "irrip_v1"),
    "@@R_PRO@@": ratio("Trace2", "irrip_v1", "irrip_v2"),
    "@@R_EVI@@": ratio("Trace2", "irrip_v2", "irrip_v3"),
    "@@MEAN_V1@@": "%.4f" % mean_v["irrip_v1"], "@@MEAN_V2@@": "%.4f" % mean_v["irrip_v2"],
    "@@MEAN_V3@@": "%.4f" % mean_v["irrip_v3"],
    "@@MAIN_TABLE@@": main_table, "@@MEAN_TABLE@@": mean_table, "@@PLOTS@@": plots_html,
    "@@TBL_VS_LRU@@": tbl_vs_lru, "@@TBL_VS_RRIP@@": tbl_vs_rrip, "@@TBL_LADDER@@": tbl_ladder,
}
body = BODY
for k, v in subs.items():
    body = body.replace(k, v)
assert "@@" not in body, "unfilled placeholder in document"

page = "<html><head><meta charset='utf-8'><title>CS683 PA2 Task 2A Summary</title><style>%s</style></head><body>%s</body></html>" % (CSS, body)
open("Summary.html", "w").write(page)
print("wrote Summary.html")

# ---------------------------------------------------------------------------- PDF
for exe in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
    path = shutil.which(exe)
    if path:
        r = subprocess.run([path, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                            "--print-to-pdf=Summary.pdf", "Summary.html"], capture_output=True, text=True)
        print("wrote Summary.pdf using", exe if r.returncode == 0 else "(failed: %s)" % r.stderr[-200:])
        break
else:
    print("No Chrome/Chromium found: open Summary.html in a browser, press Ctrl+P and 'Save as PDF' -> Summary.pdf")