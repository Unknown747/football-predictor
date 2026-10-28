#!/usr/bin/env python3
"""
Test suite predict.py — 15 test cases + parity + determinism.
Tidak menyentuh file produksi. Output ke /tmp/test_predict_output/.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PREDICT = BASE / "predict.py"
FIXTURES = BASE / "tests" / "fixtures"
TMP_OUT = Path("/tmp/test_predict_output")

results = []

def record(name, passed, detail=""):
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")

def run_predict(input_csv, output_dir):
    """Run predict.py on input CSV. Return (success, output_csv_path)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(PREDICT),
           "--input", str(input_csv),
           "--output-dir", str(out_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        return False, None, proc.stderr
    # Find newest CSV
    csvs = sorted(out_dir.glob("predictions_*.csv"), key=lambda p: p.stat().st_mtime)
    if not csvs:
        return False, None, "no output csv"
    return True, csvs[-1], ""

def load_output(csv_path):
    import pandas as pd
    return pd.read_csv(csv_path)


def main():
    import pandas as pd
    import numpy as np

    # Reset tmp output
    if TMP_OUT.exists():
        shutil.rmtree(TMP_OUT)
    TMP_OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("TEST SUITE predict.py")
    print("=" * 70)
    print()

    # ============================================================
    # T1: Match lengkap (full history, full odds)
    # ============================================================
    print("T1: Match lengkap, full history, full odds")
    f = FIXTURES / "full_history.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T1")
    if not ok:
        record("T1_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        status_ok = r["data_status"] in ("OK", "OK_WITH_WARNING")
        prob_valid = (0 <= r["p_H"] <= 1) and (0 <= r["p_D"] <= 1) and (0 <= r["p_A"] <= 1)
        sum_ok = abs(r["p_H"] + r["p_D"] + r["p_A"] - 1.0) < 1e-5
        record("T1_status_ok", status_ok, f"status={r['data_status']}")
        record("T1_prob_valid", prob_valid)
        record("T1_prob_sum_1", sum_ok, f"sum={r['p_H']+r['p_D']+r['p_A']:.6f}")

    # ============================================================
    # T2: Tim baru (UNKNOWN_TEAM)
    # ============================================================
    print("\nT2: Tim baru → UNKNOWN_TEAM")
    f = FIXTURES / "unknown_team.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T2")
    if not ok:
        record("T2_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T2_unknown_team", r["data_status"] == "UNKNOWN_TEAM",
               f"status={r['data_status']}")
        record("T2_probs_nan",
               pd.isna(r["p_H"]) and pd.isna(r["p_D"]) and pd.isna(r["p_A"]),
               f"p_H={r['p_H']}, p_D={r['p_D']}, p_A={r['p_A']}")

    # ============================================================
    # T3: H2H kosong (tetap prediksi)
    # ============================================================
    print("\nT3: H2H kosong (debut pair)")
    f = FIXTURES / "h2h_empty.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T3")
    if not ok:
        record("T3_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        # Status bisa OK_WITH_WARNING jika history kurang, tapi harus predict
        record("T3_predicts", not pd.isna(r["p_H"]), f"p_H={r['p_H']}")

    # ============================================================
    # T4: Odds tidak ada
    # ============================================================
    print("\nT4: Odds tidak ada")
    f = FIXTURES / "no_odds.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T4")
    if not ok:
        record("T4_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T4_used_odds_none", r["used_odds_input"] == "none",
               f"used={r['used_odds_input']}")
        record("T4_odds_nan", pd.isna(r["odds_home"]) and pd.isna(r["value_1x2_H"]))
        record("T4_predicts", not pd.isna(r["p_H"]))
        record("T4_selects_no_odds_model", r["prediction_mode"] == "A_NO_ODDS",
               f"mode={r['prediction_mode']}")

    # ============================================================
    # T5: Odds lengkap
    # ============================================================
    print("\nT5: Odds lengkap (1x2 + ou25)")
    f = FIXTURES / "full_odds.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T5")
    if not ok:
        record("T5_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T5_used_odds_both", r["used_odds_input"] == "both",
               f"used={r['used_odds_input']}")
        record("T5_selects_odds_model", r["prediction_mode"] == "B_WITH_ODDS",
               f"mode={r['prediction_mode']}")
        # implied sum=1
        s = r["implied_H"] + r["implied_D"] + r["implied_A"]
        record("T5_implied_sum_1", abs(s - 1.0) < 1e-5, f"sum={s:.6f}")
        record("T5_value_nonnull", not pd.isna(r["value_1x2_H"]))

    # ============================================================
    # T6: Duplikat di input
    # ============================================================
    print("\nT6: Duplikat input")
    f = FIXTURES / "duplicates.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T6")
    if not ok:
        record("T6_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        # Harus 1 baris (dupe di-dedupe)
        record("T6_dedup", len(df) == 1, f"rows={len(df)}")

    # ============================================================
    # T7: Tanggal invalid
    # ============================================================
    print("\nT7: Tanggal invalid")
    f = FIXTURES / "invalid_date.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T7")
    if not ok:
        record("T7_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T7_invalid_date", r["data_status"] == "INVALID_DATE",
               f"status={r['data_status']}")

    # ============================================================
    # T8: Home == Away
    # ============================================================
    print("\nT8: Home == Away")
    f = FIXTURES / "home_eq_away.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T8")
    if not ok:
        record("T8_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T8_invalid_match", r["data_status"] == "INVALID_MATCH",
               f"status={r['data_status']}")

    # ============================================================
    # T9: Tanggal masa lalu
    # ============================================================
    print("\nT9: Tanggal masa lalu")
    f = FIXTURES / "past_date.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T9")
    if not ok:
        record("T9_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T9_past_date", r["data_status"] == "DATE_NOT_IN_FUTURE",
               f"status={r['data_status']}")

    # ============================================================
    # T10: Schema length
    # ============================================================
    print("\nT10: Schema 50 kolom")
    expected_cols = 50
    record("T10_columns_50", len(df.columns) == expected_cols,
           f"cols={len(df.columns)}")

    # ============================================================
    # T11: Match_id uniqueness
    # ============================================================
    print("\nT11: match_id uniqueness")
    f = FIXTURES / "three_matches.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T11")
    if not ok:
        record("T11_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        record("T11_unique_matchid", df["match_id"].nunique() == len(df),
               f"unique={df['match_id'].nunique()}/{len(df)}")

    # ============================================================
    # T12: Determinism
    # ============================================================
    print("\nT12: Determinism (run 2x, hash compare)")
    f = FIXTURES / "full_history.csv"
    ok1, out1, _ = run_predict(f, TMP_OUT / "T12a")
    ok2, out2, _ = run_predict(f, TMP_OUT / "T12b")
    if not (ok1 and ok2):
        record("T12_determinism", False, "run failed")
    else:
        df1 = load_output(out1)
        df2 = load_output(out2)
        # Compare semua kolom numerik
        numeric_cols = df1.select_dtypes(include=[np.number]).columns.tolist()
        all_same = True
        for c in numeric_cols:
            v1 = df1[c].values
            v2 = df2[c].values
            same = ((pd.isna(v1) & pd.isna(v2)) |
                    (np.isclose(v1, v2, equal_nan=True))).all()
            if not same:
                all_same = False
                break
        record("T12_determinism", all_same)

    # ============================================================
    # T13: Cutoff injection (parity)
    # ============================================================
    print("\nT13: Cutoff (parity test historical)")
    sys.path.insert(0, str(BASE))
    sys.path.insert(0, str(BASE / "logs"))
    from reconstruct_pit import reconstruct
    feat = pd.read_csv(BASE / "data" / "features_train.csv", nrows=200)
    feat["Date"] = pd.to_datetime(feat["Date"])
    with open(BASE / "logs" / "feat_cols_modeB_ordered.json") as f:
        feat_cols = json.load(f)
    non_odds = [c for c in feat_cols if not c.startswith("odds_")]
    # Ambil 1 sample
    row = feat.iloc[5]
    recon = reconstruct(row["Date"], row["HomeTeam_canon"],
                        row["AwayTeam_canon"], row["league_name"])
    n_diff = 0
    for c in non_odds:
        sv = row.get(c)
        rv = recon.get(c)
        if pd.isna(sv) and pd.isna(rv):
            continue
        if pd.isna(sv) != pd.isna(rv):
            n_diff += 1
            continue
        if abs(float(sv) - float(rv)) > 1e-6:
            n_diff += 1
    record("T13_parity_1_sample", n_diff == 0, f"n_diff={n_diff}")

    # ============================================================
    # T14: Case-insensitive team
    # ============================================================
    print("\nT14: Case-insensitive team names")
    f = FIXTURES / "case_insensitive.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T14")
    if not ok:
        record("T14_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T14_resolves", r["data_status"] in ("OK", "OK_WITH_WARNING"),
               f"status={r['data_status']}")

    # ============================================================
    # T15: Liga tidak dikenal
    # ============================================================
    print("\nT15: Liga tidak dikenal")
    f = FIXTURES / "unknown_league.csv"
    ok, out, err = run_predict(f, TMP_OUT / "T15")
    if not ok:
        record("T15_predict_runs", False, err[:200])
    else:
        df = load_output(out)
        r = df.iloc[0]
        record("T15_unknown_league", r["data_status"] == "UNKNOWN_LEAGUE",
               f"status={r['data_status']}")

    # ============================================================
    # Ringkasan
    # ============================================================
    print()
    print("=" * 70)
    print("RINGKASAN")
    print("=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, _ in results:
        print(f"  {'PASS' if ok else 'FAIL':4s} {name}")
    print()
    print(f"TOTAL: {passed}/{total} PASS")
    print()

    if passed == total:
        print("✓ SEMUA TEST PASS")
        return 0
    else:
        print("✗ ADA TEST GAGAL — STOP, JANGAN PRODUCTION")
        return 1


if __name__ == "__main__":
    sys.exit(main())
