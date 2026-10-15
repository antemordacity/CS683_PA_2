# CS683 PA2 Task 2 report

**Status (15 October 2026): implementation, builds, policy tests, synthetic integration tests, and historical-data audit are complete. The required new 25M + 25M Trace1/Trace2/Trace3 experiments and measured dynamic threshold sensitivity remain blocked by missing assignment traces.** No synthetic or historical result is presented as a new full benchmark.

## 1. Evidence and provenance

| Evidence class | What is available | What it establishes |
|---|---|---|
| Historical assignment runs | 15 saved LRU/RRIP/I-RRIP V1/V2/V3 logs, plus 3 `lru_check` logs | Saved measurements are complete and internally consistent; all 15 old table rows match logs; historical LRU rerun values match |
| New source audit | `results/task2_audit/source_audit_final/audit.json` | 11 call sites, 30 signatures, and preservation of 30 original artifacts checked |
| New builds | `results/task2_audit/build/manifest.json`, six binaries and compiler logs | All six variants compile/link under GCC 13.3 with common simulator configuration |
| New policy tests | `results/task2_audit/tests_final/summary.json` and per-policy logs | Deterministic unit behavior, metadata bounds, counters, switches, and actual static/dynamic policy equivalence |
| New synthetic simulator tests | `results/task2_audit/synthetic/summary.json` | 13 completed 100K + 100K test runs, all requested thresholds plus endpoints, final diagnostics, repeatability |
| New complete runner test | `results/task2_audit/runner_synthetic.log` and its printed result directory | Smoke workflow exercised with explicitly marked synthetic inputs; see section 6 |
| Final verification | `results/task2_audit/final_verification/checks.txt` | Final source hashes, expanded regression suite, plot/report generation, trace-discovery errors and failed-run manifest checks all pass |
| Required new assignment runs | **Unavailable** | Real traces are absent; no new assignment IPC, MPKI or dynamic sensitivity measurements claimed |

The original `Summary.html`, `Summary.pdf`, result logs, table and four plots are preserved. Their recorded build/compiler provenance is historical, not independently reconstructable without the original traces and binaries. The new isolated builds retain source snapshots, compiler commands, hashes and logs. Newly parsed historical results retain the simulator's displayed precision.

## 2. Task 2a audit and corrections

### Callback plumbing and classification

`inc/cache.h` contains the trailing `uint8_t isInstruction` parameter in the generic function pointer and all replacement callback declarations. All replacement definitions accept it. Eight calls in `src/cache.cc` pass the matching packet's `.instruction`: MSHR bypass/fill, WQ hit/fill, RQ hit, PQ hit, and the two optional DTLB prefetch-buffer paths. The three BTB calls in `src/ooo_cpu.cc` pass zero: they do not have an incoming cache packet, and their LRU implementation ignores the flag. Compilation checks the active configuration; optional `PUSH_DTLB_PB` paths were source-audited, not enabled or runtime-tested.

MSHR merges are already handled in the cache: an existing instruction flag is preserved when merging. `fill_cache` sets the resident block's `instruction` flag for instruction LOAD/PREFETCH fills. Instruction-origin translation requests may have a packet instruction flag while their resident blocks are classified as translation. **The preserved static policy and the dynamic policy use the incoming packet flag for insertion/promotion/sampling, and the resident block flag for eviction.** This distinction is intentional compatibility with the supplied simulator; dynamic sampling includes non-load requests and is not identical to the instruction-load MPKI split. Shared instruction/data lines retain the simulator's fill-time classification; no unrelated classification redesign was made.

### Policy rules

All RRIP policies use values 0 through 3. Lower values receive more protection. If no valid line has RRPV 3, increment every line until a victim exists. Incrementing is bounded: the loop only ages when every RRPV is less than 3. Ties use ascending way index.

