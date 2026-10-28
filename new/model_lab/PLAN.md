# Rencana Mempertajam Model

## Tujuan

Mencari kombinasi fitur, model, dan kalibrasi yang paling kuat **untuk tiap pasar**, bukan memaksa satu model menjadi juara untuk semua target:

1. 1X2: Home / Draw / Away.
2. Total gol pertandingan Over/Under 2.5.
3. Gol tim kandang Over/Under 0.5 dan 1.5.
4. Gol tim tandang Over/Under 0.5 dan 1.5.

Model saat ini menggunakan statistik tim historis yang disiapkan dari data proyek. Semua eksperimen tahap ini offline. Prediksi belum pernah digunakan untuk live bet dan tidak ada klaim profitabilitas.

Tujuan pengguna saat ini adalah menilai model berbasis histori untuk kemungkinan penggunaan taruhan nyata. Data yang ada hanya mendukung eksperimen pra-pertandingan; tidak ada data in-play atau odds pada waktu keputusan. Karena seluruh periode test historis sudah ditinjau, hasil berikutnya tetap harus dianggap referensi dan tidak cukup untuk menyatakan model siap taruhan.

## Batas yang tidak boleh dilanggar

- Semua kode eksperimen, konfigurasi, model kandidat, prediksi, dan laporan disimpan di `new/model_lab/`.
- Script dan artefak utama tetap baca-saja selama pencarian: `features.py`, `train.py`, `predict.py`, `predict_dc.py`, `data/`, `models/`, `predictions/`, dan `backtest/`.
- Jangan jalankan scan dashboard, scraping, atau pipeline produksi untuk eksperimen ini.
- Tidak ada taruhan uang. Tahap prospektif, bila nanti disetujui, hanya paper tracking tanpa stake.
- Jangan menyebut kandidat “siap live” atau “menguntungkan” berdasarkan backtest saja.
- Promosi ke script utama adalah tugas terpisah dan memerlukan persetujuan eksplisit setelah hasil kandidat ditinjau.

## Titik terakhir yang sudah tersedia

Artefak di bawah ini sudah ada; angka berikut **referensi historis**, bukan hasil eksperimen baru:

| Pasar | Model saat ini: LogLoss | Pembanding tercatat | Catatan |
|---|---:|---:|---|
| 1X2 | 1.0143 | Odds 1.0025 | Model lebih buruk pada test tercatat |
| Total O/U 2.5 | 0.6820 | Odds 0.6781 | Model lebih buruk pada test tercatat |
| Kandang O/U 0.5 | 0.5129 | Base rate 0.5332 | Lebih baik dari base rate; belum ada pembanding bookmaker untuk pasar ini |
| Kandang O/U 1.5 | 0.6539 | Base rate 0.6858 | Lebih baik dari base rate; belum ada pembanding bookmaker untuk pasar ini |
| Tandang O/U 0.5 | 0.5893 | Base rate 0.6074 | Lebih baik dari base rate; belum ada pembanding bookmaker untuk pasar ini |
| Tandang O/U 1.5 | 0.6253 | Base rate 0.6494 | Lebih baik dari base rate; belum ada pembanding bookmaker untuk pasar ini |

Sumber: `reports/final_audit_20261026/FINAL_REPORT.md` dan `MODEL_METRICS.md`. Laporan mencatat 9.438 pertandingan test, enam model LightGBM Mode B, dan 78 fitur. Split yang tercatat di `train.py`: train sampai 2024-06-30, validasi sampai 2025-06-30, lalu test sesudahnya.

Kalibrasi Platt yang pernah diuji memberi perubahan kecil dan belum meyakinkan. Percobaan H2H sebelumnya juga tidak menunjukkan peningkatan luas yang konsisten: ringkasannya ada di `logs/summary_retrain.log`. Laporan kesiapan menyatakan performa prospektif, odds opening, dan profitabilitas belum terverifikasi.

