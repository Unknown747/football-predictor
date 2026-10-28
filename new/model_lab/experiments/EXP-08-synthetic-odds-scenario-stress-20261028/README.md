# Catatan Eksperimen — EXP-08

## Pertanyaan dan hipotesis
- Pertanyaan: apakah peringkat kandidat berubah saat input diuji dengan skenario odds sintetis yang berbeda?
- Hipotesis: model statistik tanpa odds seharusnya relatif stabil; model Mode B dapat berubah karena model tersebut dilatih dengan fitur odds penutupan.
- ID register: `EXP-08`

## Ruang lingkup
- Pasar: keenam pasar dalam protokol lab.
- Data dan hash: `data/features_train.csv`, SHA-256 `37b54914bd714fdb752e8f794e00d92a0d192d24d57aa452d496f20b34ff2f09`.
- Rentang pertandingan uji: 2026-07-31 sampai 2026-10-21; 1.792 pertandingan per pasar.
- Fold: train sampai 2026-06-30; fold uji parsial `2026-27-partial`.
- Mode input: statistik pra-pertandingan untuk kandidat lab; quote sintetis untuk stress test Mode B.
- Odds: empat skenario sintetis, margin 6%; bukan odds bookmaker, bukan harga bertimestamp, dan bukan input live.

## Konfigurasi yang dibekukan
- Baseline: model Mode B utama, prior train, serta quote sintetis.
- Kandidat: empat keluarga model EXP-05 dan grup fitur EXP-01 F0-F5.
- Fitur H2H: tersedia sebelum pertandingan; keluarga model penuh dan F4/F5 memakainya, sedangkan F0-F3 menjadi ablation tanpa H2H.
- Skenario: `STANDARD`, `HEAVY_FAVOURITE`, `EXTREME_GAP`, dan `MISMATCHED_ODDS`.
- Aturan EV hipotetis: sinyal hanya dicatat jika EV maksimum ≥3%; tidak ada stake atau taruhan.
- Metrik: LogLoss, Brier, ECE, bias kelas, perbedaan prediksi, sensitivitas Mode B, dan koherensi probabilitas.
- Batas keputusan: semua hasil historis tetap `REFERENCE_ONLY`; tidak ada kandidat final tanpa validasi prospektif.

## Hasil

| Pasar | Pemimpin screening | LogLoss | Brier | ECE |
|---|---|---:|---:|---:|
| 1X2 | `LAB_FAMILY_logreg` | 1.03533 | 0.62160 | 0.04020 |
| O/U 2.5 | `LAB_F2_logreg` | 0.67496 | 0.24105 | 0.03118 |
| Kandang O/U 0.5 | `LAB_FAMILY_xgboost` | 0.51189 | 0.16659 | 0.02364 |
| Kandang O/U 1.5 | `LAB_FAMILY_logreg` | 0.67044 | 0.23871 | 0.04010 |
| Tandang O/U 0.5 | `LAB_FAMILY_logreg` | 0.57838 | 0.19617 | 0.01961 |
| Tandang O/U 1.5 | `LAB_FAMILY_logreg` | 0.64401 | 0.22588 | 0.02866 |

- Rerun mereproduksi `scenario_metrics.csv`, `synthetic_odds_quotes.csv`, dan CSV metrik keluarga/grup fitur dengan hash yang sama seperti keluaran sebelumnya. Perbedaan `fit_details.json` terbatas pada waktu eksekusi. Laporan baru menambahkan diagnostik koherensi dan sensitivitas; tabel pemimpin tidak lagi menampilkan yield hipotetis, yang hanya tersimpan di metrik mentah untuk audit.
- Probabilitas per pasar berjumlah satu dalam seluruh 559.104 pemeriksaan.
- Ada 2.451 pelanggaran `Over 1.5 ≤ Over 0.5` dari 186.368 pemeriksaan. Sebanyak 2.439 berasal dari referensi quote sintetis di `MISMATCHED_ODDS` karena tiap garis dibalik secara independen; ini bukan harga lintas-pasar yang koheren. Dua belas lainnya muncul pada beberapa model keluarga HistGradientBoosting/logistic.
- Skenario mismatch membalik kelas MAIN_MODE_B untuk O/U 2.5 pada 84,9% pertandingan, 1X2 pada 68,0%, dan tandang O/U 1.5 pada 58,1%. Ini menunjukkan sensitivitas terhadap distribusi quote sintetis, bukan hasil pasar nyata.
- LogLoss tetap stabil di antara empat keluarga/grup yang tidak memakai odds; quote sintetis tidak memberi bukti nilai taruhan maupun profit.

## Keputusan
- Status: `REFERENCE_ONLY`.
- Pemimpin di atas hanya screening per pasar; tidak ditetapkan sebagai kandidat final.
- Keterbatasan: fold parsial telah ditinjau, tidak ada holdout independen, tidak ada odds bookmaker bertimestamp, dan Mode B mengalami pergeseran distribusi terhadap closing odds sintetis.
- Hasil: `new/model_lab/results/EXP-08-synthetic-odds-scenario-stress-20261028-reproduction/`.

Tidak ada model, prediksi produksi, data utama, atau dashboard yang diubah. Tidak ada live bet.
