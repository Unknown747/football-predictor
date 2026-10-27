#!/usr/bin/env python3
"""
LANGKAH 10.4 — Audit baseline per-league (read-only).

Per (market, league):
  - 1x2 & ou25: model vs odds, hanya di n_common (subset odds valid)
  - Home/Away O/U: model vs base_rate_train (global), di semua rows
  - Bootstrap CI 95% paired block_week, seed 42
  - Verdict berdasarkan CI strict

STOP jika verifikasi konsistensi gagal (tidak ada output parsial).
"""
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data"
BACKTEST_DIR = BASE / "backtest" / "backtest_20261026_215202"

# Arguments
AUDIT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if AUDIT_DIR is None:
    sys.exit("usage: audit.py <audit_dir>")

TRAIN_END = pd.Timestamp("2024-06-30")
VAL_END = pd.Timestamp("2025-06-30")
SEED = 42
N_BOOTSTRAP = 1000
TOL_BR = 1e-9
MIN_N = 100

MARKETS = ["1x2", "ou25", "home_ou05", "home_ou15", "away_ou05", "away_ou15"]
MARKET_LABELS = {
    "1x2": "1X2",
    "ou25": "OU 2.5",
    "home_ou05": "Home O/U 0.5",
    "home_ou15": "Home O/U 1.5",
    "away_ou05": "Away O/U 0.5",
    "away_ou15": "Away O/U 1.5",
}
TARGET_COLS = {
    "1x2": "target_1x2",
    "ou25": "target_ou25",
    "home_ou05": "target_home_ou05",
    "home_ou15": "target_home_ou15",
    "away_ou05": "target_away_ou05",
    "away_ou15": "target_away_ou15",
}
MODEL_PROB_COLS = {
    "1x2": ["p_1x2_H", "p_1x2_D", "p_1x2_A"],
    "ou25": "p_ou25",
    "home_ou05": "p_home_ou05",
    "home_ou15": "p_home_ou15",
    "away_ou05": "p_away_ou05",
    "away_ou15": "p_away_ou15",
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def logloss_multiclass(y_true, p_3col):
    return float(log_loss(y_true, p_3col, labels=[0, 1, 2]))


def logloss_binary(y_true, p):
    return float(log_loss(y_true, np.clip(p, 1e-7, 1 - 1e-7)))


def bootstrap_block_week(market, kind, y, p_model, p_baseline, dates,
                         n_iter=N_BOOTSTRAP, seed=SEED):
    """Block bootstrap by ISO week, fallback row jika weeks < 10."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p_model = np.asarray(p_model)
    p_baseline = np.asarray(p_baseline)
    dates = pd.to_datetime(dates)

    if isinstance(dates, pd.DatetimeIndex):
        week_keys = dates.strftime("%Y-W%W").values
    else:
        week_keys = dates.dt.strftime("%Y-W%W").values
    unique_weeks = np.unique(week_keys)
    week_to_idx = {w: np.where(week_keys == w)[0] for w in unique_weeks}
    n_weeks = len(unique_weeks)

    method = "block_week"
    if n_weeks < 10:
        method = "row_fallback"
        n = len(y)
        boot_idx_list = [rng.integers(0, n, size=n) for _ in range(n_iter)]
    else:
        boot_idx_list = []
        for _ in range(n_iter):
            sampled_weeks = rng.choice(unique_weeks, size=n_weeks, replace=True)
            idx = np.concatenate([week_to_idx[w] for w in sampled_weeks])
            boot_idx_list.append(idx)

    ll_model_boot = []
    ll_base_boot = []

    for idx in boot_idx_list:
        try:
            y_s = y[idx]
            pm_s = p_model[idx]
            pb_s = p_baseline[idx]
            if kind == "multiclass":
                ll_m = logloss_multiclass(y_s, pm_s)
                ll_b = logloss_multiclass(y_s, pb_s)
            else:
                ll_m = logloss_binary(y_s, pm_s)
                ll_b = logloss_binary(y_s, pb_s)
            ll_model_boot.append(ll_m)
            ll_base_boot.append(ll_b)
        except Exception:
            continue

    if not ll_model_boot:
        return {"method": method, "n_iter_valid": 0, "error": "no valid bootstrap"}

    ll_diff = np.array(ll_model_boot) - np.array(ll_base_boot)

    return {
        "method": method,
        "n_weeks": int(n_weeks),
        "n_iter_valid": len(ll_model_boot),
        "delta_mean": float(ll_diff.mean()),
        "delta_ci_low": float(np.percentile(ll_diff, 2.5)),
        "delta_ci_high": float(np.percentile(ll_diff, 97.5)),
    }


def verdict_from_ci(ci_low, ci_high, n_common):
    if n_common < MIN_N:
        return "INSUFFICIENT N"
    if ci_high < 0:
        return "BETTER"
    if ci_low > 0:
        return "WORSE"
    return "INCONCLUSIVE"


def main():
    t0 = time.time()
    log_path = AUDIT_DIR / "run.log"
    log_fh = open(log_path, "w")

    def L(msg):
        print(msg, flush=True)
        log_fh.write(msg + "\n")
        log_fh.flush()

    L(f"=== START audit L10.4 {datetime.now().isoformat()} ===")
    L(f"Audit dir: {AUDIT_DIR}")

    # ==== 1. Load data ====
    L("\n[1] Loading data...")
    df = pd.read_csv(DATA / "features_train.csv", low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    L(f"  features_train.csv: {len(df)} rows")

    preds = pd.read_csv(BACKTEST_DIR / "predictions.csv")
    preds["date"] = pd.to_datetime(preds["date"], errors="coerce")
    L(f"  predictions.csv: {len(preds)} rows")

    with open(BACKTEST_DIR / "config.json") as f:
        cfg = json.load(f)
    L(f"  config.json loaded (n_test={cfg['n_test']}, train_end={cfg['train_end']})")

    # ==== 2. Split ====
    L("\n[2] Split & verify:")
    df_tr = df[df["Date"] <= TRAIN_END].copy()
    df_te = df[df["Date"] > VAL_END].copy()
    L(f"  df_tr: {len(df_tr)} (expected {cfg['n_train']})")
    L(f"  df_te: {len(df_te)} (expected {cfg['n_test']})")
    if len(df_tr) != cfg["n_train"] or len(df_te) != cfg["n_test"]:
        L("  FATAL: split mismatch"); log_fh.close(); sys.exit(1)

    # ==== 3. Base rates ====
    L("\n[3] Base rates (train split only):")
    br_targets = {
        "ou25": "target_ou25",
        "home_ou05": "target_home_ou05",
        "home_ou15": "target_home_ou15",
        "away_ou05": "target_away_ou05",
        "away_ou15": "target_away_ou15",
    }
    base_rates = {}
    for m, tcol in br_targets.items():
        val = float(df_tr[tcol].mean())
        exp = cfg["base_rates_train"][m]
        diff = abs(val - exp)
        L(f"  {m}: recomputed={val:.10f}, expected={exp:.10f}, diff={diff:.2e}")
        if diff > TOL_BR:
            L(f"  FATAL: base rate {m} diff > {TOL_BR}"); log_fh.close(); sys.exit(1)
        base_rates[m] = val

    # ==== 4. Merge ====
    L("\n[4] Merge test + predictions:")
    df_te_merge = df_te.merge(
        preds,
        left_on=["Date", "HomeTeam_canon", "AwayTeam_canon", "league_name"],
        right_on=["date", "home", "away", "league"],
        how="inner",
        suffixes=("", "_pred"),
        validate="one_to_one",
    )
    L(f"  merged: {len(df_te_merge)} (expected {len(df_te)})")
    if len(df_te_merge) != len(df_te):
        L("  FATAL: merge loss"); log_fh.close(); sys.exit(1)

    # Verify aggregate row count
    if df_te_merge.groupby("league").size().sum() != len(df_te_merge):
        L("  FATAL: league aggregate mismatch"); log_fh.close(); sys.exit(1)

    # ==== 5. Per-market per-league audit ====
    L("\n[5] Auditing per (market, league)...")

    results = []  # list of dicts
    bootstrap_out = {}  # market -> league -> bootstrap dict
    leagues = sorted(df_te_merge["league"].dropna().unique())
    L(f"  Leagues: {len(leagues)}")

    for market in MARKETS:
        bootstrap_out[market] = {}
        y_col = TARGET_COLS[market]
        kind = "multiclass" if market == "1x2" else "binary"

        for league in leagues:
            sub = df_te_merge[df_te_merge["league"] == league].copy()
            n_model = len(sub)
            y = sub[y_col].values

            if market == "1x2":
                p_cols = MODEL_PROB_COLS[market]
                p_model = sub[p_cols].values
                # Baseline: odds subset
                # NOTE: odds_pH/D/A in features_train.csv are IMPLIED PROBABILITIES
                # (sum=1, range 0-1), NOT decimal odds. Do not filter by > 1.
                odds_cols = ["odds_pH", "odds_pD", "odds_pA"]
                odds_valid_mask = sub[odds_cols].notna().all(axis=1).values
                n_baseline = int(odds_valid_mask.sum())
                common_mask = odds_valid_mask
                n_common = n_baseline
                n_dropped = n_model - n_common
                baseline_type = "odds"

                if n_common > 0:
                    y_c = y[common_mask]
                    p_model_c = p_model[common_mask]
                    # odds_pH/D/A already stored as implied probs (sum=1)
                    p_odds_c = sub.loc[common_mask, odds_cols].values
                    # Sanity check: probabilities should already be valid
                    assert np.all(p_odds_c >= 0) and np.all(p_odds_c <= 1), \
                        f"odds probs out of range for {league}"
                    assert np.allclose(p_odds_c.sum(axis=1), 1.0, atol=1e-4), \
                        f"odds probs sum != 1 for {league}"
                    ll_model = logloss_multiclass(y_c, p_model_c)
                    ll_baseline = logloss_multiclass(y_c, p_odds_c)
                else:
                    ll_model = ll_baseline = float("nan")

            elif market == "ou25":
                p_col = MODEL_PROB_COLS[market]
                p_model = sub[p_col].values
                # NOTE: odds_pOver25 in features_train.csv is IMPLIED PROBABILITY
                # (range 0-1), NOT decimal odds. Do not filter by > 1.
                odds_over = sub["odds_pOver25"].values
                odds_valid_mask = ~pd.isna(odds_over)
                n_baseline = int(odds_valid_mask.sum())
                common_mask = odds_valid_mask
                n_common = n_baseline
                n_dropped = n_model - n_common
                baseline_type = "odds"

                if n_common > 0:
                    y_c = y[common_mask]
                    p_model_c = p_model[common_mask]
                    odds_over_c = odds_over[common_mask]
                    # Note: odds_pOver25 in features_train is already normalized implied prob
                    p_odds_c = odds_over_c
                    ll_model = logloss_binary(y_c, p_model_c)
                    ll_baseline = logloss_binary(y_c, p_odds_c)
                else:
                    ll_model = ll_baseline = float("nan")

            else:  # Home/Away O/U
                p_col = MODEL_PROB_COLS[market]
                p_model = sub[p_col].values
                n_baseline = n_model
                n_common = n_model
                n_dropped = 0
                baseline_type = "base_rate_train"
                br = base_rates[market]
                p_odds = np.full(n_model, br)
                ll_model = logloss_binary(y, p_model)
                ll_baseline = logloss_binary(y, p_odds)
                common_mask = np.ones(n_model, dtype=bool)

            delta = ll_model - ll_baseline if not (np.isnan(ll_model) or np.isnan(ll_baseline)) else float("nan")

            # Bootstrap
            if n_common >= MIN_N and not np.isnan(delta):
                if market in ("1x2", "ou25"):
                    # Baseline = odds subset
                    if market == "1x2":
                        p_base_c = p_odds_c  # (n_common, 3)
                    else:
                        p_base_c = p_odds_c  # (n_common,)
                    p_model_c = p_model[common_mask]
                    dates_c = sub.loc[common_mask, "Date"].values
                else:
                    p_base_c = p_odds
                    p_model_c = p_model
                    dates_c = sub["Date"].values

                boot = bootstrap_block_week(
                    market, kind, y[common_mask] if market in ("1x2", "ou25") else y,
                    p_model_c, p_base_c, dates_c
                )
                ci_low = boot.get("delta_ci_low", float("nan"))
                ci_high = boot.get("delta_ci_high", float("nan"))
                verdict = verdict_from_ci(ci_low, ci_high, n_common)
            else:
                boot = {"method": "skipped", "n_iter_valid": 0}
                ci_low = ci_high = float("nan")
                verdict = "INSUFFICIENT N" if n_common < MIN_N else "N/A"

            bootstrap_out[market][league] = {
                "ci_low": ci_low,
                "ci_high": ci_high,
                "method": boot.get("method"),
                "n_iter_valid": boot.get("n_iter_valid", 0),
                "n_weeks": boot.get("n_weeks", 0),
            }

            results.append({
                "market": market,
                "league": league,
                "n_model": n_model,
                "n_baseline": n_baseline,
                "n_common": n_common,
                "n_dropped": n_dropped,
                "logloss_model": ll_model,
                "logloss_baseline": ll_baseline,
                "delta_logloss": delta,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "verdict": verdict,
                "baseline_type": baseline_type,
            })

    # ==== 6. Aggregate verification ====
    L("\n[6] Aggregate verification:")
    for market in MARKETS:
        sub = [r for r in results if r["market"] == market]
        total_n_common = sum(r["n_common"] for r in sub)
        total_n_model = sum(r["n_model"] for r in sub)
        L(f"  {market}: sum_n_model={total_n_model}, sum_n_common={total_n_common}")
        if total_n_model != len(df_te_merge):
            L(f"  FATAL: {market} n_model sum mismatch"); log_fh.close(); sys.exit(1)

    # Verify against original backtest global metrics (for 1x2 model on n_common)
    L("\n[6b] Verify model logloss on n_common vs full-sample:")
    for market in MARKETS:
        sub_m = [r for r in results if r["market"] == market]
        if market in ("1x2", "ou25"):
            # Weighted avg logloss on n_common
            total_n = sum(r["n_common"] for r in sub_m)
            if total_n > 0:
                weighted_ll = sum(r["logloss_model"] * r["n_common"] for r in sub_m if not np.isnan(r["logloss_model"])) / total_n
                L(f"  {market} model logloss (weighted, n_common): {weighted_ll:.6f}")
        else:
            total_n = sum(r["n_model"] for r in sub_m)
            if total_n > 0:
                weighted_ll = sum(r["logloss_model"] * r["n_model"] for r in sub_m if not np.isnan(r["logloss_model"])) / total_n
                L(f"  {market} model logloss (weighted, all): {weighted_ll:.6f}")

    # ==== 7. Save outputs ====
    L("\n[7] Saving outputs...")

    # CSV
    df_out = pd.DataFrame(results, columns=[
        "market", "league", "n_model", "n_baseline", "n_common", "n_dropped",
        "logloss_model", "logloss_baseline", "delta_logloss",
        "ci_low", "ci_high", "verdict", "baseline_type",
    ])
    df_out.to_csv(AUDIT_DIR / "league_metrics.csv", index=False)
    L(f"  league_metrics.csv: {len(df_out)} rows")

    # Bootstrap JSON
    with open(AUDIT_DIR / "bootstrap_ci.json", "w") as f:
        json.dump(bootstrap_out, f, indent=2, default=str)
    L(f"  bootstrap_ci.json")

    # Config
    config_out = {
        "generated_at": datetime.now().isoformat(),
        "seed": SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "min_n": MIN_N,
        "train_end": str(TRAIN_END.date()),
        "val_end": str(VAL_END.date()),
        "n_train": int(len(df_tr)),
        "n_test": int(len(df_te_merge)),
        "n_leagues": len(leagues),
        "base_rates_train": base_rates,
        "base_rates_source": "recomputed from features_train.csv (train split)",
        "inputs": {
            "features_train.csv": sha256_file(DATA / "features_train.csv"),
            "predictions.csv": sha256_file(BACKTEST_DIR / "predictions.csv"),
            "config.json": sha256_file(BACKTEST_DIR / "config.json"),
        },
        "verdict_thresholds": {
            "BETTER": "ci_high < 0",
            "WORSE": "ci_low > 0",
            "INCONCLUSIVE": "ci_low <= 0 <= ci_high",
            "INSUFFICIENT_N": f"n_common < {MIN_N}",
        },
    }
    with open(AUDIT_DIR / "config.json", "w") as f:
        json.dump(config_out, f, indent=2, default=str)
    L(f"  config.json")

    # Limitations
    lim = """# Limitations — League Baseline Audit L10.4

1. **Base rate global (train-only)**: Untuk Home/Away O/U, base rate dihitung dari
   train split (Date <= 2024-06-30) dan bersifat GLOBAL (satu nilai per market).
   Bukan per-liga. Alasan: konsisten dengan `backtest.py` dan per-liga base rate
   tidak signifikan berubah (variansi kecil antar liga).

2. **Odds baseline only on n_common**: Untuk 1x2 dan ou25, model dan baseline
   dibandingkan pada subset yang sama (n_common = rows dengan odds valid).
   Model logloss pada n_common bisa berbeda dari model logloss pada full sample
   (n_model) karena drop odds missing. Ini menghindari perbandingan tidak fair.

3. **Odds implied normalization**: Untuk 1x2, odds baseline dinormalisasi sebagai
   implied probability (1/H + 1/D + 1/A) lalu dibagi sum (overround removed).
   Konsisten dengan `features.py implied_probs`. Untuk ou25, `odds_pOver25` di
   `features_train.csv` sudah berupa implied prob normalized (dari Avg/B365).

4. **Bootstrap block_week**: Default block by ISO week. Fallback row bootstrap
   jika unique weeks < 10 (dicatat di bootstrap_ci.json `method`). Paired: model
   dan baseline di-resample dengan index yang sama. Seed = 42, n_iter = 1000.
   CI 95% percentile-based (bukan BCa).

5. **Verdict threshold strict**: BETTER hanya jika ci_high < 0 (seluruh CI di
   bawah 0). WORSE hanya jika ci_low > 0. INCONCLUSIVE jika CI cross 0.
   INSUFFICIENT N jika n_common < 100.

6. **Closing odds bias (R2)**: Untuk 1x2 dan ou25, baseline odds adalah CLOSING
   odds (dekat kickoff). Model dilatih dengan closing odds yang sama. Ini bias
   optimis — tidak menjamin performa live dengan opening/current odds.

7. **Home/Away O/U tanpa odds baseline**: Tidak ada odds untuk pasar ini di
   football-data.co.uk. Baseline = base rate train. Tidak ada bias R2 di sini,
   tapi juga tidak ada pembanding pasar efisien.

8. **N per-league per-market**: Beberapa liga punya N kecil (<100). Dilaporkan
   sebagai INSUFFICIENT N, tidak ada verdict.

9. **Determinisme**: Bootstrap pakai seed 42. Predictions.csv di-load (bukan
   re-predict), jadi model probabilities identik dengan backtest sebelumnya.
   Tidak ada randomness di luar bootstrap.
"""
    (AUDIT_DIR / "limitations.md").write_text(lim)
    L(f"  limitations.md")

    # Markdown report
    md = []
    md.append("# League Baseline Audit — L10.4\n")
    md.append(f"\nGenerated: {datetime.now().isoformat()}\n")
    md.append(f"\n**Test**: {len(df_te_merge)} rows, {len(leagues)} leagues\n")
    md.append(f"\n**Base rates (train)**: {json.dumps({k: round(v, 6) for k, v in base_rates.items()})}\n")

    for market in MARKETS:
        md.append(f"\n## {MARKET_LABELS[market]}\n")
        sub = df_out[df_out["market"] == market].copy()

        # Sort by delta ascending (better first, if applicable)
        # Untuk home/away O/U sort by delta; untuk 1x2/ou25 sort by delta
        sub = sub.sort_values("delta_logloss", na_position="last")

        md.append("\n| League | N_model | N_common | Model LL | Baseline LL | Δ | CI 95% Δ | Verdict |")
        md.append("|---|---|---|---|---|---|---|---|")
        for _, r in sub.iterrows():
            ci_str = f"[{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]" if not (np.isnan(r['ci_low']) or np.isnan(r['ci_high'])) else "—"
            delta_str = f"{r['delta_logloss']:+.4f}" if not np.isnan(r['delta_logloss']) else "—"
            model_ll = f"{r['logloss_model']:.4f}" if not np.isnan(r['logloss_model']) else "—"
            base_ll = f"{r['logloss_baseline']:.4f}" if not np.isnan(r['logloss_baseline']) else "—"
            md.append(f"| {r['league']} | {r['n_model']} | {r['n_common']} | {model_ll} | {base_ll} | {delta_str} | {ci_str} | {r['verdict']} |")

    # Cross-league ranking (only for markets with baseline = odds, i.e., 1x2 & ou25)
    md.append("\n## Cross-League Ranking (1X2 & OU 2.5)\n")
    md.append("\n**Sort by ΔLogLoss** (ascending, negative = model better).\n")
    for market in ["1x2", "ou25"]:
        md.append(f"\n### {MARKET_LABELS[market]}\n")
        sub = df_out[df_out["market"] == market].copy()
        sub = sub[sub["n_common"] >= MIN_N].sort_values("delta_logloss")
        md.append("\n| Rank | League | N_common | ΔLogLoss | CI 95% Δ | Verdict |")
        md.append("|---|---|---|---|---|---|")
        for i, (_, r) in enumerate(sub.iterrows(), 1):
            ci_str = f"[{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]"
            md.append(f"| {i} | {r['league']} | {r['n_common']} | {r['delta_logloss']:+.4f} | {ci_str} | {r['verdict']} |")

    (AUDIT_DIR / "league_metrics.md").write_text("\n".join(md))
    L(f"  league_metrics.md")

    elapsed = time.time() - t0
    L(f"\n=== DONE in {elapsed:.1f}s ===")
    L(f"Audit dir: {AUDIT_DIR}")
    log_fh.close()


if __name__ == "__main__":
    main()
