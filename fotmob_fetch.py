#!/usr/bin/env python3
"""Fetch fixtures dari FotMob via /leagues/{id}/fixtures/{slug}.
Tidak butuh x-mas, tidak butuh proxy, tidak butuh wrapper.
"""
import subprocess, re, json, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAPPING = json.load(open(BASE / "logs" / "fotmob_league_ids.json"))
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"


def curl_get(url):
    p = subprocess.run(["curl", "-sL", "--compressed", "-A", UA, url],
                       capture_output=True, text=True, timeout=30)
    return p.stdout


def next_data(url):
    html = curl_get(url)
    if not html:
        return None
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def find_matches(node, out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if {"home", "away", "status"} <= node.keys() and "id" in node:
            out.append(node)
        for v in node.values():
            find_matches(v, out)
    elif isinstance(node, list):
        for v in node:
            find_matches(v, out)
    return out


def norm(m):
    st = m.get("status") or {}
    h, a = m.get("home") or {}, m.get("away") or {}
    return {
        "match_id": str(m["id"]),
        "home": h.get("name"),
        "away": a.get("name"),
        "utc": st.get("utcTime"),
        "finished": st.get("finished"),
        "score": st.get("scoreStr"),
    }


def fetch_fixtures(liga, days_ahead=7, sleep_between=1.0):
    """Ambil fixture liga, filter days_ahead hari ke depan (belum selesai)."""
    if liga not in MAPPING:
        raise ValueError(f"Liga tidak dikenal: {liga}")
    info = MAPPING[liga]
    url = f"https://www.fotmob.com/leagues/{info['id']}/fixtures/{info['slug']}"
    data = next_data(url)
    if not data:
        raise RuntimeError(f"Gagal ambil __NEXT_DATA__: {url}")
    matches = find_matches(data)
    seen, rows = set(), []
    for m in matches:
        r = norm(m)
        if r["match_id"] in seen:
            continue
        seen.add(r["match_id"])
        rows.append(r)

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)
    upcoming = []
    for r in rows:
        if r["finished"]:
            continue
        if not r["utc"]:
            continue
        try:
            dt = datetime.fromisoformat(r["utc"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if now <= dt <= cutoff:
            upcoming.append(r)
    upcoming.sort(key=lambda x: x["utc"])
    time.sleep(sleep_between)
    return upcoming


def fetch_all(days_ahead=7, sleep_between=1.0):
    """Ambil fixture semua liga. Return dict liga -> list fixture."""
    out = {}
    for liga in MAPPING:
        try:
            rows = fetch_fixtures(liga, days_ahead, sleep_between)
            out[liga] = rows
            print(f"  {liga:<22} {len(rows):>3} upcoming")
        except Exception as e:
            print(f"  {liga:<22} ERROR: {str(e)[:60]}")
            out[liga] = []
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        res = fetch_all(days)
        total = sum(len(v) for v in res.values())
        print(f"\nTotal: {total} fixture {days} hari")
    else:
        liga = sys.argv[1] if len(sys.argv) > 1 else "England-PL"
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        rows = fetch_fixtures(liga, days)
        print(f"{liga}: {len(rows)} upcoming")
        for r in rows[:10]:
            print(f"  {r['utc']} | {r['home']} vs {r['away']}")
