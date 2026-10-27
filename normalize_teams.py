#!/usr/bin/env python3
"""
Normalisasi nama tim v2: manual dict + strict fuzzy + blocklist + audit.
Spec:
- WRatio scorer
- auto-merge >= 95 + semua guard lolos
- suggest 90-94 (tidak merge, untuk review)
- Guard: min_length>=6, |len_a-len_b|<3, ada token identik non-stopword,
  tidak ada tahun berbeda, tidak di blocklist, geo token terakhir tidak konflik
"""
import re
import unicodedata
import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz, process
from collections import defaultdict

BASE = Path("/root/football-predictor")
DATA = BASE / "data"
LOGS = BASE / "logs"
CONFIG = BASE / "config"
LOGS.mkdir(exist_ok=True)
CONFIG.mkdir(exist_ok=True)

# ============ ALIAS EXPANSION (spesifik & aman) ============
ALIASES = {
    "Utd": "United",
    "St": "Saint",
    "Sp Prague": "Sparta Prague",
    # tidak alias global Ath->Athletic (bikin Bilbao~Madrid)
    "Ath": "Athletic",  # aman karena yg dominan "Ath Bilbao"/"Ath Madrid" manual-handled
}

# ============ STOPWORDS untuk Guard 3 ============
STOPWORDS = {
    "fc", "cf", "sc", "ac", "as", "ss", "ssc", "sv", "vfl", "vfb",
    "ca", "cd", "ud", "sd", "rc", "rcd", "real",  # real kalau sendirian bukan token geo
    "the", "de", "of", "the",
}

