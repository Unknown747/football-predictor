# Catatan Eksperimen — `<ID>`

## Pertanyaan dan hipotesis
- Pertanyaan:
- Hipotesis sebelum melihat hasil:
- ID register:

## Ruang lingkup
- Pasar: `1x2 | ou25 | home_ou05 | home_ou15 | away_ou05 | away_ou15`
- Data dan hash/snapshot:
- Rentang tanggal:
- Fold train / validation / test:
- Mode input: `team-stats-only | timestamp-valid-odds`
- Sumber dan timestamp odds (jika ada):

## Konfigurasi yang dibekukan
- Baseline:
- Perubahan fitur/model tunggal:
- Parameter:
- Aturan early stopping:
- Metrik utama:
- Metrik sekunder:
- Batas keputusan yang ditetapkan sebelum run:

## Pemeriksaan sebelum run
- [ ] Semua artefak baru berada di `new/model_lab/`.
- [ ] Tidak ada file utama, data, model, atau hasil produksi yang ditulis.
- [ ] Fitur tersedia sebelum kick-off; tidak ada target/post-match leakage.
- [ ] Split kronologis; test fold tidak digunakan untuk memilih konfigurasi.
- [ ] Kelas dan missing history dihitung per fold.
- [ ] Odds hanya dipakai bila timestamp-nya sesuai waktu ramalan.

## Hasil
| Fold | Target | N | Model LogLoss | Baseline LogLoss | Model Brier | Baseline Brier | Catatan kalibrasi |
|---|---|---:|---:|---:|---:|---:|---|
| | | | | | | | |

- Interval ketidakpastian / block bootstrap:
- Hasil per liga atau musim:
- Konsistensi probabilitas lintas pasar:
- Kegagalan dan data yang dikecualikan:

## Keputusan
- Status: `REPRODUCED | CANDIDATE | REJECTED`
- Alasan:
- Keterbatasan:
- File konfigurasi, log, prediksi, dan hash artefak:

Tidak ada prediksi pada halaman utama yang diubah oleh eksperimen ini. Tidak ada live bet.
