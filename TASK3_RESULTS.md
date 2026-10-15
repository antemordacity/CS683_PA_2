# Task 3 results: where everything is

Branch: `task3-spp-aware` (built on `origin/tan`, SPP imported from `origin/shullies` @ `ac2ab4c`).
All runs: Trace1, Trace2, Trace3; **25M warmup + 25M simulation instructions**; L2C threshold fixed at 0.25.

## Files

| Path | What it is |
| --- | --- |
| `results/task3_full/<tag>_Trace<N>.txt` | Raw ChampSim output, one per config and trace (15 files) |
| `results/task3_full/spp_dyn_aware_Trace2_repeat.txt` | Repeat of one candidate run (determinism check) |
| `results/task3_full/batch.log` | Log of the batch run for the four non-aware configs |
| `task3_table.csv` | Parsed table: IPC, speedup vs LRU, MPKIs, accuracy/useful/issued counts |
| `parse_task3.py` | Produces the CSV: `python3 parse_task3.py results/task3_full > task3_table.csv` |
| `run_t3_batch.sh` | Builds and runs the four configs that need no new code (lru, dyn, spp, spp_dyn) |
| `replacement/dyn_irrip.l2c_repl` | Dynamic I-RRIP with the Task 3 prefetch-aware option (`DYN_PREFETCH_AWARE`, default 0 = original) |
| `prefetcher/spp.l1d_pref` | Team SPP (imported) |

## Config tags (the `<tag>` in file names)

| Tag | L1D prefetcher | L2 replacement | Build name |
| --- | --- | --- | --- |
| `lru` | none | LRU | `baseline` |
| `dyn` | none | original dynamic I-RRIP | `dyn_irrip` |
| `spp` | SPP | LRU | `spp` |
| `spp_dyn` | SPP | original dynamic I-RRIP | `spp+dyn_irrip` |
| `spp_dyn_aware` | SPP | prefetch-aware dynamic I-RRIP | `spp+dyn_irrip` with `DYN_PREFETCH_AWARE 1` |

Speedup in the CSV is IPC divided by the `lru` IPC of the same trace.

## Prefetch-aware policy (followers only; leader sets stay plain RRIP)

- Data line filled by a prefetch: inserted at RRPV `DYN_PF_INSERT_RRPV` (3) instead of 2.
- Prefetch hit on a resident line: no promotion.
- Demand hit on a line still marked as prefetched: promoted to RRPV 0.
- Leader-set sampling is unchanged (prefetch accesses count as non-instruction, as in Task 2).
- Diagnostics: the `DYN_PF_STATS` line at the end of each raw output (`aware=`, `pf_fills`, `pf_hits`, `demand_reuse_of_prefetched`); `DYN_STATS` has mode and update counts.

## How to reproduce one run

```bash
# edit replacement/dyn_irrip.l2c_repl: set DYN_PREFETCH_AWARE to 1 for the aware config
./build_champsim.sh spp+dyn_irrip
BIN=$(ls -t bin/hashed* | head -1); cp $BIN bin/t3_spp_dyn_aware
./bin/t3_spp_dyn_aware -warmup_instructions 25000000 -simulation_instructions 25000000 \
  -traces ~/traces/Trace2.gz > results/task3_full/spp_dyn_aware_Trace2.txt
```
Traces (`Trace1.gz`, `Trace2.gz`, `Trace3.gz`) are not in Git; put them in `~/traces`.

## Caveats

- The "resolved accuracy" printed by SPP uses its own lifetime counters, which include warmup. Do not call it simulation-only accuracy.
- The simulator's printed `ACCURACY` field is not a general L1D/L2 accuracy; use the useful and issued counts instead.
- Coverage is not computed by the parser; define it before reporting (see `TASK3_TEAMMATE_HANDOFF.md`).
- Single 25M-instruction window per trace, no variance estimate; differences of about 0.1% are within noise.
- The repeat of `spp_dyn_aware` on Trace2 gave identical IPC and cycles (only the printed wall-clock time differed).
- Task 2 evidence is separate and unchanged (`results/task2_full_20261015T014645Z_z4ffcl21/`, commit `febc4df`).
