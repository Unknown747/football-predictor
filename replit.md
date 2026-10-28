# Menjalankan proyek di Replit

- Workflow **Start application** menjalankan `bash run_dashboard.sh` dan menyajikan dashboard Flask pada port 5000.
- Dependensi Python tercantum dalam `requirements.txt`. Launcher mengatur `LD_LIBRARY_PATH` untuk pustaka native LightGBM.
- Untuk menjalankan secara manual, gunakan `bash run_dashboard.sh`.
- Tombol scan di dashboard menjalankan scraping fixture, prediksi, dan pembuatan ulang HTML. Gunakan hanya jika memang ingin memperbarui data; membuka dashboard tidak menjalankan pipeline tersebut.

## Mode kandidat EXP-06

- Mode prediksi default tetap Mode B. Jangan gunakan mode kandidat sebagai pengganti Mode B tanpa perubahan yang disetujui.
- Kandidat tersedia sebagai mode CLI opt-in `EXP06_BLEND_V1`; status output-nya `EXP06_BLEND_V1_REFERENCE_ONLY`. Kandidat tidak menggunakan odds sebagai fitur dan bukan model siap taruhan.
- Bundle inferensi dilatih ulang secara terpisah dari `data/features_train.csv` dengan cutoff inklusif 30 Juni 2026, diperiksa koherensinya pada data setelah cutoff, lalu disimpan di `new/model_lab/candidates/EXP06_BLEND_V1_REFERENCE_ONLY/`. Jalankan sekali: `bash new/model_lab/build_exp06_bundle.sh`.
- Untuk memprediksi secara manual tanpa menimpa snapshot dashboard: `bash new/model_lab/predict_exp06.sh --input <file-fixture.csv>`. Secara default output masuk ke `new/model_lab/paper/EXP06_BLEND_V1/`; opsi `--output-dir` dapat mengubah lokasi.
- Dashboard tetap memilih snapshot Mode B saja. Hasil kandidat tetap reference-only sampai evaluasi prospektif yang belum dilihat selesai; tidak ada klaim profitabilitas atau kesiapan taruhan.
