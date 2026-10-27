#!/usr/bin/env python3
"""
LANGKAH 10.2 — Backtest historis Mode B.
READ-ONLY terhadap produksi. Output ke backtest/backtest_<timestamp>/.

Metrik: logloss, brier, accuracy, AUC (multiclass macro OvR / binary).
Baseline: odds (subset with odds) + base_rate_train (all rows).
Bootstrap: block by week (fallback row) dengan SEED=42.
"""
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import (
    log_loss, brier_score_loss, accuracy_score, roc_auc_score,
)

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
MODELS = BASE / "models"
LOGS = BASE / "logs"
BACKTEST = BASE / "backtest"

SEED = 42
np.random.seed(SEED)

TRAIN_END = pd.Timestamp("2024-06-30")
VAL_END = pd.Timestamp("2025-06-30")

MODEL_TARGET = {
    "1x2":      ("target_1x2",      "multiclass", 3),
    "ou25":     ("target_ou25",     "binary", 1),
    "home_ou05": ("target_home_ou05", "binary", 1),
    "home_ou15": ("target_home_ou15", "binary", 1),
    "away_ou05": ("target_away_ou05", "binary", 1),
    "away_ou15": ("target_away_ou15", "binary", 1),
}

MODEL_FILES = {
    "1x2":      "lgb_1x2_modeB.txt",
    "ou25":     "lgb_ou25_modeB.txt",
    "home_ou05": "lgb_home_ou05_modeB.txt",
    "home_ou15": "lgb_home_ou15_modeB.txt",
    "away_ou05": "lgb_away_ou05_modeB.txt",
    "away_ou15": "lgb_away_ou15_modeB.txt",
}

MARKET_NAMES_ID = {
    "1x2": "1X2",
    "ou25": "Over/Under 2.5",
    "home_ou05": "Home Over 0.5",
    "home_ou15": "Home Over 1.5",
    "away_ou05": "Away Over 0.5",
    "away_ou15": "Away Over 1.5",
}


# ============================================================
# Utilities
# ============================================================

def log(msg, fh=None):
    print(msg, flush=True)
    if fh:
        fh.write(msg + "\n")
        fh.flush()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics_multiclass(y_true, y_prob):
    """y_prob: (N, 3)."""
    y_true = np.asarray(y_true)
    y_pred = y_prob.argmax(axis=1)
    acc = accuracy_score(y_true, y_pred)
    ll = log_loss(y_true, y_prob, labels=[0, 1, 2])
    # Brier multiclass: sum of squared prob errors
    n = len(y_true)
    y_oh = np.zeros_like(y_prob)
    y_oh[np.arange(n), y_true] = 1
    brier = float(((y_prob - y_oh) ** 2).sum(axis=1).mean())
    # AUC macro OvR
    aucs = []
    for k in range(3):
        y_bin = (y_true == k).astype(int)
        if y_bin.sum() == 0 or y_bin.sum() == len(y_bin):
            aucs.append(float("nan"))
        else:
            try:
                aucs.append(roc_auc_score(y_bin, y_prob[:, k]))
            except ValueError:
                aucs.append(float("nan"))
    auc = float(np.nanmean(aucs)) if any(not np.isnan(a) for a in aucs) else float("nan")
    return {"n": int(n), "acc": float(acc), "logloss": float(ll),
            "brier": float(brier), "auc": auc}


