#!/usr/bin/env python3
"""
Bandingkan model baru (setelah retrain) vs model lama (dari backup).
Test set identik: Date > 2025-06-30 (9438 match).
Metrik: accuracy, logloss, brier, AUC.
Tidak mengubah apa pun. Read-only.
"""
import json
import sys
from pathlib import Path

BACKUP_JSON_A = Path("models/_backup_20261026/models/evaluation_modeA.json")
BACKUP_JSON_B = Path("models/_backup_20261026/models/evaluation_modeB.json")
NEW_JSON_A = Path("models/evaluation_modeA.json")
NEW_JSON_B = Path("models/evaluation_modeB.json")

MARKETS = ["1x2", "ou25", "home_ou05", "home_ou15", "away_ou05", "away_ou15"]
METRICS_MULTICLASS = ["acc", "logloss", "brier"]
METRICS_BINARY = ["acc", "logloss", "brier", "auc"]


def load(path, name):
    if not path.exists():
        print(f"FATAL: {name} JSON tidak ada: {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def fmt(v, digits=4):
    if v is None:
        return "  -   "
    return f"{v:.{digits}f}"


def verdict(delta, metric, threshold=0.001):
    """Higher better: acc, auc. Lower better: logloss, brier."""
    if delta is None:
        return "-"
    if metric in ("acc", "auc"):
        if delta > threshold: return "BETTER"
        if delta < -threshold: return "WORSE"
        return "NEUTRAL"
    else:  # logloss, brier
        if delta < -threshold: return "BETTER"
        if delta > threshold: return "WORSE"
        return "NEUTRAL"


def compare_mode(mode, old_json, new_json, markets):
    print()
    print("=" * 88)
    print(f"PERBANDINGAN MODE {mode} — TEST SET (Date > 2025-06-30)")
    print("=" * 88)
    print()
    print(f"{'Market':<12} {'Metric':<9} {'OLD':>10} {'NEW':>10} {'DELTA':>12} {'VERDICT':>10}")
    print("-" * 88)

    summary = {}
    for market in markets:
        mkey = f"{market}_model"
        old = old_json.get(mkey, {}).get("test", {})
        new = new_json.get(mkey, {}).get("test", {})

        # Cek n sample sama
        n_old = old.get("n")
        n_new = new.get("n")
        if n_old != n_new:
            print(f"  ✗ WARN: N sample mismatch untuk {market}: old={n_old}, new={n_new}")

        metrics = METRICS_MULTICLASS if market == "1x2" else METRICS_BINARY
        summary[market] = {}
        for metric in metrics:
            ov = old.get(metric)
            nv = new.get(metric)
            if ov is None or nv is None:
                print(f"{market:<12} {metric:<9} {'MISSING':>10}")
                continue
            delta = nv - ov
            v = verdict(delta, metric)
            print(f"{market:<12} {metric:<9} {fmt(ov):>10} {fmt(nv):>10} {delta:>+12.4f} {v:>10}")
            summary[market][metric] = {"old": ov, "new": nv, "delta": delta, "verdict": v}
        print("-" * 88)

    return summary


def baseline_note(mode, old_json, new_json):
    """Baseline odds tidak berubah — verifikasi."""
    print()
    print(f"BASELINE odds Mode {mode} (harus identik OLD vs NEW):")
    for market in MARKETS:
        bkey = f"{market}_baseline"
        old_b = old_json.get(bkey, {}).get("test", {})
        new_b = new_json.get(bkey, {}).get("test", {})
        same = all(abs(old_b.get(k, 0) - new_b.get(k, 0)) < 1e-9
                   for k in ["acc", "logloss"])
        print(f"  {market:<12} baseline identical: {same}")


def main():
    print()
    print("#" * 88)
    print("# EVALUASI PERBANDINGAN: MODEL BARU (H2H FIX) vs MODEL LAMA")
    print("#" * 88)

    old_a = load(BACKUP_JSON_A, "backup modeA")
    old_b = load(BACKUP_JSON_B, "backup modeB")
    new_a = load(NEW_JSON_A, "new modeA")
    new_b = load(NEW_JSON_B, "new modeB")

    summary_a = compare_mode("A", old_a, new_a, MARKETS)
    summary_b = compare_mode("B", old_b, new_b, MARKETS)

    baseline_note("A", old_a, new_a)
    baseline_note("B", old_b, new_b)

    # Simpan ringkasan JSON
    out = {
        "mode_A": summary_a,
        "mode_B": summary_b,
    }
    Path("logs/comparison_retrain.json").write_text(
        json.dumps(out, indent=2))
    print()
    print("Saved: logs/comparison_retrain.json")
    print("#" * 88)


if __name__ == "__main__":
    main()
