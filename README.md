# ChampSim - CS683 PA2

ChampSim is a trace-based processor simulator. This branch implements Task 2a
(static instruction-conscious RRIP V1/V2/V3) and Task 2b (Dynamic I-RRIP).

**The required Task 2 real-trace experiment matrix is complete.** The latest report uses
one retained 25M warmup + 25M simulation dataset, including all five dynamic
thresholds on Trace1/Trace2/Trace3.

- [Report and requirement checklist](TASK2_REPORT.md)
- [Beginner setup, traces, running and troubleshooting](TASK2_README.md)
- [Retained results](results/README.md)
- [Teammate submission handoff](TASK2_TEAMMATE_HANDOFF.md)
- [Commands and cleanup record](TASK2_COMMANDS.md)
- [Task 3 team handoff: integrate SPP from shullies with this branch](TASK3_TEAMMATE_HANDOFF.md)

Task 3 implementation and experiments remain to be done on a branch based on
this Task 2 code. The handoff identifies the SPP source, integration steps and
required comparisons; Task 2 completion does not imply Task 3 completion.

## Repository map

`inc/` holds simulator declarations/configuration, `src/` implements the CPU/cache/
memory machinery, `replacement/` holds replacement policies, `prefetcher/` holds
prefetch policies, and `branch/` holds the branch predictor. Task 2 automation and
tests are in `task2/`; experiment evidence is in `results/`.

## Rerun when needed (Ubuntu / Linux)

```bash
bash run_task2.sh --trace-dir "$HOME/traces" --mode smoke
bash run_task2.sh --trace-dir "$HOME/traces" --mode full
```

Use course-provided compressed traces, stored outside Git. Do not use synthetic
fixtures as assignment measurements. Install dependencies as described in the
beginner guide; old GCC 7 installation instructions are no longer necessary.
The retained full run used GCC 11.4, and development builds also passed GCC 13.3.

The original `Makefile` and `build_champsim.sh` remain available for individual
simulator builds; the Task 2 runner builds in isolated directories.

Course resources:

- [Course traces (course-account access may be required)](https://drive.google.com/drive/folders/1zYchkn-M1auZp_l5wRkIzAcDYPkNtW3H?usp=sharing)
- [ChampSim documentation](https://champsim.github.io/ChampSim/master/index.html)
