# Yang Sudah Diperbaiki atau Diverifikasi

Catatan ini membedakan perbaikan kode dari temuan yang hanya sudah diverifikasi.

## 1. Baseline halaman uji dibuat terpisah

- `new/index.html` dibangun ulang dari generator HTML proyek dengan keluaran dialihkan ke folder `new/`, sehingga tidak menulis ke halaman utama.
- Banner menandai halaman sebagai uji.
- Tombol scan dinonaktifkan agar halaman uji tidak memanggil `/api/scan`, yang menjalankan pipeline dan menulis ulang halaman utama.
- Halaman utama tetap menjadi sumber produksi dan tidak diubah oleh eksperimen ini.

## 2. Sumber angka AC Milan–Bologna sudah dicocokkan

Untuk snapshot yang diperiksa:

- Kartu **Home Win 49.0%** cocok dengan `p_H=48.96%` dari `predictions/predictions_20261028_030931.csv`.
- Tabel **Away Win 41.3%** cocok dengan `p_A=41.28%` dari baris yang sama.
- **AC Milan 59%** dan **Bologna 35%** adalah tingkat kemenangan historis terpisah dari 98 laga kandang/tandang masing-masing.
- Ketiga probabilitas model adalah `p_H=48.9626%`, `p_D=9.7525%`, `p_A=41.2849%`; totalnya 100.0000% setelah dibulatkan ke empat angka desimal.

**Kesimpulan:** nilai probabilitas pada kartu yang tersedia cocok dengan CSV. Selisih 49% vs 59%/35% membandingkan probabilitas model dengan win rate historis, bukan dua nilai model yang seharusnya sama.

## 3. Prototipe label dan cakupan penuh tersedia di halaman uji

- `new/index.html` menampilkan 226 kartu dari 226 baris CSV berstatus valid.
- Tabel 1X2 menampilkan Home, Draw, dan Away; judul panel riwayat menyebut bahwa win rate historis bukan probabilitas model.
- Mode model ditandai “tidak tercatat” karena kolom itu tidak ada pada CSV sumber terbaru.
- Tombol scan tetap nonaktif di halaman uji.
- Setelah hasil uji lolos, perubahan label dan cakupan diterapkan ke generator dan halaman utama.

## 4. Halaman utama sudah diregenerasi dan dicocokkan

- Snapshot sebelum regenerasi memiliki 190 kartu dari 226 baris valid; **36 baris belum tampil saat itu**.
- Halaman utama kini menampilkan **226 kartu** dari 226 baris valid.
- Pemeriksaan berdasarkan tanggal, tim, dan p_H/p_D/p_A menemukan 226 kecocokan dan **0 selisih probabilitas**.
- Tombol scan tetap aktif di halaman utama; banner dan tombol nonaktif hanya ada di `new/index.html`.
- Generator memang memilih CSV terbaru menurut timestamp pada nama file dan sekarang merapikan spasi akhir saat menulis HTML.

## 5. Penyebab `prediction_mode` hilang sudah ditelusuri

- CSV terbaru cocok persis dengan skema 49 kolom dari predictor lama; skema saat ini menambah satu kolom `prediction_mode`.
- Predictor lama menggunakan model Mode B untuk semua prediksi dan tidak menyimpan nama mode ke CSV.
- `used_odds_input=none` tidak cukup untuk mengubah label historis menjadi `A_NO_ODDS`; mode lama tidak ditebak atau ditulis ulang.
- Jalur scan saat ini menjalankan predictor yang menulis mode. Tidak ada pemindaian atau prediksi ulang yang dijalankan saat investigasi.

## 6. Perbaikan rekonstruksi historis yang sudah ada

- `logs/reconstruct_pit.py` memberi `match_id` stabil dari indeks baris saat `data/master_canon.csv` tidak menyediakan kolom tersebut.
- Verifikasi terakhir `python tests/test_predict.py`: **24/24 lulus**.
- Perbaikan ini berada di pipeline prediksi, bukan perubahan pada dashboard utama.
