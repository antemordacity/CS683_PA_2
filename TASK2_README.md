# CS683 PA2 Task 2: beginner setup and running guide

The Task 2 implementation and automated checks are ready. **The real Trace1, Trace2 and Trace3 experiments still need the assignment trace files.** Historical results are preserved under `results/`; new verification evidence is under `results/task2_audit/`. Read `TASK2_REPORT.md` for the distinction between historical measurements, new synthetic tests, and pending measurements.

## 1. Open a Linux terminal

The simulator expects Linux tools. On Windows, open the installed **Ubuntu-24.04** application, or run this in PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Inside Ubuntu, move to this repository:

```bash
cd /mnt/e/IITB/5th_Semester/CS683/CS683_PA_2
```

`pwd` prints your current directory. `ls` should show `run_task2.sh`, `inc`, `src`, and `replacement`. Run all subsequent commands in this Linux terminal, not PowerShell. `$HOME` is your Linux home directory (here `/home/sailesh`), not your Windows user directory.

## 2. Install prerequisites

On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3 python3-matplotlib gzip xz-utils
```

Type your Linux password when sudo asks; the terminal does not display password characters. `poppler-utils` is optional if you want to extract the old PDF. GCC 13.3 successfully built all six variants in this session; you do not need to add an old Ubuntu repository or downgrade GCC. The existing page-table missing-return fix is already present.

Check installation:

```bash
g++ --version
python3 -c 'import matplotlib; print(matplotlib.__version__)'
```

The runner uses two compiler jobs by default. Set `TASK2_JOBS=1` before the command if memory is limited. `CXX=g++-13` can explicitly select a compiler. All policy comparisons within a run use the same compiler, flags, and simulator configuration.

## 3. Obtain and place the assignment traces

Obtain the actual three assignment traces from the course's authorized trace download listed in the repository README. This may require your course account. They were **not available** in this workspace or `/home/sailesh/traces` during verification. Do not substitute the generated synthetic test fixture for assignment measurements.

```bash
mkdir -p "$HOME/traces"
```

Copy the three downloaded files into that directory using your file manager. For example, Windows can access the Ubuntu home directory through `\\wsl.localhost\Ubuntu-24.04\home\sailesh`. Supported names are case-insensitive:

```text
$HOME/traces/
  Trace1.gz
  Trace2.gz
  Trace3.gz
```

Also accepted: `Trace1.xz`, `trace1.champsimtrace.gz`, or `trace1.champsimtrace.xz`, and the equivalent Trace2/3 names. Keep exactly one accepted file per trace; duplicate gzip/xz copies are rejected. Keep them compressed. The runner verifies compressed-file integrity and records SHA-256 hashes. It cannot establish that a valid compressed file is the correct course workload; use the actual supplied traces.

## 4. First run the short smoke check

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
```

This uses **100,000 warmup + 100,000 simulation instructions** for each trace/configuration, so it is a functionality check, not the requested final experiment. It compiles policies, runs policy/parser tests, then runs LRU, RRIP, static I-RRIP V1/V2/V3, and dynamic thresholds 0.10, 0.20, 0.25, 0.35, 0.50 on each of the three traces (30 simulations). It repeats dynamic 0.25 on Trace1 to check reproducibility.

The program prints a unique directory such as `results/task2_smoke_DATE_RANDOM/`. It never reuses an existing result directory. Compilation and simulations are sequential at the policy/trace level to avoid oversubscribing your machine. Leave the terminal open until it reports completion; use Ctrl+C to stop if necessary. Partial logs are retained and must not be reported as successful experiments.

## 5. Run the final assignment experiments

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

This runs **25,000,000 warmup + 25,000,000 simulation instructions**, with the same 30 configurations and one repeat. Runtime depends on your hardware and traces. There is no claim that these full runs were performed in this session. If a run fails, inspect its log; rerunning starts a new result directory and preserves the failed run.

For both modes, the simulator configuration is one CPU, hashed perceptron branch predictor, no prefetching at any level, and LRU everywhere except the selected L2 policy. The existing 1024-set, 8-way L2 geometry is unchanged.

## 6. Read the results

Inside the printed result directory:

| Path | Contents |
|---|---|
| `manifest.json` | Mode, instruction budgets, trace hashes, stable trace aliases, simulator commands, binary hashes, repeat status |
| `build/manifest.json` | Compiler, compilation commands, source hashes, configuration |
| `build/source/` | Isolated source snapshot; your working source files are never replaced by the build |
| `build/bin/` | Six simulator binaries; dynamic thresholds share one binary |
| `build/*.log` | Compiler/linker diagnostics |
| `tests/summary.json` | Policy, equivalence, parser, and reproducibility checks |
| `logs/` | Complete simulator output per configuration and trace |
| `analysis/metrics.csv`, `validated.json`, `TABLES.md`, `REPORT.md` | Validated measurements, dynamic diagnostics, numerical sensitivity summary, and report with plots |
| `analysis/ipc.png`, `speedup.png`, `load_mpki.png`, `instr_mpki.png`, `data_mpki.png` | Five comparison plots |
| `analysis/sensitivity_*.png` | Five threshold sensitivity plots, with LRU, RRIP, and static V3 reference lines |

