#!/usr/bin/env python3
"""
Ringkasan verdict global per mode dari comparison_retrain.json.
"""
import json
from collections import Counter
from pathlib import Path

with open("logs/comparison_retrain.json") as f:
    data = json.load(f)

for mode in ["mode_A", "mode_B"]:
    summary = data[mode]
    print()
    print("=" * 70)
    print(f"RINGKASAN VERDICT MODE {mode}")
    print("=" * 70)

    total = 0
    verdicts = Counter()
    better_markets = []
    worse_markets = []

    for market, metrics in summary.items():
        # Fokus pada metrik utama: logloss untuk binary & multiclass, plus AUC binary
        primary = "logloss"
        v = metrics.get(primary, {}).get("verdict", "-")
        total += 1
        verdicts[v] += 1

        if v == "BETTER":
            better_markets.append(f"{market} (Δlogloss={metrics[primary]['delta']:+.4f})")
        elif v == "WORSE":
            worse_markets.append(f"{market} (Δlogloss={metrics[primary]['delta']:+.4f})")

    print(f"Total pasar: {total}")
    for v, cnt in verdicts.items():
        print(f"  {v}: {cnt}")
    print()
    if better_markets:
        print("BETTER markets:")
        for m in better_markets:
            print(f"  ✓ {m}")
    if worse_markets:
        print("WORSE markets:")
        for m in worse_markets:
            print(f"  ✗ {m}")
    if not better_markets and not worse_markets:
        print("Semua pasar NEUTRAL (Δlogloss < 0.001)")

    # Cek target utama: apakah model baru lebih baik di 1x2 logloss?
    print()
    print("Catatan interpretasi:")
    print("- Δlogloss < -0.001 = BETTER (model baru lebih baik)")
    print("- |Δlogloss| < 0.001 = NEUTRAL (noise)")
    print("- Δlogloss > 0.001 = WORSE (model baru lebih buruk)")
    print("- H2H fix diisolasi di 2 kolom fitur — bukan klaim kausal")
