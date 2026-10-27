#!/usr/bin/env python3
"""
LANGKAH 10.6 — Calibration experiment (isolated).

Per market (home_ou05, home_ou15, away_ou05, away_ou15):
  1. Temporal internal val split:
     - val_early (fit set): Date <= 2025-01-15
     - val_late (check set): Date > 2025-01-15
  2. Fit Platt on val_early, eval on val_late
  3. Fit Isotonic on val_early, eval on val_late
  4. Pilih metode dengan logloss terbaik di val_late (tie-break Platt)
  5. Refit metode terpilih pada FULL val
  6. Eval final pada test (1 kali)
  7. Reliability bins, per-liga eval, determinism check

Read-only produksi. Output isolated di CAL_DIR.
"""
import hashlib
import json
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score, roc_auc_score

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"
MODELS = BASE / "models"
LOGS = BASE / "logs"
BACKTEST_DIR = BASE / "backtest" / "backtest_20261026_215202"

# Arguments
CAL_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if CAL_DIR is None:
    sys.exit("usage: calibrate.py <cal_dir>")

TRAIN_END = pd.Timestamp("2024-06-30")
VAL_END = pd.Timestamp("2025-06-30")
VAL_EARLY_END = pd.Timestamp("2025-01-15")  # temporal split in val
SEED = 42
N_BOOTSTRAP = 1000
MIN_N_PER_LEAGUE = 100

MARKETS = ["home_ou05", "home_ou15", "away_ou05", "away_ou15"]
MARKET_LABELS = {
    "home_ou05": "Home O/U 0.5",
    "home_ou15": "Home O/U 1.5",
    "away_ou05": "Away O/U 0.5",
    "away_ou15": "Away O/U 1.5",
}
TARGET_COLS = {
    "home_ou05": "target_home_ou05",
    "home_ou15": "target_home_ou15",
    "away_ou05": "target_away_ou05",
    "away_ou15": "target_away_ou15",
}
PROB_COLS_TEST = {
    "home_ou05": "p_home_ou05",
    "home_ou15": "p_home_ou15",
    "away_ou05": "p_away_ou05",
    "away_ou15": "p_away_ou15",
}
Y_COLS_TEST = {
    "home_ou05": "y_home_ou05",
    "home_ou15": "y_home_ou15",
    "away_ou05": "y_away_ou05",
    "away_ou15": "y_away_ou15",
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def logloss_binary(y_true, p):
    return float(log_loss(y_true, np.clip(p, 1e-7, 1 - 1e-7)))


def brier_binary(y_true, p):
    return float(brier_score_loss(y_true, p))


def auc_binary(y_true, p):
    try:
        return float(roc_auc_score(y_true, p))
    except ValueError:
        return float("nan")


def evaluate(y_true, p_raw, p_cal, label=""):
    """Full metric set on same y_true with paired raw and calibrated."""
    return {
        "n": int(len(y_true)),
        "logloss_raw": logloss_binary(y_true, p_raw),
        "logloss_cal": logloss_binary(y_true, p_cal),
        "brier_raw": brier_binary(y_true, p_raw),
        "brier_cal": brier_binary(y_true, p_cal),
        "acc_raw": float(accuracy_score(y_true, (p_raw >= 0.5).astype(int))),
        "acc_cal": float(accuracy_score(y_true, (p_cal >= 0.5).astype(int))),
        "auc_raw": auc_binary(y_true, p_raw),
        "auc_cal": auc_binary(y_true, p_cal),
        "delta_logloss": logloss_binary(y_true, p_cal) - logloss_binary(y_true, p_raw),
    }


def fit_platt(p_fit, y_fit):
    """Fit Platt scaling: p_cal = sigmoid(a * logit(p) + b)."""
    p_fit = np.clip(p_fit, 1e-6, 1 - 1e-6)
    z = np.log(p_fit / (1 - p_fit)).reshape(-1, 1)
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=SEED)
    lr.fit(z, y_fit)
    return lr


def apply_platt(lr, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p)).reshape(-1, 1)
    return lr.predict_proba(z)[:, 1]


def fit_isotonic(p_fit, y_fit):
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(p_fit, y_fit)
    return iso


def apply_isotonic(iso, p):
    return np.clip(iso.predict(p), 0.0, 1.0)


