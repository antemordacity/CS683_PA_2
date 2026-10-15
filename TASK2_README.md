# CS683 PA2 Task 2: setup and running guide

**The required full experiment matrix is complete.** Use [TASK2_REPORT.md](TASK2_REPORT.md) and the retained run listed in [results/README.md](results/README.md) for report preparation. You do not need to simulate again unless you change simulator/policy code or want additional experiments.

The retained run used GCC 11.4 on Ubuntu 22.04. Earlier development checks used GCC 13.3 successfully. The latest full run is the only report dataset in this working tree; old measurements are not mixed with it.

## 1. Open Ubuntu / Linux

On Windows, open Ubuntu or enter this in PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Then, in Ubuntu:

```bash
cd /mnt/e/IITB/5th_Semester/CS683/CS683_PA_2
```

Change this path if you cloned the repository elsewhere. `pwd` shows your current directory; `ls` should show `run_task2.sh`, `src`, `inc`, and `task2`.

## 2. Install tools if you want to rerun experiments or tests

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3 python3-matplotlib gzip xz-utils
```

Use your Linux password when sudo asks. Check with `g++ --version` and:

```bash
python3 -c 'import matplotlib; print(matplotlib.__version__)'
```

There is no need to add an old Ubuntu package repository or install GCC 7. `CXX=g++-11` can select an installed compiler; the experiment manifest records the actual compiler. The builder uses two compilation jobs by default; use `TASK2_JOBS=1` on a memory-limited machine.

## 3. Place actual course traces outside the repository

To rerun simulations, obtain the course-provided traces using the authorized download linked in the root README. They are inputs, not part of Git. Your teammate's original run read `/home/tanish/traces`; that path need not exist on your machine.

```bash
mkdir -p "$HOME/traces"
ls -lh "$HOME/traces"
```

Expected files:

```text
$HOME/traces/
  Trace1.gz
  Trace2.gz
  Trace3.gz
```

Supported alternatives are `.xz` and `trace1.champsimtrace.gz`/`.xz`, with equivalent names for traces 2 and 3; matching is case-insensitive. Keep exactly one recognized copy per trace and keep it compressed. `$HOME` is the current Linux user's home, not the Windows user's home. Windows File Explorer can access it through `\\wsl.localhost\Ubuntu-24.04\home\YOUR_LINUX_USERNAME\traces`.

Do not use generated synthetic test inputs as assignment data. The runner checks compression and records hashes, but cannot certify that a compressed file is the correct course workload.

## 4. Run experiments only when needed

From the repository root:

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

Smoke: 100,000 warmup + 100,000 measured instructions. Full: 25,000,000 warmup + 25,000,000 measured instructions. Smoke results are preliminary tests, not submission measurements.

Each mode runs LRU, RRIP, I-RRIP V1/V2/V3 and dynamic thresholds 0.10/0.20/0.25/0.35/0.50 on each trace: 30 runs, then a dynamic-0.25 Trace1 repeat. All use one CPU, hashed perceptron, no prefetching, and LRU at other cache levels. Leave the terminal open and prevent sleep while running.

The runner creates a unique `results/task2_full_*` or `results/task2_smoke_*` directory. It does not overwrite previous results. A successful run prints `Completed: .../analysis/TABLES.md`, and its manifest says `complete`. Keep partial logs if a run fails; do not present them as complete measurements.

The legacy simulator uses unquoted paths internally and derives a seed from the filename. The runner therefore creates safe, stable-named aliases under `/tmp` and records them in the manifest. Do not move input traces during a run.

## 5. Read the retained results

```text
results/task2_full_20261015T014645Z_z4ffcl21/
  manifest.json        run status, budgets, trace hashes and commands
  build/manifest.json compiler, source hashes and compile commands
  build/source/       exact simulator source snapshot
  build/*.log         compiler and linker diagnostics
  tests/*.txt         test output
  tests/summary.json  test outcome
  logs/               30 raw measurement logs plus one repeat
  analysis/           CSV, JSON, Markdown reports and ten PNG plots
```

Build binaries, object files and test executables are rebuildable and have been removed from Git. Their historical commands/hashes remain in manifests. `analysis/REPORT.md` is the generated results report; root `TASK2_REPORT.md` also explains implementation and interpretation.

IPC is instructions per cycle (higher is better). Speedup is IPC divided by LRU IPC on the same trace. Load MPKI is misses per 1,000 retired instructions; instruction + data MPKI must equal total L2 load MPKI within printed rounding. Dynamic sampling includes warmup and all callback request types, so it differs from ROI load-only MPKI.

## 6. Validate or regenerate without rerunning simulations

Set this variable in Ubuntu:

```bash
RUN_DIR=results/task2_full_20261015T014645Z_z4ffcl21
```

Use a new output directory for every check; tools refuse to overwrite:

```bash
python3 task2/test.py --output .task2-work/my-tests
python3 task2/audit.py --run-dir "$RUN_DIR" --output .task2-work/my-audit
python3 task2/final_checks.py --run-dir "$RUN_DIR" --output .task2-work/my-checks
python3 task2/analyze.py --input "$RUN_DIR/logs" --output .task2-work/my-analysis --expected 25000000
python3 parse_results.py --input "$RUN_DIR/logs" lru rrip irrip_v1 irrip_v2 irrip_v3
```

`final_checks.py` includes policy/parser tests, source and result validation, plot generation, and trace-discovery checks. It does not need the original traces, old historical results, or stored executables. The small parser fixture under `task2/tests/fixtures/` is synthetic text solely for tests.

For fresh compiled/synthetic integration checks:

```bash
python3 task2/build.py --output .task2-work/my-build
python3 task2/integration_test.py --build .task2-work/my-build --output .task2-work/my-synthetic
python3 task2/test_runner.py --trace .task2-work/my-synthetic/synthetic.champsimtrace.gz --output .task2-work/my-runner-test
```

The last command exercises the full smoke pipeline on explicitly marked synthetic inputs. Its performance values must never be included in the assignment report.

## 7. Troubleshooting

| Problem | Action |
|---|---|
| `need exactly one Trace1...; found 0` | Check the supplied directory and supported filenames; distinguish Linux and Windows home directories. |
| `found 2` | Point to a directory with one accepted copy per trace. |
| Missing compiler or matplotlib | Install packages in Ubuntu, not just Windows Python. |
| `$'\r': command not found` | Save `run_task2.sh` with LF line endings. |
| Compiler error | Read the relevant build log before changing code or flags. |
| Compression validation fails | Obtain a complete, correctly compressed trace; renaming is insufficient. |
| Parser rejects a log | Check completion, budgets and counters; never invent missing measurements. |
| Invalid dynamic threshold | Use a finite number in `[0,1]`; default is 0.25. |
| Output directory exists | Choose a new directory; old evidence is preserved. |
| Source-hash audit fails | Simulator source differs from the recorded experiment; investigate and rerun if behavior changed. |

The report dataset is already complete. Remaining submission work is team identification and any course-required export/packaging. Extra thresholds, longer runs or additional ROIs are optional extensions.