| Policy | Fill | Hit | Valid-line victim |
|---|---|---|---|
| LRU | MRU | MRU, except writeback hits do not update recency | Least recently used |
| Ordinary RRIP | All packets at 2 | All hits to 0 | First RRPV 3 |
| I-RRIP V1 | Instruction flag: 0; otherwise 2 | All hits to 0 | First RRPV 3 |
| I-RRIP V2 | As V1 | Instruction: 0; otherwise decrement once, saturating at 0 | First RRPV 3 |
| I-RRIP V3 | As V1 | As V2 | First non-instruction resident block at 3; otherwise first block at 3 |

LRU's writeback-hit exception is preserved. Ordinary RRIP and static I-RRIP promote writeback hits according to their existing rules; they need not imitate LRU. V3 changes only a tie among currently evictable lines. It does not skip an instruction at 3 to age and evict data at a lower RRPV.

**Minimal corrections made:**

1. Both `rrip.l2c_repl` and `irrip.l2c_repl` now return the first invalid way before inspecting RRPV. Previously a low-RRPV invalid slot could lose to a valid victim. Normal cold initialization often masks this defect because all slots start at 3. The invalid-low-RRPV case is tested explicitly.
2. `IRRIP_VERSION` now has an overridable default of 3 and a compile-time check for 1/2/3. Builds no longer need to edit the source with sed to select a version.
3. The L2 final-replacement-statistics call in `src/main.cc` was moved from the multicore-only statistics path into the common final loop. This makes single-core dynamic diagnostics visible exactly once.
4. `parse_results.py` now provides an importable validated parser while preserving its old `parse()` tuple interface and command-line table use. The new analyzer adds IPC and dynamic sensitivity plots in new directories.

No changes were made to `src/cache.cc`, LRU policy code, cache geometry, the branch predictor, prefetchers, or unrelated tasks. The existing `PAGE_TABLE_WALKER::handle_page_fault` already returns 0; this was checked rather than applying another compiler workaround. All builds succeeded. Existing warnings about deprecated feature macros, ambiguous else clauses, optional-context format arguments, signedness, nested comments and potentially uninitialized variables remain in build logs. They were not suppressed or speculatively changed; synthetic success does not establish that every optional simulator path is free of defects.

### Changed-file inventory

The five modified tracked files are `replacement/dyn_irrip.l2c_repl`, `replacement/irrip.l2c_repl`, `replacement/rrip.l2c_repl`, `src/main.cc`, and `parse_results.py`. New deliverables are `run_task2.sh`, `TASK2_README.md`, this report, and `TASK2_COMMANDS.md`. New automation lives in `task2/build.py`, `run.py`, `analyze.py`, `audit.py`, `test.py`, `integration_test.py`, `test_runner.py`, and `final_checks.py`; `task2/tests/cache.h` and `policies.cc` provide the policy test harness. Generated source snapshots, binaries, compiler logs, test logs, manifests, CSV/JSON/Markdown tables and PNGs are kept under the new result directories. Ubuntu build/plot/PDF prerequisites were installed as recorded in the command log.

### Historical report/plot audit

The extracted PDF is retained at `results/task2_audit/Summary_extracted.txt`. Its result table and the original text table match all 15 logs at their printed precision. The four original PNG plots were visually inspected against those logs and their generation code. New plots below are regenerated from validated data and include the missing IPC plot.

Two interpretive corrections to the old PDF matter:

- A change labeled "insertion (LRU -> V1)" does not isolate insertion, because the underlying LRU-to-RRIP change is also present. Use **RRIP -> V1** to isolate insertion, V1 -> V2 for promotion, and V2 -> V3 for eviction.
- On Trace2 the V3 speedup is 1.0188 relative to RRIP and 1.0214 relative to LRU. The old wording that the speedup is "larger" against RRIP is incorrect. These are different baselines.

The original report's conceptual 2-bit RRPV storage description should also be distinguished from the implementation: static RRIP uses `uint32_t` per entry, while the new dynamic implementation uses `uint8_t`. Neither array is physically bit-packed. Claims that a trace is instruction-bound are interpretations supported by the miss/IPC trends, not independent causal measurements.

