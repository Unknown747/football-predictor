#!/usr/bin/env python3
"""Historical, pre-match model-family comparison isolated to new/model_lab."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "features_train.csv"
DEFAULT_OUTPUT = LAB / "results" / "EXP-05-historical-model-family-benchmark"
SEED = 20261028
EPS = 1e-12
HALF_LIFE_DAYS = 365
BOOTSTRAP_REPS = 20000
FAMILYWISE_COMPARISONS = 32
FAMILYWISE_ALPHA = 0.05

SAFE_PREFIXES = (
    "home_form5_", "home_form10_",
    "away_form5_", "away_form10_",
    "home_venue_", "away_venue_",
    "home_rest_", "away_rest_",
    "home_season_", "away_season_",
    "h2h_", "diff_",
)
SAFE_EXACT = {"sum_expected_goals"}
FORBIDDEN_FEATURES = {
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC",
    "HY", "AY", "HR", "AR",
}

MARKETS = {
    "1x2": ("target_1x2", "multiclass", 3),
    "ou25": ("target_ou25", "binary", 2),
    "home_ou05": ("target_home_ou05", "binary", 2),
    "home_ou15": ("target_home_ou15", "binary", 2),
    "away_ou05": ("target_away_ou05", "binary", 2),
    "away_ou15": ("target_away_ou15", "binary", 2),
}

# Fixed chronological folds. Every historical fold is reference-only: the
# project has already inspected its historical test period.
FOLDS = [
    {"name": "2022-23", "train_end": "2022-06-30",
     "test_start": "2022-07-01", "test_end": "2023-06-30"},
    {"name": "2023-24", "train_end": "2023-06-30",
     "test_start": "2023-07-01", "test_end": "2024-06-30"},
    {"name": "2024-25", "train_end": "2024-06-30",
     "test_start": "2024-07-01", "test_end": "2025-06-30"},
    {"name": "2025-26", "train_end": "2025-06-30",
     "test_start": "2025-07-01", "test_end": "2026-06-30"},
    {"name": "2026-27-partial", "train_end": "2026-06-30",
     "test_start": "2026-07-01", "test_end": "2027-06-30"},
]

MODEL_NAMES = ("lgbm", "xgboost", "histgb", "logreg")


def safe_feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return only the project's pre-match numeric feature whitelist."""
    columns = []
    for column in frame.columns:
        if column in SAFE_EXACT or column.startswith(SAFE_PREFIXES):
            if pd.api.types.is_numeric_dtype(frame[column]):
                columns.append(column)
    leaked = sorted(set(columns) & FORBIDDEN_FEATURES)
    if leaked:
        raise ValueError(f"Post-match fields entered the feature list: {leaked}")
    if not columns:
        raise ValueError("No safe numeric features found in the input.")
    return columns


