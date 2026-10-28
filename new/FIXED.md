# Yang Sudah Diperbaiki atau Diverifikasi

Catatan ini membedakan perbaikan kode dari temuan yang hanya sudah diverifikasi. Tidak ada perubahan pada `index.html` utama dalam pekerjaan uji ini.

## 1. Baseline halaman uji dibuat terpisah

- `new/index.html` dibuat dari salinan `index.html` utama pada 2026-10-28.
- Banner menandai halaman sebagai uji.
- Tombol scan dinonaktifkan agar halaman uji tidak memanggil `/api/scan`, yang menjalankan pipeline dan menulis ulang halaman utama.
- Halaman utama tetap menjadi sumber produksi dan tidak diubah oleh eksperimen ini.

## 2. Contoh AC Milan–Bologna sudah dicocokkan dengan sumbernya

Untuk snapshot yang diperiksa:

- Kartu **Home Win 49.0%** cocok dengan `p_H=48.96%` dari `predictions/predictions_20261028_030931.csv`.
- Tabel **Away Win 41.3%** cocok dengan `p_A=41.28%` dari baris yang sama.
- **AC Milan 59%** dan **Bologna 35%** adalah tingkat kemenangan historis terpisah dari 98 laga kandang/tandang masing-masing.

**Kesimpulan:** selisih 49% vs 59%/35% pada contoh ini bukan bukti bahwa probabilitas model tidak sinkron dengan baris prediksi. Masalah keterbacaan label dan ketiadaan `prediction_mode` pada file terbaru masih dicatat di `TO_FIX.md`; belum ada perubahan produksi untuk hal tersebut.

## 3. Perbaikan rekonstruksi historis yang sudah ada

- `logs/reconstruct_pit.py` memberi `match_id` stabil dari indeks baris saat `data/master_canon.csv` tidak menyediakan kolom tersebut.
- Verifikasi terakhir `python tests/test_predict.py`: **24/24 lulus**.
- Perbaikan ini berada di pipeline prediksi, bukan perubahan pada dashboard utama.
