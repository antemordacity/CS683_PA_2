# Task 3 handoff: build on Task 2 and the team's SPP

## Status and ownership

Task 2a/2b are implemented and have a verified 25M warmup + 25M simulation dataset. Task 3 is **not implemented or measured on `tan` yet**. The statement that no further simulations are required applies only to Task 2.

The Task 3 team should create a new branch from the cleaned `origin/tan`, import the team's SPP implementation, then implement prefetch awareness. The report author can continue preparing Task 2's report separately. Keep Task 3 implementation, scripts and new results on the Task 3 branch until reviewed; do not overwrite the retained Task 2 evidence or report.

SPP source inspected on 2026-10-15: `origin/shullies` at **`ac2ab4c28fd9041c3cb7ace3ae17d30ce15b035e`**. That branch's simulator-source changes from `origin/main` are confined to `prefetcher/spp.l1d_pref`. It also contains many historical experiments and binaries. Source inspection confirms prefetch generation using `prefetch_line` with `FILL_L1`/`FILL_L2`; this handoff does not certify SPP correctness or its performance.

## Start here: commands for the Task 3 team

Run these in your own clean checkout. Save any current work on your existing branch before switching; do not discard it. For a fresh checkout, first clone `https://github.com/antemordacity/CS683_PA_2.git` and enter it.

```bash
git fetch origin
git switch -c task3-spp-aware origin/tan
git rev-parse HEAD  # record the Task 2 handoff commit in Task 3 provenance

# Import the reviewed SPP file, leaving tan's cache interfaces and policies intact.
git restore --source=ac2ab4c28fd9041c3cb7ace3ae17d30ce15b035e -- prefetcher/spp.l1d_pref
git diff -- prefetcher/spp.l1d_pref
git add prefetcher/spp.l1d_pref
git commit -m "Import team SPP implementation for Task 3"
git push -u origin task3-spp-aware
```

One teammate creates/pushes this branch. Other teammates then use `git fetch origin` and `git switch --track origin/task3-spp-aware`. Coordinate ownership of the shared replacement file. If SPP has since improved, review its newer diff with the SPP author before changing the pinned import.

These are **handoff instructions**, not a claim that SPP was imported into `tan`. On `tan`, `prefetcher/spp.l1d_pref` remains the original empty stub. Starting on `shullies` alone would omit the Task 2 changes. Importing this file onto the Task 2 base combines the needed work without merging unrelated artifacts.

## Task 2 code you are inheriting

| Location | Purpose / integration constraint |
| --- | --- |
| `replacement/rrip.l2c_repl` | Ordinary two-bit RRIP baseline. |
| `replacement/irrip.l2c_repl` | Static I-RRIP V1/V2/V3. See the Task 2 report for the variant definitions. |
| `replacement/dyn_irrip.l2c_repl` | **Required Task 3 implementation location.** Already implements dynamic selection and diagnostics. |
| `inc/cache.h`, `inc/block.h`, `src/cache.cc` | Instruction-aware callback interfaces, resident line metadata and packet propagation. Preserve these Task 2 changes. |
| `prefetcher/spp.l1d_pref` | Import the working SPP from `shullies` here. |
| `build_champsim.sh`, `Makefile` | Existing build entry points; `spp` and `spp+dyn_irrip` already select the SPP file, but selection alone does not implement awareness. |
| `run_task2.sh`, `task2/build.py`, `task2/run.py` | Isolated Task 2 experiment automation. **The Task 2 builder selects `no` for all prefetchers.** |
| `parse_results.py`, `task2/analyze.py` | Reusable parsing/plotting foundations; Task 3 requires additional metrics and configurations. |
| `task2/test.py`, `task2/tests/` | Policy, counter, threshold, equivalence and parser tests. |
| `TASK2_REPORT.md`, `TASK2_README.md` | Verified explanation/results and installation/trace instructions. |
| `results/task2_full_20261015T014645Z_z4ffcl21/` | Frozen Task 2 logs, manifests, source snapshots, CSV and plots. Preserve unchanged. |

Dynamic I-RRIP keeps 32 deterministically distributed RRIP-only leader sets. Successful replacement updates count one access, plus one miss on a fill; victim selection does not sample, because a stalled fill can retry. Leader instruction/non-instruction counts drive `(instruction accesses + instruction misses) / (total accesses + total misses)`. Followers use I-RRIP V3 when this metric is at least the threshold, otherwise RRIP. The default threshold is 0.25, overridden with `TASK2_THRESHOLD`; statistics accumulate across warmup and simulation. Empty statistics start in RRIP. Invalid ways are selected first. `DYN_CONFIG`, `DYN_SWITCH` and `DYN_STATS` provide diagnostics.

V3 favors instruction insertion, uses different instruction/data hit promotion, and prefers a data victim among equally distant candidates. Keep insertion, promotion and eviction consistent when extending it. Read the actual code before changing these rules.

## Implement and verify Task 3

1. Keep a reproducible unmodified dynamic baseline. Prefer an explicitly recorded, default-off compile-time switch for Task 3 awareness in `dyn_irrip.l2c_repl`, so the same source can build both baseline and candidate. Preserve Task 2 behavior when disabled. This switch is a recommendation, not an existing feature.
2. Distinguish incoming `type == PREFETCH` from demand traffic. Also distinguish an incoming demand hit from a resident line originally brought by a prefetch: the packet type and resident `BLOCK::prefetch` describe different things. Check callback ordering; `src/cache.cc` clears the resident prefetch flag after a useful demand hit. Handle fills, promotion, replacement and metadata reuse together.
3. A starting hypothesis is low-priority insertion for speculative data prefetches, no demand-style promotion on repeated prefetch hits, and promotion after demonstrated demand reuse. Test alternatives; weak insertion can also evict useful prefetches too early. Explain the measured trade-off rather than promising an IPC gain.
4. Keep leader sets RRIP-only. Task 2 currently includes prefetch callbacks as non-instruction accesses if present. Explicitly decide and document the sampling treatment; silently excluding them changes the selector's meaning. Apply awareness to followers while preserving the leader baseline unless a justified design requires otherwise.
5. Add diagnostics for prefetch insertions, prefetch hits, demand reuse of prefetched lines, mode selection and leader/follower updates. Verify a prefetch event is counted once, and neither retries nor victim searches inflate access/miss counters.
6. Test invalid entries, replacement of stale metadata, policy switching, threshold edges, leader isolation and determinism. With awareness disabled, verify equivalence to the original dynamic policy. Rerun the Task 2 policy/parser tests for regressions.

