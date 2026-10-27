#!/usr/bin/env python3
import sys, json, hashlib
sys.path.insert(0, '.')
sys.path.insert(0, 'logs')
import pandas as pd
from reconstruct_pit import reconstruct

with open('logs/audit_recon_samples.json') as f:
    samples = json.load(f)

def hash_recon(rec):
    items = sorted(rec.items())
    s = "|".join(f"{k}={v}" for k, v in items)
    return hashlib.sha256(s.encode()).hexdigest()

print("=== DETERMINISME: run 2x ===")
all_pass = True
for s in samples:
    md = pd.Timestamp(s['date'])
    h1 = hash_recon(reconstruct(md, s['home'], s['away'], s['league']))
    h2 = hash_recon(reconstruct(md, s['home'], s['away'], s['league']))
    if h1 == h2:
        print(f"  ✓ {s['name']}: hash sama {h1[:16]}...")
    else:
        print(f"  ✗ {s['name']}: hash BEDA {h1[:16]} vs {h2[:16]}")
        all_pass = False

print()
print("OVERALL DETERMINISME:", "PASS ✓" if all_pass else "FAIL")
sys.exit(0 if all_pass else 1)
