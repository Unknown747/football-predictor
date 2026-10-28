# Hasil

Simpan metrik per target dan fold, prediksi out-of-fold/test, kalibrasi, interval ketidakpastian, serta ringkasan per liga/musim di sini. Hasil final harus dapat ditautkan ke ID eksperimen, konfigurasi, versi input, dan hash artefak.

Baseline lama boleh diringkas sebagai `REFERENCE_ONLY`; jangan menimpa laporan di `reports/`.

Benchmark keluarga model EXP-05 tersimpan di `EXP-05-historical-model-family-benchmark/`. Baca `REPORT.md` untuk rangkuman, `manifest.json` untuk identitas input/config, dan CSV metrik untuk rincian fold serta liga. Prediksi mentah `predictions.csv` besar dan dikecualikan dari Git/deployment; buat ulang dengan runner yang didokumentasikan di `../README.md`.

Reproduksi EXP-08 ada di `EXP-08-synthetic-odds-scenario-stress-20261028-reproduction/`. Baca `odds-report/REPORT.md` untuk pemimpin screening per pasar, bias, ketidaksepakatan, sensitivitas Mode B, dan pemeriksaan konsistensi probabilitas. Odds sepenuhnya sintetis; hasilnya tetap `REFERENCE_ONLY`.

EXP-06 blend berbobot tersimpan di `EXP-06-model-blending-20261028/blend-search/`. Screening memilih blend untuk empat dari enam pasar; dua pasar lainnya kembali ke model tunggal historis karena gerbang ketidakpastian tidak lolos. `latest_comparators.csv` membandingkan keluarga model, F0-F5, dan Mode B sintetis pada fold parsial terbaru. Seluruh hasil tetap `REFERENCE_ONLY`; lihat `../experiments/README.md` untuk meregenerasi prediksi mentah yang dikecualikan dari Git.
