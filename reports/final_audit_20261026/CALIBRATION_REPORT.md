# Calibration Report

Sumber: calibration/calibration_20261026_221135/
Metode terpilih: Platt Scaling (semua market).

Hasil Test Set (Sebelum -> Sesudah Kalibrasi):
Home O/U 0.5: 0.5129 -> 0.5121 (Delta -0.0008, BETTER)
Home O/U 1.5: 0.6539 -> 0.6531 (Delta -0.0009, BETTER)
Away O/U 0.5: 0.5893 -> 0.5894 (Delta +0.0002, INCONCLUSIVE)
Away O/U 1.5: 0.6253 -> 0.6246 (Delta -0.0007, INCONCLUSIVE)

Interpretasi:
Kalibrasi membaikkan probabilitas secara statistik di Home O/U, tetapi magnitude sangat kecil. Tidak direkomendasikan untuk produksi karena perbaikan tidak signifikan secara praktis.
