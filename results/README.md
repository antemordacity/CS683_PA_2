# Retained Task 2 results

The single report dataset is [task2_full_20261015T014645Z_z4ffcl21](task2_full_20261015T014645Z_z4ffcl21/).

- 25 million warmup + 25 million simulation instructions per run.
- LRU, RRIP, I-RRIP V1/V2/V3, and dynamic thresholds 0.10, 0.20, 0.25, 0.35, 0.50 on Trace1/2/3.
- 30 configurations plus one successful reproducibility repeat.
- GCC 11.4.0, Ubuntu 22.04; identical simulator configuration across policies.
- All 31 raw logs, the source snapshot, manifests, compiler logs, test text/JSON, final CSV/tables and ten plots are retained.

Start with [the generated analysis](task2_full_20261015T014645Z_z4ffcl21/analysis/REPORT.md) or [the main report](../TASK2_REPORT.md). Use same-run baselines throughout. Do not mix in historical or synthetic measurements.

Compiled binaries, intermediate objects and test executables are ignored/rebuildable. Older results and reports were removed from the working tree after being archived locally under `.task2-work/pre_cleanup.zip` (ignored). Previously committed versions remain accessible in Git at commit `7da94cc`; deleting them from this branch does not rewrite history.

Future experiments create new unique folders. After reviewing a newer full run, update this pointer and the report together, retain its raw evidence, and retire the previous dataset. Do not select a result merely because it gives a better number.
