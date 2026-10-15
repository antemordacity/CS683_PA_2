# ChampSim

ChampSim is a trace-based simulator for microarchitecture research.

Useful trace links:
- Traces (access requires an LDAP ID): https://drive.google.com/drive/folders/1zYchkn-M1auZp_l5wRkIzAcDYPkNtW3H?usp=sharing
- ChampSim wiki: https://champsim.github.io/ChampSim/master/index.html

## Clone the repository

```bash
git clone https://github.com/cs683-iitb-autumn-2026/pa2.git
```

## Compile

To compile ChampSim, specify which config you to want use, such as baseline, spp, ipstride, irrip or dyn_irrip etc.

For example, `./build_champsim.sh baseline` builds a single-core processor with a hashed perceptron branch predictor, no L1D data prefetcher and LRU replacement policy at all cache levels.

Your binary will have different name for different configs. Custom name help distinguish binaries for different configuration.

```bash
./build_champsim.sh ${config_name}

./build_champsim.sh baseline

--Complied Binary: hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-baseline
```

## Use GCC 7 with Docker

On macOS, start the GCC 7 container from the project directory with:

```bash
./docker-gcc7.sh
```

The script mounts this project at `/workspace` and the sibling `../traces`
directory at `/traces` (read-only), then opens a shell in the container. Build
and run ChampSim from that shell, for example:

```bash
./build_champsim.sh baseline
./bin/[BINARY] -warmup_instructions 25000000 \
  -simulation_instructions 25000000 \
  -traces /traces/Trace1-001.gz
```

The project mount is read-write, so source edits and generated files (including
the build output) are immediately visible on the Mac and persist after the
container exits. The container itself is temporary; its unmounted filesystem
is removed when you exit. The traces mount is read-only.

## Run simulation

```bash
./bin/[BINARY] -warmup_instructions [N_WARM] -simulation_instructions [N_SIM] -traces [TRACE_DIR]/[TRACE]
./bin/hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-baseline -warmup_instructions 25000000 -simulation_instructions 25000000 -traces ../traces/trace1.champsimtrace.xz
```

Where:
- `${BINARY}`: ChampSim binary compiled by `build_champsim.sh baseline` (example, `hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-baseline`)
- `${N_WARM}`: number of instructions for the warmup period (25 million)
- `${N_SIM}`: number of instructions for the detailed simulation (25 million)
- `${TRACE_DIR}`: directory containing the trace (for example, `../traces/`)
- `${TRACE}`: name of the trace (for example, `trace1.champsimtrace.xz`)

To run a built binary with the README's default instruction counts, pass its
name (looked up in `bin/`) and a trace name:

```bash
./run_simulation.sh hashed_perceptron-no-no-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-baseline trace1.champsimtrace.xz
```

You can also pass paths to the binary and trace. For a trace name, the script
looks in the current directory, `../traces/`, and `/traces/` (the Docker mount).
It runs the supplied binary as-is; it does not rebuild it or change its
configuration.

### Sweep SPP thresholds

To compare SPP settings on the same trace, run:

```bash
./sweep_spp_parameters.sh trace1.champsimtrace.xz
```

The default sweep tries switch thresholds `2 3`, SPP confidence thresholds
`1 2`, and confidence-counter maxima `4 6` (eight builds/runs total). Results,
logs, and each tested binary are saved under a timestamped directory in
`results/`. You can change the instruction counts with optional second and
third arguments, or override the tested values with `SWITCH_THRESHOLDS`,
`SPP_THRESHOLDS`, and `CONFIDENCE_MAXES`; see the script's usage text for an
example. The optional fourth argument sets the number of experiments to run
concurrently (default `2`), or set it with `PARALLEL_JOBS`. Each experiment
builds and runs in its own temporary project copy inside the `gcc:7` Docker
image, so concurrent builds do not modify the source tree or interfere with
one another. Docker Desktop must be running.

To run IP-stride on the other available `Trace*.gz` traces (excluding
`Trace1-001.gz`) and compare with the SPP results already saved from the
previous comparison, run:

```bash
./compare_spp_traces.sh
```

It uses 25 million warmup and simulation instructions per trace by default.
Its TSV includes total L1D prefetches issued and useful prefetches (hits), as
well as IPC, MPKI, and prefetch accuracy.
Optional arguments set those counts, parallel job count, and an individual
trace name, in that order. The TSV summary and full logs are saved under a new
`results/` directory. To run only the first trace, for example:

```bash
./compare_spp_traces.sh 25000000 25000000 2 Trace1-001.gz
```

The fixed-degree SPP configuration uses the best tested settings:
`UNI_THRESHOLD=2`, `NON_UNI_PREFETCH_THRESH=2`, confidence-counter maximum `6`,
and prefetch degree `3`. Prefetch accuracy is tracked for final statistics but
does not dynamically throttle prefetching.

`spp_v6.cc` is a separate experimental variant that preserves the SPP v5
prediction, signature, stride, and switcher logic while adding epoch-based
accuracy throttling. `spp_v7.cc` uses lower accuracy thresholds and a
conservative degree mapping. Copy the desired version to
`prefetcher/spp.l1d_pref` before building the `spp` configuration. Each file's
epoch length, four accuracy-regime upper bounds, and regime prefetch degrees
are configurable near the top. V6 defaults to 1,000-cycle epochs, bounds of
20%, 40%, 60%, and 80%, and degrees 1, 2, 3, 4, and 5. V7 uses bounds of 10%,
20%, 30%, and 40%, and degrees 1, 1, 2, 2, and 3. In both versions, a window
containing no resolved prefetches retains the current degree.

## Evaluate the simulation

ChampSim measures IPC (instructions per cycle) as its main performance metric. It also prints other useful metrics at the end of each simulation.

## Install GCC 7 on Ubuntu

```bash
sudo apt update
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
vim /etc/apt/sources.list
```

Update the last line with:

```bash
deb [arch=amd64] http://archive.ubuntu.com/ubuntu focal main universe
```

Then run:

```bash
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get install gcc-7
sudo apt-get install g++-7
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-7 0
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 0
```

If GCC and G++ are already present in `/usr/bin`, configure the alternatives using:

```bash
sudo update-alternatives --config g++
sudo update-alternatives --config gcc
```