# ============ MANUAL (sama seperti v1, diringkas di sini) ============
MANUAL = {
    # Inggris
    "Man United": "Manchester United", "Man Utd": "Manchester United",
    "Man City": "Manchester City", "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest",
    "Sheffield Weds": "Sheffield Wednesday", "Sheffield Utd": "Sheffield United",
    "West Ham": "West Ham United", "West Brom": "West Bromwich Albion",
    "Wolves": "Wolverhampton", "Tottenham": "Tottenham Hotspur",
    "QPR": "Queens Park Rangers", "Stoke": "Stoke City",
    "Swansea": "Swansea City", "Hull": "Hull City", "Cardiff": "Cardiff City",
    "Leicester": "Leicester City", "Norwich": "Norwich City",
    "Bournemouth": "Bournemouth",
    "Brighton": "Brighton & Hove Albion",
    "Peterboro": "Peterborough United",
    "Accrington": "Accrington Stanley",
    "Milton Keynes Dons": "MK Dons", "MK Dons": "MK Dons",
    "Bradford": "Bradford City", "Burton": "Burton Albion",
    "Cambridge": "Cambridge United", "Carlisle": "Carlisle United",
    "Cheltenham": "Cheltenham Town", "Colchester": "Colchester United",
    "Crawley": "Crawley Town", "Crewe": "Crewe Alexandra",
    "Doncaster": "Doncaster Rovers", "Exeter": "Exeter City",
    "Fleetwood": "Fleetwood Town", "Forest Green": "Forest Green Rovers",
    "Grimsby": "Grimsby Town", "Harrogate": "Harrogate Town",
    "Hartlepool": "Hartlepool United", "Lincoln": "Lincoln City",
    "Mansfield": "Mansfield Town", "Morecambe": "Morecambe",
    "Newport": "Newport County", "Northampton": "Northampton Town",
    "Notts County": "Notts County", "Oxford": "Oxford United",
    "Plymouth": "Plymouth Argyle", "Port Vale": "Port Vale",
    "Portsmouth": "Portsmouth", "Rotherham": "Rotherham United",
    "Salford": "Salford City", "Scunthorpe": "Scunthorpe United",
    "Shrewsbury": "Shrewsbury Town", "Southend": "Southend United",
    "Stockport": "Stockport County", "Sutton": "Sutton United",
    "Swindon": "Swindon Town", "Tranmere": "Tranmere Rovers",
    "Wigan": "Wigan Athletic", "Wimbledon": "AFC Wimbledon",
    "Wycombe": "Wycombe Wanderers", "Yeovil": "Yeovil Town",
    # Skotlandia
    "Dundee Utd": "Dundee United",
    "Inverness C": "Inverness Caledonian Thistle",
    "Inverness CT": "Inverness Caledonian Thistle",
    "Hamilton": "Hamilton Academical",
    # Jerman
    "Dortmund": "Borussia Dortmund", "B Dortmund": "Borussia Dortmund",
    "M'gladbach": "Borussia Monchengladbach",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "Leverkusen": "Bayer Leverkusen", "Wolfsburg": "VfL Wolfsburg",
    "Hertha": "Hertha Berlin", "Hamburg": "Hamburger SV",
    "Hoffenheim": "TSG Hoffenheim", "Freiburg": "SC Freiburg",
    "Augsburg": "FC Augsburg", "Mainz": "Mainz 05",
    "Stuttgart": "VfB Stuttgart", "Union Berlin": "Union Berlin",
    "Bochum": "VfL Bochum", "Bielefeld": "Arminia Bielefeld",
    "Darmstadt": "Darmstadt 98", "Heidenheim": "1. FC Heidenheim",
    "Holstein Kiel": "Holstein Kiel", "St Pauli": "FC St Pauli",
    # Italia
    "Milan": "AC Milan", "Inter": "Inter Milan", "Inter Milan": "Inter Milan",
    "Roma": "AS Roma", "Verona": "Hellas Verona",
    "Hellas Verona": "Hellas Verona",
    # Spanyol
    "Ath Bilbao": "Athletic Bilbao", "Ath Madrid": "Atletico Madrid",
    "Sociedad": "Real Sociedad", "Betis": "Real Betis",
    "Espanol": "Espanyol", "Espanyol": "Espanyol",
    "Alaves": "Deportivo Alaves", "Vallecano": "Rayo Vallecano",
    "Celta": "Celta Vigo", "Valladolid": "Real Valladolid",
    "Leganes": "Leganes", "Oviedo": "Real Oviedo",
    # Prancis
    "Paris SG": "Paris Saint-Germain",
    "Paris Saint Germain": "Paris Saint-Germain",
    "Marseille": "Olympique Marseille", "Lyon": "Olympique Lyonnais",
    "Monaco": "AS Monaco", "Nice": "OGC Nice",
    "Rennes": "Stade Rennais", "Lens": "RC Lens",
    "St Etienne": "Saint-Etienne", "Strasbourg": "RC Strasbourg",
    "Nantes": "FC Nantes", "Reims": "Stade de Reims",
    "Brest": "Stade Brestois", "Auxerre": "AJ Auxerre",
    "Clermont": "Clermont Foot",
    # Belanda
    "PSV": "PSV Eindhoven", "AZ": "AZ Alkmaar",
    "Twente": "FC Twente", "Utrecht": "FC Utrecht",
    "Heerenveen": "SC Heerenveen", "Groningen": "FC Groningen",
    "Nijmegen": "NEC Nijmegen", "NEC": "NEC Nijmegen",
    "Waalwijk": "RKC Waalwijk", "Heracles": "Heracles Almelo",
    "Zwolle": "PEC Zwolle", "Cambuur": "SC Cambuur",
    "Emmen": "FC Emmen", "Volendam": "FC Volendam",
    # Belgia
    "Standard": "Standard Liege", "Gent": "KAA Gent",
    "Antwerp": "Royal Antwerp", "Charleroi": "Sporting Charleroi",
    "Mechelen": "KV Mechelen", "Westerlo": "KVC Westerlo",
    "Leuven": "OH Leuven", "OH Leuven": "OH Leuven",
    "St Truiden": "Sint-Truiden", "Sint-Truiden": "Sint-Truiden",
    "Kortrijk": "KV Kortrijk", "Eupen": "KAS Eupen",
    "Oostende": "KV Oostende", "Zulte-Waregem": "Zulte Waregem",
    "Waregem": "Zulte Waregem", "Seraing": "RFC Seraing",
    "RWDM": "RWD Molenbeek",
    # Portugal
    "Porto": "FC Porto", "Sporting": "Sporting CP",
    "Sporting CP": "Sporting CP", "Braga": "SC Braga",
    "Vitoria": "Vitoria Guimaraes", "Guimaraes": "Vitoria Guimaraes",
    "Estrela": "Estrela Amadora",
    # Turki
    "Basaksehir": "Istanbul Basaksehir",
    "Rizespor": "Caykur Rizespor", "Caykur Rizespor": "Caykur Rizespor",
    # Yunani
    "Olympiakos": "Olympiacos", "Olympiacos": "Olympiacos",
    "AEK": "AEK Athens", "AEK Athens": "AEK Athens",
    "Aris": "Aris Thessaloniki", "Aris Thessaloniki": "Aris Thessaloniki",
    "OFI": "OFI Crete", "OFI Crete": "OFI Crete",
    "Volos": "Volos NFC", "Volos NFC": "Volos NFC",
    "Giannina": "PAS Giannina", "PAS Giannina": "PAS Giannina",
    "Lamias": "Lamia", "Lamia": "Lamia",
}


# ============ HELPERS ============


# ============ RESERVE TEAM SUFFIXES (Guard 7) ============
RESERVE_SUFFIXES = {"b", "ii", "u19", "u21", "u23", "women", "w", "reserves", "res", "youth"}


