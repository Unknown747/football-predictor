# EXP-08 — Uji Tekanan Odds Sintetis untuk Semua Kandidat

**Status: `REFERENCE_ONLY`; bukan hasil live, bukan bukti profit, dan bukan rekomendasi taruhan.**

## Ringkasan uji

- Fold: `2026-27-partial`, pertandingan 2026-07-31–2026-10-21.
- Baris fixture: 1,792; jumlah berlabel per pasar: 1x2=1,792, ou25=1,792, home_ou05=1,792, home_ou15=1,792, away_ou05=1,792, away_ou15=1,792.
- Kandidat mencakup model Mode B yang dipakai script utama, empat keluarga EXP-05, dan enam tingkat fitur EXP-01 (F0–F5). Seluruh F0–F5 diuji untuk enam pasar.
- Data yang dipakai untuk H2H tersedia sebelum pertandingan. Model keluarga penuh, main Mode B, F4, dan F5 memakai H2H; F0–F3 sengaja menjadi ablation tanpa H2H.
- Semua odds di bawah ini dibuat secara sintetis dari prior train dan proxy statistik pra-pertandingan. Tidak ada hasil pertandingan test yang dipakai untuk membuat harga.

## Skenario

| Skenario | Cara membentuk quote sintetis |
|---|---|
| STANDARD | Prior train dicampur dengan proxy statistik sebelum kickoff. |
| HEAVY_FAVOURITE | Satu sisi diberi probabilitas implisit tinggi; sisi lawan menjadi underdog. |
| EXTREME_GAP | Probabilitas favorit sangat tinggi, menciptakan odds panjang untuk lawannya. |
| MISMATCHED_ODDS | Quote sengaja mengunggulkan sisi yang berlawanan dengan proxy statistik. |

Setiap quote memakai margin sintetis 6%. Ini simulasi pra-pertandingan, bukan in-play. Istilah heavy favorite/huge underdog dan odds ekstrem dipakai sebagai kategori stress test, bukan deskripsi bookmaker yang benar-benar diamati.

## Pemimpin screening per pasar

Diurutkan dari rata-rata LogLoss pada empat skenario. Karena pertandingan yang sama diulang dengan harga sintetis, ini bukan empat sampel independen. Peringkat hanya menunjukkan kandidat yang perlu diuji lebih lanjut.

| Pasar | Kandidat screening teratas | LogLoss rata-rata | Brier rata-rata | ECE rata-rata |
|---|---|---:|---:|---:|
| 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 |
| ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 |
| home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 |
| home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 |
| away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 |
| away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 |

## Pemimpin tiap simulasi

| Skenario | Pasar | Kandidat LogLoss terendah | LogLoss | Brier | ECE | Sinyal bet hipotetis |
|---|---|---|---:|---:|---:|---:|
| EXTREME_GAP | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,792 |
| EXTREME_GAP | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,790 |
| EXTREME_GAP | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,792 |
| EXTREME_GAP | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,785 |
| EXTREME_GAP | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,792 |
| EXTREME_GAP | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 |
| HEAVY_FAVOURITE | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,768 |
| HEAVY_FAVOURITE | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,583 |
| HEAVY_FAVOURITE | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,674 |
| HEAVY_FAVOURITE | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,313 |
| HEAVY_FAVOURITE | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,753 |
| HEAVY_FAVOURITE | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 |
| MISMATCHED_ODDS | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,791 |
| MISMATCHED_ODDS | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,784 |
| MISMATCHED_ODDS | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,757 |
| MISMATCHED_ODDS | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,776 |
| MISMATCHED_ODDS | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,761 |
| MISMATCHED_ODDS | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 |
| STANDARD | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,491 |
| STANDARD | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 976 |
| STANDARD | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,029 |
| STANDARD | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 811 |
| STANDARD | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,151 |
| STANDARD | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,066 |

## Bias dan ketidakpastian model

