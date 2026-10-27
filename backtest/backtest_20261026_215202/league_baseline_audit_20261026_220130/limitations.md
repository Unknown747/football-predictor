# Limitations — League Baseline Audit L10.4

1. **Base rate global (train-only)**: Untuk Home/Away O/U, base rate dihitung dari
   train split (Date <= 2024-06-30) dan bersifat GLOBAL (satu nilai per market).
   Bukan per-liga. Alasan: konsisten dengan `backtest.py` dan per-liga base rate
   tidak signifikan berubah (variansi kecil antar liga).

2. **Odds baseline only on n_common**: Untuk 1x2 dan ou25, model dan baseline
   dibandingkan pada subset yang sama (n_common = rows dengan odds valid).
   Model logloss pada n_common bisa berbeda dari model logloss pada full sample
   (n_model) karena drop odds missing. Ini menghindari perbandingan tidak fair.

3. **Odds implied normalization**: Untuk 1x2, odds baseline dinormalisasi sebagai
   implied probability (1/H + 1/D + 1/A) lalu dibagi sum (overround removed).
   Konsisten dengan `features.py implied_probs`. Untuk ou25, `odds_pOver25` di
   `features_train.csv` sudah berupa implied prob normalized (dari Avg/B365).

4. **Bootstrap block_week**: Default block by ISO week. Fallback row bootstrap
   jika unique weeks < 10 (dicatat di bootstrap_ci.json `method`). Paired: model
   dan baseline di-resample dengan index yang sama. Seed = 42, n_iter = 1000.
   CI 95% percentile-based (bukan BCa).

5. **Verdict threshold strict**: BETTER hanya jika ci_high < 0 (seluruh CI di
   bawah 0). WORSE hanya jika ci_low > 0. INCONCLUSIVE jika CI cross 0.
   INSUFFICIENT N jika n_common < 100.

6. **Closing odds bias (R2)**: Untuk 1x2 dan ou25, baseline odds adalah CLOSING
   odds (dekat kickoff). Model dilatih dengan closing odds yang sama. Ini bias
   optimis — tidak menjamin performa live dengan opening/current odds.

7. **Home/Away O/U tanpa odds baseline**: Tidak ada odds untuk pasar ini di
   football-data.co.uk. Baseline = base rate train. Tidak ada bias R2 di sini,
   tapi juga tidak ada pembanding pasar efisien.

8. **N per-league per-market**: Beberapa liga punya N kecil (<100). Dilaporkan
   sebagai INSUFFICIENT N, tidak ada verdict.

9. **Determinisme**: Bootstrap pakai seed 42. Predictions.csv di-load (bukan
   re-predict), jadi model probabilities identik dengan backtest sebelumnya.
   Tidak ada randomness di luar bootstrap.
