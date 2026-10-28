#!/usr/bin/env python3
"""Compare registered model candidates under explicitly synthetic pre-match odds."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_model_families import (  # noqa: E402
    FOLDS,
    MARKETS,
    calculate_metrics,
    file_hash,
    feature_hash,
    load_frame,
    package_versions,
    validate_output_path,
)
from feature_ablation import GROUP_NAMES, MARKET_MODELS  # noqa: E402

DEFAULT_RUN_DIR = LAB / "results" / "EXP-08-synthetic-odds-scenario-stress-20261028"
DEFAULT_OUTPUT = DEFAULT_RUN_DIR / "odds-report"
DEFAULT_FAMILY_PREDICTIONS = DEFAULT_RUN_DIR / "family-models" / "predictions.csv"
DEFAULT_FEATURE_PREDICTIONS = DEFAULT_RUN_DIR / "feature-groups" / "predictions.csv"
MAIN_FEATURES = ROOT / "logs" / "feat_cols_modeB_ordered.json"
MAIN_MODEL_DIR = ROOT / "models"
FOLD_NAME = "2026-27-partial"
ODDS_MARGIN = 0.06
MIN_POSITIVE_EV = 0.03
SCENARIOS = ("STANDARD", "HEAVY_FAVOURITE", "EXTREME_GAP", "MISMATCHED_ODDS")

MAIN_MODEL_FILES = {
    "1x2": "lgb_1x2_modeB.txt",
    "ou25": "lgb_ou25_modeB.txt",
    "home_ou05": "lgb_home_ou05_modeB.txt",
    "home_ou15": "lgb_home_ou15_modeB.txt",
    "away_ou05": "lgb_away_ou05_modeB.txt",
    "away_ou15": "lgb_away_ou15_modeB.txt",
}


def _number(row: pd.Series, columns: tuple[str, ...], default: float = 0.0) -> float:
    for column in columns:
        value = row.get(column)
        if value is not None and pd.notna(value) and np.isfinite(float(value)):
            return float(value)
    return default


def team_strength(row: pd.Series) -> float:
    """Positive values indicate a stronger home side, using only pre-match inputs."""
    return _number(
        row,
        ("diff_season_ppg", "diff_ppg10", "diff_ppg5", "diff_venue_ppg"),
    )


def expected_goals(row: pd.Series, market: str) -> float:
    if market == "ou25":
        total = row.get("sum_expected_goals")
        if total is not None and pd.notna(total) and np.isfinite(float(total)):
            return float(np.clip(float(total), 0.05, 8.0))
        return max(
            0.05,
            _number(row, ("home_form5_gf",), 1.2)
            + _number(row, ("away_form5_gf",), 1.0),
        )

    if market.startswith("home_"):
        attack = _number(row, ("home_venue_form5_gf", "home_form5_gf"), 1.2)
        opposition_defence = _number(row, ("away_form5_ga",), 1.2)
    else:
        attack = _number(row, ("away_venue_form5_gf", "away_form5_gf"), 1.0)
        opposition_defence = _number(row, ("home_form5_ga",), 1.2)
    return float(np.clip((attack + opposition_defence) / 2.0, 0.05, 6.0))


def poisson_over_probability(lam: float, threshold: float) -> float:
    """P(X > threshold) under a simple Poisson quote-generation heuristic."""
    max_goals = int(math.floor(threshold))
    cumulative = sum(math.exp(-lam) * lam**k / math.factorial(k)
                     for k in range(max_goals + 1))
    return float(np.clip(1.0 - cumulative, 0.02, 0.98))


def _normalise(probabilities: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(probabilities, dtype=float), 0.01, 0.98)
    return p / p.sum()


def _scenario_probabilities(
    row: pd.Series,
    market: str,
    scenario: str,
    train_prior: np.ndarray,
) -> np.ndarray:
    """Create odds from fixed, documented rules; never consult test outcomes."""
    if market == "1x2":
        strength = team_strength(row)
        home_is_stronger = strength >= 0
        if scenario == "STANDARD":
            shift = 0.07 * math.tanh(1.5 * strength)
            q = train_prior.copy()
            q[0] += shift
            q[2] -= shift
            return _normalise(q)
        if scenario == "HEAVY_FAVOURITE":
            return np.array([0.78, 0.14, 0.08] if home_is_stronger
                            else [0.08, 0.14, 0.78])
        if scenario == "EXTREME_GAP":
            return np.array([0.93, 0.05, 0.02] if home_is_stronger
                            else [0.02, 0.05, 0.93])
        if scenario == "MISMATCHED_ODDS":
            # Quote intentionally favours the side opposing the pre-match proxy.
            return np.array([0.14, 0.18, 0.68] if home_is_stronger
                            else [0.68, 0.18, 0.14])
        raise ValueError(f"Unknown scenario: {scenario}")

    threshold = 2.5 if market == "ou25" else (0.5 if market.endswith("ou05")
                                               else 1.5)
    proxy_over = poisson_over_probability(expected_goals(row, market), threshold)
    if scenario == "STANDARD":
        p_over = 0.5 * float(train_prior[1]) + 0.5 * proxy_over
    elif scenario == "HEAVY_FAVOURITE":
        p_over = 0.82 if proxy_over >= 0.5 else 0.18
    elif scenario == "EXTREME_GAP":
        p_over = 0.94 if proxy_over >= 0.5 else 0.06
    elif scenario == "MISMATCHED_ODDS":
        p_over = 0.72 if proxy_over < 0.5 else 0.28
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    return _normalise(np.array([1.0 - p_over, p_over]))


def generate_synthetic_odds(
    fixtures: pd.DataFrame,
    priors: dict[str, np.ndarray],
) -> pd.DataFrame:
    rows = []
    for _, fixture in fixtures.iterrows():
        for scenario in SCENARIOS:
            for market, (_, _, class_count) in MARKETS.items():
                probabilities = _scenario_probabilities(
                    fixture, market, scenario, priors[market]
                )
                odds = 1.0 / (probabilities * (1.0 + ODDS_MARGIN))
                row = {
                    "_row_id": int(fixture["_row_id"]),
                    "Date": fixture["Date"],
                    "Div": fixture["Div"],
                    "HomeTeam": fixture["HomeTeam"],
                    "AwayTeam": fixture["AwayTeam"],
                    "market": market,
                    "scenario": scenario,
                    "quote_source": "SYNTHETIC_NOT_BOOKMAKER",
                    "overround": float((1.0 / odds).sum() - 1.0),
                }
                for index in range(class_count):
                    row[f"q{index}"] = float(probabilities[index])
                    row[f"odds{index}"] = float(odds[index])
                rows.append(row)
    return pd.DataFrame(rows)


def _load_predictions(path: Path, kind: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"{kind} predictions not found: {path}")
    frame = pd.read_csv(path, low_memory=False)
    if "fold" not in frame or "market" not in frame:
        raise ValueError(f"{kind} predictions missing fold/market columns.")
    frame = frame.loc[frame["fold"] == FOLD_NAME].copy()
    if frame.empty:
        raise ValueError(f"{kind} predictions contain no rows for {FOLD_NAME}.")
    return frame


def _candidate_rows(
    frame: pd.DataFrame,
    family_predictions: pd.DataFrame,
    feature_predictions: pd.DataFrame,
    priors: dict[str, np.ndarray],
) -> pd.DataFrame:
    pieces = []
    family_names = {"lgbm", "xgboost", "histgb", "logreg"}

    family = family_predictions.loc[
        family_predictions["model"].isin(family_names)
    ].copy()
    for _, source in family.groupby(["market", "model"], sort=True):
        source = source.copy()
        source["candidate"] = "LAB_FAMILY_" + source["model"].astype(str)
        source["source"] = "EXP-05 family"
        source["uses_h2h"] = True
        pieces.append(source)

    features = feature_predictions.copy()
    for group, source in features.groupby(["market", "feature_group"], sort=True):
        market, feature_group = group
        source = source.copy()
        source["candidate"] = (
            "LAB_" + str(feature_group) + "_" + str(MARKET_MODELS[market])
        )
        source["source"] = "EXP-01 feature ablation"
        source["uses_h2h"] = feature_group in {"F4", "F5"}
        pieces.append(source)

    combined = pd.concat(pieces, ignore_index=True)
    combined["candidate"] = combined["candidate"].astype(str)
    combined = combined.rename(columns={"Date": "Date"})
    return combined


def _load_main_models(model_dir: Path, feature_path: Path) -> tuple[dict, list[str]]:
    if not feature_path.is_file():
        raise FileNotFoundError(f"Main model feature manifest not found: {feature_path}")
    feature_names = json.loads(feature_path.read_text(encoding="utf-8"))
    if not isinstance(feature_names, list) or not feature_names:
        raise ValueError("Main model feature manifest is empty or invalid.")
    models = {}
    for market, filename in MAIN_MODEL_FILES.items():
        model_path = model_dir / filename
        if not model_path.is_file():
            raise FileNotFoundError(f"Main model not found: {model_path}")
        model = lgb.Booster(model_file=str(model_path))
        if model.num_feature() != len(feature_names):
            raise ValueError(
                f"{market} model expects {model.num_feature()} features but "
                f"manifest contains {len(feature_names)}."
            )
        models[market] = model
    return models, feature_names


def _main_model_rows(
    test: pd.DataFrame,
    quotes: pd.DataFrame,
    models: dict,
    feature_names: list[str],
) -> pd.DataFrame:
    missing = sorted(set(feature_names) - set(test.columns))
    if missing:
        raise ValueError(f"Main model features missing from input: {missing}")
    rows = []
    for scenario, scenario_quotes in quotes.groupby("scenario", sort=False):
        quote_lookup = scenario_quotes.set_index(["_row_id", "market"])
        match_rows = test.set_index("_row_id")
        for market, model in models.items():
            selected = match_rows.loc[match_rows.index.isin(
                scenario_quotes.loc[scenario_quotes["market"] == market, "_row_id"]
            )].copy()
            selected_ids = selected.index.to_list()
            if not selected_ids:
                continue
            matrix = selected[feature_names].apply(
                pd.to_numeric, errors="coerce"
            ).to_numpy(dtype=np.float32)
            for feature, quote_market in (
                ("odds_pH", "1x2"),
                ("odds_pD", "1x2"),
                ("odds_pA", "1x2"),
                ("odds_pOver25", "ou25"),
            ):
                if feature not in feature_names:
                    continue
                quote_class = {
                    "odds_pH": 0,
                    "odds_pD": 1,
                    "odds_pA": 2,
                    "odds_pOver25": 1,
                }[feature]
                quote_values = quote_lookup.loc[
                    [(row_id, quote_market) for row_id in selected_ids],
                    f"q{quote_class}",
                ].to_numpy(dtype=float)
                matrix[:, feature_names.index(feature)] = quote_values
            probabilities = np.asarray(model.predict(matrix), dtype=float)
            if probabilities.ndim == 1:
                probabilities = np.column_stack(
                    [1.0 - probabilities, probabilities]
                )
            probabilities = np.clip(probabilities, 1e-12, 1.0)
            probabilities /= probabilities.sum(axis=1, keepdims=True)
            for position, row_id in enumerate(selected_ids):
                target = MARKETS[market][0]
                match = match_rows.loc[row_id]
                row = {
                    "_row_id": int(row_id),
                    "Date": match["Date"],
                    "Div": match["Div"],
                    "HomeTeam": match["HomeTeam"],
                    "AwayTeam": match["AwayTeam"],
                    "fold": FOLD_NAME,
                    "market": market,
                    "candidate": "MAIN_MODE_B",
                    "source": "main script Mode B artifact",
                    "uses_h2h": True,
                    "scenario": scenario,
                    "y_true": match[target],
                }
                for class_id, probability in enumerate(probabilities[position]):
                    row[f"p{class_id}"] = float(probability)
                rows.append(row)
    return pd.DataFrame(rows)


def _reference_rows(fixtures: pd.DataFrame, quotes: pd.DataFrame,
                    priors: dict[str, np.ndarray]) -> pd.DataFrame:
    rows = []
    test_by_id = fixtures.set_index("_row_id")
    for _, quote in quotes.iterrows():
        fixture = test_by_id.loc[quote["_row_id"]]
        class_count = MARKETS[quote["market"]][2]
        row = {
            "_row_id": int(quote["_row_id"]),
            "Date": fixture["Date"],
            "Div": fixture["Div"],
            "HomeTeam": fixture["HomeTeam"],
            "AwayTeam": fixture["AwayTeam"],
            "fold": FOLD_NAME,
            "market": quote["market"],
            "scenario": quote["scenario"],
            "candidate": "SYNTHETIC_ODDS_REFERENCE",
            "source": "synthetic quote; no-vig probabilities",
            "uses_h2h": False,
            "y_true": fixture[MARKETS[quote["market"]][0]],
        }
        for class_id in range(class_count):
            row[f"p{class_id}"] = float(quote[f"q{class_id}"])
        rows.append(row)
    for market, (_, _, class_count) in MARKETS.items():
        target = MARKETS[market][0]
        eligible = fixtures.loc[fixtures[target].notna()]
        for _, fixture in eligible.iterrows():
            for scenario in SCENARIOS:
                row = {
                    "_row_id": int(fixture["_row_id"]),
                    "Date": fixture["Date"],
                    "Div": fixture["Div"],
                    "HomeTeam": fixture["HomeTeam"],
                    "AwayTeam": fixture["AwayTeam"],
                    "fold": FOLD_NAME,
                    "market": market,
                    "scenario": scenario,
                    "candidate": "TRAIN_BASE_RATE",
                    "source": "training-fold prior",
                    "uses_h2h": False,
                    "y_true": int(fixture[target]),
                }
                for class_id in range(class_count):
                    row[f"p{class_id}"] = float(priors[market][class_id])
                rows.append(row)
    return pd.DataFrame(rows)


def _metric_row(group: pd.DataFrame, quotes: pd.DataFrame) -> dict:
    market = str(group["market"].iloc[0])
    scenario = str(group["scenario"].iloc[0])
    class_count = MARKETS[market][2]
    kind = MARKETS[market][1]
    y = group["y_true"].to_numpy(dtype=int)
    probs = group[[f"p{index}" for index in range(class_count)]].to_numpy(float)
    metrics = calculate_metrics(y, probs, kind)
    means = probs.mean(axis=0)
    observed = np.bincount(y, minlength=class_count) / len(y)
    bias = means - observed
    quote_rows = quotes.loc[
        (quotes["market"] == market) & (quotes["scenario"] == scenario)
    ].set_index("_row_id").loc[group["_row_id"].to_numpy()]
    odds = quote_rows[[f"odds{index}" for index in range(class_count)]].to_numpy(float)
    ev = probs * odds - 1.0
    selected = np.argmax(ev, axis=1)
    positive = ev[np.arange(len(ev)), selected] >= MIN_POSITIVE_EV
    returns = np.zeros(len(y), dtype=float)
    returns[positive] = np.where(
        y[positive] == selected[positive],
        odds[np.arange(len(y))[positive], selected[positive]] - 1.0,
        -1.0,
    )
    bet_count = int(positive.sum())
    score = {
        **metrics,
        "scenario": scenario,
        "market": market,
        "candidate": group["candidate"].iloc[0],
        "source": group["source"].iloc[0],
        "uses_h2h": bool(group["uses_h2h"].iloc[0]),
        "signed_over_probability_bias": (
            float(bias[1]) if class_count == 2 else None
        ),
        "max_abs_class_probability_bias": float(np.abs(bias).max()),
        "mean_absolute_class_probability_bias": float(np.abs(bias).mean()),
        "mean_probability_range_vs_quote": float(
            np.abs(probs - quote_rows[
                [f"q{index}" for index in range(class_count)]
            ].to_numpy(float)).mean()
        ),
        "bet_count_at_min_ev_3pct": bet_count,
        "bet_coverage_pct": float(100.0 * bet_count / len(y)),
        "hypothetical_net_units": float(returns.sum()),
        "hypothetical_yield_pct": (
            float(100.0 * returns.sum() / bet_count) if bet_count else None
        ),
        "hypothetical_win_rate_pct": (
            float(100.0 * (y[positive] == selected[positive]).mean())
            if bet_count else None
        ),
    }
    return score


def _scenario_diagnostics(
    candidates: pd.DataFrame, quotes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    diagnostic_rows = []
    bias_rows = []
    model_rows = candidates.loc[
        ~candidates["candidate"].isin({
            "SYNTHETIC_ODDS_REFERENCE", "TRAIN_BASE_RATE",
        })
    ]
    for (market, scenario), group in model_rows.groupby(
        ["market", "scenario"], sort=True
    ):
        class_count = MARKETS[market][2]
        pivot = group.pivot(index="_row_id", columns="candidate",
                            values=[f"p{i}" for i in range(class_count)])
        prediction_matrices = []
        model_votes = []
        for candidate in group["candidate"].drop_duplicates():
            rows = group.loc[group["candidate"] == candidate].set_index("_row_id")
            prediction_matrices.append(
                rows[[f"p{i}" for i in range(class_count)]].to_numpy(float)
            )
            model_votes.append(
                rows[[f"p{i}" for i in range(class_count)]].to_numpy(float).argmax(1)
            )
        matrix = np.stack(prediction_matrices, axis=1)
        votes = np.stack(model_votes, axis=1)
        spread = (matrix.max(axis=1) - matrix.min(axis=1)).mean()
        vote_counts = np.stack(
            [(votes == class_id).mean(axis=1) for class_id in range(class_count)],
            axis=1,
        )
        consensus = vote_counts.max(axis=1).mean()
        quote_subset = quotes.loc[
            (quotes["market"] == market) & (quotes["scenario"] == scenario)
        ].set_index("_row_id").loc[group.drop_duplicates("_row_id")["_row_id"]]
        quote_picks = quote_subset[
            [f"q{index}" for index in range(class_count)]
        ].to_numpy(float).argmax(axis=1)
        model_pick = matrix.mean(axis=1).argmax(axis=1)
        diagnostic_rows.append({
            "market": market,
            "scenario": scenario,
            "candidate_count": len(prediction_matrices),
            "mean_probability_spread": float(spread),
            "mean_model_pick_consensus_pct": float(100.0 * consensus),
            "mean_candidate_consensus_pick_matches_quote_pct": float(
                100.0 * (model_pick == quote_picks).mean()
            ),
            "quote_overround_mean": float(quote_subset["overround"].mean()),
        })

    for (market, scenario, candidate), group in candidates.groupby(
        ["market", "scenario", "candidate"], sort=True
    ):
        class_count = MARKETS[market][2]
        y = group["y_true"].to_numpy(dtype=int)
        p = group[[f"p{i}" for i in range(class_count)]].to_numpy(float)
        frequencies = np.bincount(y, minlength=class_count) / len(y)
        mean_probability = p.mean(axis=0)
        for class_id in range(class_count):
            bias_rows.append({
                "market": market,
                "scenario": scenario,
                "candidate": candidate,
                "class_id": class_id,
                "class_label": (
                    ["HOME", "DRAW", "AWAY"][class_id]
                    if market == "1x2" else ["UNDER", "OVER"][class_id]
                ),
                "mean_predicted_probability": float(mean_probability[class_id]),
                "observed_frequency": float(frequencies[class_id]),
                "probability_bias": float(
                    mean_probability[class_id] - frequencies[class_id]
                ),
                "n": int(len(group)),
            })
    return pd.DataFrame(diagnostic_rows), pd.DataFrame(bias_rows)


def _coherence_model_key(candidate: str) -> str:
    parts = candidate.split("_")
    if len(parts) >= 3 and parts[0] == "LAB" and parts[1] in GROUP_NAMES:
        return "_".join(parts[:2])
    return candidate


def probability_coherence(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = candidates.copy()
    rows["coherence_model"] = rows["candidate"].map(_coherence_model_key)
    checks = []
    for (scenario, model, market), group in rows.groupby(
        ["scenario", "coherence_model", "market"], sort=True
    ):
        class_count = MARKETS[market][2]
        probabilities = group[
            [f"p{index}" for index in range(class_count)]
        ].to_numpy(float)
        error = np.abs(probabilities.sum(axis=1) - 1.0)
        checks.append({
            "scenario": scenario,
            "model": model,
            "market": market,
            "check": "probability_sum",
            "n": len(error),
            "violations": int((error > 1e-8).sum()),
            "max_error_or_excess": float(error.max()) if len(error) else None,
        })

    for (scenario, model, side), group in rows.loc[
        rows["market"].isin(
            [f"{side}_ou05" for side in ("home", "away")]
            + [f"{side}_ou15" for side in ("home", "away")]
        )
    ].groupby(
        [
            "scenario",
            "coherence_model",
            rows["market"].str.extract(r"^(home|away)")[0].rename("side"),
        ],
        sort=True,
    ):
        lower = group.loc[group["market"] == f"{side}_ou05"].set_index("_row_id")
        upper = group.loc[group["market"] == f"{side}_ou15"].set_index("_row_id")
        common = lower.index.intersection(upper.index)
        if common.empty:
            continue
        excess = (
            upper.loc[common, "p1"].to_numpy(float)
            - lower.loc[common, "p1"].to_numpy(float)
        )
        checks.append({
            "scenario": scenario,
            "model": model,
            "market": f"{side}_ou15_vs_ou05",
            "check": "over15_not_above_over05",
            "n": len(excess),
            "violations": int((excess > 1e-12).sum()),
            "max_error_or_excess": float(max(0.0, excess.max())),
        })
    return pd.DataFrame(checks)


def main_model_sensitivity(candidates: pd.DataFrame) -> pd.DataFrame:
    main = candidates.loc[candidates["candidate"] == "MAIN_MODE_B"]
    rows = []
    for market, market_rows in main.groupby("market", sort=True):
        class_count = MARKETS[market][2]
        standard = market_rows.loc[
            market_rows["scenario"] == "STANDARD"
        ].set_index("_row_id")
        for scenario in SCENARIOS:
            if scenario == "STANDARD":
                continue
            changed = market_rows.loc[
                market_rows["scenario"] == scenario
            ].set_index("_row_id")
            common = standard.index.intersection(changed.index)
            if common.empty:
                continue
            before = standard.loc[
                common, [f"p{index}" for index in range(class_count)]
            ].to_numpy(float)
            after = changed.loc[
                common, [f"p{index}" for index in range(class_count)]
            ].to_numpy(float)
            per_match = np.abs(after - before).mean(axis=1)
            rows.append({
                "market": market,
                "scenario": scenario,
                "n": len(common),
                "mean_absolute_probability_change": float(per_match.mean()),
                "max_absolute_probability_change": float(np.abs(after - before).max()),
                "prediction_class_flip_pct": float(
                    100.0 * (after.argmax(axis=1) != before.argmax(axis=1)).mean()
                ),
            })
    return pd.DataFrame(rows)


def run(args: argparse.Namespace) -> Path:
    output = validate_output_path(args.output_dir)
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise FileExistsError(
            f"Output directory is not empty: {output}; choose a new directory "
            "or pass --overwrite."
        )
    output.mkdir(parents=True, exist_ok=True)
    data_path = args.input.resolve()
    frame, safe_features = load_frame(data_path)
    fold = next(item for item in FOLDS if item["name"] == FOLD_NAME)
    train_mask = frame["Date"] <= pd.Timestamp(fold["train_end"])
    test_mask = frame["Date"].between(
        pd.Timestamp(fold["test_start"]), pd.Timestamp(fold["test_end"])
    )
    train, test = frame.loc[train_mask].copy(), frame.loc[test_mask].copy()
    if train.empty or test.empty:
        raise ValueError("No train/test rows for the configured partial season.")

    priors = {}
    for market, (target, _, class_count) in MARKETS.items():
        labels = train[target].dropna().astype(int).to_numpy()
        counts = np.bincount(labels, minlength=class_count).astype(float)
        priors[market] = (counts + 1.0) / (counts.sum() + class_count)

    family_predictions_path = args.family_predictions.resolve()
    feature_predictions_path = args.feature_predictions.resolve()
    family_predictions = _load_predictions(family_predictions_path, "EXP-05 family")
    feature_predictions = _load_predictions(feature_predictions_path, "EXP-01 feature")
    family_predictions = family_predictions.loc[
        family_predictions["model"].isin({"lgbm", "xgboost", "histgb", "logreg"})
    ].copy()
    if set(family_predictions["model"].unique()) != {
        "lgbm", "xgboost", "histgb", "logreg",
    }:
        raise ValueError("Expected all four EXP-05 model families.")
    if set(feature_predictions["feature_group"].unique()) != set(GROUP_NAMES):
        raise ValueError("Expected all six EXP-01 feature groups (F0-F5).")
    if not set(feature_predictions["market"].unique()) == set(MARKETS):
        raise ValueError("EXP-01 predictions do not contain all six markets.")

    proxy_features = [
        "home_form5_gf", "home_form5_ga", "home_venue_form5_gf",
        "away_form5_gf", "away_form5_ga", "away_venue_form5_gf",
    ]
    fixtures = test.loc[:, [
        "_row_id", "Date", "Div", "HomeTeam", "AwayTeam",
        *[column for column in safe_features if column.startswith(("h2h_", "diff_"))],
        "sum_expected_goals", *proxy_features,
        *[spec[0] for spec in MARKETS.values()],
    ]].copy()
    quotes = generate_synthetic_odds(fixtures, priors)

    family_rows = _candidate_rows(
        test, family_predictions, feature_predictions, priors
    )
    model_dir = args.main_model_dir.resolve()
    feature_path = args.main_features.resolve()
    main_models, main_feature_names = _load_main_models(model_dir, feature_path)
    main_rows = _main_model_rows(test, quotes, main_models, main_feature_names)
    ref_rows = _reference_rows(fixtures, quotes, priors)

    parts = []
    for scenario in SCENARIOS:
        odds = quotes.loc[quotes["scenario"] == scenario]
        scenario_models = family_rows.copy()
        scenario_models["scenario"] = scenario
        parts.append(scenario_models)
    parts.extend([main_rows, ref_rows])
    all_candidates = pd.concat(parts, ignore_index=True, sort=False)
    all_candidates["y_true"] = pd.to_numeric(
        all_candidates["y_true"], errors="coerce"
    )
    all_candidates = all_candidates.loc[all_candidates["y_true"].notna()].copy()
    all_candidates["y_true"] = all_candidates["y_true"].astype(int)

    metric_rows = []
    for _, group in all_candidates.groupby(
        ["scenario", "market", "candidate"], sort=True
    ):
        scenario = group["scenario"].iloc[0]
        quote_subset = quotes.loc[quotes["scenario"] == scenario]
        metric_rows.append(_metric_row(group, quote_subset))
    metrics = pd.DataFrame(metric_rows)
    diagnostics, class_bias = _scenario_diagnostics(all_candidates, quotes)
    coherence = probability_coherence(all_candidates)
    modeb_sensitivity = main_model_sensitivity(all_candidates)

    league_metrics = []
    for (scenario, market, candidate, league), group in all_candidates.groupby(
        ["scenario", "market", "candidate", "Div"], sort=True
    ):
        class_count = MARKETS[market][2]
        scored = calculate_metrics(
            group["y_true"].to_numpy(dtype=int),
            group[[f"p{i}" for i in range(class_count)]].to_numpy(float),
            MARKETS[market][1],
        )
        league_metrics.append({
            "scenario": scenario, "market": market,
            "candidate": candidate, "league": league, **scored,
        })
    league_metrics = pd.DataFrame(league_metrics)

    candidate_metrics = metrics.loc[
        ~metrics["candidate"].isin({
            "SYNTHETIC_ODDS_REFERENCE", "TRAIN_BASE_RATE",
        })
    ]
    leaders = (
        candidate_metrics.groupby(["market", "candidate", "source"], as_index=False)
        .agg(
            mean_logloss=("logloss", "mean"),
            mean_brier=("brier", "mean"),
            mean_ece=("ece_10bin", "mean"),
            scenarios=("scenario", "nunique"),
        )
        .sort_values(["market", "mean_logloss", "mean_brier"])
    )
    leaders["screening_rank"] = leaders.groupby("market").cumcount() + 1
    leaders["decision"] = "REFERENCE_ONLY_SCREENING; NOT A FINAL WINNER"
    scenario_leaders = (
        candidate_metrics.sort_values(["scenario", "market", "logloss", "brier"])
        .drop_duplicates(["scenario", "market"])[[
            "scenario", "market", "candidate", "logloss", "brier", "ece_10bin",
            "bet_count_at_min_ev_3pct",
        ]]
    )

    quotes.to_csv(output / "synthetic_odds_quotes.csv", index=False)
    metrics.to_csv(output / "scenario_metrics.csv", index=False)
    diagnostics.to_csv(output / "scenario_ambiguity.csv", index=False)
    class_bias.to_csv(output / "class_bias.csv", index=False)
    coherence.to_csv(output / "probability_coherence.csv", index=False)
    modeb_sensitivity.to_csv(output / "modeb_scenario_sensitivity.csv", index=False)
    league_metrics.to_csv(output / "per_league_metrics.csv", index=False)
    leaders.to_csv(output / "market_leaders.csv", index=False)
    scenario_leaders.to_csv(output / "scenario_leaders.csv", index=False)
    manifest = {
        "experiment_id": "EXP-08",
        "status": "REFERENCE_ONLY",
        "purpose": "all available model candidates under synthetic pre-match odds stress scenarios",
        "input": str(data_path.relative_to(ROOT)),
        "input_sha256": file_hash(data_path),
        "input_valid_date_rows": int(len(frame)),
        "test_fold": fold,
        "test_date_min": str(test["Date"].min().date()),
        "test_date_max": str(test["Date"].max().date()),
        "test_fixture_rows": int(len(test)),
        "test_labeled_rows_per_market": {
            market: int(test[target].notna().sum())
            for market, (target, _, _) in MARKETS.items()
        },
        "safe_feature_count": len(safe_features),
        "h2h_features": [name for name in safe_features if name.startswith("h2h_")],
        "feature_hash": feature_hash(safe_features),
        "candidate_inventory": {
            "main_script": "Current production Mode B LightGBM artifacts; synthetic quotes injected into odds features per scenario.",
            "EXP-05": ["lgbm", "xgboost", "histgb", "logreg"],
            "EXP-01": list(GROUP_NAMES),
            "unique_model_candidates_per_market": 11,
            "additional_references": ["TRAIN_BASE_RATE", "SYNTHETIC_ODDS_REFERENCE"],
        },
        "feature_ablation_models_by_market": MARKET_MODELS,
        "coherence_rules": [
            "1X2 and each binary market sum to 1.",
            "Team Over 1.5 probability does not exceed Over 0.5.",
        ],
        "scenarios": {
            "STANDARD": "Training-fold prior blended 50/50 with simple pre-match feature proxy.",
            "HEAVY_FAVOURITE": "Synthetic quote assigns 78% to the stronger 1X2 side; binary markets assign 82% to the feature-proxy-favoured side.",
            "EXTREME_GAP": "Synthetic quote assigns 93% to the stronger 1X2 side; binary markets assign 94% to the proxy-favoured side, creating longshot decimal prices.",
            "MISMATCHED_ODDS": "Synthetic quote favours the side opposite the pre-match strength/goal proxy.",
        },
        "synthetic_margin": ODDS_MARGIN,
        "betting_style_rule": {
            "description": "One hypothetical unit only when the largest model expected return at synthetic decimal odds is at least 3%.",
            "ev_threshold": MIN_POSITIVE_EV,
            "not_real_bets": True,
        },
        "main_model_feature_manifest": str(feature_path.relative_to(ROOT)),
        "main_model_feature_manifest_sha256": file_hash(feature_path),
        "main_model_hashes": {
            market: file_hash(model_dir / filename)
            for market, filename in MAIN_MODEL_FILES.items()
        },
        "family_predictions": str(family_predictions_path.relative_to(ROOT)),
        "family_predictions_sha256": file_hash(family_predictions_path),
        "family_manifest_sha256": file_hash(
            family_predictions_path.parent / "manifest.json"
        ),
        "feature_predictions": str(feature_predictions_path.relative_to(ROOT)),
        "feature_predictions_sha256": file_hash(feature_predictions_path),
        "feature_manifest_sha256": file_hash(
            feature_predictions_path.parent / "manifest.json"
        ),
        "package_versions": package_versions(),
        "limitations": [
            "Every test period in this project has already been reviewed; no untouched holdout.",
            "The latest-season fold is partial and is for scenario stress screening only.",
            "All odds are synthetic pre-match quotes, not bookmaker observations or live/in-play prices.",
            "The production Mode B model was trained with historical closing-odds features; synthetic odds create distribution shift.",
            "Hypothetical returns use invented prices and do not estimate real betting profit or readiness.",
            "No live bet or money stake was placed; no production artifact was changed.",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "REPORT.md").write_text(
        make_report(
            metrics, diagnostics, coherence, modeb_sensitivity,
            leaders, scenario_leaders, manifest,
        ),
        encoding="utf-8",
    )
    print(f"Saved synthetic odds stress report to {output}")
    return output


def make_report(
    metrics: pd.DataFrame,
    diagnostics: pd.DataFrame,
    coherence: pd.DataFrame,
    modeb_sensitivity: pd.DataFrame,
    leaders: pd.DataFrame,
    scenario_leaders: pd.DataFrame,
    manifest: dict,
) -> str:
    sum_checks = coherence.loc[coherence["check"] == "probability_sum"]
    team_checks = coherence.loc[
        coherence["check"] == "over15_not_above_over05"
    ]
    sum_violations = int(sum_checks["violations"].sum())
    sum_comparisons = int(sum_checks["n"].sum())
    team_summary = (
        team_checks.groupby(["model", "market"], as_index=False)
        .agg(
            comparisons=("n", "sum"),
            violations=("violations", "sum"),
            max_excess=("max_error_or_excess", "max"),
        )
        .sort_values(["violations", "model", "market"], ascending=[False, True, True])
    )
    team_issues = team_summary.loc[team_summary["violations"] > 0]
    family_issues = team_issues.loc[
        team_issues["model"].str.startswith("LAB_FAMILY_")
    ]
    quote_issues = team_summary.loc[
        team_summary["model"] == "SYNTHETIC_ODDS_REFERENCE"
    ]
    quote_violation_count = int(quote_issues["violations"].sum())
    quote_comparison_count = int(quote_issues["comparisons"].sum())
    quote_max_excess = (
        float(quote_issues["max_excess"].max()) if not quote_issues.empty else 0.0
    )
    sensitivity_top = (
        modeb_sensitivity.loc[
            modeb_sensitivity["prediction_class_flip_pct"].idxmax()
        ]
        if not modeb_sensitivity.empty
        else None
    )
    lines = [
        "# EXP-08 — Uji Tekanan Odds Sintetis untuk Semua Kandidat",
        "",
        "**Status: `REFERENCE_ONLY`; bukan hasil live, bukan bukti profit, dan bukan rekomendasi taruhan.**",
        "",
        "## Ringkasan uji",
        "",
        f"- Fold: `{FOLD_NAME}`, pertandingan {manifest['test_date_min']}–{manifest['test_date_max']}.",
        f"- Baris fixture: {manifest['test_fixture_rows']:,}; jumlah berlabel per pasar: "
        + ", ".join(f"{market}={n:,}" for market, n in manifest["test_labeled_rows_per_market"].items()) + ".",
        "- Kandidat mencakup model Mode B yang dipakai script utama, empat keluarga EXP-05, "
        "dan enam tingkat fitur EXP-01 (F0–F5). Seluruh F0–F5 diuji untuk enam pasar.",
        "- Data yang dipakai untuk H2H tersedia sebelum pertandingan. Model keluarga penuh, "
        "main Mode B, F4, dan F5 memakai H2H; F0–F3 sengaja menjadi ablation tanpa H2H.",
        "- Semua odds di bawah ini dibuat secara sintetis dari prior train dan proxy statistik "
        "pra-pertandingan. Tidak ada hasil pertandingan test yang dipakai untuk membuat harga.",
        "",
        "## Skenario",
        "",
        "| Skenario | Cara membentuk quote sintetis |",
        "|---|---|",
        "| STANDARD | Prior train dicampur dengan proxy statistik sebelum kickoff. |",
        "| HEAVY_FAVOURITE | Satu sisi diberi probabilitas implisit tinggi; sisi lawan menjadi underdog. |",
        "| EXTREME_GAP | Probabilitas favorit sangat tinggi, menciptakan odds panjang untuk lawannya. |",
        "| MISMATCHED_ODDS | Quote sengaja mengunggulkan sisi yang berlawanan dengan proxy statistik. |",
        "",
        f"Setiap quote memakai margin sintetis {ODDS_MARGIN:.0%}. Ini simulasi pra-pertandingan, "
        "bukan in-play. Istilah heavy favorite/huge underdog dan odds ekstrem dipakai sebagai "
        "kategori stress test, bukan deskripsi bookmaker yang benar-benar diamati.",
        "",
        "## Pemimpin screening per pasar",
        "",
        "Diurutkan dari rata-rata LogLoss pada empat skenario. Karena pertandingan yang sama "
        "diulang dengan harga sintetis, ini bukan empat sampel independen. Peringkat hanya "
        "menunjukkan kandidat yang perlu diuji lebih lanjut.",
        "",
        "| Pasar | Kandidat screening teratas | LogLoss rata-rata | Brier rata-rata | ECE rata-rata |",
        "|---|---|---:|---:|---:|",
    ]
    for market in MARKETS:
        best = leaders.loc[leaders["market"] == market].head(1)
        if best.empty:
            continue
        row = best.iloc[0]
        lines.append(
            f"| {market} | {row['candidate']} | {row['mean_logloss']:.5f} | "
            f"{row['mean_brier']:.5f} | {row['mean_ece']:.5f} |"
        )
    lines.extend([
        "",
        "## Pemimpin tiap simulasi",
        "",
        "| Skenario | Pasar | Kandidat LogLoss terendah | LogLoss | Brier | ECE | Sinyal bet hipotetis |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for row in scenario_leaders.itertuples(index=False):
        result = metrics.loc[
            (metrics["scenario"] == row.scenario)
            & (metrics["market"] == row.market)
            & (metrics["candidate"] == row.candidate)
        ].iloc[0]
        lines.append(
            f"| {row.scenario} | {row.market} | {row.candidate} | "
            f"{row.logloss:.5f} | {row.brier:.5f} | {row.ece_10bin:.5f} | "
            f"{int(result['bet_count_at_min_ev_3pct']):,} |"
        )
    lines.extend([
        "",
        "## Bias dan ketidakpastian model",
        "",
        "- `scenario_ambiguity.csv` mengukur seberapa jauh kandidat tidak sepakat: rentang "
        "probabilitas antarmodel, konsensus pilihan hasil, dan kecocokan pilihan konsensus "
        "dengan quote sintetis.",
        "- `class_bias.csv` menunjukkan selisih probabilitas rata-rata terhadap frekuensi "
        "hasil aktual per kelas (kandang/seri/tandang atau under/over). Nilai positif berarti "
        "kelas itu cenderung terlalu sering diperkirakan.",
        "- Perbandingan LogLoss, Brier, dan ECE pada `scenario_metrics.csv` membantu melihat "
        "apakah kandidat tetap terkalibrasi ketika harga berubah.",
        "",
        "| Pasar | Skenario | Rentang peluang antarmodel | Konsensus pilihan model | Pilihan model cocok quote |",
        "|---|---|---:|---:|---:|",
    ])
    for row in diagnostics.itertuples(index=False):
        lines.append(
            f"| {row.market} | {row.scenario} | {row.mean_probability_spread:.4f} | "
            f"{row.mean_model_pick_consensus_pct:.1f}% | "
            f"{row.mean_candidate_consensus_pick_matches_quote_pct:.1f}% |"
        )
    lines.extend([
        "",
        "## Konsistensi probabilitas antarpasar",
        "",
        f"- Jumlah probabilitas dalam tiap pasar: {sum_violations:,} pelanggaran dari "
        f"{sum_comparisons:,} pemeriksaan.",
        "- Untuk gol tim, probabilitas Over 1.5 harus tidak melebihi Over 0.5. "
        f"Terjadi {int(team_issues['violations'].sum()):,} pelanggaran di seluruh "
        "kandidat dan skenario.",
    ])
    if team_issues.empty:
        lines.append("- Tidak ada pelanggaran urutan probabilitas gol tim.")
    else:
        lines.extend([
            "",
            "| Kandidat | Relasi pasar | Pelanggaran | Perbandingan | Excess maksimum |",
            "|---|---|---:|---:|---:|",
        ])
        for row in team_issues.itertuples(index=False):
            lines.append(
                f"| {row.model} | {row.market} | {int(row.violations):,} | "
                f"{int(row.comparisons):,} | {row.max_excess:.4f} |"
            )
    if quote_violation_count:
        lines.extend([
            "",
            f"`SYNTHETIC_ODDS_REFERENCE` melanggar urutan Over 1.5 ≤ Over 0.5 pada "
            f"{quote_violation_count:,} dari {quote_comparison_count:,} perbandingan "
            f"(excess maksimum {quote_max_excess:.4f}). Ini berasal dari quote "
            "MISMATCHED_ODDS yang membalik tiap garis gol secara independen; quote "
            "tersebut sengaja adversarial dan bukan referensi lintas-pasar yang koheren.",
        ])
    if not family_issues.empty:
        lines.append(
            f"Model keluarga EXP-05 memiliki {int(family_issues['violations'].sum()):,} "
            "pelanggaran kandidat-level; nilai probabilitas pasar-pasar tersebut tidak "
            "boleh dianggap koheren hanya karena LogLoss per pasar baik."
        )
    if sensitivity_top is not None:
        lines.append(
            f"Perubahan kelas terbesar pada MAIN_MODE_B adalah "
            f"{sensitivity_top['prediction_class_flip_pct']:.1f}% untuk "
            f"`{sensitivity_top['market']}` pada skenario "
            f"`{sensitivity_top['scenario']}`; ini diagnostik pergeseran distribusi "
            "akibat odds sintetis, bukan validasi odds nyata."
        )
    lines.extend([
        "",
        "## Cara membaca simulasi bet",
        "",
        f"Kolom sinyal menghitung fixture yang melewati aturan EV tetap: satu unit hipotetis "
        f"hanya bila EV terbesar model terhadap odds sintetis minimal {MIN_POSITIVE_EV:.0%}. "
        "Unit/yield hipotetis ada hanya untuk audit di `scenario_metrics.csv`; karena harga "
        "dibuat sendiri dan tidak mewakili bookmaker, angka itu tidak layak dipakai memilih "
        "kandidat atau menyimpulkan profit. File itu memuat metrik semua kandidat, pasar, dan "
        "skenario; `per_league_metrics.csv` memberi rincian liga.",
        "",
        "## Keputusan kandidat",
        "",
    ])
    for market in MARKETS:
        top = leaders.loc[leaders["market"] == market].head(1)
        if top.empty:
            continue
        row = top.iloc[0]
        lines.append(
            f"- **{market}:** `{row['candidate']}` adalah pemimpin screening LogLoss pada "
            f"empat skenario (rata-rata {row['mean_logloss']:.5f}); status tetap "
            "`REFERENCE_ONLY_SCREENING`, bukan kandidat final."
        )
    lines.extend([
        "",
        "Belum ada pemenang final yang aman ditetapkan: semua periode test historis proyek "
        "telah pernah ditinjau, fold ini parsial, dan seluruh odds bersifat simulasi. Pemimpin "
        "di atas dicatat agar riset berikutnya dapat membandingkannya, bukan untuk dipindahkan "
        "ke script utama.",
        "",
        "## Batasan penting",
        "",
        "- Model utama Mode B dilatih dengan fitur odds historis yang berasal dari odds penutupan. "
        "Odds sintetis di sini adalah stress test dan dapat berada di luar distribusi pelatihan.",
        "- Data tidak memiliki harga live/in-play bertimestamp, harga eksekusi, komisi, atau "
        "batas taruhan. Tidak ada taruhan uang yang dilakukan.",
        "- Semua hasil historis berstatus `REFERENCE_ONLY`; perlu paper tracking prospektif "
        "tanpa stake sebelum klaim kesiapan.",
        "",
        "## File hasil",
        "",
        "- `scenario_metrics.csv`: semua kandidat × pasar × skenario, termasuk LogLoss, Brier, "
        "kalibrasi, jumlah sinyal, dan unit/yield hipotetis untuk audit saja.",
        "- `market_leaders.csv` / `scenario_leaders.csv`: pemimpin screening agregat dan per skenario.",
        "- `scenario_ambiguity.csv` / `class_bias.csv`: perbedaan pendapat, bias per kelas, dan "
        "respons kandidat.",
        "- `probability_coherence.csv`: pemeriksaan jumlah probabilitas dan urutan Over 1.5/0.5.",
        "- `modeb_scenario_sensitivity.csv`: perubahan prediksi Mode B saat quote sintetis berubah.",
        "- `synthetic_odds_quotes.csv`: odds sintetis per fixture, pasar, dan skenario.",
        "- `per_league_metrics.csv` dan `manifest.json`: rincian liga, identitas input, hash, "
        "aturan simulasi, serta batasan.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "features_train.csv")
    parser.add_argument("--family-predictions", type=Path,
                        default=DEFAULT_FAMILY_PREDICTIONS)
    parser.add_argument("--feature-predictions", type=Path,
                        default=DEFAULT_FEATURE_PREDICTIONS)
    parser.add_argument("--main-model-dir", type=Path, default=MAIN_MODEL_DIR)
    parser.add_argument("--main-features", type=Path, default=MAIN_FEATURES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