- `scenario_ambiguity.csv` mengukur seberapa jauh kandidat tidak sepakat: rentang probabilitas antarmodel, konsensus pilihan hasil, dan kecocokan pilihan konsensus dengan quote sintetis.
- `class_bias.csv` menunjukkan selisih probabilitas rata-rata terhadap frekuensi hasil aktual per kelas (kandang/seri/tandang atau under/over). Nilai positif berarti kelas itu cenderung terlalu sering diperkirakan.
- Perbandingan LogLoss, Brier, dan ECE pada `scenario_metrics.csv` membantu melihat apakah kandidat tetap terkalibrasi ketika harga berubah.

| Pasar | Skenario | Rentang peluang antarmodel | Konsensus pilihan model | Pilihan model cocok quote |
|---|---|---:|---:|---:|
| 1x2 | EXTREME_GAP | 0.2976 | 88.0% | 82.8% |
| 1x2 | HEAVY_FAVOURITE | 0.2704 | 88.0% | 82.6% |
| 1x2 | MISMATCHED_ODDS | 0.2899 | 83.7% | 33.4% |
| 1x2 | STANDARD | 0.1593 | 87.9% | 83.6% |
| away_ou05 | EXTREME_GAP | 0.1932 | 97.2% | 96.4% |
| away_ou05 | HEAVY_FAVOURITE | 0.1782 | 98.2% | 96.4% |
| away_ou05 | MISMATCHED_ODDS | 0.2317 | 98.2% | 3.5% |
| away_ou05 | STANDARD | 0.1421 | 99.0% | 99.6% |
| away_ou15 | EXTREME_GAP | 0.2462 | 93.3% | 80.0% |
| away_ou15 | HEAVY_FAVOURITE | 0.2462 | 93.3% | 80.0% |
| away_ou15 | MISMATCHED_ODDS | 0.3005 | 91.9% | 20.9% |
| away_ou15 | STANDARD | 0.1532 | 96.4% | 94.9% |
| home_ou05 | EXTREME_GAP | 0.1525 | 99.7% | 97.5% |
| home_ou05 | HEAVY_FAVOURITE | 0.1525 | 99.7% | 97.5% |
| home_ou05 | MISMATCHED_ODDS | 0.1904 | 99.7% | 2.5% |
| home_ou05 | STANDARD | 0.1333 | 99.7% | 99.8% |
| home_ou15 | EXTREME_GAP | 0.2887 | 88.4% | 76.3% |
| home_ou15 | HEAVY_FAVOURITE | 0.2783 | 88.4% | 76.2% |
| home_ou15 | MISMATCHED_ODDS | 0.3217 | 86.4% | 26.2% |
| home_ou15 | STANDARD | 0.1619 | 90.0% | 83.7% |
| ou25 | EXTREME_GAP | 0.1751 | 83.2% | 82.1% |
| ou25 | HEAVY_FAVOURITE | 0.1751 | 83.2% | 82.1% |
| ou25 | MISMATCHED_ODDS | 0.2013 | 79.0% | 35.8% |
| ou25 | STANDARD | 0.1290 | 83.1% | 77.8% |

## Konsistensi probabilitas antarpasar

- Jumlah probabilitas dalam tiap pasar: 0 pelanggaran dari 559,104 pemeriksaan.
- Untuk gol tim, probabilitas Over 1.5 harus tidak melebihi Over 0.5. Terjadi 2,451 pelanggaran di seluruh kandidat dan skenario.

| Kandidat | Relasi pasar | Pelanggaran | Perbandingan | Excess maksimum |
|---|---|---:|---:|---:|
| SYNTHETIC_ODDS_REFERENCE | away_ou15_vs_ou05 | 1,316 | 7,168 | 0.4400 |
| SYNTHETIC_ODDS_REFERENCE | home_ou15_vs_ou05 | 1,123 | 7,168 | 0.4400 |
| LAB_FAMILY_histgb | away_ou15_vs_ou05 | 4 | 7,168 | 0.0184 |
| LAB_FAMILY_histgb | home_ou15_vs_ou05 | 4 | 7,168 | 0.0009 |
| LAB_FAMILY_logreg | away_ou15_vs_ou05 | 4 | 7,168 | 0.0079 |

