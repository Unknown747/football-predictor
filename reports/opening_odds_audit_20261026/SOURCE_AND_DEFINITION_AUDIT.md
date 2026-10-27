# Source and Definition Audit

## Sumber Data
Dataset berasal dari `football-data.co.uk`.

## Definisi Kolom Odds di football-data.co.uk

Berdasarkan dokumentasi resmi football-data.co.uk (notes.txt):
- Kolom `B365H`, `B365D`, `B365A`: Odds dari Bet365. Ini adalah CLOSING odds.
- Kolom `PSH`, `PSD`, `PSA`: Odds dari Pinnacle. Ini adalah CLOSING odds.
- Kolom `AvgH`, `AvgD`, `AvgA`: Rata-rata odds pasar. Ini adalah CLOSING odds.
- Kolom `B365>2.5`, `B365<2.5`: Odds Over/Under 2.5 dari Bet365. CLOSING.
- Kolom `Avg>2.5`, `Avg<2.5`: Rata-rata odds Over/Under 2.5. CLOSING.

**Tidak ada kolom khusus untuk "opening odds"** di dataset football-data.co.uk standar.

## Kesimpulan
Status untuk opening odds: **UNVERIFIED / TIDAK TERSEDIA**.

Semua kolom odds yang ada di dataset adalah closing odds.
Tidak ada bukti lokal bahwa opening odds tersedia di file CSV yang kita miliki.
