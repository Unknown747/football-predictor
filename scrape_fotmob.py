#!/usr/bin/env python3
"""
Scrape fixture + xG dari FotMob (tanpa x-mas header).
- Search API untuk resolve matchId
- __NEXT_DATA__ dari halaman match untuk xG
- Cache SQLite untuk hindari hit berulang
"""
import subprocess, json, re, time, sqlite3, sys
from pathlib import Path
from datetime import datetime

BASE = Path("/root/football-predictor")
DB = BASE / "data" / "fotmob_cache.db"
DB.parent.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        utc TEXT, home TEXT, away TEXT,
        xg_home REAL, xg_away REAL,
        status TEXT, scraped_at TEXT
    )""")
    con.commit()
    return con

def curl_get(url, retries=3, sleep=1.5):
    for i in range(retries):
        p = subprocess.run(
            ["curl", "-sL", "--compressed", "-A", UA, url],
            capture_output=True, text=True, timeout=30
        )
        if p.returncode == 0 and p.stdout:
            return p.stdout
        time.sleep(sleep * (i + 1))
    return None

def parse_next_data(html):
    if not html:
        return None
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None

def search_match(term):
    """Resolve matchId dari query 'home away'."""
    url = f"https://apigw.fotmob.com/searchapi/suggest?term={term.replace(' ', '%20')}&lang=en"
    raw = curl_get(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out = []
    for group in data.get("matchSuggest", []):
        for opt in group.get("options", []):
            p = opt.get("payload", {})
            out.append({
                "match_id": str(p.get("id")),
                "home": p.get("homeName"),
                "away": p.get("awayName"),
                "utc": p.get("matchDate"),
                "status": p.get("statusId"),
            })
    return out

def get_match_xg(match_id):
    """Ambil xG dari halaman match via __NEXT_DATA__."""
    html = curl_get(f"https://www.fotmob.com/match/{match_id}")
    data = parse_next_data(html)
    if not data:
        return None
    pp = data.get("props", {}).get("pageProps", {})
    content = pp.get("content") or pp.get("fallback", {}).get("match", {})
    stats = (content.get("stats") or {}).get("Periods", {}).get("All", {}).get("stats", [])
    for group in stats:
        for s in group.get("stats", []):
            if s.get("key") == "expected_goals" or "expected goals" in (s.get("title") or "").lower():
                vals = s.get("stats") or [None, None]
                try:
                    return {"xg_home": float(vals[0]), "xg_away": float(vals[1])}
                except (TypeError, ValueError):
                    return None
    return None

def get_league_fixtures(league_id):
    """Ambil fixture satu liga dari halaman league."""
    html = curl_get(f"https://www.fotmob.com/leagues/{league_id}/matches/overview")
    data = parse_next_data(html)
    if not data:
        return []
    fixtures = data.get("props", {}).get("pageProps", {}).get("fixtures", {}).get("allMatches", [])
    out = []
    for f in fixtures:
        out.append({
            "match_id": str(f.get("id")),
            "utc": f.get("status", {}).get("utcTime"),
            "home": f.get("home", {}).get("name"),
            "away": f.get("away", {}).get("name"),
            "status": f.get("status", {}).get("finished"),
        })
    return out

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", type=str, default="47", help="FotMob league id (47=EPL)")
    parser.add_argument("--search", type=str, help="Search term, e.g. 'arsenal chelsea'")
    parser.add_argument("--match-id", type=str, help="Specific match id")
    args = parser.parse_args()

    con = init_db()

    if args.match_id:
        xg = get_match_xg(args.match_id)
        print(json.dumps({"match_id": args.match_id, "xg": xg}, indent=2))
        if xg:
            con.execute("""INSERT OR REPLACE INTO matches
                (match_id, utc, home, away, xg_home, xg_away, status, scraped_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (args.match_id, None, None, None, xg["xg_home"], xg["xg_away"], "ok", datetime.now().isoformat()))
            con.commit()
        return

    if args.search:
        results = search_match(args.search)
        print(json.dumps(results[:5], indent=2, ensure_ascii=False))
        return

    fixtures = get_league_fixtures(args.league)
    print(f"Found {len(fixtures)} fixtures in league {args.league}")
    for f in fixtures:
        if f.get("status") is False:  # belum selesai
            print(f"  SKIP {f['home']} vs {f['away']} (not finished)")
            continue
        xg = get_match_xg(f["match_id"])
        if xg:
            con.execute("""INSERT OR REPLACE INTO matches
                (match_id, utc, home, away, xg_home, xg_away, status, scraped_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f["match_id"], f["utc"], f["home"], f["away"],
                 xg["xg_home"], xg["xg_away"], "ok", datetime.now().isoformat()))
            print(f"  OK {f['home']} vs {f['away']} xG={xg['xg_home']}-{xg['xg_away']}")
        else:
            print(f"  NO_XG {f['home']} vs {f['away']}")
        time.sleep(1.0)
    con.commit()
    con.close()
    print(f"\nCache: {DB}")

if __name__ == "__main__":
    main()
