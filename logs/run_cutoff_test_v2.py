#!/usr/bin/env python3
import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'logs')
import numpy as np
import pandas as pd
import reconstruct_pit
from reconstruct_pit import reconstruct

with open('logs/audit_recon_samples.json') as f:
    samples = json.load(f)

print("=== CUTOFF TEST: target injection tidak boleh mengubah fitur ===")
all_pass = True
for s in samples:
    md = pd.Timestamp(s['date'])
    home, away, league = s['home'], s['away'], s['league']

    recon = reconstruct(md, home, away, league)

    master_orig = reconstruct_pit.MASTER.copy()
    target_row = {c: np.nan for c in master_orig.columns}
    target_row.update({
        'Date': md,
        'HomeTeam_canon': home,
        'AwayTeam_canon': away,
        'FTHG': 10.0, 'FTAG': 0.0, 'FTR': 'H',
        'HTHG': 5.0, 'HTAG': 0.0, 'HTR': 'H',
        'league_name': league,
        'season': s['season'],
    })
    master_poisoned = pd.concat([master_orig, pd.DataFrame([target_row])],
                                 ignore_index=True)
    reconstruct_pit.MASTER = master_poisoned

    try:
        recon_poisoned = reconstruct(md, home, away, league)
    finally:
        reconstruct_pit.MASTER = master_orig

    diffs = []
    for c in recon:
        v1 = recon[c]
        v2 = recon_poisoned[c]
        if pd.isna(v1) and pd.isna(v2): continue
        if pd.isna(v1) != pd.isna(v2):
            diffs.append((c, v1, v2))
            continue
        if isinstance(v1, (int, float)) and abs(float(v1)-float(v2)) > 1e-9:
            diffs.append((c, v1, v2))

    if len(diffs) == 0:
        print(f"  ✓ {s['name']}: cutoff OK")
    else:
        print(f"  ✗ {s['name']}: {len(diffs)} fitur berubah saat target di-inject!")
        for c, v1, v2 in diffs[:5]:
            print(f"      {c}: normal={v1} poisoned={v2}")
        all_pass = False

print()
print("OVERALL CUTOFF:", "PASS ✓" if all_pass else "FAIL")
sys.exit(0 if all_pass else 1)
