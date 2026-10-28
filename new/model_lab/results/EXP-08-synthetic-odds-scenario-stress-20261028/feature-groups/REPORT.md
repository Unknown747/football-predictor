# EXP-01 — Ablation Fitur F0-F5

**Status: REFERENCE_ONLY — hasil historis ini bukan bukti siap taruhan atau profitabilitas.**

## Protokol

- Fold: 2026-27-partial.
- Rentang hasil yang tersedia: 2026-07-31 sampai 2026-10-21; total baris berlabel per pasar dilaporkan di CSV.
- Keluarga model tiap pasar dibekukan dari hasil EXP-05 pada empat fold lengkap sebelumnya; fold ini tidak dipakai untuk memilih keluarga model.
- Feature groups kumulatif: F0 form lima laga; F1 tambah form sepuluh laga; F2 tambah venue; F3 tambah istirahat dan musim; F4 tambah H2H; F5 tambah selisih tim dan expected goals.
- Hanya fitur statistik pra-pertandingan dalam whitelist yang digunakan. Odds, target, dan statistik pascapertandingan bukan input.
- Semua periode historis dalam proyek telah ditinjau; temuan hanya untuk screening dan tidak menjadi holdout independen.

## LogLoss dan Brier per pasar

Lebih rendah lebih baik. Baris dengan LogLoss terendah hanya menandai kelompok yang layak diuji lagi; bukan kandidat terpilih.

| Pasar | Keluarga | Fitur terendah LL | LogLoss | Brier | N |
|---|---|---|---:|---:|---:|
| 1x2 | xgboost | F5 | 1.03973 | 0.62504 | 1,792 |
| ou25 | logreg | F2 | 0.67496 | 0.24105 | 1,792 |
| home_ou05 | xgboost | F4 | 0.51274 | 0.16683 | 1,792 |
| home_ou15 | xgboost | F2 | 0.67245 | 0.23977 | 1,792 |
| away_ou05 | xgboost | F4 | 0.58391 | 0.19808 | 1,792 |
| away_ou15 | xgboost | F4 | 0.64549 | 0.22678 | 1,792 |

## Perubahan bertahap terhadap kelompok sebelumnya

Δ LogLoss = kelompok saat ini dikurangi kelompok sebelumnya; nilai negatif mengarah lebih baik. Interval paired bootstrap mingguan dikoreksi Bonferroni untuk 32 perbandingan. Interval yang melintasi nol tidak memberi bukti perbedaan yang meyakinkan.

| Pasar | Perbandingan | N | Δ LogLoss | CI simultan 95% |
|---|---|---:|---:|---:|
| 1x2 | F0 → F1 | 1,792 | -0.00456 | [-0.01299, 0.01053] |
| 1x2 | F1 → F2 | 1,792 | +0.00110 | [-0.00515, 0.00546] |
| 1x2 | F2 → F3 | 1,792 | -0.00257 | [-0.01380, 0.01046] |
| 1x2 | F3 → F4 | 1,792 | -0.00406 | [-0.01220, 0.00383] |
| 1x2 | F4 → F5 | 1,792 | -0.00381 | [-0.01307, 0.00275] |
| ou25 | F0 → F1 | 1,792 | -0.00155 | [-0.00672, 0.00192] |
| ou25 | F1 → F2 | 1,792 | -0.00045 | [-0.00171, 0.00057] |
| ou25 | F2 → F3 | 1,792 | +0.00813 | [0.00115, 0.01743] |
| ou25 | F3 → F4 | 1,792 | -0.00064 | [-0.00267, 0.00162] |
| ou25 | F4 → F5 | 1,792 | +0.00094 | [-0.00042, 0.00384] |
| home_ou05 | F0 → F1 | 1,792 | -0.00108 | [-0.00988, 0.00625] |
| home_ou05 | F1 → F2 | 1,792 | +0.00120 | [-0.00295, 0.00424] |
| home_ou05 | F2 → F3 | 1,792 | +0.00144 | [-0.00423, 0.00877] |
| home_ou05 | F3 → F4 | 1,792 | -0.00268 | [-0.00678, 0.00224] |
| home_ou05 | F4 → F5 | 1,792 | +0.00167 | [-0.00377, 0.00709] |
| home_ou15 | F0 → F1 | 1,792 | -0.00600 | [-0.01574, 0.00756] |
| home_ou15 | F1 → F2 | 1,792 | -0.00038 | [-0.00436, 0.00445] |
| home_ou15 | F2 → F3 | 1,792 | +0.00587 | [-0.00062, 0.01212] |
| home_ou15 | F3 → F4 | 1,792 | -0.00238 | [-0.00700, 0.00206] |
| home_ou15 | F4 → F5 | 1,792 | -0.00172 | [-0.00587, 0.00560] |
| away_ou05 | F0 → F1 | 1,792 | +0.00160 | [-0.00385, 0.00921] |
| away_ou05 | F1 → F2 | 1,792 | -0.00230 | [-0.00491, 0.00090] |
| away_ou05 | F2 → F3 | 1,792 | -0.00069 | [-0.00490, 0.00603] |
| away_ou05 | F3 → F4 | 1,792 | -0.00293 | [-0.00801, 0.00020] |
| away_ou05 | F4 → F5 | 1,792 | +0.00048 | [-0.00422, 0.00573] |
| away_ou15 | F0 → F1 | 1,792 | -0.00639 | [-0.01375, 0.00083] |
| away_ou15 | F1 → F2 | 1,792 | +0.00068 | [-0.00231, 0.00370] |
| away_ou15 | F2 → F3 | 1,792 | -0.00158 | [-0.00595, 0.00340] |
| away_ou15 | F3 → F4 | 1,792 | -0.00062 | [-0.00311, 0.00249] |
| away_ou15 | F4 → F5 | 1,792 | +0.00421 | [-0.00059, 0.00832] |

## Interpretasi perbandingan

Tidak ada penambahan fitur yang menunjukkan peningkatan LogLoss meyakinkan setelah koreksi perbandingan berganda.
Penambahan fitur dengan interval simultan sepenuhnya di atas nol (memburuk): ou25: F2 → F3.

## Konsistensi probabilitas

Peluang 1X2 dan pasar biner seharusnya berjumlah 1; peluang Over 1.5 tidak boleh melebihi Over 0.5 untuk tim yang sama.

| Pemeriksaan | Baris cocok | Pelanggaran | Error/excess maksimum |
|---|---:|---:|---:|
| 1x2_probability_sum | 10,752 | 0 | 2.22e-16 |
| away_ou05_probability_sum | 10,752 | 0 | 0 |
| away_ou15_probability_sum | 10,752 | 0 | 0 |
| away_over15_le_over05 | 10,752 | 0 | -0.109 |
| home_ou05_probability_sum | 10,752 | 0 | 0 |
| home_ou15_probability_sum | 10,752 | 0 | 0 |
| home_over15_le_over05 | 10,752 | 0 | -0.0758 |
| ou25_probability_sum | 10,752 | 0 | 0 |

## Batas penggunaan

- Satu fold parsial dengan cakupan terbatas tidak cukup untuk memilih model terbaik yang umum atau menyatakan model siap digunakan.
- Semua hasil tetap `REFERENCE_ONLY`; tidak ada model yang dipromosikan, tidak ada taruhan, dan tidak ada artefak produksi yang diubah.
- Sebelum penggunaan nyata diperlukan paper tracking prospektif yang dibekukan sebelumnya dan odds bertimestamp pada waktu keputusan.

Manifest, metrik per fold, paired comparison, dan prediksi tersedia di folder hasil eksperimen ini.
