# Limitations — Calibration Experiment L10.6

1. **Closing odds bias (R2)**: Test probabilities dari `predictions.csv` berasal dari model yang dilatih pada closing odds. Live dengan opening odds bisa berbeda.

2. **Temporal internal val split**: Method selection menggunakan split temporal `val_early` (Date <= 2025-01-15) untuk fit dan `val_late` (Date > 2025-01-15) untuk check. Ini bukan random split — menghindari data leakage temporal.

3. **Per-market calibration, bukan per-liga**: Kalibrator di-fit global per market. Per-liga kalibrasi TIDAK dilakukan karena N per-liga di val mungkin tidak cukup (300-500 rows per liga).

4. **Fokus Home/Away O/U**: Model 1X2 dan OU25 tidak di-kalibrasi (sudah di bawah odds, kalibrasi tidak akan fundamental membantu).

5. **Reliability bins**: 10 bins, `abs_gap = |mean_p - mean_y|`. Improvement diharapkan, tapi tidak dijamin signifikan.

6. **Class preservation not assumed**: Kalibrasi monotonic TIDAK otomatis menjaga klasifikasi threshold 0.5. Setiap perubahan argmax di 0.5 dilaporkan di `config.json` `verification.n_class_changed_at_0.5`.

7. **Paired bootstrap**: 1000 iterasi, seed 42. Mengasumsikan korelasi intra-row (match). Tidak menggunakan block bootstrap by week — bisa jadi underestimate CI untuk time series.

8. **Tidak ada profitabilitas / bankroll simulation**: Kalibrasi membaikkan probabilitas, tapi tidak ada ROI, stake sizing, atau Kelly.

9. **Test eval 1x**: Setelah metode dipilih dari val, evaluasi di test hanya dilakukan sekali (tidak iterate). Ini fair.

10. **Isotonic regression caveat**: Non-parametric, butuh N besar. Jika selected, kalibrasi bisa overfit val_early. Platt lebih konservatif.
