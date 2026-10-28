# Eksperimen

## Benchmark keluarga model EXP-05

Runner `benchmark_model_families.py` membandingkan empat baseline pra-pertandingan: LightGBM, XGBoost, HistGradientBoosting, dan regresi logistik.

- Fitur dibatasi ke whitelist numeric historis yang sama dengan pola aman proyek; odds, hasil pertandingan, dan statistik pascapertandingan tidak masuk ke input model.
- Enam pasar dinilai terpisah. Model memakai bobot pelatihan half-life 365 hari.
- Fold expanding-window mengikuti musim 2022-23 sampai 2026-27 parsial. Boosting rounds untuk LightGBM/XGBoost dipilih melalui trailing inner validation 90 hari, lalu model dilatih ulang pada seluruh train fold.
- Metrik utama adalah LogLoss dan Brier. Accuracy, AUC, ECE 10-bin, hasil per liga/fold, serta paired bootstrap mingguan dengan koreksi Bonferroni 32 perbandingan dicatat sebagai diagnostik/ketidakpastian.
- Prior base-rate dihitung hanya dari train fold. Odds penutupan pada 1X2 dan O/U 2.5 hanya menjadi pembanding `CLOSING_ODDS_REFERENCE`, dengan sampel yang cocok; bukan input atau harga saat keputusan taruhan.
- Semua fold historis berstatus `REFERENCE_ONLY`, karena rentang hasil ini telah pernah ditinjau dalam proyek. Ranking tidak menghasilkan model siap taruhan.

Jalankan dari root proyek:

```bash
bash new/model_lab/run_benchmark.sh
```

Untuk menguji satu pasar, model, dan fold:

```bash
bash new/model_lab/run_benchmark.sh --markets home_ou05 --models logreg --fold 2025-26
```

Hasil tidak disalin ke `models/`, `predictions/`, `backtest/`, atau dashboard utama. Detail metode, batas odds, dan langkah lanjutan ada di keluaran `REPORT.md` serta manifest run.

## Eksperimen lain

Buat satu subfolder per run, misalnya `EXP-01-form-ablation-20261028/`. Simpan konfigurasi yang dibekukan, log, manifest input, dan catatan keputusan di folder run tersebut. Salin `../EXPERIMENT_TEMPLATE.md` sebagai catatan utama.

Semua runner dan keluaran harus tetap di bawah `new/model_lab/`. Jangan menjalankan script utama langsung dengan output ke `models/`, `predictions/`, atau `backtest/`.