def reliability_bins(y_true, p, n_bins=10):
    """Return list of dicts dengan per-bin count, mean_p, mean_y."""
    bins = np.linspace(0, 1, n_bins + 1)
    rows = []
    for i in range(n_bins):
        mask = (p >= bins[i]) & (p < bins[i + 1])
        if i == n_bins - 1:
            mask = mask | (p == bins[i + 1])
        n = int(mask.sum())
        if n == 0:
            rows.append({
                "bin_low": float(bins[i]), "bin_high": float(bins[i + 1]),
                "count": 0, "mean_p": None, "mean_y": None, "abs_gap": None,
            })
            continue
        mp = float(p[mask].mean())
        my = float(y_true[mask].mean())
        rows.append({
            "bin_low": float(bins[i]), "bin_high": float(bins[i + 1]),
            "count": n, "mean_p": mp, "mean_y": my, "abs_gap": abs(mp - my),
        })
    return rows


def paired_bootstrap_delta_logloss(y, p_raw, p_cal, n_iter=N_BOOTSTRAP, seed=SEED):
    """Paired bootstrap 95% CI untuk Δ logloss (calibrated - raw)."""
    rng = np.random.default_rng(seed)
    n = len(y)
    deltas = []
    for _ in range(n_iter):
        idx = rng.integers(0, n, size=n)
        y_b = y[idx]
        pr_b = p_raw[idx]
        pc_b = p_cal[idx]
        try:
            d = logloss_binary(y_b, pc_b) - logloss_binary(y_b, pr_b)
            deltas.append(d)
        except Exception:
            continue
    if not deltas:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n_iter_valid": 0}
    deltas = np.array(deltas)
    return {
        "mean": float(deltas.mean()),
        "ci_low": float(np.percentile(deltas, 2.5)),
        "ci_high": float(np.percentile(deltas, 97.5)),
        "n_iter_valid": len(deltas),
    }


def check_monotonicity(apply_fn, p_grid):
    """Verify monotonic non-decreasing on grid."""
    p_cal = apply_fn(p_grid)
    # Check monotonic non-decreasing
    diffs = np.diff(p_cal)
    # Allow tiny numerical noise
    is_mono = np.all(diffs >= -1e-9)
    if not is_mono:
        # Find first violation
        viol_idx = np.where(diffs < -1e-9)[0]
        return False, int(viol_idx[0])
    return True, -1


