# Ruang Riset Model — `new/model_lab/`

Status saat dibuat: **rencana saja**. Belum ada training, backtest, taruhan, atau perubahan model pada sesi ini.

Folder ini menjadi satu-satunya tempat untuk eksperimen peningkatan model. Script, konfigurasi, salinan data eksperimen, log, evaluasi, dan kandidat model harus berada di bawah `new/`.

## Aturan isolasi

- Jangan mengubah script utama `features.py`, `train.py`, `predict.py`, atau `predict_dc.py`.
- Jangan menimpa `data/`, `models/`, `predictions/`, `backtest/`, maupun hasil produksi.
- Gunakan artefak tersebut sebagai referensi baca-saja. Jika eksperimen perlu kode, buat salinan/runner khusus di folder ini.
- Model sekarang berasal dari statistik tim dalam database menurut keterangan pengguna.
- Prediksi **belum pernah digunakan untuk live bet**. Hasil historis bukan bukti hasil live atau profit.
- Perubahan dari kandidat ke sistem utama harus menjadi langkah terpisah setelah kandidat lolos gerbang evaluasi dan pengguna memberi persetujuan.

## Isi folder

```text
new/model_lab/
├── README.md
├── PLAN.md
├── EXPERIMENT_REGISTER.csv
├── EXPERIMENT_TEMPLATE.md
├── experiments/    # konfigurasi dan catatan tiap eksperimen
├── results/        # metrik, prediksi uji, dan ringkasan per fold
├── candidates/     # artefak kandidat terpilih; bukan model produksi
└── paper/          # prediksi prospektif tanpa taruhan uang
```

Mulai dari `PLAN.md`. Catat setiap run di `EXPERIMENT_REGISTER.csv` dan salin `EXPERIMENT_TEMPLATE.md` ke folder eksperimennya. Jangan menulis status `PROMOTED` tanpa persetujuan pengguna.