`SYNTHETIC_ODDS_REFERENCE` melanggar urutan Over 1.5 ≤ Over 0.5 pada 2,439 dari 14,336 perbandingan (excess maksimum 0.4400). Ini berasal dari quote MISMATCHED_ODDS yang membalik tiap garis gol secara independen; quote tersebut sengaja adversarial dan bukan referensi lintas-pasar yang koheren.
Model keluarga EXP-05 memiliki 12 pelanggaran kandidat-level; nilai probabilitas pasar-pasar tersebut tidak boleh dianggap koheren hanya karena LogLoss per pasar baik.
Perubahan kelas terbesar pada MAIN_MODE_B adalah 84.9% untuk `ou25` pada skenario `MISMATCHED_ODDS`; ini diagnostik pergeseran distribusi akibat odds sintetis, bukan validasi odds nyata.

## Cara membaca simulasi bet

Kolom sinyal menghitung fixture yang melewati aturan EV tetap: satu unit hipotetis hanya bila EV terbesar model terhadap odds sintetis minimal 3%. Unit/yield hipotetis ada hanya untuk audit di `scenario_metrics.csv`; karena harga dibuat sendiri dan tidak mewakili bookmaker, angka itu tidak layak dipakai memilih kandidat atau menyimpulkan profit. File itu memuat metrik semua kandidat, pasar, dan skenario; `per_league_metrics.csv` memberi rincian liga.

## Keputusan kandidat

- **1x2:** `LAB_FAMILY_logreg` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 1.03533); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.
- **ou25:** `LAB_F2_logreg` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 0.67496); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.
- **home_ou05:** `LAB_FAMILY_xgboost` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 0.51189); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.
- **home_ou15:** `LAB_FAMILY_logreg` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 0.67044); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.
- **away_ou05:** `LAB_FAMILY_logreg` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 0.57838); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.
- **away_ou15:** `LAB_FAMILY_logreg` adalah pemimpin screening LogLoss pada empat skenario (rata-rata 0.64401); status tetap `REFERENCE_ONLY_SCREENING`, bukan kandidat final.

Belum ada pemenang final yang aman ditetapkan: semua periode test historis proyek telah pernah ditinjau, fold ini parsial, dan seluruh odds bersifat simulasi. Pemimpin di atas dicatat agar riset berikutnya dapat membandingkannya, bukan untuk dipindahkan ke script utama.

## Batasan penting

- Model utama Mode B dilatih dengan fitur odds historis yang berasal dari odds penutupan. Odds sintetis di sini adalah stress test dan dapat berada di luar distribusi pelatihan.
- Data tidak memiliki harga live/in-play bertimestamp, harga eksekusi, komisi, atau batas taruhan. Tidak ada taruhan uang yang dilakukan.
- Semua hasil historis berstatus `REFERENCE_ONLY`; perlu paper tracking prospektif tanpa stake sebelum klaim kesiapan.

## File hasil

- `scenario_metrics.csv`: semua kandidat × pasar × skenario, termasuk LogLoss, Brier, kalibrasi, jumlah sinyal, dan unit/yield hipotetis untuk audit saja.
- `market_leaders.csv` / `scenario_leaders.csv`: pemimpin screening agregat dan per skenario.
- `scenario_ambiguity.csv` / `class_bias.csv`: perbedaan pendapat, bias per kelas, dan respons kandidat.
- `probability_coherence.csv`: pemeriksaan jumlah probabilitas dan urutan Over 1.5/0.5.
- `modeb_scenario_sensitivity.csv`: perubahan prediksi Mode B saat quote sintetis berubah.
- `synthetic_odds_quotes.csv`: odds sintetis per fixture, pasar, dan skenario.
- `per_league_metrics.csv` dan `manifest.json`: rincian liga, identitas input, hash, aturan simulasi, serta batasan.
