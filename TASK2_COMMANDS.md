# Task 2 command and verification record

Commands below were executed from `E:\IITB\5th_Semester\CS683\CS683_PA_2`, or its WSL path `/mnt/e/IITB/5th_Semester/CS683/CS683_PA_2`. Linux commands were invoked through `wsl -d Ubuntu-24.04 -- ...` from the Windows session. Paths printed with UTC timestamps are run identifiers; the user-facing audit date is 15 October 2026 in Asia/Calcutta.

## Inspection

Read `README.md`, all three RRIP policy files and LRU/base replacement code, `inc/cache.h`, relevant `src/cache.cc`, `src/main.cc`, `src/ooo_cpu.cc`, `src/page_table_walker.cc`, `inc/champsim.h`, `inc/instruction.h`, `Makefile`, `build_champsim.sh`, `run3.sh`, `run_all.sh`, `run_ladder.sh`, all reporting scripts, the historical table, and benchmark logs. Used `rg` searches for replacement callbacks, instruction propagation, statistics, RNG seeding, trace reading, and compiler warnings. Inspected the four original PNG plots and the new plots with the image viewer.

Repository checks:

```text
git branch --show-current
git ls-files
git status --short
git diff --stat
git diff --check
```

The branch is `tan`. Initial tracked worktree changes were empty. No commit, push, reset, cleanup/delete, or modification of unrelated task source was performed.

## Environment setup and PDF inspection

```powershell
wsl --list --quiet
wsl -d Ubuntu-24.04 -- bash -lc 'command -v g++ make python3 pdftotext; ls -ld ~/traces; find /home -maxdepth 3 -iname *trace* 2>/dev/null; python3 -m pip show matplotlib pypdf'
wsl -d Ubuntu-24.04 -- sudo -n apt-get update
wsl -d Ubuntu-24.04 -u root -- bash -lc 'apt-get update && apt-get install -y build-essential python3-matplotlib poppler-utils'
```

Initial sandbox enumeration: access denied; approved external enumeration: succeeded, Ubuntu-24.04 installed. One earlier nested-shell Python package probe had a quotation syntax error; the corrected probe above established the missing toolchain/packages. `sudo -n` failed because a password was required. The explicitly approved WSL-root install succeeded. Native Windows Python initially lacked numpy/matplotlib and PDF packages; the working verification environment is WSL Ubuntu with GCC 13.3, Python 3.12, and matplotlib 3.6.3.

```bash
pdftotext -layout Summary.pdf results/task2_audit/Summary_extracted.txt
```

All pages of the extracted report were read. Original PDF/HTML files were not regenerated or overwritten.

## Compilation and policy/parser tests

```bash
python3 task2/build.py --output results/task2_audit/build
python3 task2/test.py --output results/task2_audit/tests
python3 task2/test.py --output results/task2_audit/tests_final
```

Build passed for `lru`, `rrip`, `irrip_v1`, `irrip_v2`, `irrip_v3`, and `dyn_irrip`. Exact compiler/linker argument arrays and source hashes are in `results/task2_audit/build/manifest.json`; warning output is retained in its `.log` files. No compiler correction was needed.

The initial tests passed, then the suite was expanded with direct static/dynamic equivalence and mixed request types. The expanded suite passed: six policies, two 10K-event equivalence cases, deterministic repeats, seven invalid thresholds, and two Python parser tests (including all 18 historical logs and four corruption cases).

Native Python source audits:

```powershell
python task2/audit.py results/task2_audit/source_audit
python task2/audit.py results/task2_audit/source_audit_final
```

First invocation: audit helper rejected a multiline signature because it assumed one-line definitions. After fixing the helper, final audit passed 11 call sites, 30 signatures, 15 old table rows and preservation of 30 original artifacts. Failed/partial output directories were retained.

## Historical measurement validation and plots

```bash
python3 task2/analyze.py --input results --output results/task2_audit/historical --historical --expected 25000000
```

Passed all 15 primary logs and the three historical LRU repeat comparisons. Generated `metrics.csv`, `validated.json`, `TABLES.md`, and five PNGs including IPC. Old reports, plots and logs remain unchanged.

## New synthetic simulator tests (not assignment benchmarks)

```bash
python3 task2/integration_test.py --build results/task2_audit/build --output results/task2_audit/synthetic
python3 task2/test_runner.py
```

The first command passed 13 actual simulator invocations: LRU, RRIP, V1/V2/V3, dynamic thresholds 0, 0.10, 0.20, 0.25, 0.35, 0.50, 1, and a repeated dynamic 0.25 run. Every run used 100K warmup + 100K simulation. Individual simulator commands and parsed records are saved in `synthetic/summary.json`. The dynamic 0.25 repeat matched exactly; dynamic 1 matched ordinary RRIP performance statistics.

The runner test generated explicitly marked synthetic aliases and invoked the real shell runner with `--mode smoke`. Its 30 matrix simulations plus one repeat completed successfully. The runner output is in `results/task2_audit/runner_synthetic.log`; the complete result directory is:

```text
results/task2_smoke_20261014T234839Z_n_l4t8zf/
```

This directory contains a second six-variant isolated build, tests, 31 logs, validated synthetic metrics/tables, five comparison plots and five sensitivity plots. **Every plotted synthetic dataset is marked SYNTHETIC TEST ONLY.** The fixture contains no course Trace1/2/3 data. These are 31 workflow test invocations, not the required full experiments.

The runner's manifest contains the exact simulator commands and environments. Test scripts were subsequently made rerunnable with an explicit new output directory; see their `--help` and the beginner README.

## Required commands against the real trace location

```bash
bash -n run_task2.sh
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

Shell syntax check passed. Both runner commands failed at trace preflight, before building or simulating:

```text
Task 2 failed: /home/sailesh/traces: need exactly one Trace1.gz/.xz or trace1.champsimtrace.gz/.xz; found 0
```

No new 25M + 25M assignment simulation was performed. No real dynamic sensitivity measurement is available.

## Final verification

```text
python -m py_compile parse_results.py task2/build.py task2/analyze.py task2/run.py task2/test.py task2/audit.py task2/integration_test.py task2/test_runner.py
```

Final verification was run with:

```bash
python3 task2/final_checks.py --output results/task2_audit/final_verification
```

It passed all checks. Exact nested commands and their exit codes are recorded in `results/task2_audit/final_verification/checks.txt`, including the expanded test suite, source audit, historical re-analysis, synthetic comparison/sensitivity report generation, final simulator source-hash comparison, and missing/ambiguous trace rejection. A deliberately injected pre-build failure verified that the runner preserves a manifest marked `failed_or_interrupted`; it did not run another simulator.

The first final-check attempt is preserved in `results/task2_audit/final_checks.txt`. WSL Git initially interpreted Windows CRLF checkout files as whole-file modifications and rejected trailing carriage returns. `git -c core.autocrlf=true diff --check` passed with a command-local setting; no Git configuration or unrelated source was modified. New run output directories refuse overwrites by design.
