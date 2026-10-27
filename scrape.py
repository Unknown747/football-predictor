#!/usr/bin/env python3
"""Scraper football-data.co.uk - 22 liga x 6 musim = 132 CSV."""
import os
import time
import requests
from datetime import datetime
from pathlib import Path

BASE = Path("/root/football-predictor")
RAW = BASE / "raw"
LOGS = BASE / "logs"
RAW.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

LEAGUES = {
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
SEASONS = ["2122", "2223", "2324", "2425", "2526", "2627"]

HEADERS = {"User-Agent": "Mozilla/5.0 (football-research/1.0)"}
TIMEOUT = 30
RETRIES = 3
SLEEP_BETWEEN = 0.3


def log(msg, file="run.log"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOGS / file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def download(season, code, name):
    dest = RAW / f"{code}_{season}.csv"
    if dest.exists() and dest.stat().st_size > 1000:
        log(f"SKIP {season}/{code} ({dest.stat().st_size}B)")
        return "skip"

    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            if r.status_code == 404:
                log(f"FAIL {season}/{code} 404 NOT_YET_AVAILABLE", "failed.txt")
                return "404"
            if r.status_code != 200:
                last_err = f"HTTP{r.status_code}"
                log(f"RETRY {season}/{code} {last_err} attempt{attempt}/{RETRIES}")
                time.sleep(2)
                continue

            text = r.text
            first_line = text.split("\n", 1)[0] if text else ""
            if "HomeTeam" not in first_line and "home_team" not in first_line.lower():
                log(f"FAIL {season}/{code} invalid_header: {first_line[:100]}", "failed.txt")
                return "invalid"

            # minimal 2 baris data (header + 1 match)
            if len(text.splitlines()) < 2:
                log(f"FAIL {season}/{code} empty_content", "failed.txt")
                return "invalid"

            dest.write_bytes(r.content)
            log(f"OK {season}/{code} {name} -> {dest.name} ({len(r.content)}B, "
                f"{len(text.splitlines())-1} rows)")
            return "ok"
        except requests.RequestException as e:
            last_err = str(e)
            log(f"RETRY {season}/{code} exception attempt{attempt}/{RETRIES}: {last_err}")
            time.sleep(2)

    log(f"FAIL {season}/{code} exhausted_retries last_err={last_err}", "failed.txt")
    return "fail"


def main():
    log("=== START scrape ===")
    # reset failed.txt tiap run supaya akurat
    (LOGS / "failed.txt").write_text("")
    stats = {"ok": 0, "skip": 0, "404": 0, "invalid": 0, "fail": 0}

    total = len(SEASONS) * len(LEAGUES)
    i = 0
    for season in SEASONS:
        for code, name in LEAGUES.items():
            i += 1
            log(f"--- [{i}/{total}] season={season} code={code} ({name}) ---")
            result = download(season, code, name)
            stats[result] = stats.get(result, 0) + 1
            time.sleep(SLEEP_BETWEEN)

    log(f"=== END scrape === {stats}")
    print("\nFINAL STATS:", stats)


if __name__ == "__main__":
    main()
