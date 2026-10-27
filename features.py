#!/usr/bin/env python3
"""
Feature engineering dengan anti-leakage.
Output: data/features_train.csv (1 row per match, semua fitur + target)
"""
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/root/football-predictor")
DATA = BASE / "data"

# ---------- Implied probability helpers ----------

def implied_probs(df, prefix_list):
    """Kembalikan tiga kolom prob (home, draw, away) dari pasangan odds
    pertama yang tersedia di prefix_list. Normalisasi agar sum=1."""
    for pref in prefix_list:
        h, d, a = f"{pref}H", f"{pref}D", f"{pref}A"
        if all(c in df.columns for c in (h, d, a)):
            mask = df[[h, d, a]].notna().all(axis=1) & (df[h] > 1)
            p = pd.DataFrame(index=df.index, columns=["ph", "pd", "pa"], dtype=float)
            hh, dd, aa = 1.0 / df[h], 1.0 / df[d], 1.0 / df[a]
            s = hh + dd + aa
            p["ph"] = hh / s
            p["pd"] = dd / s
            p["pa"] = aa / s
            p.loc[~mask, :] = np.nan
            # isi yang masih NaN dari prefix berikutnya via rekusif
            remaining = p["ph"].isna()
            if remaining.any() and len(prefix_list) > 1:
                rest = implied_probs(df.loc[remaining].copy(),
                                     prefix_list[1:])
                p.loc[remaining, :] = rest.values
            return p
    return pd.DataFrame(np.nan, index=df.index, columns=["ph", "pd", "pa"])


def implied_ou(df):
    """Prob Over 2.5 dari B365 atau Avg."""
    for oh, ou in [("B365>2.5", "B365<2.5"), ("Avg>2.5", "Avg<2.5")]:
        if all(c in df.columns for c in (oh, ou)):
            mask = df[[oh, ou]].notna().all(axis=1) & (df[oh] > 1) & (df[ou] > 1)
            po = 1.0 / df[oh]
            pu = 1.0 / df[ou]
            s = po + pu
            res = (po / s).where(mask, np.nan)
            return res
    return pd.Series(np.nan, index=df.index)


# ---------- Bangun team-level history ----------

def build_team_rows(m):
    """Untuk tiap match buat 2 baris: (team, date, venue, goals_for, goals_against, result_points)"""
    rows = []
    for _, r in m.iterrows():
        # home row
        rows.append({
            "team": r["HomeTeam_canon"],
            "date": r["Date"],
            "venue": "H",
            "gf": r["FTHG"], "ga": r["FTAG"],
            "points": 3 if r["FTR"] == "H" else (1 if r["FTR"] == "D" else 0),
            "won": 1 if r["FTR"] == "H" else 0,
            "drawn": 1 if r["FTR"] == "D" else 0,
            "lost": 1 if r["FTR"] == "A" else 0,
            "cs": 1 if r["FTAG"] == 0 else 0,          # clean sheet
            "failed_to_score": 1 if r["FTHG"] == 0 else 0,
            "league_name": r["league_name"],
            "season": r["season"],
            "match_id": r.name,
        })
        # away row
        rows.append({
            "team": r["AwayTeam_canon"],
            "date": r["Date"],
            "venue": "A",
            "gf": r["FTAG"], "ga": r["FTHG"],
            "points": 3 if r["FTR"] == "A" else (1 if r["FTR"] == "D" else 0),
            "won": 1 if r["FTR"] == "A" else 0,
            "drawn": 1 if r["FTR"] == "D" else 0,
            "lost": 1 if r["FTR"] == "H" else 0,
            "cs": 1 if r["FTHG"] == 0 else 0,
            "failed_to_score": 1 if r["FTAG"] == 0 else 0,
            "league_name": r["league_name"],
            "season": r["season"],
            "match_id": r.name,
        })
    return pd.DataFrame(rows)


