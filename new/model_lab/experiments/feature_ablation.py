#!/usr/bin/env python3
"""Run the registered, isolated F0-F5 feature ablation."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark_model_families import (
    FOLDS,
    LAB,
    MARKETS,
    calculate_metrics,
    feature_hash,
    file_hash,
    fit_predict,
    load_frame,
    package_versions,
    paired_week_bootstrap,
    prediction_frame,
    validate_output_path,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = LAB / "results" / "EXP-01-feature-ablation-2026-27-partial"
GROUP_NAMES = ("F0", "F1", "F2", "F3", "F4", "F5")

# Freeze model family choices from the four completed folds in EXP-05.
# The current 2026-27 partial fold is excluded from model-family selection.
MARKET_MODELS = {
    "1x2": "xgboost",
    "ou25": "logreg",
    "home_ou05": "xgboost",
    "home_ou15": "xgboost",
    "away_ou05": "xgboost",
    "away_ou15": "xgboost",
}


def build_feature_groups(features: list[str]) -> dict[str, list[str]]:
    """Return the cumulative feature groups specified in PLAN.md."""
    stages = (
        ("F0", ("home_form5_", "away_form5_"), set()),
        ("F1", ("home_form10_", "away_form10_"), set()),
        ("F2", ("home_venue_", "away_venue_"), set()),
        ("F3", ("home_rest_", "away_rest_", "home_season_", "away_season_"), set()),
        ("F4", ("h2h_",), set()),
        ("F5", ("diff_",), {"sum_expected_goals"}),
    )
    groups: dict[str, list[str]] = {}
    selected: list[str] = []
    for name, prefixes, exact in stages:
        selected.extend(
            column for column in features
            if column not in selected
            and (column.startswith(prefixes) or column in exact)
        )
        groups[name] = selected.copy()

    unassigned = sorted(set(features) - set(groups["F5"]))
    if unassigned:
        raise ValueError(f"Safe features are not assigned to an F0-F5 group: {unassigned}")
    if any(not groups[name] for name in GROUP_NAMES):
        raise ValueError("Every F0-F5 feature group must contain at least one feature.")
    return groups


def _score_subset(rows: pd.DataFrame, market: str) -> dict:
    class_count = MARKETS[market][2]
    probabilities = rows[[f"p{i}" for i in range(class_count)]].to_numpy(dtype=float)
    return calculate_metrics(rows["y_true"].to_numpy(dtype=int), probabilities,
                             MARKETS[market][1])


def coherence_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Check probability sums and monotonic team-goal probabilities."""
    checks = []
    for (fold, feature_group), rows in predictions.groupby(
        ["fold", "feature_group"], sort=True
    ):
        by_market = {
            market: group.set_index("_row_id")
            for market, group in rows.groupby("market", sort=True)
        }
        if "1x2" in by_market:
            probs = by_market["1x2"][[f"p{i}" for i in range(3)]].to_numpy(float)
            errors = np.abs(probs.sum(axis=1) - 1.0)
            checks.append({
                "fold": fold, "feature_group": feature_group,
                "check": "1x2_probability_sum", "n": len(errors),
                "violations": int((errors > 1e-8).sum()),
                "max_error": float(errors.max()) if len(errors) else None,
                "max_excess": None,
            })
        for market in ("ou25", "home_ou05", "home_ou15", "away_ou05", "away_ou15"):
            if market not in by_market:
                continue
            market_rows = by_market[market]
            errors = np.abs(
                market_rows["p0"].to_numpy(float)
                + market_rows["p1"].to_numpy(float) - 1.0
            )
            checks.append({
                "fold": fold, "feature_group": feature_group,
                "check": f"{market}_probability_sum", "n": len(errors),
                "violations": int((errors > 1e-8).sum()),
                "max_error": float(errors.max()) if len(errors) else None,
                "max_excess": None,
            })
        for side in ("home", "away"):
            lower, upper = f"{side}_ou05", f"{side}_ou15"
            if lower not in by_market or upper not in by_market:
                continue
            matched = pd.concat(
                [
                    by_market[lower]["p1"].rename("over05"),
                    by_market[upper]["p1"].rename("over15"),
                ],
                axis=1,
                join="inner",
            ).dropna()
            excess = matched["over15"] - matched["over05"]
            checks.append({
                "fold": fold, "feature_group": feature_group,
                "check": f"{side}_over15_le_over05", "n": len(excess),
                "violations": int((excess > 1e-12).sum()),
                "max_error": None,
                "max_excess": float(excess.max()) if len(excess) else None,
            })
    return pd.DataFrame(checks)


