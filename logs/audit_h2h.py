#!/usr/bin/env python3
"""
Unit test untuk h2h_features() di features.py — versi BASELINE.
Tujuan: dokumentasikan perilaku IMPLEMENTASI LAMA sebelum patch.
Setiap test mencetak PASS/FAIL per assertion + penjelasan.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, '.')
from features import h2h_features

# ---------- Helper ----------
def make_match(home, away, date, fthg, ftag, ftr):
    return {
        "Date": pd.Timestamp(date),
        "HomeTeam_canon": home,
        "AwayTeam_canon": away,
        "FTHG": fthg, "FTAG": ftag, "FTR": ftr,
    }

def build_df(rows):
    df = pd.DataFrame(rows)
    # match_id selalu diambil dari index posisi
    df["match_id"] = df.index.astype("int64")
    return df

def check(name, cond, expected, actual, note=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}")
    print(f"         expected={expected}  actual={actual}")
    if note:
        print(f"         note: {note}")
    return bool(cond)

results = {}

# T1: H2H kosong
print("=" * 70)
print("T1: H2H kosong (2 tim belum pernah bertemu)")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Gamma", "2024-01-01", 2, 0, "H"),
    make_match("Beta", "Delta", "2024-01-02", 1, 1, "D"),
    make_match("Alpha", "Beta", "2024-01-10", 3, 1, "H"),  # target id=2
])
h = h2h_features(df).set_index("match_id")
r = h.loc[2]
t1 = True
t1 &= check("h2h_n == 0", r["h2h_n"] == 0, 0, r["h2h_n"])
t1 &= check("h2h_home_wins == 0", r["h2h_home_wins"] == 0, 0, r["h2h_home_wins"])
t1 &= check("h2h_away_wins == 0", r["h2h_away_wins"] == 0, 0, r["h2h_away_wins"])
t1 &= check("h2h_draws == 0", r["h2h_draws"] == 0, 0, r["h2h_draws"])
t1 &= check("h2h_total_goals_avg is NaN", pd.isna(r["h2h_total_goals_avg"]),
            "NaN", r["h2h_total_goals_avg"])
results["T1"] = t1

# T2: 1 match historis, A home menang, target A home
print()
print("=" * 70)
print("T2: A vs B (A home) A menang. Target A vs B (A home)")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Beta", "2024-01-01", 2, 0, "H"),
    make_match("Alpha", "Beta", "2024-02-01", 1, 1, "D"),  # target id=1
])
h = h2h_features(df).set_index("match_id")
r = h.loc[1]
t2 = True
t2 &= check("h2h_n == 1", r["h2h_n"] == 1, 1, r["h2h_n"])
t2 &= check("h2h_home_wins == 1 (Alpha menang)",
            r["h2h_home_wins"] == 1, 1, r["h2h_home_wins"],
            note="Alpha home current menang historis")
t2 &= check("h2h_away_wins == 0", r["h2h_away_wins"] == 0, 0, r["h2h_away_wins"])
results["T2"] = t2

# T3: 1 match historis A home menang, target B home (venue swap)
print()
print("=" * 70)
print("T3: A vs B (A home) A menang. Target B vs A (B home, A away)")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Beta", "2024-01-01", 2, 0, "H"),
    make_match("Beta", "Alpha", "2024-02-01", 1, 1, "D"),  # target id=1
])
h = h2h_features(df).set_index("match_id")
r = h.loc[1]
t3 = True
t3 &= check("h2h_n == 1", r["h2h_n"] == 1, 1, r["h2h_n"])
t3 &= check("h2h_home_wins == 0 (Beta home current tidak pernah menang)",
            r["h2h_home_wins"] == 0, 0, r["h2h_home_wins"])
t3 &= check("h2h_away_wins == 1 (Alpha menang historis, kini away)",
            r["h2h_away_wins"] == 1, 1, r["h2h_away_wins"])
results["T3"] = t3

# T4: 2 match historis: A home menang, B home menang. Target A vs B (A home)
print()
print("=" * 70)
print("T4: A vs B (A menang), B vs A (B menang). Target A vs B (A home)")
print("    Expected: home_wins (A) = 1, away_wins (B) = 1")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Beta", "2024-01-01", 2, 0, "H"),  # Alpha menang
    make_match("Beta", "Alpha", "2024-02-01", 3, 1, "H"),  # Beta menang
    make_match("Alpha", "Beta", "2024-03-01", 1, 1, "D"),  # target id=2
])
h = h2h_features(df).set_index("match_id")
r = h.loc[2]
t4 = True
t4 &= check("h2h_n == 2", r["h2h_n"] == 2, 2, r["h2h_n"])
t4 &= check("h2h_home_wins == 1 (Alpha menang 1x)",
            r["h2h_home_wins"] == 1, 1, r["h2h_home_wins"])
t4 &= check("h2h_away_wins == 1 (Beta menang 1x)",
            r["h2h_away_wins"] == 1, 1, r["h2h_away_wins"])
results["T4"] = t4

# T5: home target alfabetis LEBIH AKHIR (Zebra > Alpha)
print()
print("=" * 70)
print("T5: Alpha vs Zebra (Alpha home) Alpha menang. Target Zebra vs Alpha")
print("    Zebra (home target) alfabetis > Alpha (away target)")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Zebra", "2024-01-01", 3, 0, "H"),  # Alpha menang
    make_match("Zebra", "Alpha", "2024-02-01", 1, 1, "D"),  # target id=1
])
h = h2h_features(df).set_index("match_id")
r = h.loc[1]
t5 = True
t5 &= check("h2h_n == 1", r["h2h_n"] == 1, 1, r["h2h_n"])
t5 &= check("h2h_home_wins == 0 (Zebra tidak pernah menang)",
            r["h2h_home_wins"] == 0, 0, r["h2h_home_wins"])
t5 &= check("h2h_away_wins == 1 (Alpha menang, kini away)",
            r["h2h_away_wins"] == 1, 1, r["h2h_away_wins"])
results["T5"] = t5

# T6: Cutoff — match target dan match sesudah target tidak masuk
print()
print("=" * 70)
print("T6: Cutoff — H2H harus exclude target sendiri & match sesudahnya")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Beta", "2024-01-01", 2, 0, "H"),
    make_match("Alpha", "Beta", "2024-02-01", 3, 0, "H"),  # target id=1
    make_match("Alpha", "Beta", "2024-03-01", 4, 0, "H"),  # sesudah target
])
h = h2h_features(df).set_index("match_id")
r = h.loc[1]
t6 = True
t6 &= check("h2h_n == 1 (hanya match SEBELUM target)",
            r["h2h_n"] == 1, 1, r["h2h_n"])
results["T6"] = t6

# T7: Total goals avg benar
print()
print("=" * 70)
print("T7: h2h_total_goals_avg dihitung benar")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Beta", "2024-01-01", 2, 1, "H"),  # 3 goals
    make_match("Beta", "Alpha", "2024-02-01", 1, 3, "A"),  # 4 goals
    make_match("Alpha", "Beta", "2024-03-01", 0, 0, "D"),  # target id=2
])
h = h2h_features(df).set_index("match_id")
r = h.loc[2]
expected_avg = (3 + 4) / 2
t7 = True
t7 &= check("h2h_n == 2", r["h2h_n"] == 2, 2, r["h2h_n"])
t7 &= check(f"h2h_total_goals_avg == {expected_avg}",
            abs(r["h2h_total_goals_avg"] - expected_avg) < 1e-9,
            expected_avg, r["h2h_total_goals_avg"])
results["T7"] = t7

# T8: Target home alfabetis lebih akhir, A home menang 2x di historis venue swap
print()
print("=" * 70)
print("T8: Target Zebra vs Alpha. Historis: Alpha vs Zebra (A home menang),")
print("    Zebra vs Alpha (Z home menang). Expected: home_wins (Z) = 1, away_wins (A) = 1")
print("-" * 70)
df = build_df([
    make_match("Alpha", "Zebra", "2024-01-01", 2, 0, "H"),  # Alpha (a_team) menang
    make_match("Zebra", "Alpha", "2024-02-01", 3, 1, "H"),  # Zebra (b_team) menang
    make_match("Zebra", "Alpha", "2024-03-01", 1, 1, "D"),  # target id=2
])
h = h2h_features(df).set_index("match_id")
r = h.loc[2]
t8 = True
t8 &= check("h2h_n == 2", r["h2h_n"] == 2, 2, r["h2h_n"])
t8 &= check("h2h_home_wins == 1 (Zebra menang 1x)",
            r["h2h_home_wins"] == 1, 1, r["h2h_home_wins"])
t8 &= check("h2h_away_wins == 1 (Alpha menang 1x)",
            r["h2h_away_wins"] == 1, 1, r["h2h_away_wins"])
results["T8"] = t8

# ---------- Ringkasan ----------
print()
print("=" * 70)
print("RINGKASAN")
print("=" * 70)
passed = sum(1 for v in results.values() if v)
total = len(results)
for test, ok in results.items():
    print(f"  {test}: {'PASS' if ok else 'FAIL'}")
print()
print(f"TOTAL: {passed}/{total} PASS")
print()

# Diagnosis
print("DIAGNOSIS per test FAIL:")
found_fail = False
for test, ok in results.items():
    if not ok:
        found_fail = True
        if test in ("T3", "T4", "T5", "T8"):
            print(f"  {test}: bug identitas H2H — h2h_home_wins/h2h_away_wins "
                  f"tidak menghitung kemenangan tim home/away TARGET, "
                  f"melainkan campuran berbasis alfabetis")
        else:
            print(f"  {test}: investigasi lanjut")
if not found_fail:
    print("  Tidak ada kegagalan. Implementasi H2H sesuai spesifikasi.")