def rolling_features(team_df, prefix, window):
    """Untuk tiap tim, rolling N match sebelumnya. Menghasilkan kolom
    dengan suffix f'_{prefix}{window}_'."""
    t = team_df.sort_values(["team", "date", "match_id"]).reset_index(drop=True)

    def roll(col, agg, min_periods=1):
        return (t.groupby("team")[col]
                  .transform(lambda s: s.shift(1)
                              .rolling(window, min_periods=min_periods)
                              .agg(agg)))

    out = pd.DataFrame({
        "team": t["team"],
        "date": t["date"],
        "match_id": t["match_id"],
    })

    for col, agg, name in [
        ("points", "mean", "ppg"),
        ("points", "sum", "pts"),
        ("gf", "mean", "gf"),
        ("ga", "mean", "ga"),
        ("gf", "sum", "gf_sum"),
        ("ga", "sum", "ga_sum"),
        ("won", "mean", "win_rate"),
        ("drawn", "mean", "draw_rate"),
        ("lost", "mean", "loss_rate"),
        ("cs", "mean", "cs_rate"),
        ("failed_to_score", "mean", "fts_rate"),
    ]:
        out[f"{prefix}{name}"] = roll(col, agg)

    # total matches played so far (career)
    out[f"{prefix}n_played"] = (t.groupby("team")["date"]
        .transform(lambda s: s.shift(1).expanding().count()))
    return out


def venue_rolling(team_df, prefix, window):
    """Rolling hanya untuk venue tertentu (home-only atau away-only)."""
    t = team_df.sort_values(["team", "date", "match_id"]).reset_index(drop=True)
    out = pd.DataFrame({"team": t["team"], "date": t["date"], "match_id": t["match_id"]})
    for venue, vtag in [("H", "venue_home"), ("A", "venue_away")]:
        sub = t[t["venue"] == venue].copy()
        g = sub.groupby("team")
        def roll(col, agg):
            return g[col].transform(lambda s: s.shift(1)
                                    .rolling(window, min_periods=1).agg(agg))
        for col, agg, name in [
            ("points", "mean", "ppg"),
            ("gf", "mean", "gf"),
            ("ga", "mean", "ga"),
            ("won", "mean", "win_rate"),
        ]:
            key = f"{vtag}_{prefix}{name}"
            # reindex balik ke t
            tmp = pd.DataFrame({
                "team": sub["team"], "date": sub["date"], "match_id": sub["match_id"],
                key: roll(col, agg)
            })
            out = out.merge(tmp, on=["team", "date", "match_id"], how="left")
    return out


def rest_days(team_df):
    """Hari sejak match sebelumnya per tim."""
    t = team_df.sort_values(["team", "date", "match_id"]).reset_index(drop=True)
    t["rest_days"] = t.groupby("team")["date"].transform(
        lambda s: (s - s.shift(1)).dt.days)
    return t[["team", "date", "match_id", "rest_days"]]


def cumulative_season(team_df):
    """Cumulative ppg dalam musim saat ini (shift 1)."""
    t = team_df.sort_values(["team", "date"]).copy()
    t["season_pts_cum"] = t.groupby(["team", "season"])["points"].transform(
        lambda s: s.shift(1).expanding().sum())
    t["season_n_played"] = t.groupby(["team", "season"])["date"].transform(
        lambda s: s.shift(1).expanding().count())
    t["season_ppg"] = t["season_pts_cum"] / t["season_n_played"]
    return t[["team", "date", "match_id", "season_ppg", "season_n_played"]]


# ---------- H2H ----------