## 3. Task 2b design

### Deterministic RRIP leaders

`replacement/dyn_irrip.l2c_repl` selects 32 of 1024 L2 sets (3.125%) as permanent RRIP leaders: sets **16, 48, 80, ..., 1008**, one at the center of each consecutive 32-set interval. There is no random leader selection. The default leaves 992 follower sets. `DYN_IRRIP_LEADERS` can change the count at compile time, with checks that it is nonzero, within the set count, and divides the number of sets.

Leader insertion, hit promotion and eviction always use ordinary RRIP, regardless of the current follower mode. This supplies a stable policy reference while sampling only a small fraction of the cache. The count is a design choice, not an experimentally optimized value. Shared lower-cache traffic can still influence which accesses arrive at leaders; fixed RRIP leaders are not a proof of an independent workload sample.

### Counting and decision

Per CPU, retain four 64-bit cumulative counters:

- `ia`: instruction-flagged leader accesses; `im`: their misses.
- `da`: non-instruction leader accesses; `dm`: their misses.

A completed hit callback increments one access. A completed fill callback increments one access **and** one miss. The miss term is deliberately added again in the metric; it weights a miss twice, as required, while each event is recorded once in each applicable counter. No counters are incremented in `find_victim`, on failed allocation retries, or separately at miss lookup. MSHR-merged requests are represented by their eventual fill, matching this simulator's `sim_access`/`sim_miss` completion convention. Outstanding misses at termination do not become completed-fill samples. All request types, including writeback/prefetch/translation, participate.

```text
A = ia + da
M = im + dm
metric = (ia + im) / (A + M)
```

With no samples, the follower mode is RRIP and the reported metric is zero. After each successful leader callback, choose V3 if `metric >= threshold`, otherwise RRIP. Exact equality selects V3. The current leader callback itself still follows RRIP. Followers never affect sampling counters. The configurable runtime variable `TASK2_THRESHOLD` defaults to 0.25 and accepts only finite values in `[0,1]`. The full experiment matrix uses 0.10, 0.20, 0.25, 0.35, 0.50. A single dynamic binary serves all thresholds, avoiding accidental compile-configuration differences.

### Switching, validity and costs

Victim selection and update both consult the same current per-CPU mode and fixed leader predicate. The simulator calls final victim selection and successful fill update synchronously; no other leader callback occurs between them. If a fill is blocked, a later victim search can use a newly selected policy. Victim-call diagnostic counts include retries, but access/miss counters do not.

Switching preserves existing RRPVs; subsequent insertions, promotions and evictions use the new mode immediately. This avoids clearing a useful cache or scanning all follower sets and resembles a gradual transition rather than pretending all resident lines were inserted under the new policy. Invalid entries always take priority, even after mode changes. All decisions and way tie-breaks are deterministic.

Statistics include **warmup plus ROI**, and are intentionally not reset at the warmup boundary. Warmup trains the mode and replacement metadata. Cumulative sampling avoids a new window-size tuning parameter but reacts slowly to late phase changes; near-threshold oscillation is possible because no unrequested hysteresis is added. The mode Boolean is cached and recomputed only on leader callbacks, so follower operations need no division. The 64-bit counters are far from overflow in the required instruction budgets. This implementation is per CPU for dynamic state; the supported experiment configuration remains single-core, as are the supplied static RRPV arrays.

Dynamic RRPVs occupy 8192 bytes per CPU (`1024*8` byte entries). Four sampling counters add 32 bytes; other counters, the threshold, and the mode are diagnostics/control overhead. A hardware implementation could pack RRPVs into 2048 bytes. Leadership needs no table.

### Diagnostics

- `DYN_CONFIG`: threshold, count/list of leader sets, and counting scope.
- `DYN_SWITCH`: sample count, metric and new mode for the first 16 switches, to bound log size.
- `DYN_STATS`: all four counters, final metric/mode, total switch count, leader updates, follower updates in each mode, and victim calls in each mode.

