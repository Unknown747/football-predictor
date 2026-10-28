# Menjalankan proyek di Replit

- Workflow **Start application** menjalankan `bash run_dashboard.sh` dan menyajikan dashboard Flask pada port 5000.
- Dependensi Python tercantum dalam `requirements.txt`. Launcher mengatur `LD_LIBRARY_PATH` untuk pustaka native LightGBM.
- Untuk menjalankan secara manual, gunakan `bash run_dashboard.sh`.
- Tombol scan di dashboard menjalankan scraping fixture, prediksi, dan pembuatan ulang HTML. Gunakan hanya jika memang ingin memperbarui data; membuka dashboard tidak menjalankan pipeline tersebut.

## Model prediksi utama

- Prediksi utama memakai bundle blend EXP-06 di `models/exp06_blend_v1/`; `predict.py` memilihnya secara default dan memberi tag `EXP06_BLEND_V1_PRIMARY_REFERENCE_ONLY`.
- Model memakai 74 fitur statistik historis tanpa odds. Odds yang masuk masih dapat dipakai untuk menghitung kolom nilai, tetapi tidak mengubah probabilitas model.
- Bundle dilatih dengan cutoff inklusif 30 Juni 2026. Semua evaluasi yang tersedia bersifat historis/reference-only; model belum divalidasi prospektif, belum terbukti menguntungkan, dan bukan model siap taruhan.
- Mode B lama tetap tersedia untuk pembanding: `python predict.py --input <file-fixture.csv> --mode B`. `train.py` masih melatih Mode B lama dan tidak menimpa bundle utama EXP-06.
- Dashboard memilih snapshot terbaru bertag model yang dikenal dan menampilkan model serta batasannya. Tombol scan menjalankan scraper, prediksi utama, lalu membangun ulang dashboard.
