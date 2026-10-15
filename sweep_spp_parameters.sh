#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage: sweep_spp_parameters.sh <trace-name-or-path> [warmup-instructions] [simulation-instructions] [parallel-jobs]

By default, runs the Cartesian product of:
  SWITCH_THRESHOLDS="2 3"
  SPP_THRESHOLDS="1 2"
  CONFIDENCE_MAXES="4 6"
  parallel-jobs: default 2

Override any sweep with an environment variable, for example:
  SWITCH_THRESHOLDS="2 3 4" SPP_THRESHOLDS="1 2 3" \
    CONFIDENCE_MAXES="4 6 8" ./sweep_spp_parameters.sh trace.champsimtrace.xz

Each run's complete output and built binary are saved under results/spp_sweep-<timestamp>/.
EOF
}

if [[ $# -lt 1 || $# -gt 4 ]]; then
    usage
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

trace_arg=$1
warmup_instructions=${2:-25000000}
simulation_instructions=${3:-25000000}
parallel_jobs=${4:-${PARALLEL_JOBS:-2}}

positive_integer='^[1-9][0-9]*$'
if [[ ! $warmup_instructions =~ $positive_integer || ! $simulation_instructions =~ $positive_integer || ! $parallel_jobs =~ $positive_integer ]]; then
    echo "Error: instruction counts and parallel-jobs must be positive integers." >&2
    exit 2
fi

if [[ -f $trace_arg ]]; then
    trace_path=$trace_arg
elif [[ -f "$script_dir/../traces/$trace_arg" ]]; then
    trace_path="$script_dir/../traces/$trace_arg"
elif [[ -f "/traces/$trace_arg" ]]; then
    trace_path="/traces/$trace_arg"
else
    echo "Error: trace not found: $trace_arg" >&2
    echo "Looked in the current directory, ../traces, and /traces." >&2
    exit 1
fi

read -r -a switch_thresholds <<< "${SWITCH_THRESHOLDS:-2 3}"
read -r -a spp_thresholds <<< "${SPP_THRESHOLDS:-1 2}"
read -r -a confidence_maxes <<< "${CONFIDENCE_MAXES:-4 6}"
for value in "${switch_thresholds[@]}" "${spp_thresholds[@]}" "${confidence_maxes[@]}"; do
    if [[ ! $value =~ ^[0-9]+$ ]]; then
        echo "Error: thresholds and counter limits must be non-negative integers." >&2
        exit 2
    fi
done

if ((${#switch_thresholds[@]} == 0 || ${#spp_thresholds[@]} == 0 || ${#confidence_maxes[@]} == 0)); then
    echo "Error: each sweep variable must contain at least one value." >&2
    exit 2
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$script_dir/results"
results_dir="$(mktemp -d "$script_dir/results/spp_sweep-$timestamp.XXXXXX")"
work_root="$(mktemp -d "${TMPDIR:-/tmp}/spp-sweep.XXXXXX")"
pids=()
labels=()
failures=0

cleanup() {
    local status=$?
    if ((${BASH_SUBSHELL:-0} > 0)); then
        return
    fi
    trap - EXIT INT TERM
    for pid in "${pids[@]:-}"; do
        wait "$pid" 2>/dev/null || true
    done
    rm -rf "$work_root"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'switch_threshold\tspp_threshold\tconfidence_max\tstatus\tlog\n' > "$results_dir/summary.tsv"
run_number=0
total_runs=$((${#switch_thresholds[@]} * ${#spp_thresholds[@]} * ${#confidence_maxes[@]}))
binary_name="hashed_perceptron-no-spp-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-spp"

run_one() {
    local switch_threshold=$1
    local spp_threshold=$2
    local confidence_max=$3
    local label=$4
    local workspace="$work_root/$label"
    local build_log="$results_dir/${label}.build.log"
    local log_file="$results_dir/${label}.log"
    local status
    local trace_directory
    local trace_filename

    trap - EXIT INT TERM

    mkdir -p "$workspace"
    cp -R "$script_dir/Makefile" "$script_dir/build_champsim.sh" "$workspace/"
    for directory in branch inc prefetcher replacement src; do
        cp -R "$script_dir/$directory" "$workspace/$directory"
    done

    SWITCH_THRESHOLD_VALUE=$switch_threshold \
    SPP_THRESHOLD_VALUE=$spp_threshold \
    CONFIDENCE_MAX_VALUE=$confidence_max \
    perl -0pi -e '
        s/^#define UNI_THRESHOLD \d+$/#define UNI_THRESHOLD $ENV{SWITCH_THRESHOLD_VALUE}/m
            or die "Could not find UNI_THRESHOLD\n";
        s/^#define NON_UNI_PREFETCH_THRESH \d+$/#define NON_UNI_PREFETCH_THRESH $ENV{SPP_THRESHOLD_VALUE}/m
            or die "Could not find NON_UNI_PREFETCH_THRESH\n";
        s/^#define CONFIDENCE_COUNTER_MAX \d+$/#define CONFIDENCE_COUNTER_MAX $ENV{CONFIDENCE_MAX_VALUE}/m
            or die "Could not find confidence counter maximum\n";
    ' "$workspace/prefetcher/spp.l1d_pref"

    if ! docker run --rm \
        -v "$workspace:/workspace" \
        -w /workspace \
        gcc:7 bash -c './build_champsim.sh spp' > "$build_log" 2>&1; then
        echo "Build failed for $label. See ${label}.build.log" >&2
        printf '%s\t%s\t%s\tbuild-failed\t%s\n' \
            "$switch_threshold" "$spp_threshold" "$confidence_max" "${label}.build.log" \
            > "$results_dir/${label}.row"
        return 1
    fi

    if [[ ! -x "$workspace/bin/$binary_name" ]]; then
        echo "Expected build output not found for $label. See ${label}.build.log" >&2
        printf '%s\t%s\t%s\tmissing-binary\t%s\n' \
            "$switch_threshold" "$spp_threshold" "$confidence_max" "${label}.build.log" \
            > "$results_dir/${label}.row"
        return 1
    fi

    cp -p "$workspace/bin/$binary_name" "$results_dir/$label"
    trace_directory="$(dirname "$trace_path")"
    trace_filename="$(basename "$trace_path")"
    if docker run --rm \
        -v "$workspace:/workspace" \
        -v "$trace_directory:/trace-input:ro" \
        -w /workspace \
        gcc:7 bash -c \
        './bin/hashed_perceptron-no-spp-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-spp -warmup_instructions "$1" -simulation_instructions "$2" -traces "/trace-input/$3"' \
        bash "$warmup_instructions" "$simulation_instructions" "$trace_filename" \
        > "$log_file" 2>&1; then
        status=completed
        grep -E 'CPU 0 cumulative IPC:|Prefetch fills:|L1D PREFETCH  REQUESTED:' "$log_file" || true
    else
        status=simulation-failed
        echo "Simulation failed for $label. See ${label}.log" >&2
    fi

    printf '%s\t%s\t%s\t%s\t%s\n' \
        "$switch_threshold" "$spp_threshold" "$confidence_max" "$status" "${label}.log" \
        > "$results_dir/${label}.row"
    [[ $status == completed ]]
}

wait_batch() {
    local pid
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            failures=$((failures + 1))
        fi
    done
    pids=()
}

for switch_threshold in "${switch_thresholds[@]}"; do
    for spp_threshold in "${spp_thresholds[@]}"; do
        for confidence_max in "${confidence_maxes[@]}"; do
            run_number=$((run_number + 1))
            label="switch-${switch_threshold}_spp-${spp_threshold}_counter-${confidence_max}"
            labels+=("$label")
            echo "[$run_number/$total_runs] Queued $label"

            run_one "$switch_threshold" "$spp_threshold" "$confidence_max" "$label" &
            pids+=("$!")
            if ((${#pids[@]} >= parallel_jobs)); then
                wait_batch
            fi
        done
    done
done

if ((${#pids[@]} > 0)); then
    wait_batch
fi

for label in "${labels[@]}"; do
    if [[ -f "$results_dir/${label}.row" ]]; then
        cat "$results_dir/${label}.row" >> "$results_dir/summary.tsv"
        rm -f "$results_dir/${label}.row"
    else
        echo -e "unknown\tunknown\tunknown\tmissing-result\t${label}.log" >> "$results_dir/summary.tsv"
        failures=$((failures + 1))
    fi
done

echo "Completed sweep; summary: $results_dir/summary.tsv"
if ((failures > 0)); then
    echo "$failures experiment(s) failed; check the corresponding logs." >&2
    exit 1
fi