The analyzer verifies `im <= ia`, `dm <= da`, `leader_updates == ia+da`, the metric and the final decision. Both follower counters and switch totals show whether both modes were actually exercised. A final mode alone would not establish switching. The synthetic 0.25 test reported `ia=2576`, `im=2550`, `da=2093`, `dm=866`, giving `5126/8085 = 0.634013605442`; it switched once, with 16 follower RRIP updates and 144927 follower V3 updates. **These are synthetic diagnostic counts, not Trace1 measurements.**

## 4. Historical results, newly validated

These values come from the teammate's saved logs with 25M warmup + 25M requested simulation instructions. They were **not rerun on the updated code**. The parser checks completion, ROI uniqueness, retirement budget, IPC/count consistency, access = hit + miss, MPKI/count consistency, and instruction + data = total within six-significant-digit printing tolerance. It does not infer unavailable raw instruction-miss counts from rounded MPKI.

| Trace | Policy | IPC | Speedup / LRU | L2C load MPKI | Instruction MPKI | Data MPKI |
|---|---|---:|---:|---:|---:|---:|
| Trace1 | lru | 0.232345 | 1.000000 | 17.69560 | 10.33770 | 7.35796 |
| Trace1 | rrip | 0.232231 | 0.999509 | 17.63870 | 10.56180 | 7.07688 |
| Trace1 | irrip_v1 | 0.232256 | 0.999617 | 17.68190 | 10.11490 | 7.56700 |
| Trace1 | irrip_v2 | 0.232223 | 0.999475 | 17.69490 | 9.97300 | 7.72192 |
| Trace1 | irrip_v3 | 0.232109 | 0.998984 | 17.75250 | 9.85048 | 7.90200 |
| Trace2 | lru | 0.251158 | 1.000000 | 27.35680 | 18.85330 | 8.50352 |
| Trace2 | rrip | 0.251806 | 1.002580 | 25.74580 | 17.78130 | 7.96452 |
| Trace2 | irrip_v1 | 0.253964 | 1.011172 | 24.84760 | 16.11560 | 8.73196 |
| Trace2 | irrip_v2 | 0.255011 | 1.015341 | 23.89410 | 14.74980 | 9.14424 |
| Trace2 | irrip_v3 | 0.256535 | 1.021409 | 22.60240 | 13.25850 | 9.34396 |
| Trace3 | lru | 0.382065 | 1.000000 | 3.95424 | 1.12408 | 2.83016 |
| Trace3 | rrip | 0.381739 | 0.999147 | 4.03948 | 1.19704 | 2.84244 |
| Trace3 | irrip_v1 | 0.382002 | 0.999835 | 3.94800 | 1.07672 | 2.87128 |
| Trace3 | irrip_v2 | 0.382079 | 1.000037 | 3.89560 | 1.02440 | 2.87120 |
| Trace3 | irrip_v3 | 0.382079 | 1.000037 | 3.87840 | 0.99520 | 2.88320 |

### Instruction versus data trade-off

Relative to historical LRU, V3 reduces instruction MPKI on all three traces, but increases data MPKI on all three:

| Trace | Instruction MPKI change | Data MPKI change | Total load MPKI change | IPC change |
|---|---:|---:|---:|---:|
| Trace1 | -4.71% | +7.39% | +0.32% | -0.102% |
| Trace2 | -29.68% | +9.88% | -17.38% | +2.141% |
| Trace3 | -11.47% | +1.87% | -1.92% | +0.0037% |

Trace2's 5.5948 instruction-MPKI reduction outweighs its 0.84044 data-MPKI increase. Trace1 instead saves 0.48722 instruction MPKI while adding 0.54404 data MPKI, with slightly worse total MPKI and IPC. Trace3 has low instruction pressure and practically unchanged IPC despite fewer load misses. These trends explain the motivation for selecting instruction protection only when the sampled instruction weight is high; they do not prove that the proposed threshold metric optimizes IPC.