def is_reserve_team(name):
    toks = name.split()
    if not toks:
        return False
    last = toks[-1].lower().strip(".")
    return last in RESERVE_SUFFIXES

def load_blocklist():
    path = CONFIG / "fuzzy_blocklist.txt"
    pairs = set()
    if not path.exists():
        return pairs
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 2:
                a, b = parts
                pairs.add(frozenset([a, b]))
    return pairs


def is_blocked(a, b, pairs):
    return frozenset([a, b]) in pairs


def alias_expand(name):
    """Terapkan alias map per token (case-insensitive)."""
    tokens = name.split()
    out = []
    i = 0
    while i < len(tokens):
        # coba 2-token match dulu (misal "Sp Prague")
        if i + 1 < len(tokens):
            two = f"{tokens[i]} {tokens[i+1]}"
            if two in ALIASES:
                out.extend(ALIASES[two].split())
                i += 2
                continue
        if tokens[i] in ALIASES:
            out.extend(ALIASES[tokens[i]].split())
        else:
            out.append(tokens[i])
        i += 1
    return " ".join(out)


def tokens_nonstop(name):
    """Token lowercase non-stopword untuk pembanding."""
    toks = re.findall(r"[A-Za-z0-9]+", name.lower())
    return [t for t in toks if t not in STOPWORDS and len(t) >= 2]


def has_year(name):
    return re.findall(r"\b(?:18|19|20)\d{2}\b|\b0\d\b", name)


def last_geo_token(name):
    """Ambil token terakhir non-angka non-stopword sebagai indikator geo/club."""
    toks = [t for t in re.findall(r"[A-Za-z]+", name) if t.lower() not in STOPWORDS]
    return toks[-1].lower() if toks else ""


def check_guards(a_raw, b_raw, score, blocklist):
    """Kembalikan (pass_guards: bool, reason: str)."""
    a = alias_expand(a_raw)
    b = alias_expand(b_raw)

    if is_blocked(a_raw, b_raw, blocklist):
        return False, "blocklisted"

    if is_reserve_team(a_raw) or is_reserve_team(b_raw):
        return False, "reserve_team"

    if len(a) < 6 or len(b) < 6:
        return False, "len<6"

    if abs(len(a) - len(b)) >= 3:
        return False, f"len_diff={abs(len(a)-len(b))}>=3"

    ta, tb = tokens_nonstop(a), tokens_nonstop(b)
    common = set(ta) & set(tb)
    if not common:
        return False, "no_common_token"

    ya, yb = has_year(a), has_year(b)
    if ya or yb:
        if set(ya) != set(yb):
            return False, f"year_mismatch({ya} vs {yb})"

    if last_geo_token(a) != last_geo_token(b):
        # kalau beda geotoken, hanya boleh kalau salah satu adalah prefix/subset
        # supaya "Fortuna Sittard" vs "Sittard" tetap lolos
        if not (last_geo_token(a) in b.lower() or last_geo_token(b) in a.lower()):
            return False, f"geo({last_geo_token(a)}!={last_geo_token(b)})"

    return True, f"ok(score={score:.1f})"


def slugify(name):
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s or "unknown"


# ============ MAIN ============

