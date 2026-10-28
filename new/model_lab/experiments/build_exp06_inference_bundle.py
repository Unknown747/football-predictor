#!/usr/bin/env python3
"""Fit and package the frozen EXP-06 offline inference bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_model_families import (  # noqa: E402
    MARKETS,
    MODEL_NAMES,
    file_hash,
    make_estimator,
    safe_feature_columns,
    time_weights,
)

MODE = "EXP06_BLEND_V1"
REFERENCE_STATUS = "REFERENCE_ONLY"
TRAINING_CUTOFF = pd.Timestamp("2026-06-30")
SOURCE_SELECTION = (
    LAB / "results/EXP-06-model-blending-20261028/blend-search"
    / "candidate_selection.csv"
)
SOURCE_BLEND_MANIFEST = (
    LAB / "results/EXP-06-model-blending-20261028/blend-search/manifest.json"
)
SOURCE_FAMILY_MANIFEST = (
    LAB / "results/EXP-06-model-blending-20261028/family-models-oof-rebuilt"
    / "manifest.json"
)
DEFAULT_OUTPUT = LAB / "candidates" / "EXP06_BLEND_V1_REFERENCE_ONLY"
EXPECTED_FEATURE_HASH = (
    "990c223264342ef6e38e2c6f08d9651e9c2eb5fb71edbaaf0ebbdce45f0d1a45"
)
EPSILON = 1e-12
SAFE_PREFIXES = (
    "home_form5_", "home_form10_",
    "away_form5_", "away_form10_",
    "home_venue_", "away_venue_",
    "home_rest_", "away_rest_",
    "home_season_", "away_season_",
    "h2h_", "diff_",
)
FORBIDDEN_FEATURES = {
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC",
    "HY", "AY", "HR", "AR",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def checked_selection() -> tuple[dict, dict]:
    blend_manifest = json.loads(SOURCE_BLEND_MANIFEST.read_text(encoding="utf-8"))
    family_manifest = json.loads(SOURCE_FAMILY_MANIFEST.read_text(encoding="utf-8"))
    if blend_manifest.get("status") != REFERENCE_STATUS:
        raise ValueError("EXP-06 source manifest is not marked REFERENCE_ONLY.")
    oof_predictions = (
        LAB / "results/EXP-06-model-blending-20261028/family-models-oof-rebuilt"
        / "predictions.csv"
    )
    if (
        oof_predictions.is_file()
        and blend_manifest.get("input_predictions_sha256") != file_hash(oof_predictions)
    ):
        raise ValueError("EXP-06 OOF input predictions do not match their manifest.")
    frame = pd.read_csv(SOURCE_SELECTION)
    if frame["market"].duplicated().any() or set(frame["market"]) != set(MARKETS):
        raise ValueError("Candidate selection must contain exactly one row per market.")

    selection = {}
    for row in frame.to_dict("records"):
        market = row["market"]
        if not bool(row["selected_for_offline_bundle"]):
            raise ValueError(f"{market} is not selected for the offline bundle.")
        weights = {
            family: float(row[f"final_weight_{family}"])
            for family in MODEL_NAMES
        }
        if (
            not all(np.isfinite(value) and value >= 0 for value in weights.values())
            or not np.isclose(sum(weights.values()), 1.0)
        ):
            raise ValueError(f"Invalid EXP-06 weights for {market}: {weights}")
        expected_strategy = blend_manifest["selected_offline_strategy"][market]
        if row["selected_strategy"] != expected_strategy:
            raise ValueError(f"Strategy mismatch for {market}: selection vs manifest.")
        if row["decision"] not in {
            "BLEND_GATE_PASSED_REFERENCE_ONLY",
            "USE_HISTORICAL_SINGLE_BASELINE_REFERENCE_ONLY",
        }:
            raise ValueError(f"Unexpected reference decision for {market}.")
        if row["selected_strategy"] != "OOF_BLEND_PREVIOUS_FOLDS":
            baseline = row["historical_single_model"]
            expected_weights = {
                family: float(family == baseline) for family in MODEL_NAMES
            }
            if weights != expected_weights:
                raise ValueError(f"Fallback weights do not select {baseline} for {market}.")
        selection[market] = {
            "strategy": row["selected_strategy"],
            "weights": weights,
            "decision": row["decision"],
        }
    return selection, family_manifest


def load_training_data(input_path: Path, family_manifest: dict):
    if file_hash(input_path) != family_manifest.get("input_sha256"):
        raise ValueError(
            "data/features_train.csv differs from the data used by EXP-05/06; "
            "refusing to fit a bundle against an unverified source."
        )
    frame = pd.read_csv(input_path, low_memory=False)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.loc[
        frame["Date"].notna() & (frame["Date"] <= TRAINING_CUTOFF)
    ].copy()
    frame["_source_row"] = frame.index.astype("int64")
    frame = frame.sort_values(["Date", "_source_row"]).reset_index(drop=True)

    features = safe_feature_columns(frame)
    if sha256_text("\n".join(features)) != EXPECTED_FEATURE_HASH:
        raise ValueError("The current safe feature order does not match EXP-06.")
    if features != family_manifest.get("features"):
        raise ValueError("Feature columns/order differ from the EXP-06 manifest.")
    if set(features) & FORBIDDEN_FEATURES:
        raise ValueError("Post-match columns entered the model feature list.")
    if any(column.startswith("odds_") for column in features):
        raise ValueError("Odds features are forbidden in EXP06_BLEND_V1.")

    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")
    frame[features] = frame[features].replace([np.inf, -np.inf], np.nan)
    for target, _, class_count in MARKETS.values():
        frame[target] = pd.to_numeric(frame[target], errors="coerce")
        valid = frame[target].notna()
        values = frame.loc[valid, target].to_numpy(dtype=float)
        if not np.equal(values, np.floor(values)).all():
            raise ValueError(f"Non-integer labels found in {target}.")
        if not set(values.astype(int)).issubset(set(range(class_count))):
            raise ValueError(f"Labels out of range in {target}.")
    return frame, features


def fit_final_estimator(name: str, X: np.ndarray, y: np.ndarray,
                        dates: pd.Series, class_count: int):
    """Mirror EXP-05 fitting: time weights, trailing validation, then full refit."""
    sample_weight = time_weights(dates)
    fit_details = {
        "selected_iterations": None,
        "inner_validation_days": 90,
        "fit_rows": int(len(y)),
    }
    early_stop_start = dates.max() - pd.Timedelta(days=90)
    inner_train = dates < early_stop_start
    inner_valid = ~inner_train
    expected_classes = set(range(class_count))

    if (
        name in {"lgbm", "xgboost"}
        and inner_train.sum() >= 1000
        and inner_valid.sum() >= 100
        and set(np.unique(y[inner_train])) == expected_classes
    ):
        provisional = make_estimator(name, class_count, early_stopping=True)
        fit_kwargs = {
            "sample_weight": sample_weight[inner_train],
            "eval_set": [(X[inner_valid], y[inner_valid])],
        }
        if name == "lgbm":
            import lightgbm as lgb

            provisional.fit(
                X[inner_train], y[inner_train],
                callbacks=[lgb.early_stopping(100, verbose=False)],
                **fit_kwargs,
            )
            selected = int(provisional.best_iteration_ or 2500)
        else:
            provisional.fit(
                X[inner_train], y[inner_train], verbose=False, **fit_kwargs
            )
            selected = int(getattr(provisional, "best_iteration", 0) or 1799) + 1
        selected = max(50, selected)
        fit_details["selected_iterations"] = selected
        estimator = make_estimator(name, class_count, n_estimators=selected)
    else:
        estimator = make_estimator(name, class_count)
        if name in {"lgbm", "xgboost"}:
            fit_details["selected_iterations"] = 2500 if name == "lgbm" else 1800
        fit_details["early_stopping_skipped"] = True

    if name == "logreg":
        estimator.fit(X, y, classifier__sample_weight=sample_weight)
    else:
        estimator.fit(X, y, sample_weight=sample_weight)

    classes = np.asarray(estimator.classes_, dtype=int)
    if set(classes.tolist()) != expected_classes:
        raise ValueError(
            f"{name} learned unexpected classes {classes.tolist()}, "
            f"expected {sorted(expected_classes)}."
        )
    return estimator, fit_details


def package_versions() -> dict:
    packages = ("numpy", "pandas", "scikit-learn", "lightgbm", "xgboost", "joblib")
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def build_bundle(input_path: Path, output_dir: Path) -> Path:
    candidates_root = (LAB / "candidates").resolve()
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(candidates_root)
    except ValueError as error:
        raise ValueError(f"Bundle output must stay under {candidates_root}.") from error
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing bundle: {output_dir}. "
            "Choose a new output directory and update the predictor path after review."
        )

    selection, family_manifest = checked_selection()
    frame, features = load_training_data(input_path, family_manifest)
    training_rows = {}
    models_manifest = {}
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    X = frame[features].to_numpy(dtype=float)

    with tempfile.TemporaryDirectory(
        prefix=".exp06-bundle-build-", dir=output_dir.parent
    ) as temp_name:
        temp_dir = Path(temp_name)
        for market, (target, _, class_count) in MARKETS.items():
            market_rows = frame[target].notna()
            market_frame = frame.loc[market_rows]
            y = market_frame[target].to_numpy(dtype=int)
            market_X = X[market_rows.to_numpy()]
            dates = market_frame["Date"].reset_index(drop=True)
            if set(np.unique(y)) != set(range(class_count)):
                raise ValueError(
                    f"{market} training labels do not include all classes: "
                    f"{sorted(set(np.unique(y).tolist()))}"
                )
            training_rows[market] = {
                "n": int(len(y)),
                "label_counts": {
                    str(label): int((y == label).sum())
                    for label in range(class_count)
                },
                "date_min": str(dates.min().date()),
                "date_max": str(dates.max().date()),
            }
            market_model_info = {}
            for family, weight in selection[market]["weights"].items():
                if weight <= 0:
                    continue
                print(
                    f"Fit {market}/{family} ({len(y):,} rows, weight={weight:.1f})",
                    flush=True,
                )
                started = time.monotonic()
                estimator, fit_details = fit_final_estimator(
                    family, market_X, y, dates, class_count
                )
                filename = f"{market}_{family}.joblib"
                artifact_path = temp_dir / filename
                joblib.dump(estimator, artifact_path, compress=3)
                fit_details["fit_seconds"] = round(time.monotonic() - started, 2)
                fit_details["classes"] = [
                    int(value) for value in estimator.classes_
                ]
                market_model_info[family] = {
                    "weight": weight,
                    "file": filename,
                    "sha256": file_hash(artifact_path),
                    "fit": fit_details,
                }
            models_manifest[market] = {
                "strategy": selection[market]["strategy"],
                "decision": selection[market]["decision"],
                "weights": selection[market]["weights"],
                "models": market_model_info,
                "training": training_rows[market],
            }

        manifest = {
            "mode": MODE,
            "prediction_mode": f"{MODE}_{REFERENCE_STATUS}",
            "status": REFERENCE_STATUS,
            "historical_use_only": True,
            "betting_ready": False,
            "training_cutoff_inclusive": str(TRAINING_CUTOFF.date()),
            "training_source": str(input_path.resolve().relative_to(ROOT)),
            "training_source_sha256": file_hash(input_path),
            "training_rows_before_cutoff": int(len(frame)),
            "feature_count": len(features),
            "features": features,
            "features_sha256": sha256_text("\n".join(features)),
            "candidate_selection": str(SOURCE_SELECTION.relative_to(ROOT)),
            "candidate_selection_sha256": file_hash(SOURCE_SELECTION),
            "blend_manifest_sha256": file_hash(SOURCE_BLEND_MANIFEST),
            "family_oof_manifest_sha256": file_hash(SOURCE_FAMILY_MANIFEST),
            "weights_policy": (
                "Use EXP-06 final-fold candidate_selection weights; single-model "
                "fallback markets use the recorded EXP-05 winner."
            ),
            "markets": models_manifest,
            "package_versions": package_versions(),
            "limitations": [
                "All historical evaluation folds were already reviewed; metrics are REFERENCE_ONLY.",
                "No prospective validation with timestamped bookmaker odds is included.",
                "This bundle is an opt-in technical integration, not betting-ready.",
                "Odds are excluded from every candidate feature vector.",
            ],
        }
        (temp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.rename(temp_dir, output_dir)

    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Fit the EXP-06 reference-only inference bundle."
    )
    parser.add_argument(
        "--input", type=Path, default=ROOT / "data/features_train.csv"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_bundle(args.input, args.output_dir)
    print(f"Bundle saved: {result}")
    print("Status: REFERENCE_ONLY (not betting-ready)")


if __name__ == "__main__":
    main()
