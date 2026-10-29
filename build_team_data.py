#!/usr/bin/env python3
"""
Build per-team folders:
  data/<folder>/home.csv
  data/<folder>/away.csv
  data/<folder>/h2h.csv
Plus root:
  h2h_summary.csv
"""
import pandas as pd
from pathlib import Path

BASE = Path("/root/football-predictor")
DATA = BASE / "data"
ROOT_H2H = BASE / "h2h_summary.csv"

# Kolom yang kita simpan di setiap file tim
KEEP_COLS = [
    "Date", "league_code", "league_name", "season",
    "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    # odds 1x2 (Avg fallback B365)
    "B365H", "B365D", "B365A", "PSH", "PSD", "PSA", "AvgH", "AvgD", "AvgA",
    # over/under 2.5
    "B365>2.5", "B365<2.5", "Avg>2.5", "Avg<2.5",
    # AH
    "AHh", "B365AHH", "B365AHA",
]


def main():
    print("=== START build_team_data ===")
    master = pd.read_csv(DATA / "master_canon.csv",
                         low_memory=False, encoding="utf-8-sig")
    print(f"Loaded: {len(master)} matches")

    # Pastikan Date parsed
    master["Date"] = pd.to_datetime(master["Date"], errors="coerce")
    master = master[master["Date"].notna()].copy()

    # Kolom minimum yang ada (jangan asumsikan semua odds tersedia)
    keep = [c for c in KEEP_COLS if c in master.columns]
    base = master[keep + ["HomeTeam_canon", "AwayTeam_canon",
                          "HomeTeam_folder", "AwayTeam_folder"]].copy()

    # Tim unik dari dua sisi
    home_teams = base[["HomeTeam_canon", "HomeTeam_folder"]].drop_duplicates()
    home_teams.columns = ["team", "folder"]
    away_teams = base[["AwayTeam_canon", "AwayTeam_folder"]].drop_duplicates()
    away_teams.columns = ["team", "folder"]
    teams = pd.concat([home_teams, away_teams], ignore_index=True).drop_duplicates()
    teams = teams.dropna().reset_index(drop=True)
    print(f"Unique teams: {len(teams)}")

    # Bersihkan folder lama per tim (jangan sentuh data/master)
    n_created = 0
    n_home = 0
    n_away = 0
    n_h2h_rows = 0
    errors = []

    for _, row in teams.iterrows():
        team = row["team"]
        folder = row["folder"]
        if not isinstance(team, str) or not isinstance(folder, str) or not folder:
            errors.append(f"bad team row: {row.to_dict()}")
            continue

        outdir = DATA / folder
        outdir.mkdir(parents=True, exist_ok=True)
        n_created += 1

        # HOME: tim sebagai HomeTeam
        home_df = base[base["HomeTeam_canon"] == team].copy()
        home_df = home_df.sort_values("Date").reset_index(drop=True)
        if len(home_df):
            home_df.to_csv(outdir / "home.csv", index=False)
            n_home += len(home_df)

        # AWAY: tim sebagai AwayTeam
        away_df = base[base["AwayTeam_canon"] == team].copy()
        away_df = away_df.sort_values("Date").reset_index(drop=True)
        if len(away_df):
            away_df.to_csv(outdir / "away.csv", index=False)
            n_away += len(away_df)

        # H2H: semua match tim (home atau away) dengan kolom tambahan
        h2h = base[(base["HomeTeam_canon"] == team) | (base["AwayTeam_canon"] == team)].copy()
        if len(h2h):
            h2h["opponent"] = h2h.apply(
                lambda r: r["AwayTeam_canon"] if r["HomeTeam_canon"] == team
                else r["HomeTeam_canon"], axis=1)
            h2h["venue"] = h2h.apply(
                lambda r: "H" if r["HomeTeam_canon"] == team else "A", axis=1)
            h2h["team_goals"] = h2h.apply(
                lambda r: r["FTHG"] if r["HomeTeam_canon"] == team else r["FTAG"], axis=1)
            h2h["opp_goals"] = h2h.apply(
                lambda r: r["FTAG"] if r["HomeTeam_canon"] == team else r["FTHG"], axis=1)
            # h2h_match_no per pasangan (urut waktu)
            h2h = h2h.sort_values("Date").reset_index(drop=True)
            h2h["h2h_match_no"] = h2h.groupby("opponent").cumcount() + 1
            # total pertemuan vs opponent (info per baris)
            h2h["h2h_total_vs_opp"] = h2h.groupby("opponent")["Date"].transform("count")
            h2h.to_csv(outdir / "h2h.csv", index=False)
            n_h2h_rows += len(h2h)

    # h2h_summary.csv di root
    print("Building h2h_summary.csv ...")
    all_h2h = []
    for _, row in teams.iterrows():
        team = row["team"]
        folder = row["folder"]
        p = DATA / folder / "h2h.csv"
        if p.exists():
            h = pd.read_csv(p, low_memory=False)
            all_h2h.append(h.groupby("opponent").agg(
                n_matches=("Date", "count"),
                first_date=("Date", "min"),
                last_date=("Date", "max"),
            ).reset_index().assign(team=team))
    if all_h2h:
        summ = pd.concat(all_h2h, ignore_index=True)
        summ = summ[["team", "opponent", "n_matches", "first_date", "last_date"]]
        summ.to_csv(ROOT_H2H, index=False)
        print(f"Saved {ROOT_H2H} ({len(summ)} pairs)")

    print(f"\n=== SUMMARY ===")
    print(f"Teams with folder: {n_created}")
    print(f"Home rows total: {n_home}")
    print(f"Away rows total: {n_away}")
    print(f"H2H rows total: {n_h2h_rows}")
    print(f"Errors: {len(errors)}")
    for e in errors[:5]:
        print(f"  ! {e}")

    # Verifikasi
    folders_on_disk = [p for p in DATA.iterdir() if p.is_dir() and p.name != "__pycache__"]
    print(f"Folders on disk: {len(folders_on_disk)}")
    print("=== END ===")


if __name__ == "__main__":
    main()