def h2h_features(m):
    """H2H point-in-time. Dipanggil saat training.

    Definisi (post-fix):
    - h2h_n: jumlah pertemuan historis (date < tanggal match ini) untuk pasangan ini.
    - h2h_home_wins: kemenangan tim yang menjadi HOME pada match INI, di seluruh
      pertemuan historis (terlepas dari venue historis).
    - h2h_away_wins: kemenangan tim yang menjadi AWAY pada match INI, di seluruh
      pertemuan historis.
    - h2h_draws: jumlah seri historis.
    - h2h_total_goals_avg: rata-rata total gol historis (NaN jika n==0).

    Implementasi: state disimpan per IDENTITAS TIM (wins_a untuk team_a, wins_b
    untuk team_b), lalu di-assign ke label home/away berdasarkan identitas HOME
    pada match target. Ini memperbaiki bug lama yang menghitung 'home wins'
    historis (venue-based) lalu me-label ulang secara alfabetis.
    """
    m = m.copy()
    if "match_id" not in m.columns:
        raise ValueError("h2h_features: 'match_id' column required")
    m["match_id"] = m["match_id"].astype("int64")
    m["pair"] = m.apply(
        lambda r: tuple(sorted([r["HomeTeam_canon"], r["AwayTeam_canon"]])),
        axis=1,
    )

    # Validasi ringan: pasangan tidak boleh sama (team vs dirinya sendiri)
    bad_pairs = m[m["HomeTeam_canon"] == m["AwayTeam_canon"]]
    if len(bad_pairs) > 0:
        raise ValueError(
            f"h2h_features: {len(bad_pairs)} match dengan HomeTeam == AwayTeam"
        )

    out = []
    for pair, grp in m.groupby("pair", sort=False):
        g = grp.sort_values("Date").reset_index(drop=True)
        team_a, team_b = pair  # sorted, hanya untuk dedup nama
        # State per identitas tim
        wins_a = 0
        wins_b = 0
        draws = 0
        total_goals = 0.0

        for _, r in g.iterrows():
            home = r["HomeTeam_canon"]
            away = r["AwayTeam_canon"]
            n = wins_a + wins_b + draws

            # Assign ke label HOME/AWAY berdasarkan identitas tim HOME pada match INI
            if home == team_a:
                home_wins = wins_a
                away_wins = wins_b
            else:  # home == team_b
                home_wins = wins_b
                away_wins = wins_a

            out.append({
                "match_id": r["match_id"],
                "h2h_n": n,
                "h2h_home_wins": home_wins,
                "h2h_draws": draws,
                "h2h_away_wins": away_wins,
                "h2h_total_goals_avg": (total_goals / n) if n > 0 else np.nan,
            })

            # Update state untuk match berikutnya (pakai hasil match INI).
            # Skip update kalau hasil invalid (NaN) - defensif.
            ftr = r["FTR"]
            fthg = r["FTHG"]
            ftag = r["FTAG"]
            if pd.isna(ftr) or pd.isna(fthg) or pd.isna(ftag):
                # Data invalid: jangan update, tapi tetap hitung n (sudah lewat append)
                continue

            if ftr == "D":
                draws += 1
            elif ftr == "H":
                # Tim home historis menang
                if home == team_a:
                    wins_a += 1
                else:
                    wins_b += 1
            elif ftr == "A":
                # Tim away historis menang
                if away == team_a:
                    wins_a += 1
                else:
                    wins_b += 1
            else:
                raise ValueError(f"h2h_features: FTR tidak dikenal: {ftr!r}")

            total_goals += float(fthg) + float(ftag)

    return pd.DataFrame(out)



# ---------- MAIN ----------

