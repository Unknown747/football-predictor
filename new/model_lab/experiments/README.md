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

## Stress test odds sintetis EXP-08

```bash
bash new/model_lab/run_odds_stress.sh
```

Runner mengulang EXP-05 untuk empat keluarga model dan EXP-01 untuk F0-F5 pada fixture yang sama di fold parsial `2026-27-partial`, lalu membandingkannya dengan artefak Mode B yang dipakai `predict.py`. Pasar yang diuji: 1X2, pertandingan O/U 2.5, dan gol kandang/tandang O/U 0.5 serta 1.5.

Empat skenario quote sintetis—`STANDARD`, `HEAVY_FAVOURITE`, `EXTREME_GAP`, `MISMATCHED_ODDS`—dibuat dari prior train dan fitur sebelum kickoff; label hasil test tidak dipakai untuk membuat harga. Model Mode B menerima quote sintetis sebagai pengganti fitur odds, sementara model lab tanpa odds tetap menggunakan fitur statistiknya. Semua kandidat dinilai pada quote yang sama. Aturan taruhan ilustratif adalah satu unit hipotetis saat EV terbaik model minimal 3%; angka ini tidak merepresentasikan stake atau profit nyata.

Hasil berada di `results/EXP-08-synthetic-odds-scenario-stress-20261028/`. Laporan ada di `odds-report/REPORT.md`, metrik lengkap semua kandidat di `odds-report/scenario_metrics.csv`, dan identitas input/aturan di `odds-report/manifest.json`. Karena fold historis telah dilihat dan harga dibuat sendiri, seluruh peringkat berstatus screening `REFERENCE_ONLY`, bukan pemenang final atau kesiapan live.

## Ablation fitur F0-F5 (EXP-01)

Runner `feature_ablation.py` membandingkan kelompok fitur kumulatif yang ditetapkan di `PLAN.md`. Keluarga model dibekukan per pasar dari empat fold lengkap EXP-05 sebelum fold terbaru, lalu keenam kelompok fitur dibandingkan pada fixture/outcome terbaru yang tersedia.

```bash
bash new/model_lab/run_feature_ablation.sh
```

Secara default runner memakai fold parsial `2026-27-partial`, semua pasar, dan semua kelompok. Pilihan terbatas untuk uji cepat:

```bash
bash new/model_lab/run_feature_ablation.sh \
  --markets home_ou05 --groups F0 F5 --fold 2026-27-partial
```

Keluaran berada di `results/EXP-01-feature-ablation-2026-27-partial/`. Karena data historis proyek telah ditinjau dan fold ini masih parsial, hasil tetap `REFERENCE_ONLY`; kelompok dengan skor terendah bukan kandidat siap pakai.