def load_frame(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = pd.read_csv(path, low_memory=False)
    required = {"Date", "Div", "HomeTeam", "AwayTeam", *[
        spec[0] for spec in MARKETS.values()
    ]}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")

    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.loc[frame["Date"].notna()].copy()
    if frame.empty:
        raise ValueError("No rows with valid dates.")
    frame["_row_id"] = frame.index.astype("int64")

    features = safe_feature_columns(frame)
    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")
    frame[features] = frame[features].replace([np.inf, -np.inf], np.nan)

    for target, _, _ in MARKETS.values():
        frame[target] = pd.to_numeric(frame[target], errors="coerce")
    return frame.sort_values(["Date", "_row_id"]).reset_index(drop=True), features


def time_weights(dates: pd.Series) -> np.ndarray:
    age_days = (dates.max() - dates).dt.days.to_numpy(dtype=float)
    weights = np.power(0.5, age_days / HALF_LIFE_DAYS)
    return weights / weights.mean()


def make_estimator(name: str, class_count: int, n_estimators: int | None = None,
                   early_stopping: bool = False):
    if name == "lgbm":
        from lightgbm import LGBMClassifier

        kwargs = dict(
            objective="multiclass" if class_count == 3 else "binary",
            n_estimators=n_estimators or 2500,
            learning_rate=0.03,
            num_leaves=63,
            max_depth=-1,
            min_child_samples=50,
            subsample=0.85,
            subsample_freq=5,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            n_jobs=4,
            verbosity=-1,
        )
        if class_count == 3:
            kwargs["num_class"] = 3
        return LGBMClassifier(**kwargs)

    if name == "xgboost":
        from xgboost import XGBClassifier

        kwargs = dict(
            objective="multi:softprob" if class_count == 3 else "binary:logistic",
            n_estimators=n_estimators or 1800,
            max_depth=6,
            min_child_weight=10,
            learning_rate=0.03,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.0,
            tree_method="hist",
            random_state=42,
            n_jobs=4,
            verbosity=0,
            eval_metric="mlogloss" if class_count == 3 else "logloss",
        )
        if class_count == 3:
            kwargs["num_class"] = 3
        if early_stopping:
            kwargs["early_stopping_rounds"] = 100
        return XGBClassifier(**kwargs)

    if name == "histgb":
        return HistGradientBoostingClassifier(
            learning_rate=0.06,
            max_iter=180,
            max_leaf_nodes=31,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=42,
        )

    if name == "logreg":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("classifier", LogisticRegression(
                C=1.0,
                max_iter=1200,
                solver="lbfgs",
                random_state=42,
            )),
        ])
    raise ValueError(f"Unsupported model: {name}")


def fit_predict(name: str, X: np.ndarray, y: np.ndarray, dates: pd.Series,
                X_test: np.ndarray, class_count: int) -> tuple[np.ndarray, dict]:
    """Select boosting rounds on a trailing 90-day inner validation, then refit."""
    sample_weight = time_weights(dates)
    fit_details = {"selected_iterations": None, "inner_validation_days": 90}
    early_stop_start = dates.max() - pd.Timedelta(days=90)
    inner_train = dates < early_stop_start
    inner_valid = ~inner_train

    if name in {"lgbm", "xgboost"} and inner_train.sum() >= 1000 and inner_valid.sum() >= 100:
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
            provisional.fit(X[inner_train], y[inner_train], verbose=False, **fit_kwargs)
            selected = int(getattr(provisional, "best_iteration", 0) or 1799) + 1
        selected = max(50, selected)
        fit_details["selected_iterations"] = selected
        estimator = make_estimator(name, class_count, n_estimators=selected)
    else:
        estimator = make_estimator(name, class_count)
        if name in {"lgbm", "xgboost"}:
            fit_details["selected_iterations"] = (
                2500 if name == "lgbm" else 1800
            )

    if name == "logreg":
        estimator.fit(X, y, classifier__sample_weight=sample_weight)
    else:
        estimator.fit(X, y, sample_weight=sample_weight)

    probabilities = estimator.predict_proba(X_test)
    classes = estimator.named_steps["classifier"].classes_ if name == "logreg" \
        else estimator.classes_
    aligned = np.full((len(X_test), class_count), EPS, dtype=float)
    for position, label in enumerate(classes):
        aligned[:, int(label)] = probabilities[:, position]
    aligned = np.clip(aligned, EPS, 1.0)
    aligned /= aligned.sum(axis=1, keepdims=True)
    return aligned, fit_details


def expected_calibration_error(y: np.ndarray, probabilities: np.ndarray,
                               kind: str, bins: int = 10) -> float:
    if kind == "binary":
        confidence = probabilities[:, 1]
        observed = y.astype(int)
    else:
        predicted = probabilities.argmax(axis=1)
        confidence = probabilities.max(axis=1)
        observed = (predicted == y).astype(int)
    edges = np.linspace(0.0, 1.0, bins + 1)
    result = 0.0
    for index in range(bins):
        mask = (confidence >= edges[index]) & (
            confidence < edges[index + 1] if index < bins - 1
            else confidence <= edges[index + 1]
        )
        if mask.any():
            result += mask.mean() * abs(observed[mask].mean() - confidence[mask].mean())
    return float(result)


