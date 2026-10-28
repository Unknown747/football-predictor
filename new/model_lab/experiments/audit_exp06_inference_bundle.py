#!/usr/bin/env python3
"""Check final EXP-06 bundle probability coherence on the later reference fold."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import predict  # noqa: E402

BUNDLE = predict.EXP06_BUNDLE_DIR
TRAINING_CUTOFF = pd.Timestamp("2026-06-30")
EPSILON = 1e-12
TOLERANCE = 1e-8


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def batch_market_probabilities(models, market: str, X: np.ndarray,
                               class_count: int) -> np.ndarray:
    blended = np.zeros((len(X), class_count), dtype=float)
    total_weight = 0.0
    for estimator, weight in models[market]:
        probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
        classes = np.asarray(estimator.classes_)
        if probabilities.shape != (len(X), len(classes)):
            raise ValueError(f"Invalid probability shape for {market}: {probabilities.shape}")
        if not np.isfinite(probabilities).all() or (probabilities < 0).any():
            raise ValueError(f"Invalid model probabilities for {market}.")
        aligned = np.zeros_like(blended)
        seen = set()
        for position, label in enumerate(classes):
            class_id = int(label)
            if class_id < 0 or class_id >= class_count or class_id in seen:
                raise ValueError(f"Invalid class order in {market}.")
            aligned[:, class_id] = probabilities[:, position]
            seen.add(class_id)
        if seen != set(range(class_count)):
            raise ValueError(f"Incomplete classes in {market}.")
        sums = aligned.sum(axis=1, keepdims=True)
        if (sums <= 0).any():
            raise ValueError(f"Zero probability total in {market}.")
        blended += weight * (aligned / sums)
        total_weight += weight
    if not np.isclose(total_weight, 1.0):
        raise ValueError(f"Invalid weights for {market}.")
    row_sums = blended.sum(axis=1, keepdims=True)
    return blended / np.maximum(row_sums, EPSILON)


def coherence_summary(probabilities: dict[str, np.ndarray]) -> dict:
    summary = {}
    for market, values in probabilities.items():
        errors = np.abs(values.sum(axis=1) - 1.0)
        summary[market] = {
            "n": int(len(values)),
            "sum_violations": int((errors > TOLERANCE).sum()),
            "max_absolute_sum_error": float(errors.max(initial=0.0)),
        }

    for side in ("home", "away"):
        over05 = probabilities[f"{side}_ou05"][:, 1]
        over15 = probabilities[f"{side}_ou15"][:, 1]
        excess = over15 - over05
        positive = excess > TOLERANCE
        summary[f"{side}_over15_le_over05"] = {
            "n": int(len(excess)),
            "violations": int(positive.sum()),
            "violation_rate": float(positive.mean()) if len(positive) else 0.0,
            "max_excess": float(max(0.0, excess.max(initial=0.0))),
        }
    return summary


def run_audit() -> dict:
    models, features = predict.load_exp06_bundle()
    manifest_path = BUNDLE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = ROOT / manifest["training_source"]
    source_hash = file_hash(source)
    if source_hash != manifest.get("training_source_sha256"):
        raise ValueError("The source data hash differs from the fitted bundle.")

    frame = pd.read_csv(source, usecols=["Date", *features], low_memory=False)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.loc[
        frame["Date"].notna() & (frame["Date"] > TRAINING_CUTOFF)
    ].copy()
    if frame.empty:
        raise ValueError("No post-cutoff reference fixtures are available.")
    X = frame[features].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)

    market_probabilities = {}
    for market, class_count in predict.MARKET_CLASS_COUNTS.items():
        market_probabilities[market] = batch_market_probabilities(
            models, market, X, class_count
        )

    checks = coherence_summary(market_probabilities)
    any_violations = any(
        item.get("sum_violations", 0) > 0 or item.get("violations", 0) > 0
        for item in checks.values()
    )
    result = {
        "mode": predict.EXP06_MODE,
        "status": "REFERENCE_ONLY",
        "training_cutoff_inclusive": str(TRAINING_CUTOFF.date()),
        "reference_data": str(source.relative_to(ROOT)),
        "reference_data_sha256": source_hash,
        "evaluation_rows": int(len(frame)),
        "evaluation_date_min": str(frame["Date"].min().date()),
        "evaluation_date_max": str(frame["Date"].max().date()),
        "evaluation_features_sha256": manifest["features_sha256"],
        "historical_period_previously_reviewed": True,
        "checks": checks,
        "probability_coherence_passed": not any_violations,
        "technical_merge_ready": False,
        "blockers": [
            "Historical post-cutoff rows are reference-only, not prospective validation."
        ],
    }
    if any_violations:
        result["blockers"].append(
            "Final-bundle probabilities violate one or more coherence checks."
        )

    audit_path = BUNDLE / "inference_coherence.json"
    audit_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest["inference_coherence_audit"] = {
        "file": audit_path.name,
        "sha256": file_hash(audit_path),
        "probability_coherence_passed": result["probability_coherence_passed"],
        "technical_merge_ready": False,
        "evaluation_rows": result["evaluation_rows"],
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    report = run_audit()
    print(json.dumps(report, indent=2, ensure_ascii=False))
