# Opening Odds Audit Report

## Executive Summary
Audit ini bertujuan mengukur ketersediaan historical opening odds untuk
mengukur risiko closing-odds bias. Hasilnya: **Opening odds TIDAK TERSEDIA**
di dataset lokal. Semua kolom odds adalah closing odds.

## Status Audit Teknis: PARTIAL
(Kita bisa audit coverage closing odds, tapi tidak bisa audit opening odds)

## Metode
- Cek header `data/master_canon.csv` dan `data/features_train.csv`.
- Cek dokumentasi lokal dan skrip.
- Tidak melakukan download data baru.

## Temuan Utama
1. Tidak ada kolom dengan nama yang secara eksplisit menandakan "opening".
2. Dokumentasi football-data.co.uk menyatakan semua kolom odds adalah closing.
3. Dataset lokal hanya berisi closing odds.

## Dampak terhadap Closing-Odds Bias (R2)
Karena opening odds tidak tersedia, kita **tidak bisa** mengukur secara
langsung dampak closing-odds bias terhadap prediksi live. Model kita
dilatih dan diuji dengan closing odds. Performa live dengan opening odds
**BELUM TERVERIFIKASI**.

## Kesimpulan
- Opening odds: TIDAK TERSEDIA.
- Closing odds: TERSEDIA (tapi bukan yang kita butuhkan untuk audit live).
- Untuk audit R2 lebih lanjut, diperlukan sumber data opening odds eksternal
  (butuh approval terpisah untuk scrape/download).
