#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$LAB_DIR/../.." && pwd)"
OUTPUT_DIR="${1:-new/model_lab/results/EXP-08-synthetic-odds-scenario-stress-20261028}"
cd "$ROOT_DIR"

libgomp="$(find /nix/store -maxdepth 4 -path '*/lib/libgomp.so.1' -print -quit 2>/dev/null || true)"
if [[ -z "$libgomp" ]]; then
  echo "Missing libgomp.so.1; install the gcc system dependency first." >&2
  exit 1
fi
export LD_LIBRARY_PATH="$(dirname "$libgomp")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

case "$OUTPUT_DIR" in
  new/model_lab/results/*) ;;
  *)
    echo "Output must stay under new/model_lab/results/." >&2
    exit 1
    ;;
esac

mkdir -p "$OUTPUT_DIR"
for subdir in family-models feature-groups odds-report; do
  if [[ -d "$OUTPUT_DIR/$subdir" ]] && find "$OUTPUT_DIR/$subdir" -mindepth 1 -print -quit | grep -q .; then
    echo "Output directory already contains $subdir; choose a new run directory." >&2
    exit 1
  fi
done

bash "$LAB_DIR/run_benchmark.sh" \
  --fold 2026-27-partial \
  --output-dir "$OUTPUT_DIR/family-models"

bash "$LAB_DIR/run_feature_ablation.sh" \
  --fold 2026-27-partial \
  --output-dir "$OUTPUT_DIR/feature-groups"

python "$LAB_DIR/experiments/simulate_odds_scenarios.py" \
  --family-predictions "$OUTPUT_DIR/family-models/predictions.csv" \
  --feature-predictions "$OUTPUT_DIR/feature-groups/predictions.csv" \
  --output-dir "$OUTPUT_DIR/odds-report"
