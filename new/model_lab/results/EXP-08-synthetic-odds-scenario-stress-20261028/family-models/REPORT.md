# EXP-05 — Perbandingan Keluarga Model Historis

**Status: REFERENCE_ONLY — bukan bukti siap taruhan atau profitabilitas.**

## Ringkasan

- Input: `data/features_train.csv`; SHA-256 `37b54914bd714fdb752e8f794e00d92a0d192d24d57aa452d496f20b34ff2f09`.
- Isi prediksi out-of-fold: 57,344 baris model; tanggal 2026-07-31 sampai 2026-10-21.
- Fitur statistik pra-pertandingan: 74; SHA-256 daftar fitur `990c223264342ef6e38e2c6f08d9651e9c2eb5fb71edbaaf0ebbdce45f0d1a45`.
- Keluarga model: lgbm, xgboost, histgb, logreg; semua memakai fitur statistik tanpa odds.
- Split kronologis per musim; inner validation 90 hari hanya untuk menentukan jumlah boosting round LightGBM/XGBoost.
- Semua rentang historis di data ini sudah pernah ditinjau dalam audit/backtest proyek. Karena itu, ranking berikut adalah screening retrospektif, bukan test independen baru.

## Ranking historis per pasar

Urutan memakai LogLoss gabungan seluruh fold (lebih rendah lebih baik). Ini pemeringkatan untuk menentukan kandidat riset berikutnya, bukan rekomendasi taruhan.

| Pasar | Model teratas historis | N | LogLoss | Brier | Fold menang | Δ vs base rate | CI simultan 95% Δ |
|---|---|---:|---:|---:|---:|---:|---:|
| 1x2 | logreg | 1,792 | 1.0353 | 0.6216 | 1/1 | -0.0381 | [-0.0657, -0.0118] |
| ou25 | logreg | 1,792 | 0.6834 | 0.2450 | 1/1 | -0.0076 | [-0.0151, 0.0074] |
| home_ou05 | xgboost | 1,792 | 0.5119 | 0.1666 | 1/1 | -0.0094 | [-0.0190, -0.0031] |
| home_ou15 | logreg | 1,792 | 0.6704 | 0.2387 | 1/1 | -0.0230 | [-0.0409, -0.0092] |
| away_ou05 | logreg | 1,792 | 0.5784 | 0.1962 | 1/1 | -0.0173 | [-0.0281, -0.0054] |
| away_ou15 | logreg | 1,792 | 0.6440 | 0.2259 | 1/1 | -0.0178 | [-0.0350, -0.0012] |

Δ LogLoss dihitung terhadap prior base-rate yang hanya dipelajari dari data latih tiap fold. Interval memakai paired bootstrap per pekan dengan Bonferroni untuk 32 perbandingan yang direncanakan; interval yang melintasi nol tidak menunjukkan perbedaan yang meyakinkan. Koreksi ini tidak mengubah status semua hasil sebagai REFERENCE_ONLY.

## Odds penutupan sebagai pembanding

Untuk dua pasar yang memiliki odds, perbandingan memakai hanya baris yang memiliki odds tersedia; Δ adalah LogLoss kandidat dikurangi LogLoss odds penutupan, sehingga nilai positif berarti kandidat lebih buruk.

| Pasar | Model statistik teratas | N cocok | LL kandidat | LL odds penutupan | Δ LL kandidat−odds | CI simultan 95% |
|---|---|---:|---:|---:|---:|---:|
| 1x2 | logreg | 1,792 | 1.0353 | 1.0005 | +0.0348 | [0.0194, 0.0534] |
| ou25 | logreg | 1,792 | 0.6834 | 0.6676 | +0.0158 | [0.0042, 0.0353] |

Closing odds menang pada 1X2 dan O/U 2.5 dalam skor historis yang cocok. Tidak tersedia odds pembanding untuk gol kandang/tandang; peningkatan terhadap base rate di pasar tersebut bukan bukti edge taruhan.

## Interpretasi odds dan kesiapan taruhan

- `odds_pH`, `odds_pD`, `odds_pA`, dan `odds_pOver25` tidak dipakai sebagai fitur model. Audit proyek menyatakan nilai ini berasal dari odds penutupan.
- Odds penutupan dapat muncul sebagai baris `CLOSING_ODDS_REFERENCE` di hasil evaluasi saja; pembanding ini bukan harga yang tersedia saat keputusan taruhan dibuat.
- Dataset tidak memiliki odds bertimestamp pada saat keputusan, harga eksekusi, komisi, batas taruhan, atau hasil prospektif yang belum dilihat. Karena itu EV/ROI dan kesiapan taruhan uang nyata tidak dapat disimpulkan.
- Model ini pra-pertandingan, bukan model in-play. Data tidak berisi menit pertandingan, skor berjalan, kartu, atau odds live.
- Tidak ada taruhan yang ditempatkan, model yang disimpan sebagai kandidat, atau artefak produksi yang diubah.

## Model dan pengaturan

| Model | Pengaturan utama |
|---|---|
| lgbm | LightGBM, learning rate 0.03, 63 leaves; early stopping temporal |
| xgboost | XGBoost histogram, depth 6, learning rate 0.03; early stopping temporal |
| histgb | HistGradientBoosting, 180 iterasi, 31 leaves |
| logreg | Median imputation, standard scaling, logistic regression C=1 |

Semua model memakai bobot pelatihan half-life 365 hari. LogLoss dan Brier adalah metrik utama; accuracy/AUC/ECE disertakan sebagai diagnostik. Interval bootstrap mengoreksi 32 perbandingan dengan Bonferroni. Lihat `aggregate_metrics.csv`, `fold_metrics.csv`, `per_league_metrics.csv`, `paired_bootstrap.json`, dan `predictions.csv` untuk rincian.

## Langkah berikutnya sebelum uang nyata

1. Bekukan satu kandidat per pasar berdasarkan protokol ini; jangan memilih ulang dari hasil musim yang sama.
2. Simpan prediksi sebelum kickoff dengan waktu/sumber odds yang benar-benar tersedia saat keputusan dibuat.
3. Nilai logloss, Brier, kalibrasi, coverage, dan—hanya bila odds eksekusi bertimestamp tersedia—hasil setelah komisi dan batas taruhan pada periode prospektif yang belum dilihat.
4. Tinjau hasil prospektif terpisah sebelum menyatakan siap untuk taruhan nyata; tidak ada jaminan profit.
