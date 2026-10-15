# Task 2 commands and cleanup record

## Retained experiment

The report uses only `results/task2_full_20261015T014645Z_z4ffcl21/`:

- Full mode, 25M warmup + 25M measured instructions.
- All 30 policy/threshold/trace combinations plus one reproducibility repeat.
- GCC 11.4.0 on Ubuntu 22.04, recorded in the build manifest.
- Trace sources were `/home/tanish/traces/Trace1.gz`, `Trace2.gz`, and `Trace3.gz` on the teammate's machine.
- All 31 logs parse successfully, the repeat matches, and the original test summary reports success.

Exact historical simulator argument arrays, trace hashes, compiler commands and source hashes are retained in the run's `manifest.json` and `build/manifest.json`. Absolute paths are records of the original machine; they are not instructions to recreate that user's home directory.

The required experiment entry points are:

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

No new simulation was performed during cleanup. The original experiment's raw logs, CSV, JSON, tables, plots, source snapshot, manifests, compiler logs and test text/JSON were preserved byte-for-byte.

## Cleanup applied on branch tan

The user authorized cleanup after review. Changes were limited to documentation, analysis/test tooling, ignore rules, superseded artifacts and rebuildable outputs. No simulator or replacement-policy implementation changed.

1. Added `task2/tests/fixtures/valid_roi.txt`, explicitly synthetic parser-only input, replacing the dependency on `results/lru_Trace1.txt` and a hardcoded historical IPC.
2. Updated `task2/audit.py` and `task2/final_checks.py` to accept `--run-dir`, validate the selected matrix/logs/CSV/source hashes, and operate without old audit/smoke folders.
3. Made the synthetic runner's `--trace` explicit and added `--input` to the parser CLI.
4. Updated the report to use the latest 30-row table, real dynamic diagnostics, threshold discussion and all ten plots. Updated the root README, beginner guide and teammate handoff; added `results/README.md`.
5. Archived superseded reports/results/scripts and unused header backups in ignored `.task2-work/pre_cleanup.zip` before removing them from the working tree. Earlier committed versions also remain accessible at Git commit `7da94cc`.
6. Removed generated full-run binaries, objects and test executables, and removed them from Git's index. Their text/JSON evidence and original source snapshot remain.
7. Added ignore rules for Python caches, local test work, compiler outputs, audit/smoke runs, generated full-run executables, traces and editor backups. Final logs/manifests/plots are not ignored.

The archive contains 466 files/symlinks and passed ZIP integrity checks. Windows `Compress-Archive` initially failed on WSL symlinks without deleting the source files; the archive was then created through WSL with symlink metadata preserved. PowerShell resolved every deletion target and checked that it remained inside the repository before removal. A total of 51 planned file/directory paths were removed. The archive and cleanup plan are local ignored artifacts, not report inputs.

Untracking generated artifacts stages their deletions. Other edits and retired tracked files remain visible in `git status` for review. No commit, push, history rewrite or change to another branch was performed. Existing binary objects remain in old Git history; `.gitignore` does not purge history.

## Checks executed during cleanup

From the repository root (Linux commands were invoked through WSL Ubuntu-24.04):

```bash
python3 -m unittest task2.test.ParserTests -v
python3 task2/audit.py --run-dir results/task2_full_20261015T014645Z_z4ffcl21 --output .task2-work/precleanup-audit
python3 task2/final_checks.py --run-dir results/task2_full_20261015T014645Z_z4ffcl21 --output .task2-work/cleanup-checks
```

The first two checks passed before removal. The final suite runs after removal and includes:

- Shell syntax and Git whitespace checks.
- Six actual policy harness builds with undefined-behavior checks and deterministic repeats.
- Actual static/dynamic equivalence over 10,000 events per mode.
- Seven invalid-threshold cases and independent parser acceptance/rejection tests.
- Eleven callback sites and thirty signatures.
- Complete full-run matrix, 31 logs, matching repeat, CSV consistency, source hashes and ten existing plots.
- Regeneration of tables and all ten plots into an ignored output directory.
- Trace-discovery, missing-file and ambiguous-name checks.

The retained cleanup verification logs are in `results/task2_full_20261015T014645Z_z4ffcl21/verification/`. Generated executables and regenerated duplicate plots stay under ignored `.task2-work/`.

Additional read-only checks compare SHA-256 hashes of all 149 protected full-run files before/after cleanup, verify documentation links, inspect Git's tracked/ignored paths, and confirm the simulator source matches the experiment. Cleanup does not require another benchmark run.

## Re-run checks later

Use a fresh output directory:

```bash
RUN_DIR=results/task2_full_20261015T014645Z_z4ffcl21
python3 task2/final_checks.py --run-dir "$RUN_DIR" --output .task2-work/recheck
python3 parse_results.py --input "$RUN_DIR/logs" lru rrip irrip_v1 irrip_v2 irrip_v3
```

The local archive and deleted old datasets are not prerequisites for either command. See `TASK2_README.md` for optional full reruns or synthetic integration tests. Read `TASK2_REPORT.md` for the final measurements and requirement checklist.

## Task 3 handoff preparation (2026-10-15)

After cleanup, the user requested publishing the baseline for teammates to start
Task 3, and identified `shullies` as the team's SPP branch. The earlier statements
about no commit/push describe the cleanup phase, before this publishing request.

Fetched `origin` and inspected `origin/shullies` at
`ac2ab4c28fd9041c3cb7ace3ae17d30ce15b035e`. Its simulator-source changes from the
common base are confined to `prefetcher/spp.l1d_pref`. Added
`TASK3_TEAMMATE_HANDOFF.md` with a pinned file import, branch workflow, code map,
comparison matrix, metric caveats and delivery checklist. Linked it from the
root README and Task 2 handoff. No simulator/policy/SPP source was changed, and
no Task 3 simulation was performed. The separate local report repository
`6ad0fab29071bd1c410a25a6/` is excluded from this code handoff.

Verification executed successfully through WSL Ubuntu-24.04:

```bash
git fetch origin
git diff --name-only origin/main...origin/shullies -- src inc prefetcher replacement Makefile build_champsim.sh
git show origin/shullies:prefetcher/spp.l1d_pref
python3 task2/final_checks.py --run-dir results/task2_full_20261015T014645Z_z4ffcl21 --output .task2-work/handoff-checks
```

All policy/parser checks, both 10,000-event equivalence checks, the 31-log audit,
source/CSV/repeat checks and regeneration of ten plots passed. The new execution
log is local at `.task2-work/handoff-checks/checks.txt`; the retained cleanup
verification under `results/.../verification/` remains unchanged. Task 3's
prefetch-aware implementation, counter validation and comparable experiments
are assigned to the Task 3 team in the new handoff.
