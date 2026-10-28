#!/usr/bin/env python3
"""
Training + walk-forward validation untuk 6 target pasar.
Model: LightGBM. Baseline: odds implied probability.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import lightgbm as lgb
from sklearn.metrics import (
    accuracy_score, log_loss, brier_score_loss, roc_auc_score
)

BASE = Path("/root/football-predictor")
DATA = BASE / "data"
MODELS = BASE / "models"
LOGS = BASE / "logs"
MODELS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

FEATURES_FILE = DATA / "features_train.csv"

# Train / val / test split (walk-forward)
DEFAULT_TRAIN_END = "2024-06-30"
DEFAULT_VAL_END = "2025-06-30"
TRAIN_END = pd.Timestamp(DEFAULT_TRAIN_END)
VAL_END = pd.Timestamp(DEFAULT_VAL_END)
# test: Date > VAL_END

# Kolom yang BUKAN fitur
EXCLUDE_COLS = {
    "Date", "Div", "Time", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "league_code", "league_name", "season",
    "HomeTeam_canon", "AwayTeam_canon",
    "HomeTeam_folder", "AwayTeam_folder",
    "match_id", "source_file",
    "target_1x2", "target_ou25",
    "target_home_ou05", "target_home_ou15",
    "target_away_ou05", "target_away_ou15",
    # Derived odds probabilities (jadi fitur di mode B, exclude di mode A)
    "odds_pH", "odds_pD", "odds_pA", "odds_pOver25",
    # ---- RAW ODDS -- SELALU EXCLUDE (leakage) ----
    "B365H","B365D","B365A","PSH","PSD","PSA",
    "BWH","BWD","BWA","IWH","IWD","IWA",
    "WHH","WHD","WHA","VCH","VCD","VCA",
    "MaxH","MaxD","MaxA","AvgH","AvgD","AvgA",
    "BFH","BFD","BFA","BFDH","BFDD","BFDA",
    "BVH","BVD","BVA","PPH","PPD","PPA",
    "SKBH","SKBD","SKBA","1XBH","1XBD","1XBA",
    "B365>2.5","B365<2.5","P>2.5","P<2.5",
    "Max>2.5","Max<2.5","Avg>2.5","Avg<2.5",
    "AHh","B365AHH","B365AHA",
}

# Mode A: pure ML -- odds_p juga excluded
ODDS_P_COLS = {"odds_pH", "odds_pD", "odds_pA", "odds_pOver25"}

# ============ WHITELIST (SAFE) ============
# Hanya kolom dengan prefix ini yang BOLEH masuk fitur.
# Semua kolom lain (termasuk semua raw data post-match) otomatis dikecualikan.
SAFE_PREFIXES = (
    "home_form5_", "home_form10_",
    "away_form5_", "away_form10_",
    "home_venue_", "away_venue_",
    "home_rest_", "away_rest_",
    "home_season_", "away_season_",
    "h2h_",
    "diff_",
)
SAFE_EXACT = {"sum_expected_goals"}

# Time decay default
DEFAULT_HALF_LIFE_DAYS = 365

# Baseline columns (untuk eval, bukan fitur)
BASELINE_1X2 = ["odds_pH", "odds_pD", "odds_pA"]
BASELINE_OU25 = ["odds_pOver25"]

LGB_PARAMS = {
    "objective": "multiclass",   # override per-target
    "metric": "multi_logloss",
    "learning_rate": 0.03,
    "num_leaves": 63,
    "max_depth": -1,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 5,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "verbose": -1,
    "seed": 42,
    "num_threads": 4,
}


def metrics_multiclass(y_true, y_prob):
    """y_prob shape (N, 3)."""
    y_pred = y_prob.argmax(axis=1)
    acc = accuracy_score(y_true, y_pred)
    ll = log_loss(y_true, y_prob, labels=[0, 1, 2])
    # multiclass Brier: sum over classes of (p - y_onehot)^2, lalu mean per sample
    n, k = y_prob.shape
    y_oh = np.zeros_like(y_prob)
    y_oh[np.arange(n), y_true] = 1
    brier = float(((y_prob - y_oh) ** 2).sum(axis=1).mean())
    return {"acc": acc, "logloss": ll, "brier": brier, "n": int(len(y_true))}


def metrics_binary(y_true, y_prob):
    """y_prob shape (N,) = prob class 1."""
    y_pred = (y_prob >= 0.5).astype(int)
    acc = accuracy_score(y_true, y_pred)
    ll = log_loss(y_true, np.clip(y_prob, 1e-7, 1 - 1e-7))
    brier = brier_score_loss(y_true, y_prob)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        auc = float("nan")
    return {"acc": acc, "logloss": ll, "brier": brier, "auc": auc, "n": int(len(y_true))}


def devig_1x2(arr):
    """Normalisasi odds_p 1X2 per baris (hapus overround)."""
    arr = np.asarray(arr, dtype=float)
    s = arr.sum(axis=1, keepdims=True)
    s[s == 0] = 1.0
    return arr / s


def train_multiclass_1x2(X_tr, y_tr, X_va, y_va, X_te, y_te, df_te, w_tr=None, name="1x2"):
    print(f"\n=== Training {name} (multiclass 3) ===")
    params = {**LGB_PARAMS, "objective": "multiclass", "num_class": 3,
              "metric": "multi_logloss"}
    dtr = lgb.Dataset(X_tr, label=y_tr, weight=w_tr, free_raw_data=False)
    dva = lgb.Dataset(X_va, label=y_va, reference=dtr, free_raw_data=False)

    model = lgb.train(
        params, dtr, num_boost_round=3000,
        valid_sets=[dtr, dva],
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)],
    )
    print(f"Best iteration: {model.best_iteration}")

    # Prediksi
    prob_va = model.predict(X_va, num_iteration=model.best_iteration)
    prob_te = model.predict(X_te, num_iteration=model.best_iteration)

    m_val = metrics_multiclass(y_va, prob_va)
    m_test = metrics_multiclass(y_te, prob_te)

    # Baseline: odds
    base_va = df_te.iloc[:len(y_va)] if False else None  # placeholder
    # Untuk baseline pakai val set + test set terpisah
    # (disediakan lewat df_va / df_te)
    return model, prob_va, prob_te, m_val, m_test


def train_binary(X_tr, y_tr, X_va, y_va, X_te, y_te, w_tr=None, name="binary"):
    print(f"\n=== Training {name} (binary) ===")
    params = {**LGB_PARAMS, "objective": "binary", "metric": "binary_logloss"}
    dtr = lgb.Dataset(X_tr, label=y_tr, weight=w_tr, free_raw_data=False)
    dva = lgb.Dataset(X_va, label=y_va, reference=dtr, free_raw_data=False)
    model = lgb.train(
        params, dtr, num_boost_round=3000,
        valid_sets=[dtr, dva],
        callbacks=[lgb.early_stopping(100), lgb.log_evaluation(200)],
    )
    print(f"Best iteration: {model.best_iteration}")
    prob_va = model.predict(X_va, num_iteration=model.best_iteration)
    prob_te = model.predict(X_te, num_iteration=model.best_iteration)
    m_val = metrics_binary(y_va, prob_va)
    m_test = metrics_binary(y_te, prob_te)
    return model, prob_va, prob_te, m_val, m_test


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["B"], default="B",
                        help="Production training mode (B only; includes odds-probability features)")
    parser.add_argument("--train-end", default=DEFAULT_TRAIN_END)
    parser.add_argument("--val-end", default=DEFAULT_VAL_END)
    parser.add_argument("--half-life", type=float, default=DEFAULT_HALF_LIFE_DAYS,
                        help="Sample weight half-life in days (default 365). 0 = no decay")
    args = parser.parse_args()
    mode = args.mode
    half_life = args.half_life
    global TRAIN_END, VAL_END
    TRAIN_END = pd.Timestamp(args.train_end)
    VAL_END = pd.Timestamp(args.val_end)
    print(f"=== START training (mode {mode}, half_life={half_life}d) ===")

    df = pd.read_csv(FEATURES_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    print(f"Loaded: {df.shape}")

    # Split walk-forward
    tr_mask = df["Date"] <= TRAIN_END
    va_mask = (df["Date"] > TRAIN_END) & (df["Date"] <= VAL_END)
    te_mask = df["Date"] > VAL_END
    print(f"Train: {tr_mask.sum()}, Val: {va_mask.sum()}, Test: {te_mask.sum()}")

    df_tr = df[tr_mask].copy()
    df_va = df[va_mask].copy()
    df_te = df[te_mask].copy()

    # Fitur = WHITELIST only (aman, tidak ada post-match data)
    feat_cols = []
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        if c in SAFE_EXACT:
            feat_cols.append(c)
            continue
        if c.startswith(SAFE_PREFIXES):
            feat_cols.append(c)
            continue
        # Mode B: izinkan odds_p
        if mode == "B" and c in ODDS_P_COLS:
            feat_cols.append(c)

    # Validasi: tidak ada kolom berbahaya
    forbidden_anywhere = {"FTHG","FTAG","HTHG","HTAG","FTR",
                          "HS","AS","HST","AST","HxG","AxG",
                          "HF","AF","HC","AC","HY","AY","HR","AR"}
    leaked = [c for c in feat_cols if c in forbidden_anywhere]
    if leaked:
        raise SystemExit(f"FATAL: post-match columns leaked to features: {leaked}")

    print(f"Mode {mode}: safe features = {len(feat_cols)}")
    if mode == "B":
        has_odds = [c for c in ODDS_P_COLS if c in feat_cols]
        print(f"  Odds_p in features: {has_odds}")

    X_tr = df_tr[feat_cols].values
    X_va = df_va[feat_cols].values
    X_te = df_te[feat_cols].values

    # ---- Time decay sample weights (HANYA untuk training set) ----
    if half_life > 0:
        ref_date = df_tr["Date"].max()
        age_days = (ref_date - df_tr["Date"]).dt.days.values.astype(float)
        w_tr = np.power(0.5, age_days / half_life)
        print(f"  Sample weights: ref={ref_date.date()}, "
              f"range [{w_tr.min():.4f}, {w_tr.max():.4f}], "
              f"mean={w_tr.mean():.4f}")
    else:
        w_tr = None
        print("  Sample weights: NONE (uniform)")

    results = {}
    predictions_te = {}  # untuk output evaluasi

    # ---------------- 1X2 ----------------
    y_tr = df_tr["target_1x2"].values
    y_va = df_va["target_1x2"].values
    y_te = df_te["target_1x2"].values
    model, p_va, p_te, m_val, m_test = train_multiclass_1x2(
        X_tr, y_tr, X_va, y_va, X_te, y_te, df_te, w_tr=w_tr)
    model.save_model(str(MODELS / f"lgb_1x2_mode{mode}.txt"))
    results["1x2_model"] = {"val": m_val, "test": m_test}

    # Baseline odds
    odds_va = df_va[BASELINE_1X2].values
    odds_te = df_te[BASELINE_1X2].values
    # isi NaN dengan prior uniform
    for arr in (odds_va, odds_te):
        nan = np.isnan(arr).any(axis=1)
        arr[nan] = [1/3, 1/3, 1/3]
    arr = devig_1x2(arr)
    m_base_va = metrics_multiclass(y_va, odds_va)
    m_base_te = metrics_multiclass(y_te, odds_te)
    results["1x2_baseline"] = {"val": m_base_va, "test": m_base_te}

    predictions_te["1x2"] = {
        "prob_model": p_te, "prob_baseline": odds_te, "y": y_te,
        "df": df_te[["Date", "HomeTeam_canon", "AwayTeam_canon"]].reset_index(drop=True),
    }

    # ---------------- OU25 ----------------
    y_tr = df_tr["target_ou25"].values
    y_va = df_va["target_ou25"].values
    y_te = df_te["target_ou25"].values
    model, p_va, p_te, m_val, m_test = train_binary(
        X_tr, y_tr, X_va, y_va, X_te, y_te, w_tr=w_tr, name="OU25")
    model.save_model(str(MODELS / f"lgb_ou25_mode{mode}.txt"))
    results["ou25_model"] = {"val": m_val, "test": m_test}

    base_va = df_va["odds_pOver25"].values.copy()
    base_te = df_te["odds_pOver25"].values.copy()
    # isi NaN dengan base rate training
    train_over_rate = float(df_tr["target_ou25"].mean())
    base_va[np.isnan(base_va)] = train_over_rate
    base_te[np.isnan(base_te)] = train_over_rate
    m_base_va = metrics_binary(y_va, base_va)
    m_base_te = metrics_binary(y_te, base_te)
    results["ou25_baseline"] = {"val": m_base_va, "test": m_base_te}

    predictions_te["ou25"] = {
        "prob_model": p_te, "prob_baseline": base_te, "y": y_te,
    }

    # ---------------- HOME/AWAY O/U 0.5 / 1.5 ----------------
    for target_name, target_col in [
        ("home_ou05", "target_home_ou05"),
        ("home_ou15", "target_home_ou15"),
        ("away_ou05", "target_away_ou05"),
        ("away_ou15", "target_away_ou15"),
    ]:
        y_tr = df_tr[target_col].values
        y_va = df_va[target_col].values
        y_te = df_te[target_col].values
        model, p_va, p_te, m_val, m_test = train_binary(
            X_tr, y_tr, X_va, y_va, X_te, y_te, w_tr=w_tr, name=target_name)
        model.save_model(str(MODELS / f"lgb_{target_name}_mode{mode}.txt"))
        results[f"{target_name}_model"] = {"val": m_val, "test": m_test}

        # Baseline = base rate dari train
        base_rate = float(y_tr.mean())
        base_va = np.full(len(y_va), base_rate)
        base_te = np.full(len(y_te), base_rate)
        m_base_va = metrics_binary(y_va, base_va)
        m_base_te = metrics_binary(y_te, base_te)
        results[f"{target_name}_baseline"] = {"val": m_base_va, "test": m_base_te}
        predictions_te[target_name] = {
            "prob_model": p_te, "prob_baseline": base_te, "y": y_te,
        }

    # ---------------- Simpan hasil ----------------
    with open(MODELS / f"evaluation_mode{mode}.json", "w") as f:
        json.dump(results, f, indent=2)

    # Human readable
    lines = [f"# Model Evaluation -- Mode {mode}\n"]
    lines.append(f"Generated: {datetime.now().isoformat()}\n")
    lines.append(f"\nTrain range: <= {TRAIN_END.date()}")
    lines.append(f"Val range: {TRAIN_END.date()} .. {VAL_END.date()}")
    lines.append(f"Test range: > {VAL_END.date()}")
    lines.append(f"\nN train: {int(tr_mask.sum())}, N val: {int(va_mask.sum())}, N test: {int(te_mask.sum())}")
    lines.append(f"\nFeatures: {len(feat_cols)}\n")

    for key in ["1x2", "ou25", "home_ou05", "home_ou15", "away_ou05", "away_ou15"]:
        mkey = f"{key}_model"
        bkey = f"{key}_baseline"
        lines.append(f"\n## {key.upper()}\n")
        lines.append("| Set | Metric | Model | Baseline | Δ (Model - Baseline) |")
        lines.append("|---|---|---|---|---|")
        for split in ["val", "test"]:
            for metric in results[mkey][split].keys():
                if metric == "n":
                    continue
                mv = results[mkey][split][metric]
                mb = results[bkey][split].get(metric, float("nan"))
                # Untuk metric "higher better": acc, auc. Untuk "lower better": logloss, brier.
                diff = mv - mb
                if metric in ("acc", "auc"):
                    verdict = "BETTER" if diff > 0 else ("worse" if diff < 0 else "same")
                else:
                    verdict = "BETTER" if diff < 0 else ("worse" if diff > 0 else "same")
                lines.append(f"| {split} | {metric} | {mv:.4f} | {mb:.4f} | {diff:+.4f} ({verdict}) |")

    (MODELS / f"evaluation_mode{mode}.md").write_text("\n".join(lines))
    print("\n=== DONE ===")
    print(f"Saved: models/evaluation_mode{mode}.md, models/evaluation_mode{mode}.json")


if __name__ == "__main__":
    main()
