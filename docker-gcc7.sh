#!/usr/bin/env bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRACE_DIR="${PROJECT_DIR}/../traces"

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is not installed or is not on PATH." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Start Docker Desktop and try again." >&2
    exit 1
fi

if [ ! -d "$TRACE_DIR" ]; then
    echo "Error: expected trace directory at $TRACE_DIR" >&2
    exit 1
fi

docker run --rm -it \
    -v "$PROJECT_DIR:/workspace" \
    -v "$TRACE_DIR:/traces:ro" \
    -w /workspace \
    gcc:7 bash