For the correct insertion-only comparison on Trace2, RRIP -> V1 changes instruction MPKI from 17.7813 to 16.1156, data MPKI from 7.96452 to 8.73196, and IPC from 0.251806 to 0.253964. The V1/V2/V3 sequence then demonstrates progressively stronger instruction protection. A static policy's miss reduction need not produce a proportional speedup because latency overlap, front-end stalls, translation traffic, and other bottlenecks matter.

### Regenerated historical plots

![Historical IPC](results/task2_audit/historical/ipc.png)

![Historical speedup relative to LRU](results/task2_audit/historical/speedup.png)

![Historical L2C load MPKI](results/task2_audit/historical/load_mpki.png)

![Historical instruction load MPKI](results/task2_audit/historical/instr_mpki.png)

![Historical data load MPKI](results/task2_audit/historical/data_mpki.png)

The source CSV and full validated records are in `results/task2_audit/historical/`. Old LRU and `lru_check` logs match on all parsed metrics and counts for each trace, supporting the teammate's historical callback-regression claim. That is a comparison of existing files, not a new benchmark rerun.

## 5. Threshold sensitivity: what is and is not measured

**No real-trace dynamic threshold measurements are available.** The requested matrix is implemented but cannot run until the actual traces are placed in `/home/sailesh/traces` or another supplied directory.

| Threshold | Real Trace1, 25M + 25M | Real Trace2, 25M + 25M | Real Trace3, 25M + 25M |
|---|---|---|---|
| 0.10 | Pending: trace absent | Pending: trace absent | Pending: trace absent |
| 0.20 | Pending: trace absent | Pending: trace absent | Pending: trace absent |
| 0.25 | Pending: trace absent | Pending: trace absent | Pending: trace absent |
| 0.35 | Pending: trace absent | Pending: trace absent | Pending: trace absent |
| 0.50 | Pending: trace absent | Pending: trace absent | Pending: trace absent |

For a fixed sampled metric, a lower threshold chooses V3 more often; a higher threshold requires stronger instruction pressure. Actual trajectories may change when the policy changes, so monotonic IPC or miss rates must not be assumed. The default 0.25 is configurable, not claimed optimal. Cumulative warmup training can make several thresholds produce identical mode trajectories. A valid final study must inspect the switch counts, both follower-update counts, IPC/speedup, and all three MPKI measures together.

`task2/analyze.py` generates five sensitivity plots with RRIP/static V3/LRU reference lines, a diagnostics table, and numerical best-threshold/tie summaries for each trace. The complete smoke workflow also exercises these outputs on explicitly labeled synthetic inputs; those plots are pipeline tests only and are not substituted here for missing assignment measurements. Once real full runs finish, their `analysis/REPORT.md`, `TABLES.md`, CSV, and ten plots provide the measured sensitivity evidence.

## 6. Verification and automation

### Policy tests

`task2/test.py` compiles the actual policy source into a small cache-interface harness with undefined-behavior sanitization. Tests cover insertion, promotion, eviction, invalid lines with low RRPV, all-instruction victim fallback, ageing to 3, saturated promotion, LRU writeback behavior, leader count/distribution, leaders remaining RRIP in all operations, empty statistics, exact threshold equality, switching both directions, state reset, mixed request types, and retries not counting accesses. Each policy executes 10,000 deterministic stress events and is run twice with identical output.

A separate equivalence stream feeds **the actual ordinary RRIP and static V3 implementations** and the dynamic follower implementation 10,000 matching events per mode. Victim and RRPV digests match for RRIP mode and V3 mode. This checks agreement without inventing a second policy algorithm as the oracle. Seven invalid threshold strings are rejected. Parser tests accept all 18 historical logs and reject deliberately incomplete, mis-budgeted, missing-field and inconsistent-IPC logs. The cache-interface harness is not a replacement for full simulator testing; both were performed on synthetic input.

### Simulator integration