def make_report(aggregate: pd.DataFrame, comparisons: dict,
                coherence: pd.DataFrame, manifest: dict) -> str:
    lines = [
        "# EXP-01 — Ablation Fitur F0-F5",
        "",
        "**Status: REFERENCE_ONLY — hasil historis ini bukan bukti siap taruhan atau profitabilitas.**",
        "",
        "## Protokol",
        "",
        f"- Fold: {', '.join(fold['name'] for fold in manifest['folds'])}.",
        f"- Rentang hasil yang tersedia: {manifest['test_date_min']} sampai "
        f"{manifest['test_date_max']}; total baris berlabel per pasar dilaporkan di CSV.",
        "- Keluarga model tiap pasar dibekukan dari hasil EXP-05 pada empat fold "
        "lengkap sebelumnya; fold ini tidak dipakai untuk memilih keluarga model.",
        "- Feature groups kumulatif: F0 form lima laga; F1 tambah form sepuluh laga; "
        "F2 tambah venue; F3 tambah istirahat dan musim; F4 tambah H2H; F5 tambah "
        "selisih tim dan expected goals.",
        "- Hanya fitur statistik pra-pertandingan dalam whitelist yang digunakan. "
        "Odds, target, dan statistik pascapertandingan bukan input.",
        "- Semua periode historis dalam proyek telah ditinjau; temuan hanya untuk "
        "screening dan tidak menjadi holdout independen.",
        "",
        "## LogLoss dan Brier per pasar",
        "",
        "Lebih rendah lebih baik. Baris dengan LogLoss terendah hanya menandai "
        "kelompok yang layak diuji lagi; bukan kandidat terpilih.",
        "",
        "| Pasar | Keluarga | Fitur terendah LL | LogLoss | Brier | N |",
        "|---|---|---|---:|---:|---:|",
    ]
    for market in MARKETS:
        rows = aggregate.loc[aggregate["market"] == market].sort_values(
            ["logloss", "brier"]
        )
        if rows.empty:
            continue
        best = rows.iloc[0]
        lines.append(
            f"| {market} | {best['model']} | {best['feature_group']} | "
            f"{best['logloss']:.5f} | {best['brier']:.5f} | {int(best['n']):,} |"
        )

    lines.extend([
        "",
        "## Perubahan bertahap terhadap kelompok sebelumnya",
        "",
        "Δ LogLoss = kelompok saat ini dikurangi kelompok sebelumnya; nilai negatif "
        "mengarah lebih baik. Interval paired bootstrap mingguan dikoreksi Bonferroni "
        "untuk 32 perbandingan. Interval yang melintasi nol tidak memberi bukti "
        "perbedaan yang meyakinkan.",
        "",
        "| Pasar | Perbandingan | N | Δ LogLoss | CI simultan 95% |",
        "|---|---|---:|---:|---:|",
    ])
    for market in MARKETS:
        market_comparisons = comparisons.get(market, {})
        for group in GROUP_NAMES[1:]:
            result = market_comparisons.get(group, {})
            if not result or result.get("delta_logloss") is None:
                continue
            lines.append(
                f"| {market} | {GROUP_NAMES[GROUP_NAMES.index(group) - 1]} → {group} | "
                f"{result['n']:,} | {result['delta_logloss']:+.5f} | "
                f"[{result['ci_low']:.5f}, {result['ci_high']:.5f}] |"
            )

    supported_gains = []
    supported_losses = []
    for market, market_comparisons in comparisons.items():
        for group, result in market_comparisons.items():
            if result.get("ci_high") is None:
                continue
            previous = GROUP_NAMES[GROUP_NAMES.index(group) - 1]
            label = f"{market}: {previous} → {group}"
            if result["ci_high"] < 0:
                supported_gains.append(label)
            elif result["ci_low"] > 0:
                supported_losses.append(label)
    lines.extend(["", "## Interpretasi perbandingan", ""])
    if supported_gains:
        lines.append(
            "Penambahan fitur dengan interval simultan sepenuhnya di bawah nol: "
            + "; ".join(supported_gains) + "."
        )
    else:
        lines.append(
            "Tidak ada penambahan fitur yang menunjukkan peningkatan LogLoss "
            "meyakinkan setelah koreksi perbandingan berganda."
        )
    if supported_losses:
        lines.append(
            "Penambahan fitur dengan interval simultan sepenuhnya di atas nol "
            "(memburuk): " + "; ".join(supported_losses) + "."
        )
    lines.extend([
        "",
        "## Konsistensi probabilitas",
        "",
        "Peluang 1X2 dan pasar biner seharusnya berjumlah 1; peluang Over 1.5 tidak "
        "boleh melebihi Over 0.5 untuk tim yang sama.",
        "",
        "| Pemeriksaan | Baris cocok | Pelanggaran | Error/excess maksimum |",
        "|---|---:|---:|---:|",
    ])
    if coherence.empty:
        lines.append("| Tidak tersedia | 0 | — | — |")
    else:
        for check, rows in coherence.groupby("check", sort=True):
            n = int(rows["n"].sum())
            violations = int(rows["violations"].fillna(0).sum())
            values = list(rows["max_error"].dropna()) + list(
                rows["max_excess"].dropna()
            )
            maximum = max(values) if values else float("nan")
            lines.append(
                f"| {check} | {n:,} | {violations:,} | {maximum:.3g} |"
            )
    lines.extend([
        "",
        "## Batas penggunaan",
        "",
        "- Satu fold parsial dengan cakupan terbatas tidak cukup untuk memilih model "
        "terbaik yang umum atau menyatakan model siap digunakan.",
        "- Semua hasil tetap `REFERENCE_ONLY`; tidak ada model yang dipromosikan, "
        "tidak ada taruhan, dan tidak ada artefak produksi yang diubah.",
        "- Sebelum penggunaan nyata diperlukan paper tracking prospektif yang "
        "dibekukan sebelumnya dan odds bertimestamp pada waktu keputusan.",
        "",
        "Manifest, metrik per fold, paired comparison, dan prediksi tersedia di folder "
        "hasil eksperimen ini.",
        "",
    ])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> Path:
    input_path = args.input.resolve()
    output_path = validate_output_path(args.output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input not found: {input_path}")
    if output_path.exists() and any(output_path.iterdir()) and not args.overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {output_path}; use --overwrite to replace it."
        )
    output_path.mkdir(parents=True, exist_ok=True)

    frame, features = load_frame(input_path)
    groups = build_feature_groups(features)
    markets = args.markets or list(MARKETS)
    requested_groups = args.groups or list(GROUP_NAMES)
    selected_folds = [fold for fold in FOLDS
                      if not args.fold or fold["name"] in args.fold]
    if not selected_folds:
        raise ValueError("No folds selected.")
    unknown_groups = set(requested_groups) - set(GROUP_NAMES)
    if unknown_groups:
        raise ValueError(f"Unknown feature groups: {sorted(unknown_groups)}")

    all_predictions: list[pd.DataFrame] = []
    fit_details: list[dict] = []
    for fold in selected_folds:
        train_mask = frame["Date"] <= pd.Timestamp(fold["train_end"])
        test_mask = frame["Date"].between(
            pd.Timestamp(fold["test_start"]), pd.Timestamp(fold["test_end"])
        )
        train = frame.loc[train_mask]
        test = frame.loc[test_mask]
        if train.empty or test.empty:
            raise ValueError(
                f"Selected fold {fold['name']} has train={len(train)} and test={len(test)}."
            )
        if train["Date"].max() >= test["Date"].min():
            raise ValueError(f"Temporal overlap found in fold {fold['name']}.")
        print(f"Fold {fold['name']}: train={len(train):,}, test={len(test):,}")

        for market in markets:
            target, _, class_count = MARKETS[market]
            clean_train = train.loc[train[target].notna()]
            clean_test = test.loc[test[target].notna()]
            if clean_train.empty or clean_test.empty:
                raise ValueError(f"No labeled train/test rows for {market}, {fold['name']}.")
            y_train = clean_train[target].to_numpy(dtype=int)
            y_test = clean_test[target].to_numpy(dtype=int)
            if not set(np.unique(y_train)).issubset(set(range(class_count))):
                raise ValueError(f"Unexpected class labels in {market}, {fold['name']}.")
            model_name = MARKET_MODELS[market]

            for group_name in requested_groups:
                columns = groups[group_name]
                X_train = clean_train[columns].to_numpy(dtype=np.float32)
                X_test = clean_test[columns].to_numpy(dtype=np.float32)
                started = time.perf_counter()
                probabilities, details = fit_predict(
                    model_name, X_train, y_train, clean_train["Date"],
                    X_test, class_count
                )
                prediction = prediction_frame(
                    clean_test, fold["name"], market, model_name,
                    y_test, probabilities
                )
                prediction["feature_group"] = group_name
                all_predictions.append(prediction)
                metrics = calculate_metrics(
                    y_test, probabilities, MARKETS[market][1]
                )
                elapsed = round(time.perf_counter() - started, 3)
                fit_details.append({
                    "fold": fold["name"],
                    "market": market,
                    "model": model_name,
                    "feature_group": group_name,
                    "feature_count": len(columns),
                    "train_n": int(len(clean_train)),
                    "test_n": int(len(clean_test)),
                    "elapsed_seconds": elapsed,
                    **details,
                })
                print(
                    f"  {market:12s} {model_name:8s} {group_name} "
                    f"features={len(columns):2d} logloss={metrics['logloss']:.5f} "
                    f"({elapsed:.1f}s)"
                )

    predictions = pd.concat(all_predictions, ignore_index=True)
    predictions["Date"] = pd.to_datetime(predictions["Date"], errors="coerce")
    fold_rows = []
    for (fold_name, market, group_name), rows in predictions.groupby(
        ["fold", "market", "feature_group"], sort=True
    ):
        fold_rows.append({
            "fold": fold_name,
            "market": market,
            "model": MARKET_MODELS[market],
            "feature_group": group_name,
            "feature_count": len(groups[group_name]),
            **_score_subset(rows, market),
        })
    fold_metrics = pd.DataFrame(fold_rows)

    aggregate_rows = []
    for (market, group_name), rows in predictions.groupby(
        ["market", "feature_group"], sort=True
    ):
        aggregate_rows.append({
            "market": market,
            "model": MARKET_MODELS[market],
            "feature_group": group_name,
            "feature_count": len(groups[group_name]),
            "folds": int(rows["fold"].nunique()),
            **_score_subset(rows, market),
        })
    aggregate = pd.DataFrame(aggregate_rows)

    comparisons: dict = {}
    for market in markets:
        market_predictions = predictions.loc[predictions["market"] == market]
        comparisons[market] = {}
        for previous, current in zip(GROUP_NAMES, GROUP_NAMES[1:]):
            if previous not in requested_groups or current not in requested_groups:
                continue
            candidate = market_predictions.loc[
                market_predictions["feature_group"] == current
            ]
            reference = market_predictions.loc[
                market_predictions["feature_group"] == previous
            ]
            comparisons[market][current] = paired_week_bootstrap(
                candidate, reference, MARKETS[market][2], reps=args.bootstrap_reps
            )
    coherence = coherence_diagnostics(predictions)

    manifest = {
        "status": "REFERENCE_ONLY",
        "purpose": "market-specific cumulative feature ablation",
        "input": str(input_path.relative_to(ROOT))
        if input_path.is_relative_to(ROOT) else str(input_path),
        "input_sha256": file_hash(input_path),
        "input_rows_with_valid_dates": int(len(frame)),
        "test_date_min": str(predictions["Date"].min().date()),
        "test_date_max": str(predictions["Date"].max().date()),
        "feature_groups": {
            name: groups[name] for name in requested_groups
        },
        "feature_group_hashes": {
            name: feature_hash(groups[name]) for name in requested_groups
        },
        "model_selection": (
            "Fixed per market from EXP-05 aggregate logloss on completed folds "
            "2022-23 through 2025-26; the selected 2026-27 partial fold is excluded."
        ),
        "models": {market: MARKET_MODELS[market] for market in markets},
        "markets": markets,
        "folds": selected_folds,
        "bootstrap_reps": args.bootstrap_reps,
        "familywise_comparisons": 32,
        "familywise_confidence": 0.95,
        "coherence_check": (
            "1X2/binary probability sums and P(team Over 1.5) <= P(team Over 0.5)"
        ),
        "odds_policy": "No odds used as model inputs or evaluation references.",
        "limitations": [
            "Historical periods have already been inspected; results are reference-only.",
            "The default 2026-27 fold is partial and has limited coverage.",
            "No timestamped decision-time odds or prospective validation.",
            "No live betting or profit guarantee.",
        ],
        "package_versions": package_versions(),
    }
    (output_path / "predictions.csv").parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path / "predictions.csv", index=False)
    fold_metrics.to_csv(output_path / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_path / "aggregate_metrics.csv", index=False)
    coherence.to_csv(output_path / "coherence_checks.csv", index=False)
    (output_path / "paired_comparisons.json").write_text(
        json.dumps(comparisons, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "fit_details.json").write_text(
        json.dumps(fit_details, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "REPORT.md").write_text(
        make_report(aggregate, comparisons, coherence, manifest), encoding="utf-8"
    )
    print(f"Saved isolated experiment to {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=Path(__file__).resolve().parents[3] / "data" /
                        "features_train.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markets", nargs="+", choices=sorted(MARKETS))
    parser.add_argument("--groups", nargs="+", choices=list(GROUP_NAMES))
    parser.add_argument(
        "--fold", nargs="+", choices=[fold["name"] for fold in FOLDS],
        default=["2026-27-partial"],
    )
    parser.add_argument("--bootstrap-reps", type=int, default=5000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.bootstrap_reps < 100:
        parser.error("--bootstrap-reps must be at least 100.")
    return args


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