Before real runs, verify SPP actually issues prefetches and that the replacement policy sees `PREFETCH` events. A configuration called `spp` with the stub compiled in is not an SPP experiment.

## Comparable experiments still required

Use Trace1, Trace2 and Trace3, each with **25 million warmup and 25 million simulation instructions**, identical simulator configuration, trace bytes, compiler/options and seed handling. Store traces outside Git, normally in `$HOME/traces`; use `TASK2_README.md` for setup.

| Configuration | L1D prefetcher | L2 replacement | Purpose |
| --- | --- | --- | --- |
| LRU, no prefetch | no | LRU | Common speedup reference |
| Dynamic I-RRIP, no prefetch | no | Original dynamic | Required comparison |
| Standalone SPP | Team SPP | LRU | Required comparison; other settings match |
| SPP + original dynamic | Team SPP | Original dynamic | Isolate the benefit of awareness |
| SPP + aware dynamic | Team SPP | Task 3 candidate | Proposed policy |

This is 15 full runs plus a deterministic repeat of at least one candidate run. Additional tuning runs must be labeled separately. Fix the threshold initially at 0.25 across the dynamic comparisons and record it; do not compare separately tuned policies without disclosing the tuning. The original Task 2 threshold sweep remains available for context.

The retained Task 2 no-prefetch controls may be reused only after confirming full configuration, source behavior, trace identity, seed, compiler and measurement compatibility; otherwise rerun controls on the same setup. Do not treat old `shullies` measurements as directly comparable without the same checks.

Add Task 3 automation (for example `run_task3.sh` and `task3/`) that reuses Task 2 utilities where practical. It must compile the actual selected prefetcher and separate common object directories by prefetch configuration; `task2/build.py` currently builds common objects once with all prefetchers disabled. Record source/configuration/binary hashes, exact commands and run status. Use new result directories; never write into the frozen Task 2 dataset. Keep binaries, objects and smoke outputs ignored, but retain full-run logs, manifests, CSV and final plots. No Task 3 runner exists in this handoff yet.

## Metrics and counter pitfalls

Produce both tables and plots for IPC, speedup, prefetch accuracy, prefetch coverage, and LOAD MPKI for L1D, L2C, L2 instruction and L2 data. Use simulation-region instructions for MPKI: `1000 * load_misses / retired_instructions`. Check that L2 instruction and data load misses sum to total L2 load misses. Report speedup relative to the common LRU control, and explicitly show the candidate's IPC ratios against dynamic without SPP and standalone SPP.

Choose and state the prefetch metric definitions **before** measuring:

- The pinned SPP prints **resolved accuracy**, `useful / (useful + useless)`. This differs from useful/issued accuracy; unresolved prefetches are excluded. Its custom lifetime totals are not visibly reset at the warmup boundary in this implementation. Do not label that output as simulation-only accuracy without adding a correct reset or boundary snapshot/subtraction. Keep the adaptive epoch metric separate from the reported measurement metric.
- The simulator also prints an `ACCURACY` field using `pf_lower_level`. Source inspection on `tan` found that counter increment in an STLB path, not a general L1D/L2 SPP issue counter. Do not blindly use that field. Inspect accepted issues, duplicates/merges, useful fills and per-cache accounting, then instrument consistent ROI counters as needed.
- Coverage is not currently produced by the Task 2 parser. If using `useful / (useful + demand_load_misses)`, state that it is a useful-prefetch coverage proxy and define the cache/type scope. A paired miss-reduction measure `(misses_without_prefetch - misses_with_prefetch) / misses_without_prefetch` is a different metric and needs matched replacement policies. Follow any course-specified definition first; do not mix definitions between rows.
- Treat zero denominators as N/A. Explain boundary effects such as a line prefetched during warmup and first used in simulation. Do not manufacture missing values or silently replace undefined accuracy with zero.

## Delivery checklist for the Task 3 team

| Requirement | Evidence to return |
| --- | --- |
| Prefetch-aware dynamic policy | Code in `replacement/dyn_irrip.l2c_repl`, reviewed SPP import and design rationale |
| Correct baseline and switching behavior | Tests plus leader, mode and prefetch-event diagnostics |
| Performance comparison | Matched full-run raw logs for all three traces and all controls above |
| IPC and speedup | Validated CSV, tables and plots, including both required comparisons |
| Accuracy and coverage | Explicit definitions, ROI counter evidence, tables and plots |
| Four load-MPKI breakdowns | L1D/L2C/L2 instruction/L2 data tables and plots with sum checks |
| Reproducibility | Runner, parser/plotter, manifests, source hashes, compiler/configuration and repeat |
| Report handoff | Task 3 report with rationale, measured gains/regressions, limitations and artifact links |

Outperforming both controls is an experimental goal, not an established result. If a candidate loses, report it honestly and use the counters to guide improvements. Send the report author the final commit, exact CSV/plot paths, metric definitions and a short explanation of the winning design. Keep Task 2's report/evidence untouched so report work can proceed independently.