All six binaries were compiled with `-Wall -g -std=c++11 -O3` and static linking, matching the repository Makefile's intended flags. The builder reuses the policy/prefetcher selections in `build_champsim.sh` inside an isolated copy and compiles common objects once. LRU, RRIP, V1/V2/V3 and dynamic thresholds 0, 0.10, 0.20, 0.25, 0.35, 0.50, 1 were each run on a generated 64-byte-record fixture with 100K warmup + 100K ROI. Dynamic 0.25 was repeated, yielding identical parsed metrics and diagnostics. Dynamic threshold 1 stayed in RRIP and matched the ordinary RRIP parsed performance statistics on this fixture. This verifies execution and integration, not benchmark performance or correctness of every simulator path.

### Runner behavior

`run_task2.sh` supports the exact required commands:

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

Both were executed against the real expected trace location and exited with:

```text
Task 2 failed: /home/sailesh/traces: need exactly one Trace1.gz/.xz or trace1.champsimtrace.gz/.xz; found 0
```

Smoke uses 100K + 100K, full uses 25M + 25M. Each mode requests 30 simulations: five static configurations plus five dynamic thresholds, each on three traces; then one dynamic reproducibility repeat. Missing files, ambiguous names, missing tools, corrupted compression, failed simulation, missing diagnostics, incorrect instruction budgets and inconsistent parsed statistics cause errors. Output directories are unique and existing artifacts are never overwritten.

The simulator derives part of its random seed from the trace path. The runner therefore creates safe `/tmp` aliases with stable names `TraceN.champsimtrace.gz`/`.xz`, making the relevant seed token `TraceN` independent of the original location or timestamp. Every compared policy uses the same alias. This seed convention differs from historical direct `~/traces/TraceN.gz` commands; historical and new numbers must remain separate. The trace SHA-256, original path, alias, binary hash, source hashes, compiler and commands are retained. The full smoke workflow was additionally run with a `.SYNTHETIC_TEST_ONLY` marker and its outputs prominently identify that provenance.

The complete synthetic runner output is `results/task2_smoke_20261014T234839Z_n_l4t8zf/`. Its 30 matrix runs plus repeat passed, bringing the total actual synthetic simulator invocations to 44 when combined with the 13 direct integration runs. Final re-analysis with the latest reporting code is in `results/task2_audit/final_verification/synthetic_analysis/REPORT.md`, with five comparison plots and five sensitivity plots. The final checks also deliberately injected a pre-build failure to verify the retained `failed_or_interrupted` manifest; that test directory is not a failed benchmark experiment.

### Checks that failed or remained blocked

- Initial sandbox WSL enumeration was denied; the approved external WSL check succeeded. The first nested-shell package probe had a quoting error, then the corrected probe succeeded.
- WSL initially lacked a compiler, make, plotting package and PDF extractor. `sudo -n` required a password. An approved WSL-root package install supplied `build-essential`, `python3-matplotlib` and `poppler-utils`; builds then passed.
- The first source-audit helper assumed single-line signatures and rejected the new multiline definition. The helper was corrected to parse multiline signatures; the final 11-site/30-signature audit passed. This was an audit-tool failure, not a policy failure.
- An initial WSL `git diff --check` interpreted the Windows checkout's CRLF endings as changes throughout the repository. A command-local `-c core.autocrlf=true` matched the checkout conversion and the check passed; no repository Git configuration or unrelated files were changed. The original failed diagnostic log was preserved.
- No compiler failure, sanitizer failure, policy assertion failure, or synthetic simulator failure was observed in the completed checks.
- The real smoke/full experiment commands are **blocked by missing traces**. No amount of parsing the old logs supplies the missing dynamic measurements.

See `TASK2_COMMANDS.md` for executed setup, verification and reproduction commands. See `TASK2_README.md` for beginner installation, trace placement and troubleshooting.

## 7. Assignment requirement checklist

