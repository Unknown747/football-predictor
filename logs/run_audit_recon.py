#!/usr/bin/env python3
import sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'logs')
import numpy as np
import pandas as pd
from reconstruct_pit import reconstruct

# Load samples
with open('logs/audit_recon_samples.json') as f:
    samples = json.load(f)

# Load dataset baru
feat = pd.read_csv('data/features_train.csv', low_memory=False)
feat['Date'] = pd.to_datetime(feat['Date'])

# Load feat_cols (dari audit sebelumnya)
with open('logs/audit_feat_cols_modeB.json') as f:
    feat_cols = json.load(f)

# Kategori kolom untuk report
CATEGORIES = {
    "FORM5": [c for c in feat_cols if 'form5' in c and 'venue' not in c],
    "FORM10": [c for c in feat_cols if 'form10' in c],
    "VENUE": [c for c in feat_cols if 'venue_' in c],
    "REST": [c for c in feat_cols if 'rest' in c],
    "SEASON": [c for c in feat_cols if 'season' in c],
    "H2H": [c for c in feat_cols if 'h2h' in c],
    "DERIVED": [c for c in feat_cols if c.startswith(('diff_', 'sum_'))],
    "ODDS": [c for c in feat_cols if 'odds' in c],
}

overall_pass = True
failures = []

for s in samples:
    name = s['name']
    md = pd.Timestamp(s['date'])
    home = s['home']
    away = s['away']
    league = s['league']

    stored = feat[(feat['Date']==md) &
                  (feat['HomeTeam_canon']==home) &
                  (feat['AwayTeam_canon']==away)]
    if len(stored) == 0:
        print(f"{name}: STORED ROW NOT FOUND")
        overall_pass = False
        failures.append((name, "row missing"))
        continue
    stored = stored.iloc[0]

    recon = reconstruct(md, home, away, league)

    print("=" * 70)
    print(f"{name}: {md.date()} {home} vs {away}")
    print("=" * 70)

    cat_results = {}
    for cat, cols in CATEGORIES.items():
        cat_fail = []
        for c in cols:
            sv = stored.get(c, np.nan)
            rv = recon.get(c, np.nan)

            # Odds: expected mismatch (kita tidak punya odds untuk match historis)
            if cat == "ODDS":
                if not (pd.isna(rv)):
                    cat_fail.append((c, sv, rv, "expected NaN, got value"))
                continue

            if pd.isna(sv) and pd.isna(rv):
                continue
            if pd.isna(sv) != pd.isna(rv):
                cat_fail.append((c, sv, rv, "NaN mismatch"))
                continue
            if abs(float(sv) - float(rv)) > 1e-6:
                cat_fail.append((c, sv, rv, f"diff={abs(float(sv)-float(rv)):.2e}"))

        if len(cat_fail) == 0:
            cat_results[cat] = "PASS"
            print(f"  [{cat:10s}] PASS ({len(cols)} cols)")
        else:
            cat_results[cat] = "FAIL"
            overall_pass = False
            print(f"  [{cat:10s}] FAIL ({len(cat_fail)}/{len(cols)} cols)")
            for c, sv, rv, reason in cat_fail[:5]:
                print(f"     {c}: stored={sv} recon={rv} ({reason})")
            if len(cat_fail) > 5:
                print(f"     ... and {len(cat_fail)-5} more")
            failures.append((name, cat, cat_fail[:5]))

print()
print("=" * 70)
print("OVERALL:", "PASS ✓" if overall_pass else f"FAIL — {len(failures)} failures")
print("=" * 70)

if not overall_pass:
    sys.exit(1)
