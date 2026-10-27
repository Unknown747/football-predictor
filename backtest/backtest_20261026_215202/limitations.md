# Limitations

## R2: Closing Odds Bias
Training dan test sama-sama menggunakan closing odds (`odds_pH/D/A`, `odds_pOver25`).
Closing odds adalah odds dekat kickoff — sudah incorporate lineup/cedera terbaru.
**Performa backtest ini TIDAK menjamin performa live** dengan opening/current odds.
Model Mode B dengan closing odds di test = bias optimis terhadap skenario live.

## R3: Odds Coverage
`odds_pH/D/A`: 99.87% coverage pada test. `odds_pOver25`: 99.75%.
Baseline odds hanya dihitung pada subset dengan odds valid — fair comparison.

## R4: AUC 1X2
Multiclass AUC dihitung sebagai **macro OvR** (one-vs-rest per class, rata-rata).
Ini bukan satu-satunya interpretasi AUC untuk multiclass. Tidak comparable dengan binary AUC.

## R5: N per League / Season
Grup dengan N < 100 dilaporkan sebagai "insufficient N" — tidak ada kesimpulan.
Test split (2025-07-25 .. 2026-10-21) mencakup akhir musim 2526 + awal 2627.

## R6: Bootstrap Assumption
Bootstrap default: **block by ISO week** (mengasumsikan korelasi intra-week).
Fallback row bootstrap jika unique weeks < 10 — dengan disclaimer eksplisit.
CI 95% percentile-based (bukan BCa).

## R7: Base Rate from Train
Base rate untuk binary target dihitung dari **train split saja** (Date <= 2024-06-30),
tidak termasuk validation atau test — mencegah information leakage.

## R8: Uniform Baseline (1X2 Only)
Uniform [1/3, 1/3, 1/3] hanya untuk 1X2. Untuk binary pakai base_rate_train.
Uniform tidak merepresentasikan skenario live — hanya lower bound naive predictor.

## R9: Determinisme
LightGBM predict menggunakan default `num_threads` — tidak byte-identical deterministic,
tapi statistik stabil. Bootstrap pakai seed 42.
