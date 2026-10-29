#!/usr/bin/env python3
"""Validasi & konsolidasi raw CSV -> master dataframe."""
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = Path("/root/football-predictor")
RAW = BASE / "raw"
LOGS = BASE / "logs"
OUT = BASE / "data"
OUT.mkdir(exist_ok=True)

LEAGUE_MAP = {
    "E0": "England-PL", "E1": "England-Champ", "E2": "England-L1",
    "E3": "England-L2", "EC": "England-Conference",
    "SC0": "Scotland-Prem", "SC1": "Scotland-Champ",
    "SC2": "Scotland-L1", "SC3": "Scotland-L2",
    "D1": "Germany-BL1", "D2": "Germany-BL2",
    "I1": "Italy-SA", "I2": "Italy-SB",
    "SP1": "Spain-LaLiga", "SP2": "Spain-Segunda",
    "F1": "France-L1", "F2": "France-L2",
    "N1": "Netherlands-ED", "B1": "Belgium-JPL",
    "P1": "Portugal-Liga1", "T1": "Turkey-SL", "G1": "Greece-SL",
}

# Kolom yang kita butuhkan (semua optional kecuali core)
CORE_COLS = ["Div", "Date", "HomeTeam", "AwayTeam",
             "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR"]
OPTIONAL_COLS = ["Time", "Referee", "HS", "AS", "HST", "AST", "HF", "AF",
                 "HC", "AC", "HY", "AY", "HR", "AR", "HxG", "AxG",
                 # Odds
                 "B365H", "B365D", "B365A",
                 "PSH", "PSD", "PSA",
                 "BWH", "BWD", "BWA",
                 "IWH", "IWD", "IWA",
                 "WHH", "WHD", "WHA",
                 "VCH", "VCD", "VCA",
                 "MaxH", "MaxD", "MaxA",
                 "AvgH", "AvgD", "AvgA",
                 "BFH", "BFD", "BFA",
                 "BFDH", "BFDD", "BFDA",
                 "BVH", "BVD", "BVA",
                 "PPH", "PPD", "PPA",
                 "SKBH", "SKBD", "SKBA",
                 "1XBH", "1XBD", "1XBA",
                 # O/U 2.5
                 "B365>2.5", "B365<2.5",
                 "P>2.5", "P<2.5",
                 "Max>2.5", "Max<2.5",
                 "Avg>2.5", "Avg<2.5",
                 # AH
                 "AHh", "B365AHH", "B365AHA",
                 "AHH", "AHA"]

log_lines = []


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_lines.append(line)