def calculate_metrics(y: np.ndarray, probabilities: np.ndarray,
                      kind: str) -> dict:
    if len(y) == 0:
        raise ValueError("Cannot score an empty set.")
    probabilities = np.clip(probabilities, EPS, 1.0)
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    if kind == "multiclass":
        labels = list(range(probabilities.shape[1]))
        one_hot = np.eye(len(labels), dtype=float)[y.astype(int)]
        losses = -np.log(probabilities[np.arange(len(y)), y.astype(int)])
        brier = np.square(probabilities - one_hot).sum(axis=1).mean()
        prediction = probabilities.argmax(axis=1)
        score = {
            "logloss": float(losses.mean()),
            "brier": float(brier),
            "accuracy": float(accuracy_score(y, prediction)),
            "n": int(len(y)),
        }
        for class_id in labels:
            binary_y = (y == class_id).astype(int)
            class_p = probabilities[:, class_id]
            class_loss = -(binary_y * np.log(class_p) +
                           (1 - binary_y) * np.log1p(-class_p))
            score[f"class_{class_id}_logloss"] = float(class_loss.mean())
            score[f"class_{class_id}_brier"] = float(
                np.square(binary_y - class_p).mean()
            )
        try:
            score["auc_ovr_macro"] = float(
                roc_auc_score(y, probabilities, multi_class="ovr", average="macro")
            )
        except ValueError:
            score["auc_ovr_macro"] = None
    else:
        y = y.astype(int)
        p = probabilities[:, 1]
        score = {
            "logloss": float(log_loss(y, probabilities, labels=[0, 1])),
            "brier": float(np.square(y - p).mean()),
            "accuracy": float(accuracy_score(y, probabilities.argmax(axis=1))),
            "n": int(len(y)),
        }
        try:
            score["auc"] = float(roc_auc_score(y, p))
        except ValueError:
            score["auc"] = None
    score["ece_10bin"] = expected_calibration_error(
        y.astype(int), probabilities, kind
    )
    return score


def train_prior(y: np.ndarray, class_count: int) -> np.ndarray:
    counts = np.bincount(y.astype(int), minlength=class_count).astype(float)
    prior = counts / counts.sum()
    return prior


