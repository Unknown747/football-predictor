# Limitations and Risks

1. Data and Features:
- Closing Odds Bias: Model dilatih dengan closing odds. Live prediction dengan opening odds bisa berbeda.
- Tidak ada xG rolling, cedera, atau lineup.
- Tidak ada odds pembanding untuk Home/Away O/U.

2. Split and Evaluation:
- Test period hanya 14 bulan.
- Belum ada validasi prospektif (live).
- Model tidak di-retrain periodik (bisa drift).

3. Model:
- Model tidak bisa mengalahkan bookmaker di 1X2/OU2.5.
- Model menang dari base rate di Home/Away O/U, TAPI belum tentu mengalahkan bookmaker.

4. Calibration:
- Magnitude kecil (-0.0008 logloss).
- Per-liga tidak uniform.

5. Statistik:
- Block bootstrap mengasumsikan korelasi intra-week.
- Multiple testing tanpa koreksi.
- Tidak ada simulasi bankroll.