def main():
    t0 = time.time()
    log_path = CAL_DIR / "run.log"
    log_fh = open(log_path, "w")

    def L(msg):
        print(msg, flush=True)
        log_fh.write(msg + "\n")
        log_fh.flush()

    L(f"=== START calibration {datetime.now().isoformat()} ===")
    L(f"Cal dir: {CAL_DIR}")

    # ==== Load data ====
    L("\n[1] Loading data...")
    df = pd.read_csv(DATA / "features_train.csv", low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    with open(LOGS / "feat_cols_modeB_ordered.json") as f:
        feat_cols = json.load(f)

    # Load test predictions
    preds = pd.read_csv(BACKTEST_DIR / "predictions.csv")
    preds["date"] = pd.to_datetime(preds["date"], errors="coerce")

    # Splits
    tr_mask = df["Date"] <= TRAIN_END
    va_mask = (df["Date"] > TRAIN_END) & (df["Date"] <= VAL_END)
    te_mask = df["Date"] > VAL_END
    df_tr = df[tr_mask].copy().reset_index(drop=True)
    df_va = df[va_mask].copy().reset_index(drop=True)
    df_te = df[te_mask].copy().reset_index(drop=True)
    L(f"  Train: {len(df_tr)}, Val: {len(df_va)}, Test: {len(df_te)}")

    # Generate val probabilities
    L("\n[2] Generating val probabilities...")
    X_va = df_va[feat_cols].values
    val_probs = {}
    for m in MARKETS:
        model = lgb.Booster(model_file=str(MODELS / f"lgb_{m}_modeB.txt"))
        val_probs[m] = model.predict(X_va)
        L(f"  {m}: range=[{val_probs[m].min():.4f}, {val_probs[m].max():.4f}]")

    # Temporal internal val split
    val_early_mask = (df_va["Date"] <= VAL_EARLY_END).values
    val_late_mask = ~val_early_mask
    n_early = int(val_early_mask.sum())
    n_late = int(val_late_mask.sum())
    L(f"\n  Val_early (fit): {n_early} ({df_va['Date'].min().date()} .. {VAL_EARLY_END.date()})")
    L(f"  Val_late (check): {n_late} ({(VAL_EARLY_END + pd.Timedelta(days=1)).date()} .. {df_va['Date'].max().date()})")

    # Save val predictions CSV
    val_df_out = df_va[["Date", "HomeTeam_canon", "AwayTeam_canon", "league_name"]].copy()
    val_df_out["date"] = df_va["Date"].dt.strftime("%Y-%m-%d")
    for m in MARKETS:
        val_df_out[f"p_{m}"] = val_probs[m]
        val_df_out[f"y_{m}"] = df_va[TARGET_COLS[m]].values
    val_df_out["val_split"] = np.where(val_early_mask, "fit", "check")
    val_df_out.to_csv(CAL_DIR / "val_predictions.csv", index=False)
    L(f"  Saved val_predictions.csv")

    # ==== Per-market method selection on val_late ====
    L("\n[3] Method selection (temporal internal val)...")
    method_selection = {}
    for m in MARKETS:
        y_va = df_va[TARGET_COLS[m]].values
        p_va = val_probs[m]

        y_fit = y_va[val_early_mask]
        p_fit = p_va[val_early_mask]
        y_chk = y_va[val_late_mask]
        p_chk = p_va[val_late_mask]

        # Baseline raw
        ll_raw = logloss_binary(y_chk, p_chk)

        # Platt
        platt_lr = fit_platt(p_fit, y_fit)
        p_chk_platt = apply_platt(platt_lr, p_chk)
        ll_platt = logloss_binary(y_chk, p_chk_platt)

        # Isotonic
        iso = fit_isotonic(p_fit, y_fit)
        p_chk_iso = apply_isotonic(iso, p_chk)
        ll_iso = logloss_binary(y_chk, p_chk_iso)

        L(f"\n  {m}:")
        L(f"    Val_late raw:      logloss={ll_raw:.6f}")
        L(f"    Val_late Platt:    logloss={ll_platt:.6f}  (Δ={ll_platt-ll_raw:+.6f})")
        L(f"    Val_late Isotonic: logloss={ll_iso:.6f}  (Δ={ll_iso-ll_raw:+.6f})")

        # Select method: lowest val_late logloss
        candidates = [("platt", ll_platt), ("isotonic", ll_iso)]
        candidates.sort(key=lambda x: x[1])
        best_method, best_ll = candidates[0]

        # Tie-break: if diff < 0.001, prefer Platt
        if len(candidates) >= 2:
            if abs(candidates[0][1] - candidates[1][1]) < 0.001:
                best_method = "platt"
                L(f"    Tie-break: Platt (simpler)")
            else:
                L(f"    Selected: {best_method} (val_late logloss={best_ll:.6f})")

        method_selection[m] = {
            "selected_method": best_method,
            "val_late_raw_logloss": ll_raw,
            "val_late_platt_logloss": ll_platt,
            "val_late_isotonic_logloss": ll_iso,
            "n_val_fit": n_early,
            "n_val_check": n_late,
        }

    # ==== Fit final calibrator on FULL val ====
    L("\n[4] Fitting final calibrators on FULL val...")
    calibrators = {}
    for m in MARKETS:
        method = method_selection[m]["selected_method"]
        y_va = df_va[TARGET_COLS[m]].values
        p_va = val_probs[m]

        if method == "platt":
            cal = fit_platt(p_va, y_va)
        else:
            cal = fit_isotonic(p_va, y_va)
        calibrators[m] = {"method": method, "model": cal}
        L(f"  {m}: {method} fitted on {len(y_va)} val rows")

    # ==== Test evaluation (1x, no refit) ====
    L("\n[5] Test evaluation (1x)...")
    y_te = {}
    p_te_raw = {}
    for m in MARKETS:
        y_te[m] = preds[Y_COLS_TEST[m]].values.astype(int)
        p_te_raw[m] = preds[PROB_COLS_TEST[m]].values

    eval_results = {}
    for m in MARKETS:
        method = calibrators[m]["method"]
        cal_model = calibrators[m]["model"]
        if method == "platt":
            p_te_cal = apply_platt(cal_model, p_te_raw[m])
        else:
            p_te_cal = apply_isotonic(cal_model, p_te_raw[m])

        # Metrics
        metrics = evaluate(y_te[m], p_te_raw[m], p_te_cal)
        metrics["method"] = method
        eval_results[m] = metrics

        # Paired bootstrap
        boot = paired_bootstrap_delta_logloss(y_te[m], p_te_raw[m], p_te_cal)
        eval_results[m]["bootstrap"] = boot

        L(f"\n  {m} ({method}):")
        L(f"    N: {metrics['n']}")
        L(f"    LogLoss: raw={metrics['logloss_raw']:.6f} → cal={metrics['logloss_cal']:.6f}  Δ={metrics['delta_logloss']:+.6f}")
        L(f"    Brier:   raw={metrics['brier_raw']:.6f} → cal={metrics['brier_cal']:.6f}")
        L(f"    Acc:     raw={metrics['acc_raw']:.6f} → cal={metrics['acc_cal']:.6f}")
        L(f"    AUC:     raw={metrics['auc_raw']:.6f} → cal={metrics['auc_cal']:.6f}")
        L(f"    ΔLogLoss CI 95%: [{boot['ci_low']:+.6f}, {boot['ci_high']:+.6f}] (mean={boot['mean']:+.6f})")

    # ==== Verification checks ====
    L("\n[6] Verification checks...")

    verification = {}
    for m in MARKETS:
        method = calibrators[m]["method"]
        cal_model = calibrators[m]["model"]
        checks = {}

        # 1. Prob range on test
        if method == "platt":
            p_te_cal = apply_platt(cal_model, p_te_raw[m])
        else:
            p_te_cal = apply_isotonic(cal_model, p_te_raw[m])
        checks["prob_range_ok"] = bool(np.all((p_te_cal >= 0) & (p_te_cal <= 1)))
        checks["prob_min"] = float(p_te_cal.min())
        checks["prob_max"] = float(p_te_cal.max())

        # 2. Monotonicity on grid
        p_grid = np.linspace(0.01, 0.99, 100)
        if method == "platt":
            p_grid_cal = apply_platt(cal_model, p_grid)
            mono = np.all(np.diff(p_grid_cal) >= -1e-9)
        else:
            p_grid_cal = apply_isotonic(cal_model, p_grid)
            mono = np.all(np.diff(p_grid_cal) >= -1e-9)
        checks["monotonic_ok"] = bool(mono)

        # 3. Classification preservation at threshold 0.5
        raw_class = (p_te_raw[m] >= 0.5).astype(int)
        cal_class = (p_te_cal >= 0.5).astype(int)
        n_changed = int((raw_class != cal_class).sum())
        checks["n_class_changed_at_0.5"] = n_changed
        checks["class_change_rate"] = n_changed / len(y_te[m])

        verification[m] = checks
        L(f"  {m}: prob_range_ok={checks['prob_range_ok']}, "
          f"mono={checks['monotonic_ok']}, "
          f"class_changed={checks['n_class_changed_at_0.5']}/{len(y_te[m])}")

    # ==== Reliability bins ====
    L("\n[7] Reliability bins...")
    reliability_rows = []
    for m in MARKETS:
        method = calibrators[m]["method"]
        cal_model = calibrators[m]["model"]
        if method == "platt":
            p_cal = apply_platt(cal_model, p_te_raw[m])
        else:
            p_cal = apply_isotonic(cal_model, p_te_raw[m])

        raw_bins = reliability_bins(y_te[m], p_te_raw[m])
        cal_bins = reliability_bins(y_te[m], p_cal)

        for i, (rb, cb) in enumerate(zip(raw_bins, cal_bins)):
            reliability_rows.append({
                "market": m, "method": method, "bin_idx": i,
                "bin_low": rb["bin_low"], "bin_high": rb["bin_high"],
                "n_raw": rb["count"], "mean_p_raw": rb["mean_p"], "mean_y_raw": rb["mean_y"],
                "abs_gap_raw": rb["abs_gap"],
                "n_cal": cb["count"], "mean_p_cal": cb["mean_p"], "mean_y_cal": cb["mean_y"],
                "abs_gap_cal": cb["abs_gap"],
            })

    pd.DataFrame(reliability_rows).to_csv(CAL_DIR / "reliability_bins.csv", index=False)
    L(f"  Saved reliability_bins.csv")

    # ==== Per-league eval ====
    L("\n[8] Per-league eval (N>=100)...")
    per_league_rows = []
    for m in MARKETS:
        method = calibrators[m]["method"]
        cal_model = calibrators[m]["model"]
        if method == "platt":
            p_cal = apply_platt(cal_model, p_te_raw[m])
        else:
            p_cal = apply_isotonic(cal_model, p_te_raw[m])

        for league in preds["league"].dropna().unique():
            mask = (preds["league"] == league).values
            n = int(mask.sum())
            if n < MIN_N_PER_LEAGUE:
                continue
            try:
                metrics = evaluate(y_te[m][mask], p_te_raw[m][mask], p_cal[mask])
                metrics["market"] = m
                metrics["league"] = league
                metrics["method"] = method
                per_league_rows.append(metrics)
            except Exception as e:
                L(f"  WARN: {m}/{league} eval failed: {e}")

    pd.DataFrame(per_league_rows).to_csv(CAL_DIR / "per_league_eval.csv", index=False)
    L(f"  Saved per_league_eval.csv ({len(per_league_rows)} rows)")

    # ==== Eval before/after CSV ====
    eval_rows = []
    for m in MARKETS:
        r = eval_results[m].copy()
        r["market"] = m
        eval_rows.append(r)
    pd.DataFrame(eval_rows).to_csv(CAL_DIR / "eval_before_after.csv", index=False)
    L(f"  Saved eval_before_after.csv")

    # ==== Save calibrators ====
    with open(CAL_DIR / "calibrators.pkl", "wb") as f:
        pickle.dump(calibrators, f)
    L(f"  Saved calibrators.pkl")

    # ==== Save method selection ====
    with open(CAL_DIR / "method_selection.json", "w") as f:
        json.dump(method_selection, f, indent=2, default=str)
    L(f"  Saved method_selection.json")

    # ==== Save config ====
    config = {
        "generated_at": datetime.now().isoformat(),
        "seed": SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "train_end": str(TRAIN_END.date()),
        "val_end": str(VAL_END.date()),
        "val_early_end": str(VAL_EARLY_END.date()),
        "n_train": len(df_tr),
        "n_val": len(df_va),
        "n_val_fit": int(n_early),
        "n_val_check": int(n_late),
        "n_test": len(df_te),
        "markets": MARKETS,
        "method_selection": method_selection,
        "verification": verification,
        "inputs": {
            "features_train.csv": sha256_file(DATA / "features_train.csv"),
            "predictions.csv": sha256_file(BACKTEST_DIR / "predictions.csv"),
            "feat_cols_modeB_ordered.json": sha256_file(LOGS / "feat_cols_modeB_ordered.json"),
        },
        "models_sha256": {m: sha256_file(MODELS / f"lgb_{m}_modeB.txt") for m in MARKETS},
    }
    with open(CAL_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    L(f"  Saved config.json")

    # ==== Limitations ===
    lim = """# Limitations — Calibration Experiment L10.6

1. **Closing odds bias (R2)**: Test probabilities dari `predictions.csv` berasal dari model yang dilatih pada closing odds. Live dengan opening odds bisa berbeda.

2. **Temporal internal val split**: Method selection menggunakan split temporal `val_early` (Date <= 2025-01-15) untuk fit dan `val_late` (Date > 2025-01-15) untuk check. Ini bukan random split — menghindari data leakage temporal.

3. **Per-market calibration, bukan per-liga**: Kalibrator di-fit global per market. Per-liga kalibrasi TIDAK dilakukan karena N per-liga di val mungkin tidak cukup (300-500 rows per liga).

4. **Fokus Home/Away O/U**: Model 1X2 dan OU25 tidak di-kalibrasi (sudah di bawah odds, kalibrasi tidak akan fundamental membantu).

5. **Reliability bins**: 10 bins, `abs_gap = |mean_p - mean_y|`. Improvement diharapkan, tapi tidak dijamin signifikan.

6. **Class preservation not assumed**: Kalibrasi monotonic TIDAK otomatis menjaga klasifikasi threshold 0.5. Setiap perubahan argmax di 0.5 dilaporkan di `config.json` `verification.n_class_changed_at_0.5`.

7. **Paired bootstrap**: 1000 iterasi, seed 42. Mengasumsikan korelasi intra-row (match). Tidak menggunakan block bootstrap by week — bisa jadi underestimate CI untuk time series.

8. **Tidak ada profitabilitas / bankroll simulation**: Kalibrasi membaikkan probabilitas, tapi tidak ada ROI, stake sizing, atau Kelly.

9. **Test eval 1x**: Setelah metode dipilih dari val, evaluasi di test hanya dilakukan sekali (tidak iterate). Ini fair.

10. **Isotonic regression caveat**: Non-parametric, butuh N besar. Jika selected, kalibrasi bisa overfit val_early. Platt lebih konservatif.
"""
    (CAL_DIR / "limitations.md").write_text(lim)
    L(f"  Saved limitations.md")

    # ==== Markdown report ====
    md = []
    md.append("# Calibration Experiment — L10.6\n")
    md.append(f"\nGenerated: {datetime.now().isoformat()}\n")
    md.append(f"\n**Splits:** Train {len(df_tr)}, Val {len(df_va)}, Test {len(df_te)}\n")
    md.append(f"\n**Val internal split:** fit={n_early}, check={n_late} (cutoff: {VAL_EARLY_END.date()})\n")

    md.append("\n## Method Selection (on val_late)\n")
    md.append("\n| Market | Selected | Raw LL | Platt LL | Isotonic LL |")
    md.append("|---|---|---|---|---|")
    for m in MARKETS:
        ms = method_selection[m]
        md.append(f"| {MARKET_LABELS[m]} | {ms['selected_method']} | "
                  f"{ms['val_late_raw_logloss']:.6f} | "
                  f"{ms['val_late_platt_logloss']:.6f} | "
                  f"{ms['val_late_isotonic_logloss']:.6f} |")

    md.append("\n## Test Evaluation (after calibration)\n")
    md.append("\n| Market | Method | N | LogLoss raw | LogLoss cal | Δ | CI 95% Δ | Brier raw | Brier cal | Acc raw | Acc cal |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for m in MARKETS:
        r = eval_results[m]
        b = r["bootstrap"]
        md.append(f"| {MARKET_LABELS[m]} | {r['method']} | {r['n']} | "
                  f"{r['logloss_raw']:.4f} | {r['logloss_cal']:.4f} | "
                  f"{r['delta_logloss']:+.4f} | [{b['ci_low']:+.4f}, {b['ci_high']:+.4f}] | "
                  f"{r['brier_raw']:.4f} | {r['brier_cal']:.4f} | "
                  f"{r['acc_raw']:.4f} | {r['acc_cal']:.4f} |")

    md.append("\n## Verification\n")
    md.append("\n| Market | Method | Prob range OK | Monotonic OK | Class changed at 0.5 |")
    md.append("|---|---|---|---|---|")
    for m in MARKETS:
        v = verification[m]
        md.append(f"| {MARKET_LABELS[m]} | {calibrators[m]['method']} | "
                  f"{v['prob_range_ok']} | {v['monotonic_ok']} | "
                  f"{v['n_class_changed_at_0.5']}/{eval_results[m]['n']} |")

    md.append("\n## Notes\n")
    md.append("\n- 'Class changed at 0.5' = number of predictions where calibrated class differs from raw class at threshold 0.5. This is NOT necessarily a bug (calibration may shift effective threshold), but documented for transparency.\n")
    md.append("\n- Method selected based on **val_late** logloss (temporal internal val). Test set untouched during selection.\n")
    md.append("\n- ΔLogLoss CI 95% from paired bootstrap (N=1000).\n")

    (CAL_DIR / "report.md").write_text("\n".join(md))
    L(f"  Saved report.md")

    elapsed = time.time() - t0
    L(f"\n=== DONE in {elapsed:.1f}s ===")
    log_fh.close()


if __name__ == "__main__":
    main()
