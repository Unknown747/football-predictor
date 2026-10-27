# Final Project Report - Football Predictor

## 1. Executive Summary
Pipeline ini memproses 40.064 pertandingan dari 22 liga. Menggunakan 6 model LightGBM (Mode B) dengan 78 fitur.

Hasil Utama:
- 1X2 & OU2.5: Model KALAH melawan odds bookmaker (closing).
- Home/Away O/U: Model MENANG melawan base rate, TAPI belum tentu menang melawan bookmaker.

## 2. Status Teknis
- Pipeline end-to-end: PASS
- Backtest reproducible: PASS
- Anti-leakage: PASS
- Point-in-time validity: PASS
- Calibration: INCONCLUSIVE (tidak signifikan)
- Validasi Live / Profitabilitas: BELUM TERVERIFIKASI

## 3. Arsitektur Data
raw/ -> master_canon.csv -> features_train.csv -> models/ -> predict.py -> backtest/

## 4. Metrik Test Set (9.438 match)
- 1X2: Model LogLoss 1.0143 vs Odds 1.0025 (WORSE)
- OU2.5: Model LogLoss 0.6820 vs Odds 0.6781 (WORSE)
- Home O/U 0.5: Model LogLoss 0.5129 vs Base 0.5332 (BETTER)
- Home O/U 1.5: Model LogLoss 0.6539 vs Base 0.6858 (BETTER)
- Away O/U 0.5: Model LogLoss 0.5893 vs Base 0.6074 (BETTER)
- Away O/U 1.5: Model LogLoss 0.6253 vs Base 0.6494 (BETTER)

## 5. Kesimpulan
Jangan gunakan model untuk melawan bookmaker di 1X2/OU2.5. Model bisa digunakan untuk Home/Away O/U karena mengalahkan base rate, tetapi butuh validasi lanjutan dengan odds opening. Tidak ada klaim profitabilitas.
