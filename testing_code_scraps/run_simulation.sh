#!/usr/bin/env bash

set -euo pipefail

usage() {
    echo "Usage: $0 <binary-name-or-path> <trace-name-or-path>" >&2
    echo "Runs with the README defaults: 25000000 warmup and 25000000 simulation instructions." >&2
}

if [[ $# -ne 2 ]]; then
    usage
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
binary_arg=$1
trace_arg=$2

if [[ "$binary_arg" == */* ]]; then
    binary_path=$binary_arg
else
    binary_path="$script_dir/bin/$binary_arg"
fi

if [[ ! -f "$binary_path" ]]; then
    echo "Error: binary not found: $binary_path" >&2
    exit 1
fi
if [[ ! -x "$binary_path" ]]; then
    echo "Error: binary is not executable: $binary_path" >&2
    exit 1
fi

if [[ -f "$trace_arg" ]]; then
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

exec "$binary_path" \
    -warmup_instructions 25000000 \
    -simulation_instructions 25000000 \
    -traces "$trace_path"