| Requirement | Implementation / deliverable | Evidence | Report section / status |
|---|---|---|---|
| Inspect README, PDF, policies, cache sources, build/run/report scripts and outputs | Source review; PDF extraction | `Summary_extracted.txt`, source audit and historical audit | 1-2: done |
| Propagate `packet.instruction` through required callbacks | Existing callback plumbing retained | 11 calls, 30 signatures checked; all variants compile | 2: active paths tested, optional PB paths source-only |
| Audit insertion, promotion, eviction and V1/V2/V3 differences | `irrip.l2c_repl`, `rrip.l2c_repl`; invalid-way fix, version override | Six harness tests, stress streams, synthetic runs | 2, 6: done at code/test level |
| Preserve LRU and ordinary RRIP correctness | LRU unchanged; RRIP invalid-entry priority | LRU/writeback tests, ordinary RRIP tests, synthetic runs | 2, 6: tested; real rerun pending |
| Validate historical results and plots, add IPC | Validated parser/analyzer; five new historical PNGs | 15 table rows, 18 logs, visual inspection | 4: done for historical data |
| Explain instruction/data miss trade-off | Historical comparison and corrected baseline attribution | Validated instruction/data/total MPKI and IPC | 4: done |
| Implement Dynamic I-RRIP | `replacement/dyn_irrip.l2c_repl` | Compiled binary, policy/equivalence tests | 3: done |
| Small deterministic distributed RRIP-only leaders | 32 sets, `set % 32 == 16` | Leader count and insertion/promotion/eviction tests | 3: done |
| Access/miss counters without duplicate events | Completed-callback sampling only | Exact synthetic unit counts; retry test; final diagnostic invariants | 3, 6: done |
| Required metric and configurable threshold | `(ia+im)/(ia+da+im+dm)`, runtime environment | Equality, invalid-input, empty-state tests; diagnostics | 3: done |
| Consistent insertion/promotion/eviction under selected mode | Shared mode and leader predicate | 10K-event actual-policy equivalence in both modes | 3, 6: done |
| Empty statistics, invalid entries, switching, optimizations | RRIP fallback, invalid-first, retain RRPVs, cached decision | Unit tests and switching diagnostics | 3: done |
| Compile/test LRU, RRIP, static V3 and dynamic | Six isolated builds plus tests | Build manifests, sanitizer tests, 13 synthetic runs | 6: done with stated limits |
| Reproducibility | Fixed leaders/aliases; repeated deterministic runs | Harness repeats, dynamic simulator repeat, runner repeat | 6: synthetic verified; real repeat pending |
| Trace1/2/3 at 25M + 25M identical configurations | `run_task2.sh --mode full` | Command attempted; trace preflight failed | 5-6: **blocked, not completed** |
| Thresholds 0.10/0.20/0.25/0.35/0.50 | Runner matrix, single dynamic binary | All thresholds exercised on synthetic fixture | 5: real sensitivity **pending** |
| Five metrics and comparison/sensitivity plots vs RRIP/static | `task2/analyze.py`; historical plots; labeled synthetic pipeline plots | Validated CSV/JSON/Markdown and plot generation | 4-5: historical done; real dynamic **pending** |
| Beginner setup/run/troubleshooting documentation | `TASK2_README.md` | Document covers exact commands and missing-trace errors | Deliverable present |
| Verified report and explicit requirement mapping | `TASK2_REPORT.md`, `TASK2_COMMANDS.md` | This report and linked evidence | Deliverables present; missing measurements explicit |
| Preserve teammate files/results; no commit/push/delete/unrelated edits | New isolated outputs; five targeted tracked-file edits | Original-artifact audit and Git diff | 1-2: done |

## 8. Remaining action

Place the actual course Trace1/Trace2/Trace3 files in `$HOME/traces` inside Ubuntu. Run the smoke command, then the full command. Only after those succeed can the real dynamic tables, sensitivity plots, best-threshold analysis and real-trace reproducibility items above be marked complete. Do not use the synthetic fixture or historical static logs to fill those gaps.