def closing_odds_probabilities(test: pd.DataFrame,
                               market: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Return a matched, explicitly non-live benchmark from closing-odds fields."""
    if market == "1x2":
        columns = ["odds_pH", "odds_pD", "odds_pA"]
    elif market == "ou25":
        columns = ["odds_pOver25"]
    else:
        return None
    if not set(columns).issubset(test.columns):
        return None
    odds = test[columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(odds).all(axis=1) & (odds > 0).all(axis=1)
    if market == "1x2":
        total = odds.sum(axis=1)
        valid &= total > 0
        odds[valid] = odds[valid] / total[valid, None]
        return valid, odds[valid]
    valid &= (odds[:, 0] < 1.0)
    p_event = np.clip(odds[valid, 0], EPS, 1.0 - EPS)
    return valid, np.column_stack([1.0 - p_event, p_event])


def prediction_frame(rows: pd.DataFrame, fold: str, market: str, model: str,
                     y: np.ndarray, probabilities: np.ndarray,
                     valid: np.ndarray | None = None) -> pd.DataFrame:
    if valid is not None:
        rows = rows.loc[valid].copy()
    out = rows[["_row_id", "Date", "Div", "HomeTeam", "AwayTeam"]].copy()
    out["fold"] = fold
    out["market"] = market
    out["model"] = model
    out["y_true"] = y
    for class_id in range(probabilities.shape[1]):
        out[f"p{class_id}"] = probabilities[:, class_id]
    return out


def row_losses(frame: pd.DataFrame, class_count: int) -> np.ndarray:
    y = frame["y_true"].to_numpy(dtype=int)
    matrix = frame[[f"p{i}" for i in range(class_count)]].to_numpy(dtype=float)
    return -np.log(np.clip(matrix[np.arange(len(y)), y], EPS, 1.0))


def paired_week_bootstrap(candidate: pd.DataFrame, reference: pd.DataFrame,
                          class_count: int, reps: int = BOOTSTRAP_REPS) -> dict:
    left = candidate.set_index("_row_id")
    right = reference.set_index("_row_id")
    common = left.index.intersection(right.index)
    left, right = left.loc[common], right.loc[common]
    if len(common) == 0:
        return {"n": 0, "delta_logloss": None, "ci_low": None, "ci_high": None}
    delta = row_losses(left, class_count) - row_losses(right, class_count)
    weeks = left["Date"].dt.to_period("W-SUN").astype(str).to_numpy()
    sums = pd.DataFrame({"week": weeks, "delta": delta}).groupby("week")[
        "delta"
    ].agg(["sum", "count"])
    week_sums = sums["sum"].to_numpy()
    week_counts = sums["count"].to_numpy()
    rng = np.random.default_rng(SEED)
    draws = np.empty(reps, dtype=float)
    for start in range(0, reps, 512):
        stop = min(start + 512, reps)
        sample = rng.integers(
            0, len(week_sums), size=(stop - start, len(week_sums))
        )
        draws[start:stop] = (
            week_sums[sample].sum(axis=1) / week_counts[sample].sum(axis=1)
        )
    tail = FAMILYWISE_ALPHA / (2 * FAMILYWISE_COMPARISONS)
    return {
        "n": int(len(common)),
        "weeks": int(len(week_sums)),
        "delta_logloss": float(delta.mean()),
        "ci_low": float(np.quantile(draws, tail)),
        "ci_high": float(np.quantile(draws, 1.0 - tail)),
        "bootstrap_reps": reps,
        "unit": "calendar_week",
        "familywise_confidence": 1.0 - FAMILYWISE_ALPHA,
        "bonferroni_comparisons": FAMILYWISE_COMPARISONS,
    }


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    fold_rows, league_rows, comparisons = [], [], {}
    for (fold, market, model), group in predictions.groupby(
        ["fold", "market", "model"], sort=True
    ):
        kind = MARKETS[market][1]
        class_count = MARKETS[market][2]
        metrics = calculate_metrics(
            group["y_true"].to_numpy(dtype=int),
            group[[f"p{i}" for i in range(class_count)]].to_numpy(dtype=float),
            kind,
        )
        fold_rows.append({"fold": fold, "market": market, "model": model, **metrics})
    for (market, model), group in predictions.groupby(
        ["market", "model"], sort=True
    ):
        kind = MARKETS[market][1]
        class_count = MARKETS[market][2]
        metrics = calculate_metrics(
            group["y_true"].to_numpy(dtype=int),
            group[[f"p{i}" for i in range(class_count)]].to_numpy(dtype=float),
            kind,
        )
        metrics.update({"folds": int(group["fold"].nunique())})
        league_rows.append({"market": market, "model": model, **metrics})

    for market, market_group in predictions.groupby("market", sort=True):
        class_count = MARKETS[market][2]
        comparisons[market] = {}
        for model in MODEL_NAMES:
            candidate = market_group.loc[market_group["model"] == model]
            if candidate.empty:
                continue
            for reference_name in ("BASE_RATE", "CLOSING_ODDS_REFERENCE"):
                reference = market_group.loc[
                    market_group["model"] == reference_name
                ]
                if reference.empty:
                    continue
                comparisons[market][f"{model}_vs_{reference_name}"] = (
                    paired_week_bootstrap(candidate, reference, class_count)
                )
    return pd.DataFrame(fold_rows), pd.DataFrame(league_rows), comparisons


def feature_hash(columns: list[str]) -> str:
    payload = "\n".join(columns).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_output_path(path: Path) -> Path:
    output_path = Path(path).resolve()
    try:
        output_path.relative_to(LAB.resolve())
    except ValueError as error:
        raise ValueError(
            f"Experiment output must stay inside {LAB.resolve()}."
        ) from error
    return output_path


def package_versions() -> dict:
    names = ("numpy", "pandas", "scikit-learn", "lightgbm", "xgboost")
    versions = {}
    for name in names:
        if _package_exists(name):
            versions[name] = importlib.metadata.version(name)
    return versions


def _package_exists(name: str) -> bool:
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def make_report(predictions: pd.DataFrame, aggregate: pd.DataFrame,
                input_path: Path, output_path: Path, features: list[str],
                input_hash: str) -> str:
    predictions = predictions.copy()
    predictions["Date"] = pd.to_datetime(predictions["Date"], errors="coerce")
    min_date = predictions["Date"].min().date()
    max_date = predictions["Date"].max().date()
    candidates = aggregate.loc[aggregate["model"].isin(MODEL_NAMES)]
    lines = [
        "# EXP-05 — Perbandingan Keluarga Model Historis",
        "",
        "**Status: REFERENCE_ONLY — bukan bukti siap taruhan atau profitabilitas.**",
        "",
        "## Ringkasan",
        "",
        f"- Input: `{input_path.relative_to(ROOT)}`; SHA-256 `{input_hash}`.",
        f"- Isi prediksi out-of-fold: {len(predictions):,} baris model; "
        f"tanggal {min_date} sampai {max_date}.",
        f"- Fitur statistik pra-pertandingan: {len(features)}; "
        f"SHA-256 daftar fitur `{feature_hash(features)}`.",
        f"- Keluarga model: {', '.join(MODEL_NAMES)}; semua memakai fitur statistik "
        "tanpa odds.",
        "- Split kronologis per musim; inner validation 90 hari hanya untuk "
        "menentukan jumlah boosting round LightGBM/XGBoost.",
        "- Semua rentang historis di data ini sudah pernah ditinjau dalam audit/"
        "backtest proyek. Karena itu, ranking berikut adalah screening retrospektif, "
        "bukan test independen baru.",
        "",
        "## Ranking historis per pasar",
        "",
        "Urutan memakai LogLoss gabungan seluruh fold (lebih rendah lebih baik). "
        "Ini pemeringkatan untuk menentukan kandidat riset berikutnya, bukan "
        "rekomendasi taruhan.",
        "",
        "| Pasar | Model teratas historis | N | LogLoss | Brier | Fold menang | Δ vs base rate | "
        "CI simultan 95% Δ |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    all_comparisons = json.loads(
        (output_path / "paired_bootstrap.json").read_text(encoding="utf-8")
    )
    for market in MARKETS:
        rows = candidates.loc[candidates["market"] == market].sort_values(
            ["logloss", "brier"]
        )
        if rows.empty:
            continue
        winner = rows.iloc[0]
        fold_candidates = pd.read_csv(output_path / "fold_metrics.csv")
        market_folds = fold_candidates.loc[
            (fold_candidates["market"] == market) &
            fold_candidates["model"].isin(MODEL_NAMES)
        ]
        fold_wins = 0
        for _, fold in market_folds.groupby("fold"):
            fold_wins += int(fold.loc[fold["logloss"].idxmin(), "model"] ==
                             winner["model"])
        ref = aggregate.loc[
            (aggregate["market"] == market) & (aggregate["model"] == "BASE_RATE")
        ]
        delta = float(winner["logloss"] - ref.iloc[0]["logloss"]) if len(ref) else np.nan
        pair = all_comparisons.get(market, {}).get(
            f"{winner['model']}_vs_BASE_RATE", {}
        )
        ci = (
            f"[{pair['ci_low']:.4f}, {pair['ci_high']:.4f}]"
            if pair.get("ci_low") is not None else "n/a"
        )
        lines.append(
            f"| {market} | {winner['model']} | {int(winner['n']):,} | "
            f"{winner['logloss']:.4f} | {winner['brier']:.4f} | "
            f"{fold_wins}/{market_folds['fold'].nunique()} | {delta:+.4f} | {ci} |"
        )
    lines.extend([
        "",
        "Δ LogLoss dihitung terhadap prior base-rate yang hanya dipelajari dari data "
        "latih tiap fold. Interval memakai paired bootstrap per pekan dengan "
        "Bonferroni untuk 32 perbandingan yang direncanakan; interval yang melintasi "
        "nol tidak menunjukkan perbedaan yang meyakinkan. Koreksi ini tidak mengubah "
        "status semua hasil sebagai REFERENCE_ONLY.",
        "",
        "## Odds penutupan sebagai pembanding",
        "",
        "Untuk dua pasar yang memiliki odds, perbandingan memakai hanya baris yang "
        "memiliki odds tersedia; Δ adalah LogLoss kandidat dikurangi LogLoss odds "
        "penutupan, sehingga nilai positif berarti kandidat lebih buruk.",
        "",
        "| Pasar | Model statistik teratas | N cocok | LL kandidat | LL odds penutupan | "
        "Δ LL kandidat−odds | CI simultan 95% |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for market in ("1x2", "ou25"):
        rows = candidates.loc[candidates["market"] == market].sort_values(
            ["logloss", "brier"]
        )
        reference = aggregate.loc[
            (aggregate["market"] == market) &
            (aggregate["model"] == "CLOSING_ODDS_REFERENCE")
        ]
        if rows.empty or reference.empty:
            continue
        winner = rows.iloc[0]
        reference_rows = predictions.loc[
            (predictions["market"] == market) &
            (predictions["model"] == "CLOSING_ODDS_REFERENCE")
        ]
        candidate_rows = predictions.loc[
            (predictions["market"] == market) &
            (predictions["model"] == winner["model"])
        ].set_index("_row_id")
        reference_rows = reference_rows.set_index("_row_id")
        common = candidate_rows.index.intersection(reference_rows.index)
        class_count = MARKETS[market][2]
        matched_metrics = calculate_metrics(
            candidate_rows.loc[common, "y_true"].to_numpy(dtype=int),
            candidate_rows.loc[common, [f"p{i}" for i in range(class_count)]]
            .to_numpy(dtype=float),
            MARKETS[market][1],
        )
        close_metrics = calculate_metrics(
            reference_rows.loc[common, "y_true"].to_numpy(dtype=int),
            reference_rows.loc[common, [f"p{i}" for i in range(class_count)]]
            .to_numpy(dtype=float),
            MARKETS[market][1],
        )
        pair = all_comparisons.get(market, {}).get(
            f"{winner['model']}_vs_CLOSING_ODDS_REFERENCE", {}
        )
        ci = (
            f"[{pair['ci_low']:.4f}, {pair['ci_high']:.4f}]"
            if pair.get("ci_low") is not None else "n/a"
        )
        delta = pair.get("delta_logloss")
        lines.append(
            f"| {market} | {winner['model']} | {len(common):,} | "
            f"{matched_metrics['logloss']:.4f} | {close_metrics['logloss']:.4f} | "
            f"{delta:+.4f} | {ci} |"
        )
    lines.extend([
        "",
        "Closing odds menang pada 1X2 dan O/U 2.5 dalam skor historis yang cocok. "
        "Tidak tersedia odds pembanding untuk gol kandang/tandang; peningkatan "
        "terhadap base rate di pasar tersebut bukan bukti edge taruhan.",
        "",
        "## Interpretasi odds dan kesiapan taruhan",
        "",
        "- `odds_pH`, `odds_pD`, `odds_pA`, dan `odds_pOver25` tidak dipakai sebagai "
        "fitur model. Audit proyek menyatakan nilai ini berasal dari odds penutupan.",
        "- Odds penutupan dapat muncul sebagai baris `CLOSING_ODDS_REFERENCE` di "
        "hasil evaluasi saja; pembanding ini bukan harga yang tersedia saat keputusan "
        "taruhan dibuat.",
        "- Dataset tidak memiliki odds bertimestamp pada saat keputusan, harga "
        "eksekusi, komisi, batas taruhan, atau hasil prospektif yang belum dilihat. "
        "Karena itu EV/ROI dan kesiapan taruhan uang nyata tidak dapat disimpulkan.",
        "- Model ini pra-pertandingan, bukan model in-play. Data tidak berisi menit "
        "pertandingan, skor berjalan, kartu, atau odds live.",
        "- Tidak ada taruhan yang ditempatkan, model yang disimpan sebagai kandidat, "
        "atau artefak produksi yang diubah.",
        "",
        "## Model dan pengaturan",
        "",
        "| Model | Pengaturan utama |",
        "|---|---|",
        "| lgbm | LightGBM, learning rate 0.03, 63 leaves; early stopping temporal |",
        "| xgboost | XGBoost histogram, depth 6, learning rate 0.03; early stopping temporal |",
        "| histgb | HistGradientBoosting, 180 iterasi, 31 leaves |",
        "| logreg | Median imputation, standard scaling, logistic regression C=1 |",
        "",
        "Semua model memakai bobot pelatihan half-life 365 hari. LogLoss dan Brier "
        "adalah metrik utama; accuracy/AUC/ECE disertakan sebagai diagnostik. "
        "Interval bootstrap mengoreksi 32 perbandingan dengan Bonferroni. "
        "Lihat `aggregate_metrics.csv`, `fold_metrics.csv`, `per_league_metrics.csv`, "
        "`paired_bootstrap.json`, dan `predictions.csv` untuk rincian.",
        "",
        "## Langkah berikutnya sebelum uang nyata",
        "",
        "1. Bekukan satu kandidat per pasar berdasarkan protokol ini; jangan memilih "
        "ulang dari hasil musim yang sama.",
        "2. Simpan prediksi sebelum kickoff dengan waktu/sumber odds yang benar-benar "
        "tersedia saat keputusan dibuat.",
        "3. Nilai logloss, Brier, kalibrasi, coverage, dan—hanya bila odds eksekusi "
        "bertimestamp tersedia—hasil setelah komisi dan batas taruhan pada periode "
        "prospektif yang belum dilihat.",
        "4. Tinjau hasil prospektif terpisah sebelum menyatakan siap untuk taruhan "
        "nyata; tidak ada jaminan profit.",
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
    input_hash = file_hash(input_path)
    markets = args.markets or list(MARKETS)
    models = args.models or list(MODEL_NAMES)
    unknown = set(markets) - set(MARKETS)
    if unknown:
        raise ValueError(f"Unknown markets: {sorted(unknown)}")
    unknown = set(models) - set(MODEL_NAMES)
    if unknown:
        raise ValueError(f"Unknown models: {sorted(unknown)}")

    X_all = frame[features].to_numpy(dtype=np.float32)
    all_predictions = []
    run_details = []
    selected_folds = [f for f in FOLDS if not args.fold or f["name"] in args.fold]
    if not selected_folds:
        raise ValueError("No folds selected.")

    for fold in selected_folds:
        train_mask = frame["Date"] <= pd.Timestamp(fold["train_end"])
        test_mask = frame["Date"].between(
            pd.Timestamp(fold["test_start"]), pd.Timestamp(fold["test_end"])
        )
        train = frame.loc[train_mask].copy()
        test = frame.loc[test_mask].copy()
        if train.empty or test.empty:
            print(f"SKIP fold {fold['name']}: train={len(train)} test={len(test)}")
            continue
        if train["Date"].max() >= test["Date"].min():
            raise ValueError(f"Temporal overlap found in fold {fold['name']}.")
        print(f"Fold {fold['name']}: train={len(train):,}, test={len(test):,}")
        X_test_full = X_all[test.index.to_numpy()]

        for market in markets:
            target, kind, class_count = MARKETS[market]
            clean_train = train.loc[train[target].notna()]
            clean_test = test.loc[test[target].notna()]
            if clean_train.empty or clean_test.empty:
                print(f"  SKIP {market}: no labeled train/test rows")
                continue
            y_train = clean_train[target].to_numpy(dtype=int)
            y_test = clean_test[target].to_numpy(dtype=int)
            if not set(np.unique(y_train)).issubset(set(range(class_count))):
                raise ValueError(f"Unexpected class labels in {market}, {fold['name']}.")
            X_train = X_all[clean_train.index.to_numpy()]
            X_test = X_all[clean_test.index.to_numpy()]
            fold_started = time.perf_counter()

            prior = train_prior(y_train, class_count)
            base_prob = np.tile(prior, (len(clean_test), 1))
            all_predictions.append(prediction_frame(
                clean_test, fold["name"], market, "BASE_RATE", y_test, base_prob
            ))

            odds = closing_odds_probabilities(clean_test, market)
            if odds is not None:
                valid, odds_prob = odds
                if valid.any():
                    all_predictions.append(prediction_frame(
                        clean_test, fold["name"], market,
                        "CLOSING_ODDS_REFERENCE", y_test[valid], odds_prob, valid
                    ))

            for model_name in models:
                model_started = time.perf_counter()
                probabilities, details = fit_predict(
                    model_name, X_train, y_train, clean_train["Date"],
                    X_test, class_count
                )
                all_predictions.append(prediction_frame(
                    clean_test, fold["name"], market, model_name,
                    y_test, probabilities
                ))
                elapsed = time.perf_counter() - model_started
                run_details.append({
                    "fold": fold["name"],
                    "market": market,
                    "model": model_name,
                    "train_n": int(len(clean_train)),
                    "test_n": int(len(clean_test)),
                    "elapsed_seconds": round(elapsed, 3),
                    **details,
                })
                print(
                    f"  {market:12s} {model_name:8s} "
                    f"logloss={calculate_metrics(y_test, probabilities, kind)['logloss']:.5f} "
                    f"({elapsed:.1f}s)"
                )
            print(f"  fold elapsed: {time.perf_counter() - fold_started:.1f}s")

    if not all_predictions:
        raise RuntimeError("No predictions were produced.")
    predictions = pd.concat(all_predictions, ignore_index=True)
    fold_metrics, aggregate_metrics, comparisons = summarize(predictions)
    predictions.to_csv(output_path / "predictions.csv", index=False)
    fold_metrics.to_csv(output_path / "fold_metrics.csv", index=False)
    aggregate_metrics.to_csv(output_path / "aggregate_metrics.csv", index=False)

    per_league_rows = []
    for (fold, market, model, division), group in predictions.groupby(
        ["fold", "market", "model", "Div"], sort=True
    ):
        kind = MARKETS[market][1]
        class_count = MARKETS[market][2]
        metrics = calculate_metrics(
            group["y_true"].to_numpy(dtype=int),
            group[[f"p{i}" for i in range(class_count)]].to_numpy(dtype=float),
            kind,
        )
        per_league_rows.append({
            "fold": fold, "market": market, "model": model,
            "league": division, **metrics,
        })
    pd.DataFrame(per_league_rows).to_csv(
        output_path / "per_league_metrics.csv", index=False
    )

    (output_path / "paired_bootstrap.json").write_text(
        json.dumps(comparisons, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "fit_details.json").write_text(
        json.dumps(run_details, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "REFERENCE_ONLY",
        "purpose": "historical pre-match model-family screening",
        "input": str(input_path.relative_to(ROOT))
        if input_path.is_relative_to(ROOT) else str(input_path),
        "input_sha256": input_hash,
        "input_rows_with_valid_dates": int(len(frame)),
        "input_date_min": str(frame["Date"].min().date()),
        "input_date_max": str(frame["Date"].max().date()),
        "feature_count": len(features),
        "features": features,
        "features_sha256": feature_hash(features),
        "models": models,
        "markets": markets,
        "folds": selected_folds,
        "half_life_days": HALF_LIFE_DAYS,
        "inner_validation_days": 90,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "familywise_comparisons": FAMILYWISE_COMPARISONS,
        "familywise_confidence": 1.0 - FAMILYWISE_ALPHA,
        "random_seed": SEED,
        "odds_policy": (
            "No odds used as model inputs. Closing odds included only as "
            "REFERENCE_ONLY comparator for 1x2/ou25."
        ),
        "limitations": [
            "Historical periods have already been inspected; no untouched test set.",
            "No timestamped decision-time or in-play odds.",
            "No prospective evidence or profit guarantee.",
        ],
        "package_versions": package_versions(),
    }
    (output_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    report = make_report(
        predictions, aggregate_metrics, input_path, output_path, features, input_hash
    )
    (output_path / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"Saved isolated experiment to {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markets", nargs="+", choices=sorted(MARKETS))
    parser.add_argument("--models", nargs="+", choices=list(MODEL_NAMES))
    parser.add_argument("--fold", nargs="+", choices=[f["name"] for f in FOLDS])
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
