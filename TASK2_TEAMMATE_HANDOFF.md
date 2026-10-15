# CS683 PA2 — Task 2: real-trace experiment handoff

**For the teammate who has Trace1, Trace2 and Trace3.**

## What is already done

Task 2a (static I-RRIP) and Task 2b (Dynamic I-RRIP) have been implemented. The updated repository contains a runner, six replacement-policy configurations, tests, historical Task 2a measurements, and report-generation scripts. The developer reports successful builds and synthetic tests. **The real Task 2b benchmark results are still missing**, because the three course traces were not available on the developer's machine.

**Your job:** pull the latest repository changes, run the three real traces, check that the run completed, and send back the generated analysis so the final report can be completed. You do not need to implement cache policies or manually try each threshold.

> Important: Only use the **real course-supplied traces**. Synthetic tests are not acceptable as assignment results.

## Step 1 — Get the updated code

Use an Ubuntu/Linux terminal. If you are using Windows, open **Ubuntu / WSL**, not PowerShell, for the commands below.

If this repository is **not yet cloned**, run:

```bash
 git clone https://github.com/antemordacity/CS683_PA_2.git
 cd CS683_PA_2
```

If it is **already cloned**, open that folder in Ubuntu/Linux:

```bash
 cd /path/to/CS683_PA_2
 git status --short
 git pull --ff-only
```

Make sure you are on the branch containing the new Task 2 changes; ask the teammate who pushed them for the **branch name**. If you have uncommitted changes, do not force-pull, reset, or delete them; coordinate first.

You should see `run_task2.sh`, `TASK2_README.md`, `TASK2_REPORT.md`, and the `task2/` directory:

```bash
ls run_task2.sh TASK2_README.md TASK2_REPORT.md task2/run.py
```

## Step 2 — Install the required tools (one time)

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3 python3-matplotlib gzip xz-utils
```

Check that the compiler and plotting package are available:

```bash
g++ --version
python3 -c 'import matplotlib; print("matplotlib OK")'
```

If you already have these packages, you can skip installation. The current code was previously built successfully on Ubuntu with GCC 13.3; an exact GCC 9 installation is **not** required by the new runner.

## Step 3 — Put the course traces into a folder

Create the folder:

```bash
mkdir -p "$HOME/traces"
```

Copy your three compressed course trace files into it. The expected layout is:

```text
/home/YOUR_LINUX_USERNAME/traces/
├── Trace1.gz
├── Trace2.gz
└── Trace3.gz
```

Files ending in `.xz` are also supported. You can keep them compressed; **do not extract them**. Windows users can browse their Linux home folder through `\\wsl.localhost\<Ubuntu-distribution>\home\<Linux-username>\traces` in File Explorer. Or, if the files are in Windows Downloads, copy them from `/mnt/c/Users/.../Downloads/` using your actual Windows username.

Verify:

```bash
ls -lh "$HOME/traces"
```

There must be **exactly one** recognized file per trace, with the corresponding Trace1/Trace2/Trace3 name. Do not place test/synthetic data into this folder.

## Step 4 — Run the short smoke test

From the **repository root** (where `run_task2.sh` is located):

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
```

The smoke run tests 100,000 warmup instructions and 100,000 simulated instructions per configuration. It compiles the simulator, runs tests, tries all policies/thresholds, and generates sample tables and plots. It is **not** the required assignment result.

Wait until it prints a line similar to:

```text
Completed: .../results/task2_smoke_.../analysis/TABLES.md
```

If it fails, **stop and record the error** before moving to the full test.

## Step 5 — Run the required full experiments

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

This uses **25 million warmup + 25 million measured instructions** per run. The program automatically executes:

- LRU, RRIP, and I-RRIP versions 1, 2 and 3
- Dynamic I-RRIP with thresholds **0.10, 0.20, 0.25, 0.35, 0.50**
- All of the above for **Trace1, Trace2 and Trace3** (30 configurations), followed by one reproducibility repeat

A full experiment can take a long time. Keep the laptop plugged in, avoid sleep/hibernation, and do not close the terminal. You can leave the machine to finish. The runner creates a **new unique folder** under `results/` and does not overwrite previous results.

Look for the `Results:` line near the start of the terminal output, for example:

```text
Results: .../results/task2_full_2026..._<random>/
```

Save that directory name: it is the **full-run results folder**, referred to as `RUN_DIR` below.

## Step 6 — Verify success

After the full run returns successfully, open its `manifest.json`. It must have:

```json
"mode": "full",
"warmup": 25000000,
"simulation": 25000000,
"status": "complete"
```

The full results folder should contain:

```text
RUN_DIR/
├── manifest.json
├── build/
├── tests/
├── logs/
└── analysis/
    ├── TABLES.md
    ├── REPORT.md
    ├── metrics.csv
    ├── validated.json
    ├── ipc.png
    ├── speedup.png
    ├── load_mpki.png
    ├── instr_mpki.png
    ├── data_mpki.png
    └── sensitivity_*.png   (5 threshold-sensitivity plots)
```

Look inside `analysis/TABLES.md`: every policy should have IPC, speedup vs LRU, L2C load MPKI, instruction load MPKI, and data load MPKI for all three traces, plus dynamic counters and threshold comparisons. `analysis/REPORT.md` includes the generated tables and plots. The `logs/` folder contains the raw simulator output for 30 configurations and one repeat.

**Do not mark the run complete if** `manifest.json` says `failed_or_interrupted`, logs are incomplete, any measurements are missing, or data were generated using the synthetic test fixture. Contact your teammate with the exact error.

## Step 7 — Send back the results

Please send these files or the entire `analysis/` folder to the teammate preparing the submission:

1. `RUN_DIR/analysis/` — contains the CSV, tables, plots, validated statistics and generated report.
2. `RUN_DIR/manifest.json` — documents run completion, configuration and trace hashes.
3. `RUN_DIR/tests/summary.json` — unit-test summary.
4. If anything failed or results look odd, also send the corresponding text file from `RUN_DIR/logs/` and the exact error message.

To package the main deliverables into one file, run this from the repository root, **replacing the path** with your actual full-run directory:

```bash
RUN_DIR="results/task2_full_REPLACE_WITH_ACTUAL_DIRECTORY"
tar -czf task2_real_results.tar.gz -C "$RUN_DIR" analysis manifest.json tests/summary.json
```

Send `task2_real_results.tar.gz` to your teammate. The three large trace files themselves should **not** be added to Git or included in this archive.

## Step 8 — Complete the final assignment report

**The full run does not automatically replace the existing `TASK2_REPORT.md`.** The report author must incorporate the real measurements from `RUN_DIR/analysis/REPORT.md` and its plots into the final Task 2 report.

Before submission, explicitly:

- Replace the **Task 2b pending-results** section with the actual measured IPC, speedup, L2C/instruction/data load MPKI tables and threshold plots.
- Discuss which thresholds performed well **on each trace** and whether follower mode actually switched. Look at mode-switch totals and follower RRIP/I-RRIP updates; do not assume a threshold is effective simply because it was tested.
- Compare Dynamic I-RRIP against LRU, ordinary RRIP and static I-RRIP V3 using the **new, same-run** measurements.
- Retain the rationale for 32 leader sets, insertion/promotion/eviction, and the limitations of cumulative sampling.
- Remove or update all “pending” statements only after real results are validated.
- Check that Markdown image links point to plots actually included in the submission. Convert to PDF only if required by the course submission instructions.

**Historical Task 2a results use an earlier seed convention,** so do not directly interpret tiny differences between historical logs and new results as improvements. Use the new-run comparisons for a consistent baseline.

## Common errors

| Problem | What to do |
|---|---|
| `need exactly one Trace1 ... found 0` | Verify that the traces exist in the directory you supplied and use supported filenames. |
| `found 2` | Remove the duplicate from the **trace input folder only** or use a clean input folder. |
| `No module named matplotlib` | Install `python3-matplotlib` **inside Ubuntu**, not only Windows. |
| `g++` not found | Install `build-essential`. |
| Compilation fails | Read `RUN_DIR/build/*.log` and share the error. Do not silently change source or compiler options. |
| It looks stuck | A 50M-instruction simulator run may take time; check whether the current `RUN_DIR/logs/` file is being written and whether the process is running. |
| Run stops halfway | Keep its logs/manifest, report the failure, and rerun when fixed; a new run creates a separate directory. |

For deeper explanations, read the existing `TASK2_README.md` in the repository.

---

## Checklist for the teammate who is pushing the code

Before handing this to the trace owner:

- [ ] Push **all** new scripts/documents, including `task2/` and `run_task2.sh`, as well as the updated policy/source files, to a known branch.
- [ ] Give the trace owner the branch name and this document. Verify they can read the repository.
- [ ] Keep course traces, simulator binaries, temporary directories and unnecessary large generated logs out of Git.
- [ ] If `TASK2_REPORT.md` references historical plots under `results/task2_audit/historical/`, ensure those image files are actually shared or committed; otherwise the report's pictures will be broken for other readers.
- [ ] Do **not** claim Task 2b's real-trace results are finished until the full run succeeds and the report is updated.

**Suggested short message:** “I’ve pushed the Task 2 implementation and automated runner to branch `<branch>`. Please follow `TASK2_TEAMMATE_HANDOFF.md` on your Linux/WSL laptop with the three course traces. Run smoke first, then full, and send me the generated full-run `analysis/` and `manifest.json`. No coding is needed unless something fails.”
