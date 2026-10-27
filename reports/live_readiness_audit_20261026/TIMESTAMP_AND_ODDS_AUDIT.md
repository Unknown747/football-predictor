# Audit Waktu Prediksi dan Odds

## Temuan 1: Timestamp Fitur
Model menggunakan fitur form, H2H, dan rest days. Fitur-fitur ini dibangun
menggunakan cutoff `Date < kickoff_date` (strict). 

Status: PASS (untuk fitur statistik non-odds)
Bukti: logs/reconstruct_pit.py diverifikasi di L8 (parity 30/30 sampel).

## Temuan 2: Odds Closing vs Odds Opening
Model Mode B dilatih dan dievaluasi menggunakan `odds_pH`, `odds_pD`, `odds_pA`,
dan `odds_pOver25` dari features_train.csv. Odds ini adalah CLOSING ODDS
(odds yang tersedia mendekati kickoff).

Untuk live prediction, jika kita menginput odds yang tersedia saat ini (misal
H-3 hari), karakteristiknya berbeda dengan closing odds.

Status: BELUM TERVERIFIKASI (apakah input odds opening akan menghasilkan
performa setara dengan backtest closing).

## Temuan 3: Odds untuk Home/Away O/U
Tidak ada odds Home/Away O/U di dataset (football-data.co.uk). Model dilatih
tanpa fitur odds untuk pasar ini.

Status: PASS (tidak ada risiko leakage odds untuk pasar ini)

## Kesimpulan
- Fitur non-odds: PASS (cutoff ketat)
- Fitur odds: BELUM TERVERIFIKASI untuk live (closing vs opening)
- Pasar Home/Away O/U: PASS (tidak pakai odds)