**Penting:** test historis tersebut sudah pernah dilihat dan dipakai dalam laporan/perbandingan. Perlakukan sebagai acuan lama, bukan test set baru yang masih tersegel untuk tuning.

## Tahapan

### 0. Bekukan acuan

- Simpan salinan evaluasi dan manifest/hash input yang diperlukan di bawah `new/model_lab/results/baseline/`.
- Catat versi model, daftar fitur, rentang tanggal, definisi target, mode odds, dan jumlah baris.
- Jangan melatih ulang hanya untuk membuat ulang hasil yang sudah tersedia.

### 1. Audit data dan titik-waktu

- Verifikasi tiap fitur tersedia sebelum waktu kick-off target; statistik tim harus hanya memakai pertandingan sebelumnya.
- Pastikan tidak ada skor/hasil pascapertandingan, kolom target, atau odds yang baru diketahui setelah waktu ramalan sebagai fitur.
- Pisahkan mode tanpa odds dari mode yang memakai odds. Mode dengan odds hanya boleh memakai kutipan yang timestamp-nya tersedia pada waktu ramalan simulasi; odds closing tidak boleh diperlakukan sebagai input live.
- Catat coverage, missing history, perubahan skema, liga, musim, dan rentang waktu per target.

### 2. Reproduksi baseline secara terisolasi

- Buat runner eksperimen di `new/model_lab/`; baca sumber proyek sebagai input saja.
- Reproduksi hasil baseline pada subset dan periode yang disepakati sebelum mengubah fitur.
- Jika angka tidak cocok, hentikan ablation dan cari penyebab perbedaan data, split, fitur, atau bobot waktu.

### 3. Uji kombinasi fitur per pasar

Bandingkan secara bertahap; jangan mencoba banyak kombinasi acak sekaligus.

| Kelompok | Isi untuk diuji |
|---|---|
| F0 — inti | Form tim bergulir 5 pertandingan |
| F1 — jangka lebih panjang | F0 + form 10 pertandingan |
| F2 — venue | F1 + statistik performa kandang/tandang yang sesuai |
| F3 — konteks waktu | F2 + hari istirahat dan statistik kumulatif musim |
| F4 — H2H | F3 + fitur pertemuan sebelumnya, dihitung sebelum tanggal target |
| F5 — perbandingan tim | F4 + selisih PPG/gol/kebobolan dan estimasi total gol |

Lakukan ablation satu kelompok demi satu kelompok. Setelah itu uji subset yang masuk akal hanya pada validation. Catat hasil terpisah untuk keenam target; fitur yang membantu 1X2 belum tentu membantu gol individual.

### 4. Bandingkan model dan probabilitas

- Jadikan LightGBM sekarang sebagai baseline model, bukan pemenang otomatis.
- Bandingkan dengan baseline sederhana yang sesuai: frekuensi historis/base rate dan odds tanpa vig bila kutipan yang valid tersedia. Model sederhana tambahan hanya dijalankan di folder ini.
- Tuning hyperparameter dan pilihan fitur hanya memakai train/validation pada fold waktu.
- Uji kalibrasi tanpa kalibrasi vs Platt/isotonic; fit calibrator hanya dari prediksi validation/out-of-fold.
- Uji ensemble hanya dari prediksi out-of-fold; jangan melatih bobot ensemble dari test yang akan dilaporkan.
- Periksa konsistensi probabilitas: tiga probabilitas 1X2 berjumlah 1; Over + Under berjumlah 1; probabilitas Over 1.5 tidak melebihi Over 0.5 untuk tim yang sama.

### 5. Evaluasi waktu dan ketahanan

