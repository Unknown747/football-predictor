#!/usr/bin/env python3
"""Scrape fixture 7 hari dari FotMob (test version — output ke /tmp/)."""
import sys, json
from pathlib import Path
from datetime import datetime, timezone
from rapidfuzz import process, fuzz

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from fotmob_fetch import fetch_all
import pandas as pd

# Load database tim
tm = pd.read_csv(BASE / "team_map.csv")
aliases = pd.read_csv(BASE / "team_aliases_override.csv")

lookup = {}
for _, r in tm.iterrows():
    if pd.notna(r["raw_name"]): lookup[str(r["raw_name"]).strip().lower()] = r["canonical_name"]
    if pd.notna(r["canonical_name"]): lookup[str(r["canonical_name"]).strip().lower()] = r["canonical_name"]
for _, r in aliases.iterrows():
    if pd.notna(r["external_name"]): lookup[str(r["external_name"]).strip().lower()] = r["canonical_name"]

canon_set = list(lookup.keys())


def resolve_team(name):
    """Resolve nama tim ke canonical. Return (canon, match_type, score)."""
    if not name:
        return None, "empty", 0
    n = str(name).strip()
    key = n.lower()
    # Exact
    if key in lookup:
        return lookup[key], "exact", 100
    # Fuzzy 95
    best = process.extractOne(key, canon_set, scorer=fuzz.WRatio)
    if best and best[1] >= 95:
        return lookup[best[0]], "fuzzy95", best[1]
    # Fuzzy 85
    if best and best[1] >= 85:
        return lookup[best[0]], "fuzzy85", best[1]
    return None, "unmatched", best[1] if best else 0


def main(days=7, out_path=f"predictions/fixtures_7hari/fixture_7hari_{datetime.now().strftime('%Y%m%d')}.csv"):
    print(f"=== Fetch fixture {days} hari dari FotMob ===")
    fixtures_by_liga = fetch_all(days)

    rows = []
    unresolved = []
    for liga, fixtures in fixtures_by_liga.items():
        for f in fixtures:
            home_c, h_type, h_score = resolve_team(f["home"])
            away_c, a_type, a_score = resolve_team(f["away"])
            if home_c is None or away_c is None:
                unresolved.append({
                    "liga": liga, "home": f["home"], "away": f["away"],
                    "h_type": h_type, "h_score": h_score,
                    "a_type": a_type, "a_score": a_score,
                })
                continue
            # Parse tanggal
            try:
                dt = datetime.fromisoformat(f["utc"].replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                continue
            rows.append({
                "date": date_str,
                "home_team": home_c,
                "away_team": away_c,
                "league_name": liga,
                "match_id_fotmob": f["match_id"],
                "utc": f["utc"],
            })

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df = df.drop_duplicates(subset=["date", "home_team", "away_team"]).reset_index(drop=True)
        df = df.sort_values(["date", "home_team"]).reset_index(drop=True)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path} ({len(df)} match)")

    if unresolved:
        print(f"\n⚠️  {len(unresolved)} fixture dengan tim tidak resolved:")
        for u in unresolved[:20]:
            print(f"  [{u['liga']}] {u['home']} vs {u['away']} "
                  f"(h={u['h_type']}/{u['h_score']:.0f}, a={u['a_type']}/{u['a_score']:.0f})")

    print(f"\n=== Ringkasan per liga ===")
    if len(df) > 0:
        print(df.groupby("league_name").size().to_string())
    print(f"\nTotal: {len(df)} match, {len(unresolved)} unresolved")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", default="predictions/fixtures_7hari/fixture_fotmob_latest.csv")
    args = parser.parse_args()
    main(args.days, args.output)
