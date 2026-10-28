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

| Skenario | Pasar | Kandidat LogLoss terendah | LogLoss | Brier | ECE | Bet hipotetis | Yield hipotetis |
|---|---|---|---:|---:|---:|---:|---:|
| EXTREME_GAP | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,792 | +1342.5% |
| EXTREME_GAP | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,790 | +348.0% |
| EXTREME_GAP | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,792 | +514.2% |
| EXTREME_GAP | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,785 | +254.1% |
| EXTREME_GAP | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,792 | +563.3% |
| EXTREME_GAP | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 | +603.7% |
| HEAVY_FAVOURITE | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,768 | +258.9% |
| HEAVY_FAVOURITE | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,583 | +59.5% |
| HEAVY_FAVOURITE | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,674 | +111.9% |
| HEAVY_FAVOURITE | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,313 | +35.5% |
| HEAVY_FAVOURITE | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,753 | +124.2% |
| HEAVY_FAVOURITE | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 | +134.6% |
| MISMATCHED_ODDS | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,791 | +198.4% |
| MISMATCHED_ODDS | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 1,784 | +141.2% |
| MISMATCHED_ODDS | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,757 | +107.0% |
| MISMATCHED_ODDS | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 1,776 | +162.8% |
| MISMATCHED_ODDS | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,761 | +95.3% |
| MISMATCHED_ODDS | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,792 | +86.1% |
| STANDARD | 1x2 | LAB_FAMILY_logreg | 1.03533 | 0.62160 | 0.04020 | 1,491 | +15.1% |
| STANDARD | away_ou05 | LAB_FAMILY_logreg | 0.57838 | 0.19617 | 0.01961 | 976 | +4.9% |
| STANDARD | away_ou15 | LAB_FAMILY_logreg | 0.64401 | 0.22588 | 0.02866 | 1,029 | +13.0% |
| STANDARD | home_ou05 | LAB_FAMILY_xgboost | 0.51189 | 0.16659 | 0.02364 | 811 | +10.0% |
| STANDARD | home_ou15 | LAB_FAMILY_logreg | 0.67044 | 0.23871 | 0.04010 | 1,151 | +11.0% |
| STANDARD | ou25 | LAB_F2_logreg | 0.67496 | 0.24105 | 0.03118 | 1,066 | +7.6% |

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

## Cara membaca simulasi bet

Kolom bet memakai aturan tetap: pasang satu unit hipotetis hanya bila EV terbesar model terhadap odds sintetis minimal 3%. Hasil unit dan yield berasal dari harga yang dibuat sendiri; jangan dibaca sebagai keuntungan yang bisa diulang. `scenario_metrics.csv` memuat metrik setiap kandidat, pasar, dan skenario; `per_league_metrics.csv` memberi rincian liga.

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

- `scenario_metrics.csv`: semua kandidat × pasar × skenario, termasuk LogLoss, Brier, kalibrasi, cakupan pilihan, dan unit hipotetis.
- `market_leaders.csv` / `scenario_leaders.csv`: pemimpin screening agregat dan per skenario.
- `scenario_ambiguity.csv` / `class_bias.csv`: perbedaan pendapat, bias per kelas, dan respons kandidat.
- `synthetic_odds_quotes.csv`: odds sintetis per fixture, pasar, dan skenario.
- `per_league_metrics.csv` dan `manifest.json`: rincian liga, identitas input, hash, aturan simulasi, serta batasan.