Speedup is IPC divided by LRU IPC on the same trace and instruction budget. MPKI means load misses per 1,000 retired simulation instructions. Instruction MPKI + data MPKI must equal total L2 load MPKI, allowing for printed rounding. Dynamic sampling counters include warmup and all request types; they are not ROI load-only MPKI counters.

The final report currently includes verified historical tables and explicitly marks the missing full experiments. After running `--mode full`, use the newly generated `analysis/TABLES.md` and plots as the measured Task 2b evidence. Review mode switches and follower counts before drawing conclusions about sensitivity; a threshold that never selects both modes is a valid observation, not an automatic failure.

## 7. Re-run individual checks or parsing

Use a **new output directory** on each invocation (these tools intentionally refuse to overwrite):

```bash
python3 task2/build.py --output results/my_task2_build
python3 task2/test.py --output results/my_task2_tests
python3 task2/integration_test.py --build results/my_task2_build --output results/my_synthetic_check
python3 task2/audit.py results/my_source_audit
python3 task2/analyze.py --input results --output results/my_historical_analysis --historical --expected 25000000
python3 parse_results.py lru rrip irrip_v1 irrip_v2 irrip_v3
```

To regenerate plots from a completed full run, replace `RUN_DIRECTORY` below with its actual name:

```bash
python3 task2/analyze.py --input results/RUN_DIRECTORY/logs --output results/my_full_analysis --expected 25000000
```

For labeled synthetic logs, also pass `--synthetic`. `python3 task2/test_runner.py --output results/my_runner_test` is a developer integration test using a generated fixture and the `.SYNTHETIC_TEST_ONLY` marker; its measurements must never enter an assignment result table. It expects `results/task2_audit/synthetic/synthetic.champsimtrace.gz` from the integration check, or accepts `--trace` with another generated fixture path.

To run a dynamic binary directly, set its threshold with an environment variable:

```bash
TASK2_THRESHOLD=0.35 results/my_task2_build/bin/dyn_irrip -warmup_instructions 25000000 -simulation_instructions 25000000 -traces /absolute/safe/path/Trace1.champsimtrace.gz
```

Prefer the runner: the legacy simulator embeds trace paths in shell commands without quoting. The runner creates safe symlinks under `/tmp/cs683_task2_*`, keeps a stable trace filename for the simulator's filename-derived random seed, and records the alias. Do not move the original files during a run. These small symlink directories are retained for reproducibility.

## 8. Troubleshooting

- **`need exactly one Trace1...; found 0`**: the file is missing or misnamed, or you used the Windows home instead of the Ubuntu home. Check `ls -l "$HOME/traces"`.
- **`found 2`**: two accepted copies of a trace exist. Point to a directory containing only one copy of each trace.
- **`No module named matplotlib`**: install `python3-matplotlib` in Ubuntu. Installing it in Windows Python does not install it in Ubuntu.
- **`g++` not found**: install `build-essential`. If `CXX` names an unavailable compiler, unset it or choose an installed compiler.
- **`$'\r': command not found`**: the shell file has Windows CRLF endings. Save `run_task2.sh` with LF endings in your editor. It is supplied with LF endings.
- **Compiler error**: inspect `build/*.log`. Preserve the log and diagnose the specific cause; do not change compiler flags or unrelated source speculatively. Existing warnings are documented in the report.
- **gzip/xz validation failure**: re-download the trace; renaming a compressed file does not change its actual format.
- **Parser rejection**: inspect the corresponding log for an aborted run, absent ROI, mixed budgets, or inconsistent counts. Do not fill in missing measurements.
- **Invalid threshold**: only finite numbers in `[0,1]` are accepted; the default is 0.25. Empty strings, NaN, infinity, and trailing junk are rejected.
- **No dynamic diagnostics**: rebuild with the updated `src/main.cc`; it now calls L2 replacement final statistics on the single-core path.
- **Full run is slow**: the workload is 30 simulations plus one repeat at 50M total instructions each. Smoke mode is only a preliminary check. Old results are not silently reused.

The legacy `run_ladder.sh`, `plot_results.py`, and `make_summary.py` remain preserved. They can change old files; use the new runner/analyzer for this workflow.
