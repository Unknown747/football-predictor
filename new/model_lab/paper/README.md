# EXP-07 — Paper tracking tanpa taruhan

EXP-07 mencatat prediksi EXP-06 yang dibuat sebelum kick-off. Cohort pertama dibuka pada **28 Oktober 2026** dari snapshot bertimestamp `2026-10-28T08:26:37Z`: 228 fixture cocok, semuanya masih akan datang pada saat prediksi dibuat. Hasil pertandingan belum masuk, jadi metrik saat ini berstatus `PENDING_RESULTS`; kesiapan model belum dinilai.

Prediksi, hasil, dan protokol disimpan di sini:

- `exp07_forecasts.jsonl`: ledger prediksi append-only dengan rantai SHA-256.
- `exp07_results.jsonl`: ledger hasil akhir append-only dengan rantai SHA-256.
- `exp07_protocol.json`: bundle EXP-06 yang dibekukan dan aturan evaluasi.
- `scorecard/`: laporan metrik turunan; dapat dibuat ulang dari dua ledger.

Semua eksperimen dan output tetap di `new/model_lab/`. Script ini memakai Python standard library dan tidak mengubah model, prediksi, dashboard, atau pipeline utama.

## Membuka cohort dari snapshot pra-pertandingan

Timestamp pada nama file prediksi berasal dari waktu lokal proses `predict.py`; di lingkungan ini zona waktunya UTC. Tetap berikan timestamp UTC secara eksplisit:

```bash
python new/model_lab/paper/exp07_tracker.py capture \
  --predictions predictions/predictions_YYYYMMDD_HHMMSS.csv \
  --fixtures predictions/fixtures_7hari/fixture_fotmob_latest.csv \
  --captured-at-utc YYYY-MM-DDTHH:MM:SSZ
```

Script memeriksa hash bundle terhadap manifest, tag model, probabilitas, dan waktu kick-off. Match yang sudah dimulai ditolak. Hanya satu prediksi per ID pertandingan dan waktu kick-off yang disimpan; capture berikutnya tidak dapat menimpa prediksi. Pertandingan yang dijadwal ulang mendapat ID event berbeda, sehingga rekaman lama tetap utuh.

## Memasukkan hasil dan menghitung skor

Setelah hasil resmi tersedia, buat template. Masukkan skor 90 menit/regulasi, tanpa perpanjangan waktu atau adu penalti, agar label hasil sejalan dengan data latih:

```bash
python new/model_lab/paper/exp07_tracker.py results-template
```

Isi hanya baris dengan `status=FINISHED`; catat skor, waktu kick-off aktual UTC, sumber hasil, dan waktu data diambil UTC. Impor dan hitung:

```bash
python new/model_lab/paper/exp07_tracker.py import-results \
  --input new/model_lab/paper/exp07_results_input_template.csv
python new/model_lab/paper/exp07_tracker.py score
```

Skor mencakup LogLoss, Brier, ECE 10-bin, akurasi, coverage hasil, dan interval bootstrap 95% per minggu jika ada sedikitnya dua minggu kick-off yang selesai. Nilai multi-kelas Brier 1X2 adalah jumlah kuadrat error tiga kelas, konsisten dengan benchmark lab. Hasil tanpa kick-off aktual setelah timestamp prediksi ditolak.

Metrik ini mengukur probabilitas pada pertandingan mendatang saja. Tidak ada stake, ROI, atau klaim profit. Tidak ada odds bookmaker bertimestamp yang tercatat untuk cohort awal, sehingga evaluasi odds/value tidak tersedia. EXP-07 **tidak mengesahkan kesiapan**; hasil deskriptif saja bukan bukti model siap untuk penggunaan live.