def parse_date(s):
    """Coba beberapa format tanggal football-data.co.uk."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT


def load_one(path):
    """Load satu CSV dan return dataframe dengan kolom tervalidasi."""
    fname = path.stem  # e.g., E0_2122
    m = re.match(r"^([A-Z0-9]+)_(\d{4})$", fname)
    if not m:
        log(f"WARN skip file malformed name: {path.name}")
        return None
    code, season = m.group(1), m.group(2)

    try:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception as e:
        log(f"ERROR read {path.name}: {e}")
        return None

    # Normalisasi nama kolom (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Cek kolom core
    missing = [c for c in CORE_COLS if c not in df.columns]
    if missing:
        log(f"ERROR {fname} missing cols {missing}")
        return None

    # Tambah metadata
    df["league_code"] = code
    df["league_name"] = LEAGUE_MAP.get(code, code)
    df["season"] = season
    df["source_file"] = path.name

    # Buang kolom yg tidak relevan, tapi jangan drop yg ada di OPTIONAL
    keep = CORE_COLS + [c for c in OPTIONAL_COLS if c in df.columns] + \
           ["league_code", "league_name", "season", "source_file"]
    df = df[[c for c in keep if c in df.columns]].copy()

    return df


def main():
    log("=== START validate ===")

    files = sorted(RAW.glob("*.csv"))
    log(f"Files found: {len(files)}")

    frames = []
    for p in files:
        df = load_one(p)
        if df is not None:
            frames.append(df)

    if not frames:
        log("FATAL: no valid files loaded")
        return

    # Union all columns
    log("Concatenating all frames...")
    df = pd.concat(frames, ignore_index=True, sort=False)
    log(f"Raw merged shape: {df.shape}")

    # Parse Date
    log("Parsing dates...")
    df["Date"] = df["Date"].apply(parse_date)
    bad_dates = df["Date"].isna().sum()
    log(f"Bad dates: {bad_dates}")
    if bad_dates > 0:
        log("Sample bad dates:")
        for s in df.loc[df["Date"].isna(), "Date"].head(3):
            log(f"  -> {s!r}")

    # Drop bad dates
    before = len(df)
    df = df[df["Date"].notna()].copy()
    log(f"Dropped {before - len(df)} rows with bad dates")

    # Drop duplicate (same match, same source can't happen, but be safe):
    # key = (league, season, Date, HomeTeam, AwayTeam)
    log("Checking duplicates...")
    dup_mask = df.duplicated(subset=["league_code", "season", "Date",
                                      "HomeTeam", "AwayTeam"], keep="first")
    n_dup = dup_mask.sum()
    log(f"Duplicates found: {n_dup}")
    if n_dup > 0:
        log("Sample duplicates:")
        for _, r in df[dup_mask].head(3).iterrows():
            log(f"  -> {r['Date']} {r['HomeTeam']} vs {r['AwayTeam']}")
        df = df[~dup_mask].copy()

    # Buang baris dengan team kosong
    before = len(df)
    df = df[df["HomeTeam"].notna() & df["AwayTeam"].notna()].copy()
    log(f"Dropped {before - len(df)} rows with missing team")

    # Buang baris dengan FTHG/FTAG NaN tapi FTR terisi (harusnya tidak terjadi)
    before = len(df)
    df = df.dropna(subset=["FTHG", "FTAG", "FTR"]).copy()
    log(f"Dropped {before - len(df)} rows with missing score")

    # Cast numerik
    for c in ["FTHG", "FTAG", "HTHG", "HTAG"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Urutkan
    df = df.sort_values(["Date", "league_code"]).reset_index(drop=True)

    # Simpan master
    master_path = OUT / "master.csv"
    df.to_csv(master_path, index=False)
    log(f"Saved master: {master_path} ({len(df)} rows, {df.shape[1]} cols)")

    # Ringkasan per liga-musim
    log("=== SUMMARY per league-season ===")
    summary_lines = ["league_code,league_name,season,matches,teams,date_min,date_max"]
    for (code, name, season), g in df.groupby(["league_code", "league_name", "season"]):
        teams = set(g["HomeTeam"]).union(set(g["AwayTeam"]))
        dmin = g["Date"].min().strftime("%Y-%m-%d")
        dmax = g["Date"].max().strftime("%Y-%m-%d")
        line = f"{code},{name},{season},{len(g)},{len(teams)},{dmin},{dmax}"
        summary_lines.append(line)
        log(f"  {code:4s} {season}  {len(g):4d} matches  {len(teams):3d} teams  {dmin}..{dmax}")

    (OUT / "summary.csv").write_text("\n".join(summary_lines) + "\n")

    # Total unique teams (belum dinormalisasi)
    all_teams = pd.concat([df["HomeTeam"], df["AwayTeam"]]).dropna().unique()
    log(f"=== GLOBAL ===")
    log(f"Total matches: {len(df)}")
    log(f"Unique team names (RAW): {len(all_teams)}")

    # Distribusi odds availability
    log("=== Odds availability ===")
    for group, cols in [
        ("B365 1X2", ["B365H", "B365D", "B365A"]),
        ("PS 1X2",   ["PSH", "PSD", "PSA"]),
        ("Avg 1X2",  ["AvgH", "AvgD", "AvgA"]),
        ("O/U 2.5 B365", ["B365>2.5", "B365<2.5"]),
        ("O/U 2.5 Avg",  ["Avg>2.5", "Avg<2.5"]),
    ]:
        avail = [c for c in cols if c in df.columns]
        if not avail:
            log(f"  {group}: NONE")
            continue
        nn = df[avail].notna().all(axis=1).sum()
        pct = 100 * nn / len(df)
        log(f"  {group}: {nn}/{len(df)} ({pct:.1f}%)")

    log(f"=== END validate ===")
    (LOGS / "validate.log").write_text("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    main()
