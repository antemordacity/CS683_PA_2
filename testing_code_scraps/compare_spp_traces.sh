#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: $0 [warmup-instructions] [simulation-instructions] [parallel-jobs] [trace-name]" >&2
}

if (($# > 4)); then
    usage
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
traces_dir="$script_dir/../traces"
warmup_instructions=${1:-25000000}
simulation_instructions=${2:-25000000}
parallel_jobs=${3:-${PARALLEL_JOBS:-2}}
selected_trace=${4:-}

positive_integer='^[1-9][0-9]*$'
if [[ ! $warmup_instructions =~ $positive_integer ||
      ! $simulation_instructions =~ $positive_integer ||
      ! $parallel_jobs =~ $positive_integer ]]; then
    echo "Error: instruction counts and parallel-jobs must be positive integers." >&2
    exit 2
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "Error: Docker must be installed and running." >&2
    exit 1
fi
if ! docker image inspect gcc:7 >/dev/null 2>&1; then
    echo "Error: required Docker image gcc:7 is not available." >&2
    exit 1
fi
if [[ ! -d $traces_dir ]]; then
    echo "Error: expected trace directory at $traces_dir" >&2
    exit 1
fi

traces=()
if [[ -n $selected_trace ]]; then
    if [[ $selected_trace != "$(basename "$selected_trace")" ||
          ! -f "$traces_dir/$selected_trace" ]]; then
        echo "Error: trace not found in $traces_dir: $selected_trace" >&2
        exit 1
    fi
    traces+=("$traces_dir/$selected_trace")
else
    for trace_path in "$traces_dir"/Trace*.gz; do
        [[ -f $trace_path ]] || continue
        [[ $(basename "$trace_path") == Trace1-001.gz ]] && continue
        traces+=("$trace_path")
    done
fi
if ((${#traces[@]} == 0)); then
    echo "Error: no matching trace files found in $traces_dir" >&2
    exit 1
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$script_dir/results"
results_dir="$(mktemp -d "$script_dir/results/spp_vs_ipstride-$timestamp.XXXXXX")"
work_root="$(mktemp -d "${TMPDIR:-/tmp}/spp-compare.XXXXXX")"
configs=(ipstride)
pids=()
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

printf 'trace\tconfiguration\tstatus\tipc\tl1d_mpki\tload_mpki\ttotal_prefetches\tprefetch_hits\tprefetch_useless\tprefetch_accuracy\ttracker_useful\ttracker_useless\ttracker_accuracy\tlog\n' \
    > "$results_dir/summary.tsv"

extract_metric() {
    local file=$1
    local pattern=$2
    local field=$3
    awk -v pattern="$pattern" -v field="$field" '
        index($0, pattern) == 1 {
            for (i = 1; i <= NF; i++)
                if ($i == field) { print $(i + 1); exit }
        }
    ' "$file"
}

run_config() {
    local config=$1
    local workspace="$work_root/$config"
    local build_log="$results_dir/${config}.build.log"
    local binary_name
    local trace_path
    local trace_name
    local label
    local log_file
    local status
    local ipc
    local l1d_mpki
    local load_mpki
    local pf_total
    local pf_hits
    local pf_useless
    local pf_accuracy
    local tracker_useful
    local tracker_useless
    local tracker_accuracy

    trap - EXIT INT TERM
    mkdir -p "$workspace"
    cp -R "$script_dir/Makefile" "$script_dir/build_champsim.sh" "$workspace/"
    for directory in branch inc prefetcher replacement src; do
        cp -R "$script_dir/$directory" "$workspace/$directory"
    done

    if [[ $config == ipstride ]]; then
        binary_name="hashed_perceptron-no-ip_stride-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-ip_stride"
        build_config=ipstride
    else
        binary_name="hashed_perceptron-no-spp-no-no-no-no-no-lru-lru-lru-lru-lru-lru-lru-lru-1core-spp"
        build_config=spp
        case "$config" in
            switch-2_spp-2_counter-6)
                switch_threshold=2
                spp_threshold=2
                confidence_max=6
                ;;
            switch-2_spp-2_counter-4)
                switch_threshold=2
                spp_threshold=2
                confidence_max=4
                ;;
        esac

        SWITCH_THRESHOLD_VALUE=$switch_threshold \
        SPP_THRESHOLD_VALUE=$spp_threshold \
        CONFIDENCE_MAX_VALUE=$confidence_max \
        perl -0pi -e '
            s/^#define UNI_THRESHOLD \d+$/#define UNI_THRESHOLD $ENV{SWITCH_THRESHOLD_VALUE}/m
                or die "Could not find UNI_THRESHOLD\n";
            s/^#define NON_UNI_PREFETCH_THRESH \d+$/#define NON_UNI_PREFETCH_THRESH $ENV{SPP_THRESHOLD_VALUE}/m
                or die "Could not find NON_UNI_PREFETCH_THRESH\n";
            s/if \(counter < \d+\) counter\+\+;/if (counter < $ENV{CONFIDENCE_MAX_VALUE}) counter++;/m
                or die "Could not find confidence counter limit\n";
        ' "$workspace/prefetcher/spp.l1d_pref"
    fi

    if ! docker run --rm \
        -v "$workspace:/workspace" \
        -w /workspace \
        gcc:7 bash -c './build_champsim.sh "$1"' bash "$build_config" \
        > "$build_log" 2>&1; then
        echo "Build failed for $config; see ${config}.build.log" >&2
        for trace_path in "${traces[@]}"; do
            trace_name=$(basename "$trace_path")
            label="${config}__${trace_name%.gz}"
            printf '%s\t%s\tbuild-failed\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\t%s\n' \
                "$trace_name" "$config" "${config}.build.log" \
                > "$results_dir/${label}.row"
        done
        return 1
    fi

    if [[ ! -x "$workspace/bin/$binary_name" ]]; then
        echo "Expected binary missing for $config; see ${config}.build.log" >&2
        return 1
    fi
    cp -p "$workspace/bin/$binary_name" "$results_dir/${config}.binary"

    for trace_path in "${traces[@]}"; do
        trace_name=$(basename "$trace_path")
        label="${config}__${trace_name%.gz}"
        log_file="$results_dir/${label}.log"
        if docker run --rm \
            -v "$workspace:/workspace" \
            -v "$traces_dir:/traces:ro" \
            -w /workspace \
            gcc:7 bash -c \
            './bin/"$1" -warmup_instructions "$2" -simulation_instructions "$3" -traces "/traces/$4"' \
            bash "$binary_name" "$warmup_instructions" "$simulation_instructions" "$trace_name" \
            > "$log_file" 2>&1; then
            status=completed
        else
            status=simulation-failed
            echo "Simulation failed for $config on $trace_name; see ${label}.log" >&2
        fi

        ipc=$(awk '/^CPU 0 cumulative IPC:/ {print $5; exit}' "$log_file")
        l1d_mpki=$(extract_metric "$log_file" "L1D TOTAL" "MPKI:")
        load_mpki=$(extract_metric "$log_file" "L1D LOAD" "MPKI:")
        pf_total=$(extract_metric "$log_file" "L1D PREFETCH" "ISSUED:")
        pf_hits=$(extract_metric "$log_file" "L1D PREFETCH" "USEFUL:")
        pf_useless=$(extract_metric "$log_file" "L1D PREFETCH" "USELESS:")
        pf_accuracy=$(extract_metric "$log_file" "L1D USEFUL LOAD PREFETCHES:" "ACCURACY:")
        tracker_useful=$(awk '/^Prefetch fills:/ {for (i=1;i<=NF;i++) if ($i=="useful:") {print $(i+1); exit}}' "$log_file")
        tracker_useless=$(awk '/^Prefetch fills:/ {for (i=1;i<=NF;i++) if ($i=="useless:") {print $(i+1); exit}}' "$log_file")
        tracker_accuracy=$(awk '/^Prefetch fills:/ {for (i=1;i<=NF;i++) if ($i=="accuracy:") {print $(i+1); exit}}' "$log_file")
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$trace_name" "$config" "$status" "${ipc:-NA}" "${l1d_mpki:-NA}" \
            "${load_mpki:-NA}" "${pf_total:-NA}" "${pf_hits:-NA}" \
            "${pf_useless:-NA}" "${pf_accuracy:-NA}" "${tracker_useful:-NA}" \
            "${tracker_useless:-NA}" "${tracker_accuracy:-NA}" "${label}.log" \
            > "$results_dir/${label}.row"
    done
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

echo "Running IP-stride on ${#traces[@]} traces; jobs=$parallel_jobs"
printf 'Traces:'
printf ' %s' "${traces[@]##*/}"
printf '\nResults: %s\n' "$results_dir"

for config in "${configs[@]}"; do
    run_config "$config" &
    pids+=("$!")
    if ((${#pids[@]} >= parallel_jobs)); then
        wait_batch
    fi
done
if ((${#pids[@]} > 0)); then
    wait_batch
fi

for trace_path in "${traces[@]}"; do
    trace_name=$(basename "$trace_path")
    for config in "${configs[@]}"; do
        label="${config}__${trace_name%.gz}"
        if [[ -f "$results_dir/${label}.row" ]]; then
            cat "$results_dir/${label}.row" >> "$results_dir/summary.tsv"
            rm -f "$results_dir/${label}.row"
        else
            printf '%s\t%s\tmissing-result\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\tNA\t%s.log\n' \
                "$trace_name" "$config" "$label" >> "$results_dir/summary.tsv"
            failures=$((failures + 1))
        fi
    done
done

echo "Summary: $results_dir/summary.tsv"
if ((failures > 0)); then
    echo "$failures configuration build(s) or runs failed." >&2
    exit 1
fi