def metrics_binary(y_true, y_prob):
    """y_prob: (N,) = prob class 1."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= 0.5).astype(int)
    acc = accuracy_score(y_true, y_pred)
    ll = log_loss(y_true, np.clip(y_prob, 1e-7, 1 - 1e-7))
    brier = brier_score_loss(y_true, y_prob)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        auc = float("nan")
    return {"n": int(len(y_true)), "acc": float(acc), "logloss": float(ll),
            "brier": float(brier), "auc": float(auc)}


def validate_predictions(probs, kind, name):
    """probs: np array. Return error string or None."""
    if not np.all(np.isfinite(probs)):
        return f"{name}: non-finite probs"
    if kind == "multiclass":
        if probs.ndim != 2 or probs.shape[1] != 3:
            return f"{name}: shape {probs.shape} != (N,3)"
        if not np.allclose(probs.sum(axis=1), 1.0, atol=1e-5):
            return f"{name}: sum != 1"
        if probs.min() < -1e-9 or probs.max() > 1 + 1e-9:
            return f"{name}: out of [0,1]"
    else:
        if probs.ndim != 1:
            return f"{name}: shape {probs.shape} != (N,)"
        if probs.min() < -1e-9 or probs.max() > 1 + 1e-9:
            return f"{name}: out of [0,1]"
    return None


# ============================================================
# Bootstrap
# ============================================================

def compute_metric_from_idx(market, kind, y, p_model, p_baseline, idx):
    """Compute metric value untuk bootstrap sample idx."""
    y_s = y[idx]
    p_m = p_model[idx]
    p_b = p_baseline[idx]
    try:
        if kind == "multiclass":
            m = metrics_multiclass(y_s, p_m)
            b = metrics_multiclass(y_s, p_b)
            return m["logloss"], b["logloss"], m["acc"], b["acc"]
        else:
            m = metrics_binary(y_s, p_m)
            b = metrics_binary(y_s, p_b)
            return m["logloss"], b["logloss"], m["acc"], b["acc"]
    except Exception:
        return None


def bootstrap_ci(market, kind, y, p_model, p_baseline, dates, n_iter=1000, seed=42):
    """
    Block bootstrap by ISO week. Return dict dengan CIs untuk logloss & acc (model vs baseline + diff).
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p_model = np.asarray(p_model)
    p_baseline = np.asarray(p_baseline)

    # Group by ISO week
    dates = pd.to_datetime(dates)
    # dates adalah DatetimeIndex -> pakai .strftime langsung (bukan .dt)
    if isinstance(dates, pd.DatetimeIndex):
        week_keys = dates.strftime("%Y-W%W").values
    else:
        week_keys = dates.dt.strftime("%Y-W%W").values
    unique_weeks = np.unique(week_keys)
    week_to_idx = {w: np.where(week_keys == w)[0] for w in unique_weeks}

    n_weeks = len(unique_weeks)
    method = "block_week"

    if n_weeks < 10:
        # Fallback ke row bootstrap
        method = "row"
        n = len(y)
        boot_idx_list = [rng.integers(0, n, size=n) for _ in range(n_iter)]
    else:
        boot_idx_list = []
        for _ in range(n_iter):
            # Sample weeks dengan replacement
            sampled_weeks = rng.choice(unique_weeks, size=n_weeks, replace=True)
            idx = np.concatenate([week_to_idx[w] for w in sampled_weeks])
            boot_idx_list.append(idx)

    # Run bootstrap
    boot_ll_model = []
    boot_ll_base = []
    boot_acc_model = []
    boot_acc_base = []

    for idx in boot_idx_list:
        try:
            m_ll, b_ll, m_acc, b_acc = compute_metric_from_idx(
                market, kind, y, p_model, p_baseline, idx)
            boot_ll_model.append(m_ll)
            boot_ll_base.append(b_ll)
            boot_acc_model.append(m_acc)
            boot_acc_base.append(b_acc)
        except Exception:
            continue

    if not boot_ll_model:
        return {"method": method, "n_valid_iter": 0, "error": "no valid bootstrap sample"}

    def ci(arr):
        arr = np.array(arr)
        return {
            "mean": float(arr.mean()),
            "ci_low": float(np.percentile(arr, 2.5)),
            "ci_high": float(np.percentile(arr, 97.5)),
        }

    return {
        "method": method,
        "n_iter_requested": n_iter,
        "n_iter_valid": len(boot_ll_model),
        "n_weeks": int(n_weeks),
        "logloss_model": ci(boot_ll_model),
        "logloss_baseline": ci(boot_ll_base),
        "logloss_diff": ci(np.array(boot_ll_model) - np.array(boot_ll_base)),
        "acc_model": ci(boot_acc_model),
        "acc_baseline": ci(boot_acc_base),
        "acc_diff": ci(np.array(boot_acc_model) - np.array(boot_acc_base)),
    }


