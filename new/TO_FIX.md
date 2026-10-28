# Yang Masih Perlu Diuji atau Diperbaiki

Status: **belum dianggap bug model yang terkonfirmasi**. Semua eksperimen UI dilakukan di `new/index.html`; jangan menyalin perubahan ke `index.html` utama sebelum hasilnya terbukti.

## 1. Selidiki perbedaan angka AC Milan–Bologna

Keluhan yang perlu diuji: kartu menampilkan **Home Win 49%**, sedangkan panel tim menampilkan **AC Milan menang kandang 59%** dan **Bologna menang tandang 35%**.

Pemeriksaan pada snapshot data yang tersedia menemukan:

- File prediksi terbaru berdasarkan timestamp nama file adalah `predictions/predictions_20261028_030931.csv`.
- Baris AC Milan–Bologna (`2026-10-28`, `Italy-SA`) berstatus `OK` dan berisi `p_H=0.4896`, `p_D=0.0975`, `p_A=0.4128`, `pred_1x2=H`.
- Nilai kartu **49.0%** dan tabel **Away Win 41.3%** cocok dengan probabilitas model tersebut setelah pembulatan.
- Angka **59%** dan **35%** berasal dari tingkat kemenangan historis di `data/ac_milan/home.csv` dan `data/bologna/away.csv`; masing-masing dihitung dari 98 pertandingan sebelum tanggal target. Itu statistik historis, bukan probabilitas 1X2 model, jadi angkanya tidak harus sama atau berjumlah 100%.

Karena itu, contoh ini **belum membuktikan bahwa tabel prediksi tidak sinkron dengan data**. Yang perlu dipastikan adalah apakah label dan tata letaknya cukup jelas agar statistik historis tidak disangka sebagai probabilitas model.

## 2. Periksa sumber dan keterlacakan mode model

File prediksi terbaru tersebut tidak memiliki kolom `prediction_mode`. Tanpa kolom ini, mode model yang menghasilkan angka AC Milan–Bologna tidak dapat dipastikan dari file tersebut. Telusuri pembuatan file prediksi dan pilihan file terbaru sebelum menyimpulkan ada kesalahan model.

## Kriteria sebelum dianggap selesai

- Setiap nilai prediksi di kartu dan tabel cocok dengan kolom `p_H`, `p_D`, atau `p_A` pada baris prediksi untuk tanggal, tim, dan liga yang sama.
- Statistik historis diberi label jelas dan dihitung dari file tim yang benar dengan cutoff sebelum tanggal pertandingan.
- Mode model serta sumber file prediksi dapat ditelusuri; jika tidak tersedia, UI harus menyebutkannya, bukan menebak.
- Pengujian mencakup AC Milan–Bologna dan pertandingan lain dengan mode/odds berbeda.
- Perubahan hanya dipindahkan ke `index.html` utama setelah hasil uji disetujui.

## Batas isolasi

- Gunakan `new/index.html` untuk percobaan visual.
- Tombol scan pada halaman uji sengaja dinonaktifkan. Endpoint `/api/scan` membangun ulang halaman utama, sehingga tidak aman dipanggil dari uji terisolasi.
- Jangan ubah `index.html` atau `build_html_dashboard.py` utama selama tahap investigasi ini.
