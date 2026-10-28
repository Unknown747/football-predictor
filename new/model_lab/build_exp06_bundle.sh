#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
libgomp="$(find /nix/store -maxdepth 4 -path '*/lib/libgomp.so.1' -print -quit 2>/dev/null || true)"
if [[ -z "$libgomp" ]]; then
    echo "Missing libgomp.so.1; install the gcc system dependency first." >&2
    exit 1
fi

export LD_LIBRARY_PATH="$(dirname "$libgomp")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$ROOT"
python new/model_lab/experiments/build_exp06_inference_bundle.py "$@"
exec python new/model_lab/experiments/audit_exp06_inference_bundle.py