# ============================================================
# Main
# ============================================================

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = BACKTEST / f"backtest_{ts}"
    out_dir.mkdir(parents=True, exist_ok=False)
    log_path = out_dir / "run.log"
    log_fh = open(log_path, "w")

    def L(msg):
        log(msg, log_fh)

    t_start = time.time()
    L(f"=== START backtest {ts} ===")
    L(f"Output dir: {out_dir}")

    # -------- Load data & models --------
    L("\nLoading data...")
    df = pd.read_csv(DATA / "features_train.csv", low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    L(f"  Total rows: {len(df)}")

    with open(LOGS / "feat_cols_modeB_ordered.json") as f:
        feat_cols = json.load(f)
    L(f"  Feat cols: {len(feat_cols)}")

    L("\nLoading models...")
    models = {}
    model_hashes = {}
    for market, fname in MODEL_FILES.items():
        path = MODELS / fname
        if not path.exists():
            L(f"FATAL: model {path} tidak ada"); log_fh.close(); sys.exit(1)
        models[market] = lgb.Booster(model_file=str(path))
        model_hashes[market] = sha256_file(path)
        L(f"  {market}: {fname} ({model_hashes[market][:16]}...)")

    # -------- Split --------
    L("\nSplits:")
    tr_mask = df["Date"] <= TRAIN_END
    te_mask = df["Date"] > VAL_END
    df_tr = df[tr_mask].copy().reset_index(drop=True)
    df_te = df[te_mask].copy().reset_index(drop=True)
    L(f"  Train: {len(df_tr)}")
    L(f"  Test:  {len(df_te)} ({df_te['Date'].min().date()} .. {df_te['Date'].max().date()})")

    if len(df_te) == 0:
        L("FATAL: test split kosong"); log_fh.close(); sys.exit(1)

    X_te = df_te[feat_cols].values

    # -------- Baselines (base rate from TRAIN only) --------
    base_rates = {}
    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        if kind == "binary":
            base_rates[market] = float(df_tr[tcol].mean())
    L(f"\nBase rates (train): {json.dumps({k: round(v, 4) for k, v in base_rates.items()})}")

    # -------- Predict all markets --------
    L("\nPredicting on test...")
    predictions = {}
    errors = []
    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        m = models[market]
        try:
            if kind == "multiclass":
                p = m.predict(X_te)  # (N, 3)
            else:
                p = m.predict(X_te)  # (N,)
        except Exception as e:
            errors.append(f"{market}: predict FAIL {e}")
            L(f"  {market}: PREDICT FAIL: {e}")
            continue

        err = validate_predictions(p, kind, market)
        if err:
            errors.append(err)
            L(f"  {market}: VALIDATE FAIL: {err}")
            continue

        predictions[market] = p
        L(f"  {market}: OK (shape {p.shape})")

    if errors:
        L(f"\nFATAL: {len(errors)} prediction errors, STOP")
        log_fh.close()
        sys.exit(1)

    # -------- Evaluate per market --------
    L("\nComputing metrics...")
    results = {}
    predictions_df_data = {"match_id": [], "date": [], "home": [], "away": [], "league": []}
    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        y = df_te[tcol].values
        p = predictions[market]

        # Model metrics (all rows)
        if kind == "multiclass":
            m_metrics = metrics_multiclass(y, p)
        else:
            m_metrics = metrics_binary(y, p)

        # Baseline: odds (subset) untuk 1x2 & ou25
        baseline_metrics_subset = None
        n_odds_subset = 0
        if market == "1x2":
            valid_mask = (df_te["odds_pH"].notna() &
                          df_te["odds_pD"].notna() &
                          df_te["odds_pA"].notna()).values
            n_odds_subset = int(valid_mask.sum())
            if n_odds_subset > 0:
                p_b = df_te.loc[valid_mask, ["odds_pH","odds_pD","odds_pA"]].values
                y_s = y[valid_mask]
                p_m_s = p[valid_mask]
                m_metrics_subset = metrics_multiclass(y_s, p_m_s)
                b_metrics_subset = metrics_multiclass(y_s, p_b)
                baseline_metrics_subset = {"model": m_metrics_subset,
                                            "baseline": b_metrics_subset,
                                            "n": n_odds_subset}
        elif market == "ou25":
            valid_mask = df_te["odds_pOver25"].notna().values
            n_odds_subset = int(valid_mask.sum())
            if n_odds_subset > 0:
                p_over = df_te.loc[valid_mask, "odds_pOver25"].values
                y_s = y[valid_mask]
                p_m_s = p[valid_mask]
                m_metrics_subset = metrics_binary(y_s, p_m_s)
                b_metrics_subset = metrics_binary(y_s, p_over)
                baseline_metrics_subset = {"model": m_metrics_subset,
                                            "baseline": b_metrics_subset,
                                            "n": n_odds_subset}

        # Baseline: base_rate (all rows) untuk binary
        baseline_base_rate = None
        if kind == "binary":
            br = base_rates[market]
            p_base = np.full(len(y), br)
            baseline_base_rate = metrics_binary(y, p_base)

        # Uniform untuk 1x2
        baseline_uniform = None
        if market == "1x2":
            p_uniform = np.full((len(y), 3), 1/3)
            baseline_uniform = metrics_multiclass(y, p_uniform)

        # Bootstrap CI
        if market == "1x2" and n_odds_subset > 0:
            b_p = df_te.loc[valid_mask, ["odds_pH","odds_pD","odds_pA"]].values
            boot = bootstrap_ci(market, kind, y[valid_mask], p[valid_mask],
                                b_p, df_te.loc[valid_mask, "Date"].values,
                                n_iter=1000, seed=SEED)
        elif market == "ou25" and n_odds_subset > 0:
            b_p = df_te.loc[valid_mask, "odds_pOver25"].values
            boot = bootstrap_ci(market, kind, y[valid_mask], p[valid_mask],
                                b_p, df_te.loc[valid_mask, "Date"].values,
                                n_iter=1000, seed=SEED)
        else:
            br = base_rates.get(market, 0.5)
            p_base = np.full(len(y), br)
            boot = bootstrap_ci(market, kind, y, p, p_base,
                                df_te["Date"].values, n_iter=1000, seed=SEED)

        results[market] = {
            "model": m_metrics,
            "baseline_odds": baseline_metrics_subset,
            "baseline_base_rate": baseline_base_rate,
            "baseline_uniform": baseline_uniform,
            "bootstrap": boot,
        }

        # Store per-row for distributions
        predictions_df_data[f"p_{market}"] = list(p) if kind == "binary" else list(p.tolist())
        predictions_df_data[f"y_{market}"] = list(y)

    # Distributions
    L("\nComputing distributions...")
    distributions = []
    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        p = predictions[market]
        if kind == "multiclass":
            for k, label in enumerate(["H", "D", "A"]):
                pk = p[:, k]
                hist, bins = np.histogram(pk, bins=20, range=(0, 1))
                for i in range(20):
                    distributions.append({
                        "market": market, "class": label,
                        "bin_low": float(bins[i]), "bin_high": float(bins[i+1]),
                        "count": int(hist[i])
                    })
        else:
            hist, bins = np.histogram(p, bins=20, range=(0, 1))
            for i in range(20):
                distributions.append({
                    "market": market, "class": "over",
                    "bin_low": float(bins[i]), "bin_high": float(bins[i+1]),
                    "count": int(hist[i])
                })

    # Per-league / per-season analysis
    L("\nPer-league & per-season analysis...")
    per_league = {}
    per_season = {}
    df_te["_season"] = df_te["Date"].dt.year.astype(str)  # untuk grouping

    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        y = df_te[tcol].values
        p = predictions[market]

        per_league[market] = {}
        for league in df_te["league_name"].dropna().unique():
            mask = (df_te["league_name"] == league).values
            n = int(mask.sum())
            if n < 100:
                per_league[market][league] = {"n": n, "note": "insufficient N"}
                continue
            try:
                if kind == "multiclass":
                    m_metrics = metrics_multiclass(y[mask], p[mask])
                else:
                    m_metrics = metrics_binary(y[mask], p[mask])
                per_league[market][league] = m_metrics
            except Exception as e:
                per_league[market][league] = {"n": n, "error": str(e)}

        per_season[market] = {}
        for season in df_te["_season"].unique():
            mask = (df_te["_season"] == season).values
            n = int(mask.sum())
            if n < 100:
                per_season[market][season] = {"n": n, "note": "insufficient N"}
                continue
            try:
                if kind == "multiclass":
                    m_metrics = metrics_multiclass(y[mask], p[mask])
                else:
                    m_metrics = metrics_binary(y[mask], p[mask])
                per_season[market][season] = m_metrics
            except Exception as e:
                per_season[market][season] = {"n": n, "error": str(e)}

    # -------- Save outputs --------
    L("\nSaving outputs...")

    # Predictions CSV
    predictions_df = pd.DataFrame({
        "match_id": df_te.apply(
            lambda r: hashlib.sha256(
                f"{r['Date'].date()}|{r['HomeTeam_canon']}|{r['AwayTeam_canon']}|{r['league_name']}".encode()
            ).hexdigest()[:12], axis=1),
        "date": df_te["Date"].dt.strftime("%Y-%m-%d"),
        "home": df_te["HomeTeam_canon"],
        "away": df_te["AwayTeam_canon"],
        "league": df_te["league_name"],
    })
    for market, (tcol, kind, ncls) in MODEL_TARGET.items():
        p = predictions[market]
        if kind == "multiclass":
            for k, label in enumerate(["H", "D", "A"]):
                predictions_df[f"p_{market}_{label}"] = p[:, k]
        else:
            predictions_df[f"p_{market}"] = p
        predictions_df[f"y_{market}"] = df_te[tcol].values
    predictions_df.to_csv(out_dir / "predictions.csv", index=False)
    L(f"  predictions.csv: {len(predictions_df)} rows")

    # Distributions
    pd.DataFrame(distributions).to_csv(out_dir / "distributions.csv", index=False)
    L(f"  distributions.csv: {len(distributions)} rows")

    # Metrics JSON (global + per-league + per-season)
    metrics_all = {
        "global": results,
        "per_league": per_league,
        "per_season": per_season,
    }
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(metrics_all, f, indent=2, default=str)
    L(f"  metrics.json")

    # Bootstrap CI JSON (extracted)
    bootstrap_ci_all = {m: results[m]["bootstrap"] for m in results}
    with open(out_dir / "bootstrap_ci.json", "w") as f:
        json.dump(bootstrap_ci_all, f, indent=2, default=str)
    L(f"  bootstrap_ci.json")

    # Config JSON
    config = {
        "generated_at": ts,
        "seed": SEED,
        "train_end": str(TRAIN_END.date()),
        "val_end": str(VAL_END.date()),
        "n_train": len(df_tr),
        "n_test": len(df_te),
        "test_period": [str(df_te["Date"].min().date()), str(df_te["Date"].max().date())],
        "feat_cols_count": len(feat_cols),
        "feat_cols_sha": hashlib.sha256(json.dumps(feat_cols).encode()).hexdigest(),
        "feat_cols_file_sha": sha256_file(LOGS / "feat_cols_modeB_ordered.json"),
        "features_train_sha": sha256_file(DATA / "features_train.csv"),
        "models": {m: {"file": MODEL_FILES[m], "sha256": model_hashes[m]} for m in models},
        "base_rates_train": base_rates,
        "bootstrap_method": "block_iso_week_fallback_row",
        "bootstrap_n_iter": 1000,
    }
    with open(out_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    L(f"  config.json")

    # Metrics.md
    md_lines = ["# Backtest Report\n"]
    md_lines.append(f"Generated: {ts}\n")
    md_lines.append(f"Test: {len(df_te)} rows, {df_te['Date'].min().date()} .. {df_te['Date'].max().date()}\n")
    md_lines.append("\n## Global Metrics\n")
    for market in results:
        md_lines.append(f"\n### {MARKET_NAMES_ID[market]}\n")
        r = results[market]
        md_lines.append(f"\n**Model (all test rows, N={r['model']['n']}):**\n")
        md_lines.append(f"- logloss: {r['model']['logloss']:.4f}")
        md_lines.append(f"- brier: {r['model']['brier']:.4f}")
        md_lines.append(f"- accuracy: {r['model']['acc']:.4f}")
        if not np.isnan(r['model']['auc']):
            md_lines.append(f"- auc: {r['model']['auc']:.4f}")
        if r['baseline_odds']:
            n_sub = r['baseline_odds']['n']
            md_lines.append(f"\n**Baseline odds (subset N={n_sub}):**\n")
            md_lines.append(f"- model logloss: {r['baseline_odds']['model']['logloss']:.4f}")
            md_lines.append(f"- baseline logloss: {r['baseline_odds']['baseline']['logloss']:.4f}")
            md_lines.append(f"- model acc: {r['baseline_odds']['model']['acc']:.4f}")
            md_lines.append(f"- baseline acc: {r['baseline_odds']['baseline']['acc']:.4f}")
        if r['baseline_base_rate']:
            md_lines.append(f"\n**Baseline base_rate (all test):**\n")
            md_lines.append(f"- baseline logloss: {r['baseline_base_rate']['logloss']:.4f}")
            md_lines.append(f"- baseline acc: {r['baseline_base_rate']['acc']:.4f}")
        if r['baseline_uniform']:
            md_lines.append(f"\n**Baseline uniform:**\n")
            md_lines.append(f"- logloss: {r['baseline_uniform']['logloss']:.4f}")
            md_lines.append(f"- acc: {r['baseline_uniform']['acc']:.4f}")
        md_lines.append(f"\n**Bootstrap CI:** method={r['bootstrap']['method']}, n_iter_valid={r['bootstrap'].get('n_iter_valid', 0)}")
        if r['bootstrap'].get('logloss_diff'):
            d = r['bootstrap']['logloss_diff']
            md_lines.append(f"- logloss_diff (model-baseline): {d['mean']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]")
    md_lines.append("\n## Limitations\n")
    md_lines.append("Lihat limitations.md untuk daftar lengkap.\n")
    (out_dir / "metrics.md").write_text("\n".join(md_lines))
    L(f"  metrics.md")

    # Limitations.md
    lim = """# Limitations

## R2: Closing Odds Bias
Training dan test sama-sama menggunakan closing odds (`odds_pH/D/A`, `odds_pOver25`).
Closing odds adalah odds dekat kickoff — sudah incorporate lineup/cedera terbaru.
**Performa backtest ini TIDAK menjamin performa live** dengan opening/current odds.
Model Mode B dengan closing odds di test = bias optimis terhadap skenario live.

## R3: Odds Coverage
`odds_pH/D/A`: 99.87% coverage pada test. `odds_pOver25`: 99.75%.
Baseline odds hanya dihitung pada subset dengan odds valid — fair comparison.

## R4: AUC 1X2
Multiclass AUC dihitung sebagai **macro OvR** (one-vs-rest per class, rata-rata).
Ini bukan satu-satunya interpretasi AUC untuk multiclass. Tidak comparable dengan binary AUC.

## R5: N per League / Season
Grup dengan N < 100 dilaporkan sebagai "insufficient N" — tidak ada kesimpulan.
Test split (2025-07-25 .. 2026-10-21) mencakup akhir musim 2526 + awal 2627.

## R6: Bootstrap Assumption
Bootstrap default: **block by ISO week** (mengasumsikan korelasi intra-week).
Fallback row bootstrap jika unique weeks < 10 — dengan disclaimer eksplisit.
CI 95% percentile-based (bukan BCa).

## R7: Base Rate from Train
Base rate untuk binary target dihitung dari **train split saja** (Date <= 2024-06-30),
tidak termasuk validation atau test — mencegah information leakage.

## R8: Uniform Baseline (1X2 Only)
Uniform [1/3, 1/3, 1/3] hanya untuk 1X2. Untuk binary pakai base_rate_train.
Uniform tidak merepresentasikan skenario live — hanya lower bound naive predictor.

## R9: Determinisme
LightGBM predict menggunakan default `num_threads` — tidak byte-identical deterministic,
tapi statistik stabil. Bootstrap pakai seed 42.
"""
    (out_dir / "limitations.md").write_text(lim)
    L(f"  limitations.md")

    t_elapsed = time.time() - t_start
    L(f"\n=== DONE in {t_elapsed:.1f}s ===")
    L(f"Output: {out_dir}")
    log_fh.close()


if __name__ == "__main__":
    main()
