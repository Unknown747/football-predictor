# Audit Integritas Artefak

## 1. Model Files
- models/lgb_1x2_modeB.txt: 0e78456e59e8ff63...
- models/lgb_ou25_modeB.txt: de65429544bee058...
- models/lgb_home_ou05_modeB.txt: c91dd5bc44f0bdf0...
- models/lgb_home_ou15_modeB.txt: 1de2dd1ce6c19932...
- models/lgb_away_ou05_modeB.txt: 8ff79bc5716a30a3...
- models/lgb_away_ou15_modeB.txt: 7de8119cce018a42...
Status: PASS (semua file ada, hash tercatat di config.json L10.7).

## 2. Dataset
- data/features_train.csv: 37b54914bd714fdb... (stabil)
- data/master_canon.csv: 3337a960b355a9de... (stabil)
Status: PASS

## 3. Kalibrasi
calibration/calibration_20261026_221135/ (calibrators.pkl, eval CSV)
Status: PASS sebagai ARTEFAK EKSPERIMEN, bukan production.

Catatan: Kalibrator TIDAK diintegrasikan ke predict.py. Kalibrasi eksperimen
hanya ada di folder calibration/. predict.py menggunakan raw probabilities.

## 4. Dokumentasi L10.7
- FINAL_REPORT.md: ada
- MODEL_METRICS.md: ada
- LEAGUE_AUDIT.md: ada
- CALIBRATION_REPORT.md: ada
- LIMITATIONS.md: ada
- ARTIFACT_INDEX.md: ada
Status: PASS (semua file ada di reports/final_audit_20261026/)

## 5. Reference Check
Laporan L10.7 mengacu ke artefak backtest L10.2 dan audit L10.4 v2. Semua path
yang dirujuk sudah diverifikasi ada di langkah sebelumnya.

Status: PASS

## Kesimpulan
- Model files: PASS
- Dataset: PASS
- Kalibrasi (eksperimen, bukan production): PASS
- Dokumentasi L10.7: PASS
- Reference: PASS