- Gunakan expanding/rolling walk-forward; tidak ada random split.
- Gunakan beberapa jendela test kronologis yang tidak dipakai untuk memilih konfigurasi pada jendela tersebut.
- Karena test lama sudah pernah ditinjau, tandai hasilnya `REFERENCE_ONLY`. Jika data historis tak menyediakan holdout baru yang independen, nyatakan keterbatasan itu dan lanjutkan ke paper tracking tanpa taruhan.
- Metrik utama: LogLoss dan Brier. Untuk 1X2 laporkan juga per kelas; AUC/akurasi hanya metrik tambahan.
- Laporkan kalibrasi, hasil per liga/musim, coverage, serta jumlah observasi. Jangan hanya merangking dari accuracy.
- Ukur ketidakpastian dengan paired block bootstrap berdasarkan pekan/kelompok waktu; kendalikan multiple testing karena enam pasar dan banyak konfigurasi.
- Bandingkan terhadap baseline yang tepat pada tanggal dan informasi yang sama. Untuk empat pasar gol tim, jangan mengklaim menang dari bookmaker bila odds pembanding tidak tersedia.

### 6. Gerbang kandidat terbaik

Tetapkan keputusan per pasar. Sebuah konfigurasi baru menjadi **CANDIDATE**, bukan “best” hanya karena satu skor test paling rendah. Minimal harus:

1. Lulus audit kebocoran dan reproduksi.
2. Membaik pada metrik probabilitas utama terhadap baseline yang relevan di beberapa fold waktu; peningkatan dan interval ketidakpastiannya harus dilaporkan.
3. Tidak bergantung pada satu liga, satu musim, atau satu kelompok kecil pertandingan.
4. Memiliki kalibrasi dan probabilitas antarpasar yang masuk akal.
5. Menyertakan batasan odds dan coverage. Klaim value hanya boleh diuji jika odds bertimestamp pada waktu ramalan tersedia.

Jika lolos, simpan model, daftar fitur, parameter, hash, dan evaluasi di `new/model_lab/candidates/<candidate_id>/`. Jangan menyalin atau mengaktifkannya di luar `new/`.

### 7. Paper tracking tanpa taruhan

Setelah kandidat dipilih, catat ramalan yang dibuat sebelum pertandingan, waktu dan sumber input, odds pada waktu tersebut bila tersedia, lalu hasil akhir. Tidak ada stake atau live bet. Bandingkan performa prospektif dengan protokol yang sudah ditetapkan sebelum melihat hasil.

Status paper tracking tetap berbeda dari bukti live betting dan profitabilitas. Promosi ke model utama memerlukan keputusan dan persetujuan terpisah.

## Status eksperimen

Gunakan status berikut dalam register: `REFERENCE_ONLY`, `PLANNED`, `RUNNING`, `REPRODUCED`, `CANDIDATE`, `REJECTED`, `PAPER_ONLY`, `PROMOTED_WITH_APPROVAL`.

`EXP-05` adalah perbandingan keluarga model pra-pertandingan tanpa odds sebagai fitur. Script dan protokolnya dijelaskan dalam `experiments/README.md`; semua hasil harus berstatus `REFERENCE_ONLY` sampai validasi prospektif yang belum dilihat selesai.

`EXP-00` masih `PLANNED`: spot check `home_ou05` pada fold `2025-26` cocok tepat dengan hasil tersimpan, tetapi reproduksi penuh semua pasar dan fold belum dilakukan.

`EXP-01` sudah dijalankan sebagai `REFERENCE_ONLY` pada fold parsial `2026-27`. Tidak ada penambahan fitur yang meningkatkan LogLoss secara meyakinkan setelah koreksi perbandingan berganda; F3 memperburuk O/U 2.5. Hasil satu fold parsial tidak memilih kandidat atau membuktikan kesiapan.

## Referensi

- Baseline: `reports/final_audit_20261026/`
- Kalibrasi: `reports/final_audit_20261026/CALIBRATION_REPORT.md`
- Batasan live: `reports/live_readiness_audit_20261026/READINESS_REPORT.md`
- Hasil retrain terdahulu: `logs/summary_retrain.log`
- Definisi target dan split terdahulu: `features.py`, `train.py` (baca-saja selama riset)
