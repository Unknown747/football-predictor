#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$LAB_DIR/../.." && pwd)"
libgomp="$(find /nix/store -maxdepth 4 -path '*/lib/libgomp.so.1' -print -quit 2>/dev/null || true)"
if [[ -z "$libgomp" ]]; then
    echo "Missing libgomp.so.1; install the gcc system dependency first." >&2
    exit 1
fi

export LD_LIBRARY_PATH="$(dirname "$libgomp")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec python "$LAB_DIR/experiments/benchmark_model_families.py" "$@"
