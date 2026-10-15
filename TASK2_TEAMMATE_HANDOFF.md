# Task 2 teammate handoff: report preparation

**The required Task 2 real-trace experiments are complete. No new simulations are needed for the specified Task 2 matrix.** Task 3 needs new implementation and experiments; see [the Task 3 handoff](TASK3_TEAMMATE_HANDOFF.md).

The retained dataset is `results/task2_full_20261015T014645Z_z4ffcl21/`. Its manifest reports a complete full run with 25M warmup + 25M simulation instructions, all 30 configurations and a matching reproducibility repeat. Independent parsing verified all 31 logs and the measurement CSV.

## What to use

- `TASK2_REPORT.md`: implementation explanation, latest verified measurements, ten plots, threshold discussion and requirement checklist.
- `results/.../analysis/REPORT.md`: generated measurement report.
- `results/.../analysis/metrics.csv`: final numerical data.
- `results/.../logs/`: raw evidence, including repeat.
- `results/.../manifest.json`, `build/manifest.json`, and `tests/summary.json`: provenance and verification.
- `TASK2_README.md`: installation, trace placement, validation and rerun commands.

The full run used GCC 11.4 on Ubuntu 22.04; prior GCC 13.3 tests are development verification, not the compiler for these measurements. Traces came from `/home/tanish/traces` on the teammate's machine and are not included in Git.

## Remaining submission steps

1. Read the latest report and verify your team's required names/LDAP identifiers are added to the submission cover or template.
2. Preserve the report's relative plot paths when sharing it. Include the retained `analysis/` directory if exporting or packaging Markdown.
3. If the course requests PDF, export the report and inspect all tables and figures.
4. Do not claim that dynamic I-RRIP universally beats RRIP or static V3: the best threshold differs by trace, and static V3 is slightly faster on Trace2/Trace3.
5. Use the cleaned `tan` baseline for report preparation. The subsequent Task 3 handoff includes this cleanup; teammates should branch from that baseline following `TASK3_TEAMMATE_HANDOFF.md`.

Old report datasets, scripts and generated development artifacts were retired; parser tests now have their own tiny fixture. The retained raw data are unchanged. Rebuildable executables/objects are excluded from Git, while logs, manifests, source snapshots, test evidence and plots remain.

For optional reruns, use the exact smoke/full commands in `TASK2_README.md`. Any simulator or policy behavior change requires fresh comparable measurements; documentation and test-fixture cleanup does not.
