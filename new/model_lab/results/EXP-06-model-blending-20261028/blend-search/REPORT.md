# EXP-06 — Gabungan Model per Pasar

**Status: `REFERENCE_ONLY`; file kandidat hanya untuk prediksi offline/paper.**

## Metode

- Prediksi keluarga model memakai 5 fold kronologis out-of-fold; bobot untuk tiap fold hanya dipilih dari fold sebelumnya.
- Grid bobot simplex memakai langkah 0.1; fungsi pilih meminimalkan LogLoss, lalu Brier, kemudian lebih sedikit model.
- Fold pertama menggunakan bobot sama yang ditetapkan sebelum melihat hasil; fold ini tidak masuk gerbang pemilihan kandidat.
- Blend hanya dipilih jika LogLoss membaik dengan CI paired-week bootstrap terkoreksi 24 perbandingan seluruhnya di bawah nol, Brier tidak memburuk, dan ECE tidak memburuk lebih dari 0,005. Jika gagal, paket memakai model tunggal pemenang EXP-05 historis untuk pasar itu.
- Semua periode historis sudah ditinjau sebelumnya. Angka ini tidak menjadi holdout independen atau bukti profit.
- Keluarga EXP-05 dan blend memakai fitur statistik pra-pertandingan termasuk H2H; F0-F3 tidak memakai H2H, sedangkan F4-F5 memakainya.

## Strategi screening per pasar

| Pasar | Pilihan paket offline | Model tunggal historis | Δ LogLoss blend−single | Δ Brier | Δ ECE | CI LogLoss simultan |
|---|---|---|---:|---:|---:|---:|
| 1x2 | Blend | xgboost | -0.00394 | -0.00268 | -0.00277 | [-0.00497, -0.00285] |
| ou25 | Tunggal: logreg | logreg | -0.00028 | -0.00011 | +0.00145 | [-0.00148, 0.00083] |
| home_ou05 | Blend | xgboost | -0.00188 | -0.00071 | -0.00167 | [-0.00272, -0.00108] |
| home_ou15 | Blend | xgboost | -0.00255 | -0.00118 | +0.00197 | [-0.00364, -0.00141] |
| away_ou05 | Tunggal: logreg | logreg | -0.00102 | -0.00055 | -0.00538 | [-0.00235, 0.00033] |
| away_ou15 | Blend | xgboost | -0.00279 | -0.00123 | -0.00344 | [-0.00420, -0.00132] |

## Metrik evaluasi

`scorecard.csv` berisi LogLoss, Brier, akurasi, ECE, AUC bila berlaku, jumlah pertandingan, model, pasar, dan fold. `aggregate_metrics.csv` merangkum fold evaluasi yang digunakan untuk keputusan (semua fold kecuali fold pertama). `latest_comparators.csv` menambahkan F0-F5 dan Mode B sebagai pembanding pada fold terbaru; Mode B memakai quote sintetis `STANDARD`, sehingga bukan perbandingan harga yang setara.

## Koherensi dan batasan

- Jumlah probabilitas: 0 pelanggaran dari 1,244,305 pemeriksaan.
- Over 1.5 ≤ Over 0.5: 417 pelanggaran dari 392,976 pemeriksaan pada data OOF.
- Rincian pelanggaran O/U tim menurut model: logreg: 329, histgb: 88.
- Tidak ada hasil baru yang dapat membuktikan kesiapan taruhan uang: odds bookmaker bertimestamp dan holdout prospektif belum tersedia.
- Bobot terpilih dan tabel perbandingan disimpan di folder hasil run ini; tidak ada paket model atau artefak proyek utama yang ditulis. Promosi memerlukan peninjauan dan persetujuan terpisah.