def main():
    print("=== START normalize v2 ===")
    blocklist = load_blocklist()
    print(f"Blocklist pairs loaded: {len(blocklist)}")

    master = pd.read_csv(DATA / "master.csv", low_memory=False, encoding="utf-8-sig")
    print(f"Loaded master: {len(master)} rows")

    raw_names = sorted(set(
        list(master["HomeTeam"].dropna().unique()) +
        list(master["AwayTeam"].dropna().unique())
    ))
    print(f"Raw team names: {len(raw_names)}")

    # Step 1: manual map
    after_manual = {}
    for n in raw_names:
        after_manual[n] = MANUAL.get(n, n)

    manual_names = sorted(set(after_manual.values()))
    print(f"After manual: {len(manual_names)} unique")

    # Step 2: canonical set utamakan yang sudah manual
    canonical = set(manual_names)
    # akan kita coba merge; iterasi dari nama terpanjang -> pendek supaya
    # nama versi panjang jadi target jika cocok
    fuzzy_merges = []
    suggest = []

    name_to_canonical = {n: n for n in manual_names}

    # Iterasi: cari duplikat
    # Urutkan by length descending: nama pendek cenderung fragment (misal "Airdrie Utd" 
    # bisa jadi alias "Airdrieonians"), tapi kita tidak tahu arah. 
    # Strategi: sort by length asc -> nama pendek jadi "anchor" yang dicoba match 
    # ke nama lebih panjang. Tapi itu kebalikan dari intuisi. 
    # Yang benar: untuk tiap nama, cek apakah ada canonical LAIN yang lebih "lengkap".
    # Pakai process.extract dengan WRatio ke semua canonical lain.
    ordered = sorted(manual_names, key=lambda x: (-len(x), x))

    removed = set()
    for name in ordered:
        if name in removed:
            continue
        # cari kandidat dari canonical yang BELUM dihapus dan bukan diri sendiri
        candidates = [c for c in canonical if c != name and c not in removed]
        if not candidates:
            continue
        matches = process.extract(name, candidates, scorer=fuzz.WRatio,
                                  limit=3, score_cutoff=90)
        if not matches:
            continue
        for cand_name, score, _ in matches:
            passed, reason = check_guards(name, cand_name, score, blocklist)
            if score >= 95 and passed:
                # auto-merge: name -> cand_name
                name_to_canonical[name] = cand_name
                removed.add(name)
                fuzzy_merges.append({
                    "raw_name": name,
                    "canonical_target": cand_name,
                    "score": round(score, 1),
                    "scorer": "WRatio",
                    "tokens_a": "|".join(tokens_nonstop(name)),
                    "tokens_b": "|".join(tokens_nonstop(cand_name)),
                    "manual_override": name in MANUAL,
                    "blocklisted": False,
                    "decision": "AUTO_MERGE",
                    "reason": reason,
                })
                break
            elif 90 <= score < 95:
                suggest.append({
                    "raw_name": name,
                    "candidate": cand_name,
                    "score": round(score, 1),
                    "reason": reason,
                })
                # tidak break: bisa ada kandidat lain dengan skor auto-merge
            else:
                # score >= 95 tapi guard gagal -- catat untuk audit
                if score >= 95:
                    suggest.append({
                        "raw_name": name,
                        "candidate": cand_name,
                        "score": round(score, 1),
                        "reason": f"REJECTED: {reason}",
                    })

    # Terapkan chain: raw -> manual -> fuzzy
    final_map = {}
    for raw in raw_names:
        mid = after_manual[raw]
        final_map[raw] = name_to_canonical.get(mid, mid)

    # Cek slug collision
    slug_map = defaultdict(list)
    for raw, can in final_map.items():
        slug_map[slugify(can)].append(can)
    collisions = {s: sorted(set(v)) for s, v in slug_map.items() if len(set(v)) > 1}
    if collisions:
        print(f"\n!!! SLUG COLLISIONS: {collisions}")

    # Simpan team_map.csv
    rows = []
    for raw, can in sorted(final_map.items()):
        rows.append({
            "raw_name": raw,
            "canonical_name": can,
            "folder_name": slugify(can),
            "manual_override": raw in MANUAL,
            "is_self_canonical": raw == can,
        })
    tm = pd.DataFrame(rows)
    tm.to_csv(BASE / "team_map.csv", index=False)
    print(f"Saved team_map.csv ({len(tm)} rows)")

    # Simpan audit
    if fuzzy_merges:
        pd.DataFrame(fuzzy_merges).to_csv(LOGS / "fuzzy_merges.csv", index=False)
        print(f"Saved fuzzy_merges.csv: {len(fuzzy_merges)} auto-merge")
    else:
        (LOGS / "fuzzy_merges.csv").write_text(
            "raw_name,canonical_target,score,scorer,tokens_a,tokens_b,"
            "manual_override,blocklisted,decision,reason\n")
        print("fuzzy_merges.csv: EMPTY (no auto-merge)")

    if suggest:
        pd.DataFrame(suggest).to_csv(LOGS / "fuzzy_candidates.csv", index=False)
        print(f"Saved fuzzy_candidates.csv: {len(suggest)} candidates for review")
    else:
        (LOGS / "fuzzy_candidates.csv").write_text(
            "raw_name,candidate,score,reason\n")
        print("fuzzy_candidates.csv: EMPTY")

    # Terapkan ke master
    master["HomeTeam_canon"] = master["HomeTeam"].map(final_map)
    master["AwayTeam_canon"] = master["AwayTeam"].map(final_map)
    master["HomeTeam_folder"] = master["HomeTeam_canon"].apply(slugify)
    master["AwayTeam_folder"] = master["AwayTeam_canon"].apply(slugify)
    master.to_csv(DATA / "master_canon.csv", index=False)
    print(f"Saved master_canon.csv ({len(master)} rows)")

    print(f"\nFinal canonical names: {len(set(final_map.values()))}")
    print(f"Auto-merges: {len(fuzzy_merges)}")
    print(f"Suggest candidates: {len(suggest)}")
    print("=== END normalize v2 ===")


if __name__ == "__main__":
    main()
