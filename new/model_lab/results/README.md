# Hasil

Simpan metrik per target dan fold, prediksi out-of-fold/test, kalibrasi, interval ketidakpastian, serta ringkasan per liga/musim di sini. Hasil final harus dapat ditautkan ke ID eksperimen, konfigurasi, versi input, dan hash artefak.

Baseline lama boleh diringkas sebagai `REFERENCE_ONLY`; jangan menimpa laporan di `reports/`.

Benchmark keluarga model EXP-05 tersimpan di `EXP-05-historical-model-family-benchmark/`. Baca `REPORT.md` untuk rangkuman, `manifest.json` untuk identitas input/config, dan CSV metrik untuk rincian fold serta liga. Prediksi mentah `predictions.csv` besar dan dikecualikan dari Git/deployment; buat ulang dengan runner yang didokumentasikan di `../README.md`.
