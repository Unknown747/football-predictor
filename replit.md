# Menjalankan proyek di Replit

- Workflow **Start application** menjalankan `bash run_dashboard.sh` dan menyajikan dashboard Flask pada port 5000.
- Dependensi Python tercantum dalam `requirements.txt`. Launcher mengatur `LD_LIBRARY_PATH` untuk pustaka native LightGBM.
- Untuk menjalankan secara manual, gunakan `bash run_dashboard.sh`.
- Tombol scan di dashboard menjalankan scraping fixture, prediksi, dan pembuatan ulang HTML. Gunakan hanya jika memang ingin memperbarui data; membuka dashboard tidak menjalankan pipeline tersebut.
