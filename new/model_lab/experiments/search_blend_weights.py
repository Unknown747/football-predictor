#!/usr/bin/env python3
"""Walk-forward market-specific blend search using only prior OOF predictions."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_model_families import (  # noqa: E402
    FOLDS,
    MARKETS,
    MODEL_NAMES,
    calculate_metrics,
    file_hash,
    package_versions,
    validate_output_path,
)
from simulate_odds_scenarios import probability_coherence  # noqa: E402

EXPERIMENT_ID = "EXP-06"
BLEND_NAME = "OOF_BLEND_PREVIOUS_FOLDS"
GRID_DENOMINATOR = 10
BOOTSTRAP_REPS = 5000
BOOTSTRAP_COMPARISONS = len(MARKETS) * len(MODEL_NAMES)
BOOTSTRAP_SEED = 20261028
LATEST_FOLD = FOLDS[-1]["name"]
RUN_DIR = LAB / "results" / "EXP-06-model-blending-20261028"
DEFAULT_PREDICTIONS = RUN_DIR / "family-models" / "predictions.csv"
DEFAULT_OUTPUT = RUN_DIR / "blend-search"
DEFAULT_FEATURE_PREDICTIONS = (
    LAB / "results" /
    "EXP-08-synthetic-odds-scenario-stress-20261028-reproduction" /
    "feature-groups" / "predictions.csv"
)
DEFAULT_MODEB_METRICS = (
    LAB / "results" /
    "EXP-08-synthetic-odds-scenario-stress-20261028-reproduction" /
    "odds-report" / "scenario_metrics.csv"
)
DEFAULT_HISTORY_AGGREGATE = (
    LAB / "results" / "EXP-05-historical-model-family-benchmark" /
    "aggregate_metrics.csv"
)
EPSILON = 1e-12


def weight_grid(model_count: int = len(MODEL_NAMES),
                denominator: int = GRID_DENOMINATOR) -> list[np.ndarray]:
    """Enumerate every nonnegative simplex mixture at a fixed grid interval."""
    result = []
    for units in itertools.product(range(denominator + 1), repeat=model_count):
        if sum(units) == denominator:
            result.append(np.asarray(units, dtype=float) / denominator)
    return result


def _normalise_probabilities(probabilities: np.ndarray) -> np.ndarray:
    matrix = np.clip(np.asarray(probabilities, dtype=float), EPSILON, 1.0)
    return matrix / matrix.sum(axis=-1, keepdims=True)


def blend_probabilities(probabilities: np.ndarray,
                        weights: np.ndarray) -> np.ndarray:
    """Blend an (observations, models, classes) tensor on the class axis."""
    weights = np.asarray(weights, dtype=float)
    if probabilities.ndim != 3:
        raise ValueError("Expected probabilities with shape (rows, models, classes).")
    if probabilities.shape[1] != len(weights):
        raise ValueError("Weight count does not match the model dimension.")
    if np.any(weights < 0) or not np.isclose(weights.sum(), 1.0):
        raise ValueError("Blend weights must be nonnegative and sum to one.")
    return _normalise_probabilities(
        np.einsum("nmc,m->nc", probabilities, weights)
    )


def _selection_loss(y: np.ndarray, probabilities: np.ndarray,
                    kind: str) -> tuple[float, float]:
    probabilities = _normalise_probabilities(probabilities)
    true_probability = probabilities[np.arange(len(y)), y.astype(int)]
    logloss = float(-np.log(np.clip(true_probability, EPSILON, 1.0)).mean())
    if kind == "multiclass":
        target = np.eye(probabilities.shape[1], dtype=float)[y.astype(int)]
        brier = float(np.square(probabilities - target).sum(axis=1).mean())
    else:
        brier = float(np.square(y.astype(float) - probabilities[:, 1]).mean())
    return logloss, brier


def choose_blend_weights(y: np.ndarray, probabilities: np.ndarray,
                         kind: str,
                         denominator: int = GRID_DENOMINATOR) -> np.ndarray:
    """Choose a deterministic simplex blend by LogLoss, then Brier, then simplicity."""
    if len(y) == 0:
        raise ValueError("Cannot choose blend weights from an empty validation set.")
    best_weights = None
    best_key = None
    for weights in weight_grid(probabilities.shape[1], denominator):
        blended = blend_probabilities(probabilities, weights)
        logloss, brier = _selection_loss(y, blended, kind)
        nonzero_models = int((weights > 0).sum())
        key = (logloss, brier, nonzero_models, tuple(-weights))
        if best_key is None or key < best_key:
            best_key = key
            best_weights = weights
    if best_weights is None:
        raise RuntimeError("No candidate weights were generated.")
    return best_weights


def _fold_model_matrix(frame: pd.DataFrame, fold: str,
                       market: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    rows = frame.loc[
        (frame["fold"] == fold)
        & (frame["market"] == market)
        & frame["model"].isin(MODEL_NAMES)
    ].copy()
    if rows.empty:
        raise ValueError(f"No family predictions for {fold}/{market}.")
    indexed = {}
    for model in MODEL_NAMES:
        model_rows = rows.loc[rows["model"] == model].copy()
        if model_rows["_row_id"].duplicated().any():
            raise ValueError(f"Duplicate prediction rows for {fold}/{market}/{model}.")
        indexed[model] = model_rows.set_index("_row_id").sort_index()
    expected_ids = indexed[MODEL_NAMES[0]].index
    for model in MODEL_NAMES[1:]:
        if not expected_ids.equals(indexed[model].index):
            raise ValueError(f"Family models do not share fixtures for {fold}/{market}.")
        if not np.array_equal(
            indexed[MODEL_NAMES[0]]["y_true"].to_numpy(),
            indexed[model]["y_true"].to_numpy(),
        ):
            raise ValueError(f"Family models disagree on labels for {fold}/{market}.")

    first = indexed[MODEL_NAMES[0]]
    class_count = MARKETS[market][2]
    matrix = np.stack([
        indexed[model][[f"p{i}" for i in range(class_count)]].to_numpy(float)
        for model in MODEL_NAMES
    ], axis=1)
    y = first["y_true"].to_numpy(dtype=int)
    if np.isnan(matrix).any():
        raise ValueError(f"Missing model probabilities for {fold}/{market}.")
    metadata = first.reset_index()[
        ["_row_id", "Date", "Div", "HomeTeam", "AwayTeam"]
    ].copy()
    metadata["Date"] = pd.to_datetime(metadata["Date"], errors="coerce")
    return metadata, y, _normalise_probabilities(matrix)


def _prediction_frame(metadata: pd.DataFrame, fold: str, market: str,
                      y: np.ndarray, probabilities: np.ndarray,
                      model_name: str) -> pd.DataFrame:
    output = metadata.reset_index(drop=True).copy()
    output["fold"] = fold
    output["market"] = market
    output["model"] = model_name
    output["y_true"] = y
    for class_id in range(probabilities.shape[1]):
        output[f"p{class_id}"] = probabilities[:, class_id]
    return output


def _walk_forward_blends(family_predictions: pd.DataFrame
                          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    blend_rows = []
    weight_rows = []
    fold_names = [fold["name"] for fold in FOLDS]

    for market, (_, kind, _) in MARKETS.items():
        history_y = []
        history_probabilities = []
        history_folds = []
        for fold_name in fold_names:
            metadata, y, probabilities = _fold_model_matrix(
                family_predictions, fold_name, market
            )
            if history_y:
                fit_y = np.concatenate(history_y)
                fit_probabilities = np.concatenate(history_probabilities, axis=0)
                weights = choose_blend_weights(fit_y, fit_probabilities, kind)
                weight_source = "prior_oof_folds"
            else:
                # Fixed before any test labels exist; not selected on this fold.
                weights = np.full(len(MODEL_NAMES), 1.0 / len(MODEL_NAMES))
                weight_source = "predeclared_equal_blend_no_prior_fold"

            blended = blend_probabilities(probabilities, weights)
            blend_rows.append(_prediction_frame(
                metadata, fold_name, market, y, blended, BLEND_NAME
            ))
            weight_rows.append({
                "fold": fold_name,
                "market": market,
                "weight_source": weight_source,
                "training_folds": "|".join(history_folds),
                "training_n": int(sum(len(part) for part in history_y)),
                "grid_step": 1.0 / GRID_DENOMINATOR,
                **{
                    f"weight_{model}": float(weight)
                    for model, weight in zip(MODEL_NAMES, weights)
                },
            })
            history_y.append(y)
            history_probabilities.append(probabilities)
            history_folds.append(fold_name)

    return (
        pd.concat(blend_rows, ignore_index=True),
        pd.DataFrame(weight_rows),
    )


def _metric_row(group: pd.DataFrame) -> dict:
    market = str(group["market"].iloc[0])
    class_count = MARKETS[market][2]
    probabilities = group[[f"p{i}" for i in range(class_count)]].to_numpy(float)
    metrics = calculate_metrics(
        group["y_true"].to_numpy(dtype=int),
        probabilities,
        MARKETS[market][1],
    )
    return {
        "fold": str(group["fold"].iloc[0]),
        "market": market,
        "model": str(group["model"].iloc[0]),
        "source": "EXP-06 blend" if group["model"].iloc[0] == BLEND_NAME else "EXP-05",
        **metrics,
    }


def _fold_scorecard(scored_predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, group in scored_predictions.groupby(
        ["fold", "market", "model"], sort=True
    ):
        clean = group.loc[group["y_true"].notna()].copy()
        if not clean.empty:
            rows.append(_metric_row(clean))
    return pd.DataFrame(rows)


def _aggregate_scorecard(scored_predictions: pd.DataFrame,
                         comparison_folds: set[str]) -> pd.DataFrame:
    selected = scored_predictions.loc[
        scored_predictions["fold"].isin(comparison_folds)
    ]
    rows = []
    for _, group in selected.groupby(["market", "model"], sort=True):
        clean = group.loc[group["y_true"].notna()].copy()
        if not clean.empty:
            row = _metric_row(clean)
            row["fold"] = "WALK_FORWARD_AGGREGATE"
            row["folds"] = "|".join(sorted(clean["fold"].unique()))
            rows.append(row)
    return pd.DataFrame(rows)


def _paired_week_bootstrap(blend: pd.DataFrame, reference: pd.DataFrame,
                           market: str, reps: int = BOOTSTRAP_REPS,
                           comparisons: int = BOOTSTRAP_COMPARISONS) -> dict:
    class_count = MARKETS[market][2]
    left = blend.set_index("_row_id").sort_index()
    right = reference.set_index("_row_id").sort_index()
    common = left.index.intersection(right.index)
    if len(common) == 0:
        return {
            "n": 0, "delta_logloss": None, "ci_low": None, "ci_high": None,
            "familywise_alpha": 0.05,
        }
    left, right = left.loc[common], right.loc[common]
    if not np.array_equal(left["y_true"].to_numpy(), right["y_true"].to_numpy()):
        raise ValueError(f"Paired bootstrap label mismatch for {market}.")
    y = left["y_true"].to_numpy(dtype=int)
    left_p = left[[f"p{i}" for i in range(class_count)]].to_numpy(float)
    right_p = right[[f"p{i}" for i in range(class_count)]].to_numpy(float)
    delta = (
        -np.log(np.clip(left_p[np.arange(len(y)), y], EPSILON, 1.0))
        + np.log(np.clip(right_p[np.arange(len(y)), y], EPSILON, 1.0))
    )
    weeks = (
        left["fold"].astype(str) + "|"
        + pd.to_datetime(left["Date"]).dt.to_period("W-SUN").astype(str)
    ).to_numpy()
    weekly = pd.DataFrame({"week": weeks, "delta": delta}).groupby(
        "week", sort=True
    )["delta"].agg(["sum", "count"])
    sums = weekly["sum"].to_numpy(float)
    counts = weekly["count"].to_numpy(float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    selections = rng.integers(0, len(sums), size=(reps, len(sums)))
    boot = sums[selections].sum(axis=1) / counts[selections].sum(axis=1)
    tail = 0.05 / (2 * max(comparisons, 1))
    return {
        "n": int(len(y)),
        "weeks": int(len(sums)),
        "delta_logloss_blend_minus_reference": float(delta.mean()),
        "ci_low_familywise": float(np.quantile(boot, tail)),
        "ci_high_familywise": float(np.quantile(boot, 1.0 - tail)),
        "familywise_alpha": 0.05,
        "familywise_comparisons": int(comparisons),
        "bootstrap_repetitions": int(reps),
        "method": "paired weekly block bootstrap; Bonferroni-adjusted two-sided CI",
    }


def _candidate_selection(scored_predictions: pd.DataFrame,
                         aggregate: pd.DataFrame,
                         weight_table: pd.DataFrame,
                         history_aggregate_path: Path,
                         evaluation_folds: set[str]
                         ) -> tuple[pd.DataFrame, dict]:
    history_aggregate = pd.read_csv(history_aggregate_path)
    selection_rows = []
    bootstrap_report = {}

    for market in MARKETS:
        historic = history_aggregate.loc[
            (history_aggregate["market"] == market)
            & history_aggregate["model"].isin(MODEL_NAMES)
        ].sort_values(["logloss", "brier", "model"])
        if historic.empty:
            raise ValueError(f"No historical family winner for {market}.")
        baseline_name = str(historic.iloc[0]["model"])
        market_agg = aggregate.loc[aggregate["market"] == market].set_index("model")
        if BLEND_NAME not in market_agg.index or baseline_name not in market_agg.index:
            raise ValueError(f"Missing aggregate comparison for {market}.")
        blend_metrics = market_agg.loc[BLEND_NAME]
        baseline_metrics = market_agg.loc[baseline_name]

        blend_predictions = scored_predictions.loc[
            (scored_predictions["fold"].isin(evaluation_folds))
            & (scored_predictions["market"] == market)
            & (scored_predictions["model"] == BLEND_NAME)
        ]
        baseline_predictions = scored_predictions.loc[
            (scored_predictions["fold"].isin(evaluation_folds))
            & (scored_predictions["market"] == market)
            & (scored_predictions["model"] == baseline_name)
        ]
        bootstrap = _paired_week_bootstrap(
            blend_predictions, baseline_predictions, market
        )
        bootstrap_report[market] = {baseline_name: bootstrap}

        delta_logloss = float(
            blend_metrics["logloss"] - baseline_metrics["logloss"]
        )
        delta_brier = float(blend_metrics["brier"] - baseline_metrics["brier"])
        delta_ece = float(
            blend_metrics["ece_10bin"] - baseline_metrics["ece_10bin"]
        )
        ci_supports_blend = (
            bootstrap["ci_high_familywise"] is not None
            and bootstrap["ci_high_familywise"] < 0.0
        )
        blend_selected = (
            delta_logloss < 0.0
            and ci_supports_blend
            and delta_brier <= 0.0
            and delta_ece <= 0.005
        )
        latest_weight = weight_table.loc[
            (weight_table["fold"] == LATEST_FOLD)
            & (weight_table["market"] == market)
        ]
        if latest_weight.empty:
            raise ValueError(f"Missing final-fold blend weights for {market}.")
        weights = {
            model: float(latest_weight.iloc[0][f"weight_{model}"])
            for model in MODEL_NAMES
        }
        if not blend_selected:
            weights = {model: float(model == baseline_name) for model in MODEL_NAMES}
        selection_rows.append({
            "market": market,
            "selected_strategy": BLEND_NAME if blend_selected else baseline_name,
            "historical_single_model": baseline_name,
            "blend_logloss": float(blend_metrics["logloss"]),
            "single_logloss": float(baseline_metrics["logloss"]),
            "delta_logloss_blend_minus_single": delta_logloss,
            "delta_brier_blend_minus_single": delta_brier,
            "delta_ece_blend_minus_single": delta_ece,
            "paired_ci_low_familywise": bootstrap["ci_low_familywise"],
            "paired_ci_high_familywise": bootstrap["ci_high_familywise"],
            "selected_for_offline_bundle": True,
            "decision": (
                "BLEND_GATE_PASSED_REFERENCE_ONLY"
                if blend_selected else
                "USE_HISTORICAL_SINGLE_BASELINE_REFERENCE_ONLY"
            ),
            **{f"final_weight_{name}": weights[name] for name in MODEL_NAMES},
        })
    return pd.DataFrame(selection_rows), bootstrap_report


def _comparison_rows(frame: pd.DataFrame, model_col: str,
                     source: str) -> list[dict]:
    rows = []
    for (market, model), group in frame.groupby([ "market", model_col ], sort=True):
        clean = group.loc[group["y_true"].notna()].copy()
        if clean.empty:
            continue
        result = _metric_row(clean)
        result["model"] = str(model)
        result["source"] = source
        result["uses_h2h"] = bool(
            str(model) in MODEL_NAMES
            or str(model) == BLEND_NAME
            or str(model).startswith("LAB_FAMILY_")
            or str(model).startswith("LAB_F4_")
            or str(model).startswith("LAB_F5_")
        )
        rows.append(result)
    return rows


def _latest_comparators(scored_predictions: pd.DataFrame,
                        feature_predictions_path: Path | None,
                        modeb_metrics_path: Path | None) -> pd.DataFrame:
    rows = []
    latest = scored_predictions.loc[
        (scored_predictions["fold"] == LATEST_FOLD)
        & (
            scored_predictions["model"].isin(
                ["BASE_RATE", "CLOSING_ODDS_REFERENCE", BLEND_NAME, *MODEL_NAMES]
            )
        )
    ].copy()
    if not latest.empty:
        rows.extend(_comparison_rows(latest, "model", "EXP-05 / EXP-06"))

    if feature_predictions_path and feature_predictions_path.is_file():
        features = pd.read_csv(feature_predictions_path, low_memory=False)
        if {"fold", "market", "feature_group", "y_true", "p0", "p1"} <= set(features):
            features = features.loc[features["fold"] == LATEST_FOLD].copy()
            features["candidate"] = (
                "LAB_" + features["feature_group"].astype(str) + "_"
                + features["model"].astype(str)
            )
            feature_rows = _comparison_rows(
                features, "candidate", "EXP-01 latest fold"
            )
            for row in feature_rows:
                row["uses_h2h"] = row["model"].split("_")[1] in {"F4", "F5"}
            rows.extend(feature_rows)

    if modeb_metrics_path and modeb_metrics_path.is_file():
        modeb = pd.read_csv(modeb_metrics_path, low_memory=False)
        modeb = modeb.loc[
            (modeb["scenario"] == "STANDARD")
            & (modeb["candidate"] == "MAIN_MODE_B")
        ]
        for _, source_row in modeb.iterrows():
            row = {
                "fold": LATEST_FOLD,
                "market": source_row["market"],
                "model": "MAIN_MODE_B",
                "source": "EXP-08; synthetic STANDARD odds",
                "uses_h2h": True,
            }
            for metric in (
                "logloss", "brier", "accuracy", "ece_10bin", "auc", "n"
            ):
                row[metric] = source_row.get(metric, np.nan)
            rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty:
        result["accuracy_pct"] = result["accuracy"] * 100.0
    return result


def _report(selection: pd.DataFrame, fold_scorecard: pd.DataFrame,
            latest_comparators: pd.DataFrame, coherence: pd.DataFrame,
            manifest: dict) -> str:
    lines = [
        "# EXP-06 — Gabungan Model per Pasar",
        "",
        "**Status: `REFERENCE_ONLY`; file kandidat hanya untuk prediksi offline/paper.**",
        "",
        "## Metode",
        "",
        f"- Prediksi keluarga model memakai {len(manifest['folds'])} fold kronologis "
        "out-of-fold; bobot untuk tiap fold hanya dipilih dari fold sebelumnya.",
        f"- Grid bobot simplex memakai langkah {1 / GRID_DENOMINATOR:.1f}; fungsi "
        "pilih meminimalkan LogLoss, lalu Brier, kemudian lebih sedikit model.",
        "- Fold pertama menggunakan bobot sama yang ditetapkan sebelum melihat hasil; "
        "fold ini tidak masuk gerbang pemilihan kandidat.",
        "- Blend hanya dipilih jika LogLoss membaik dengan CI paired-week bootstrap "
        "terkoreksi 24 perbandingan seluruhnya di bawah nol, Brier tidak memburuk, "
        "dan ECE tidak memburuk lebih dari 0,005. Jika gagal, paket memakai model "
        "tunggal pemenang EXP-05 historis untuk pasar itu.",
        "- Semua periode historis sudah ditinjau sebelumnya. Angka ini tidak menjadi "
        "holdout independen atau bukti profit.",
        "- Keluarga EXP-05 dan blend memakai fitur statistik pra-pertandingan "
        "termasuk H2H; F0-F3 tidak memakai H2H, sedangkan F4-F5 memakainya.",
        "",
        "## Strategi screening per pasar",
        "",
        "| Pasar | Pilihan paket offline | Model tunggal historis | Δ LogLoss blend−single | Δ Brier | Δ ECE | CI LogLoss simultan |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in selection.itertuples(index=False):
        strategy = (
            "Blend"
            if row.selected_strategy == BLEND_NAME
            else f"Tunggal: {row.selected_strategy}"
        )
        lines.append(
            f"| {row.market} | {strategy} | {row.historical_single_model} | "
            f"{row.delta_logloss_blend_minus_single:+.5f} | "
            f"{row.delta_brier_blend_minus_single:+.5f} | "
            f"{row.delta_ece_blend_minus_single:+.5f} | "
            f"[{row.paired_ci_low_familywise:.5f}, "
            f"{row.paired_ci_high_familywise:.5f}] |"
        )
    lines.extend([
        "",
        "## Metrik evaluasi",
        "",
        "`scorecard.csv` berisi LogLoss, Brier, akurasi, ECE, AUC bila berlaku, "
        "jumlah pertandingan, model, pasar, dan fold. `aggregate_metrics.csv` "
        "merangkum fold evaluasi yang digunakan untuk keputusan (semua fold kecuali "
        "fold pertama). `latest_comparators.csv` menambahkan F0-F5 dan Mode B "
        "sebagai pembanding pada fold terbaru; Mode B memakai quote sintetis "
        "`STANDARD`, sehingga bukan perbandingan harga yang setara.",
        "",
        "## Koherensi dan batasan",
        "",
    ])
    if not coherence.empty:
        sums = coherence.loc[coherence["check"] == "probability_sum"]
        team = coherence.loc[
            coherence["check"] == "over15_not_above_over05"
        ]
        lines.append(
            f"- Jumlah probabilitas: {int(sums['violations'].sum()):,} pelanggaran "
            f"dari {int(sums['n'].sum()):,} pemeriksaan."
        )
        lines.append(
            f"- Over 1.5 ≤ Over 0.5: {int(team['violations'].sum()):,} pelanggaran "
            f"dari {int(team['n'].sum()):,} pemeriksaan pada data OOF."
        )
        source_counts = team.groupby("model", sort=True)["violations"].sum()
        source_counts = source_counts[source_counts > 0].sort_values(
            ascending=False
        )
        if source_counts.empty:
            source_summary = "tidak ada model dengan pelanggaran"
        else:
            source_summary = ", ".join(
                f"{model}: {int(count):,}"
                for model, count in source_counts.items()
            )
        lines.append(
            f"- Rincian pelanggaran O/U tim menurut model: {source_summary}."
        )
    lines.extend([
        "- Tidak ada hasil baru yang dapat membuktikan kesiapan taruhan uang: odds "
        "bookmaker bertimestamp dan holdout prospektif belum tersedia.",
        "- Bobot terpilih dan tabel perbandingan disimpan di folder hasil run ini; "
        "tidak ada paket model atau artefak proyek utama yang ditulis. Promosi "
        "memerlukan peninjauan dan persetujuan terpisah.",
        "",
    ])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> Path:
    predictions_path = args.predictions.resolve()
    output = validate_output_path(args.output_dir)
    history_aggregate_path = args.history_aggregate.resolve()
    if not predictions_path.is_file():
        raise FileNotFoundError(f"OOF predictions not found: {predictions_path}")
    if not history_aggregate_path.is_file():
        raise FileNotFoundError(
            f"EXP-05 aggregate metrics not found: {history_aggregate_path}"
        )
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {output}; choose a fresh directory "
            "or pass --overwrite."
        )
    output.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(predictions_path, low_memory=False)
    required = {
        "_row_id", "Date", "Div", "HomeTeam", "AwayTeam", "fold",
        "market", "model", "y_true", "p0", "p1",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"OOF predictions are missing columns: {missing}")
    family = source.loc[source["model"].isin(MODEL_NAMES)].copy()
    available_folds = set(family["fold"].astype(str))
    expected_folds = {fold["name"] for fold in FOLDS}
    if not expected_folds.issubset(available_folds):
        raise ValueError(
            f"Full chronological family predictions are required; missing "
            f"{sorted(expected_folds - available_folds)}."
        )
    if set(family["market"].unique()) != set(MARKETS):
        raise ValueError("OOF predictions must cover all six markets.")
    if set(family["model"].unique()) != set(MODEL_NAMES):
        raise ValueError("OOF predictions must cover all four model families.")
    family["Date"] = pd.to_datetime(family["Date"], errors="coerce")
    if family["Date"].isna().any():
        raise ValueError("OOF predictions contain invalid dates.")

    blends, weights = _walk_forward_blends(family)
    nonfamily = source.loc[~source["model"].isin(MODEL_NAMES)].copy()
    scored_predictions = pd.concat(
        [nonfamily, family, blends], ignore_index=True, sort=False
    )
    scorecard = _fold_scorecard(scored_predictions)
    first_fold = FOLDS[0]["name"]
    evaluation_folds = {fold["name"] for fold in FOLDS[1:]}
    aggregate = _aggregate_scorecard(scored_predictions, evaluation_folds)
    selection, bootstrap = _candidate_selection(
        scored_predictions,
        aggregate,
        weights,
        history_aggregate_path,
        evaluation_folds,
    )

    coherence_input = scored_predictions.loc[
        scored_predictions["model"].isin(
            [*MODEL_NAMES, "BASE_RATE", "CLOSING_ODDS_REFERENCE", BLEND_NAME]
        )
    ].copy()
    coherence_input["scenario"] = coherence_input["fold"]
    coherence_input["candidate"] = coherence_input["model"]
    coherence = probability_coherence(coherence_input)

    latest_comparators = _latest_comparators(
        scored_predictions,
        args.feature_predictions.resolve() if args.feature_predictions else None,
        args.modeb_metrics.resolve() if args.modeb_metrics else None,
    )
    league_rows = []
    comparison = scored_predictions.loc[
        scored_predictions["fold"].isin(evaluation_folds)
        & scored_predictions["model"].isin(
            ["BASE_RATE", "CLOSING_ODDS_REFERENCE", *MODEL_NAMES, BLEND_NAME]
        )
    ]
    for (fold, market, model, league), group in comparison.groupby(
        ["fold", "market", "model", "Div"], sort=True
    ):
        metrics = calculate_metrics(
            group["y_true"].to_numpy(dtype=int),
            group[[f"p{i}" for i in range(MARKETS[market][2])]].to_numpy(float),
            MARKETS[market][1],
        )
        league_rows.append({
            "fold": fold,
            "market": market,
            "model": model,
            "league": league,
            **metrics,
        })

    blend_predictions = blends.copy()
    fit_folds_by_market = weights.set_index(["fold", "market"])[
        "training_folds"
    ].to_dict()
    blend_predictions["weight_fit_folds"] = [
        fit_folds_by_market[(fold, market)]
        for fold, market in zip(
            blend_predictions["fold"], blend_predictions["market"]
        )
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "status": "REFERENCE_ONLY",
        "input_predictions": str(predictions_path.relative_to(ROOT)),
        "input_predictions_sha256": file_hash(predictions_path),
        "input_rows": int(len(source)),
        "families": list(MODEL_NAMES),
        "markets": list(MARKETS),
        "folds": [fold["name"] for fold in FOLDS],
        "first_fold_policy": (
            f"{first_fold} uses a predeclared equal-weight blend and is excluded "
            "from candidate gate."
        ),
        "weight_selection": {
            "grid_step": 1.0 / GRID_DENOMINATOR,
            "objective": "minimize prior-fold OOF LogLoss; tie-break Brier then fewer nonzero models",
            "leakage_rule": "Each fold's blend weights are fitted only on earlier OOF folds.",
        },
        "candidate_gate": {
            "paired_bootstrap": BOOTSTRAP_REPS,
            "familywise_comparisons": BOOTSTRAP_COMPARISONS,
            "must_improve_logloss_ci_upper_below_zero": True,
            "brier_must_not_worsen": True,
            "maximum_ece_increase": 0.005,
            "fallback": "EXP-05 historical single-model winner",
        },
        "evaluation_folds": [fold["name"] for fold in FOLDS[1:]],
        "latest_fold": LATEST_FOLD,
        "historical_holdout_reviewed": True,
        "package_versions": package_versions(),
        "limitations": [
            "All historical test periods were already reviewed; results are reference-only.",
            "Main Mode B comparison is available only on the latest partial fold and uses synthetic STANDARD odds.",
            "No timestamped bookmaker prices or prospective outcomes are available.",
        ],
    }
    manifest["history_aggregate_sha256"] = file_hash(history_aggregate_path)
    manifest["selected_offline_strategy"] = selection.set_index("market")[
        "selected_strategy"
    ].to_dict()

    scorecard.to_csv(output / "scorecard.csv", index=False)
    aggregate.to_csv(output / "aggregate_metrics.csv", index=False)
    weights.to_csv(output / "blend_weights.csv", index=False)
    selection.to_csv(output / "candidate_selection.csv", index=False)
    latest_comparators.to_csv(output / "latest_comparators.csv", index=False)
    pd.DataFrame(league_rows).to_csv(output / "per_league_metrics.csv", index=False)
    coherence.to_csv(output / "probability_coherence.csv", index=False)
    blend_predictions.to_csv(output / "predictions.csv", index=False)
    (output / "paired_bootstrap.json").write_text(
        json.dumps(bootstrap, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "REPORT.md").write_text(
        _report(selection, scorecard, latest_comparators, coherence, manifest),
        encoding="utf-8",
    )
    print(f"Saved isolated blend search to {output}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--history-aggregate", type=Path,
                        default=DEFAULT_HISTORY_AGGREGATE)
    parser.add_argument("--feature-predictions", type=Path,
                        default=DEFAULT_FEATURE_PREDICTIONS)
    parser.add_argument("--modeb-metrics", type=Path, default=DEFAULT_MODEB_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
