# Ruang Riset Model — `new/model_lab/`

Status: **riset offline terisolasi**. Lab ini mencari kandidat model dari data historis untuk penggunaan pra-pertandingan. Tidak ada taruhan uang yang ditempatkan.

## Tujuan dan batas klaim

- Arah proyek adalah mencari model berbasis data historis yang paling layak dipertimbangkan untuk taruhan nyata pada masa mendatang.
- "Terbaik" di lab berarti skor probabilitas historis yang lebih baik dan cukup stabil per pasar; bukan bukti value, profit, atau kesiapan taruhan nyata.
- Data saat ini tidak berisi menit pertandingan, skor berjalan, kartu, atau odds live. Jadi ruang lingkupnya pra-pertandingan, bukan prediksi in-play.
- Data odds yang tersedia untuk 1X2 dan O/U 2.5 adalah odds penutupan. Itu tidak boleh menjadi fitur atau bukti nilai taruhan pada waktu keputusan.
- Seluruh test historis proyek telah ditinjau. Ranking lab historis harus berstatus `REFERENCE_ONLY`; validasi prospektif dengan odds bertimestamp tetap diperlukan sebelum klaim kesiapan.

Folder ini menjadi satu-satunya tempat untuk eksperimen peningkatan model. Script, konfigurasi, salinan data eksperimen, log, evaluasi, dan kandidat model harus berada di bawah `new/`.

## Aturan isolasi

- Jangan mengubah script utama `features.py`, `train.py`, `predict.py`, atau `predict_dc.py`.
- Jangan menimpa `data/`, `models/`, `predictions/`, `backtest/`, maupun hasil produksi.
- Gunakan artefak tersebut sebagai referensi baca-saja. Jika eksperimen perlu kode, buat salinan/runner khusus di folder ini.
- Model sekarang berasal dari statistik tim dalam database menurut keterangan pengguna.
- Prediksi **belum pernah digunakan untuk live bet**. Hasil historis bukan bukti hasil live atau profit.
- Perubahan dari kandidat ke sistem utama harus menjadi langkah terpisah setelah kandidat lolos gerbang evaluasi dan pengguna memberi persetujuan.
- Runner model-family membandingkan LightGBM, XGBoost, HistGradientBoosting, dan regresi logistik dengan fitur statistik pra-pertandingan saja.
- Odds penutupan hanya dicatat sebagai pembanding referensi pada 1X2 dan O/U 2.5. Untuk empat pasar gol tim belum ada odds pembanding.

## Isi folder

```text
new/model_lab/
├── README.md
├── PLAN.md
├── EXPERIMENT_REGISTER.csv
├── EXPERIMENT_TEMPLATE.md
├── experiments/    # konfigurasi dan catatan tiap eksperimen
├── results/        # metrik, prediksi uji, dan ringkasan per fold
├── candidates/     # artefak kandidat terpilih; bukan model produksi
└── paper/          # prediksi prospektif tanpa taruhan uang
```

## Menjalankan benchmark model

Dependensi Python sudah tercantum di `requirements.txt`; LightGBM/XGBoost juga memerlukan GCC `libgomp.so.1` yang ditemukan oleh launcher.

```bash
bash new/model_lab/run_benchmark.sh
```

Semua file hasil akan masuk ke `new/model_lab/results/EXP-05-historical-model-family-benchmark/`. Runner menolak output di luar `new/model_lab/` dan menolak menimpa folder hasil yang sudah berisi file kecuali `--overwrite` diberikan.

Contoh subset untuk uji cepat:

```bash
bash new/model_lab/run_benchmark.sh \
  --markets home_ou05 \
  --models logreg lgbm \
  --fold 2025-26 \
  --output-dir new/model_lab/results/EXP-05-smoke
```

File utama hasil: `REPORT.md` (ringkasan dan batas klaim), `manifest.json` (hash input/fitur dan konfigurasi), `aggregate_metrics.csv`, `fold_metrics.csv`, `per_league_metrics.csv`, `paired_bootstrap.json`, `fit_details.json`, serta `predictions.csv`. CSV prediksi mentah besar dikecualikan dari Git/deployment; runner bisa membuatnya ulang.

## Alur kerja

Mulai dari `PLAN.md`; catat run di `EXPERIMENT_REGISTER.csv` dan salin `EXPERIMENT_TEMPLATE.md` ke folder eksperimennya. Untuk stress test odds di seluruh kandidat, jalankan `bash new/model_lab/run_odds_stress.sh`; runner membandingkan model Mode B utama, empat keluarga EXP-05, dan enam grup fitur EXP-01 pada fold parsial terbaru. Hasil lengkap dan batas klaim ada di `results/EXP-08-synthetic-odds-scenario-stress-20261028/odds-report/REPORT.md`.

Odds EXP-08 adalah sintetis, pra-pertandingan, dan tidak bertimestamp dari bookmaker. Angka return hanya simulasi satu unit dengan ambang EV tetap; bukan taruhan atau bukti profit. Hasil historis berstatus `REFERENCE_ONLY`. Setelah benchmark historis, jalankan paper tracking prospektif sesuai protokol yang disetujui. Jangan menulis status `PROMOTED_WITH_APPROVAL` tanpa persetujuan pengguna.