def main():
    print("=== START features ===")
    m = pd.read_csv(DATA / "master_canon.csv", low_memory=False, encoding="utf-8-sig")
    m["Date"] = pd.to_datetime(m["Date"], errors="coerce")
    m = m[m["Date"].notna()].copy().reset_index(drop=True)
    print(f"Matches: {len(m)}")

    # Target labels
    m["target_1x2"] = m["FTR"].map({"H": 0, "D": 1, "A": 2})
    m["target_ou25"] = (m["FTHG"] + m["FTAG"] > 2.5).astype(int)
    m["target_home_ou05"] = (m["FTHG"] > 0.5).astype(int)
    m["target_home_ou15"] = (m["FTHG"] > 1.5).astype(int)
    m["target_away_ou05"] = (m["FTAG"] > 0.5).astype(int)
    m["target_away_ou15"] = (m["FTAG"] > 1.5).astype(int)

    # Implied odds probabilities
    print("Computing implied odds...")
    p1x2 = implied_probs(m, ["Avg", "B365", "PS"])
    m["odds_pH"], m["odds_pD"], m["odds_pA"] = p1x2["ph"], p1x2["pd"], p1x2["pa"]
    m["odds_pOver25"] = implied_ou(m)

    # Bangun team rows
    print("Building team rows...")
    tr = build_team_rows(m)

    print("Rolling features (5)...")
    r5 = rolling_features(tr, "form5_", 5)

    print("Rolling features (10)...")
    r10 = rolling_features(tr, "form10_", 10)

    print("Venue rolling (5)...")
    vh = venue_rolling(tr, "form5_", 5)  # produces venue_home_form5_*, venue_away_form5_*

    print("Rest days...")
    rd = rest_days(tr)

    print("Cumulative season...")
    cs = cumulative_season(tr)

    # Merge all per-team features into one dataframe (team, date, match_id) -> features
    feat = r5.merge(r10, on=["team", "date", "match_id"], how="left")
    feat = feat.merge(vh, on=["team", "date", "match_id"], how="left")
    feat = feat.merge(rd, on=["team", "date", "match_id"], how="left")
    feat = feat.merge(cs, on=["team", "date", "match_id"], how="left")

    # For each match, we have two rows in feat: one for home team, one for away team.
    # Split, prefix, and join.
    # feat punya kolom: form5_*, form10_*, venue_home_form5_*, venue_away_form5_*,
    # rest_days, season_ppg, season_n_played
    # Saat membuat home_feat, prefix "home_" hanya untuk kolom non-venue (venue sudah jelas)
    def prefix_side(df, side):
        """side = 'home' atau 'away'.
        Venue columns: hanya pertahankan yang relevan untuk sisi ini.
        - home team -> pakai venue_home_*  (form kandang tim home)
        - away team -> pakai venue_away_*  (form tandang tim away)
        Lalu rename venue_home_* / venue_away_* -> venue_* dan prefiks side.
        """
        out = df.copy().rename(columns={"team": f"{side.capitalize()}Team_canon",
                                        "date": "Date"})
        keep_venue_prefix = "venue_home_" if side == "home" else "venue_away_"
        drop_cols = [c for c in out.columns
                     if c.startswith("venue_") and not c.startswith(keep_venue_prefix)]
        out = out.drop(columns=drop_cols)

        rename = {}
        for c in out.columns:
            if c.startswith("venue_home_"):
                # venue_home_form5_ppg -> home_venue_form5_ppg
                rename[c] = f"{side}_" + c.replace("venue_home_", "venue_", 1)
            elif c.startswith("venue_away_"):
                rename[c] = f"{side}_" + c.replace("venue_away_", "venue_", 1)
            elif c in ("HomeTeam_canon", "AwayTeam_canon", "Date", "match_id"):
                continue
            else:
                rename[c] = f"{side}_{c}"
        out = out.rename(columns=rename)
        return out

    home_feat = prefix_side(feat, "home")
    away_feat = prefix_side(feat, "away")

    print("Joining features to matches...")
    m2 = m.copy().reset_index().rename(columns={"index": "match_id"})
    m2["match_id"] = m2["match_id"].astype("int64")

    home_feat_join = home_feat.drop(columns=["match_id"], errors="ignore")
    away_feat_join = away_feat.drop(columns=["match_id"], errors="ignore")
    m2 = m2.merge(home_feat_join,
                  on=["HomeTeam_canon", "Date"], how="left")
    m2 = m2.merge(away_feat_join,
                  on=["AwayTeam_canon", "Date"], how="left")

    # H2H features
    print("H2H features...")
    h2h = h2h_features(m2)
    h2h["match_id"] = h2h["match_id"].astype("int64")
    m2 = m2.merge(h2h, on="match_id", how="left")

    # Derived features
    m2["diff_ppg5"] = m2["home_form5_ppg"] - m2["away_form5_ppg"]
    m2["diff_gf5"] = m2["home_form5_gf"] - m2["away_form5_gf"]
    m2["diff_ga5"] = m2["home_form5_ga"] - m2["away_form5_ga"]
    m2["diff_ppg10"] = m2["home_form10_ppg"] - m2["away_form10_ppg"]
    m2["diff_season_ppg"] = m2["home_season_ppg"] - m2["away_season_ppg"]
    m2["sum_expected_goals"] = m2["home_form5_gf"] + m2["away_form5_gf"]
    # venue-split derived:
    # home_venue_form5_ppg = form kandang tim home
    # away_venue_form5_ppg = form tandang tim away
    if ("home_venue_form5_ppg" in m2.columns
            and "away_venue_form5_ppg" in m2.columns):
        m2["diff_venue_ppg"] = (m2["home_venue_form5_ppg"]
                                - m2["away_venue_form5_ppg"])

    print("Saving features...")
    out = DATA / "features_train.csv"
    m2.to_csv(out, index=False)
    print(f"Saved {out} shape={m2.shape}")

    # Sanity: cek NaN rate kolom fitur utama
    print("\n=== NaN rate fitur kunci ===")
    key_cols = [c for c in m2.columns if c.startswith(("home_form5_", "away_form5_",
                "diff_", "h2h_", "odds_"))]
    for c in key_cols[:20]:
        print(f"  {c:35s} NaN {m2[c].isna().sum():5d} ({100*m2[c].isna().mean():.1f}%)")
    print("=== END ===")


if __name__ == "__main__":
    main()
