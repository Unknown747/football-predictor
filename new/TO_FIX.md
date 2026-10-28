# Yang Masih Perlu Diuji atau Diperbaiki

Status: perbedaan probabilitas AC Milan–Bologna **bukan bug model yang terkonfirmasi**. Ada masalah cakupan pada snapshot HTML utama. Pengujian dan prototipe tetap di `new/index.html`; halaman utama belum diubah.

## 1. Selidiki perbedaan angka AC Milan–Bologna

Keluhan yang perlu diuji: kartu menampilkan **Home Win 49%**, sedangkan panel tim menampilkan **AC Milan menang kandang 59%** dan **Bologna menang tandang 35%**.

Pemeriksaan pada snapshot data yang tersedia menemukan:

- File prediksi terbaru berdasarkan timestamp nama file adalah `predictions/predictions_20261028_030931.csv`.
- Baris AC Milan–Bologna (`2026-10-28`, `Italy-SA`) berstatus `OK` dan berisi `p_H=0.4896`, `p_D=0.0975`, `p_A=0.4128`, `pred_1x2=H`.
- Nilai kartu **49.0%** dan tabel **Away Win 41.3%** cocok dengan probabilitas model tersebut setelah pembulatan.
- Angka **59%** dan **35%** berasal dari tingkat kemenangan historis di `data/ac_milan/home.csv` dan `data/bologna/away.csv`; masing-masing dihitung dari 98 pertandingan sebelum tanggal target. Itu statistik historis, bukan probabilitas 1X2 model, jadi angkanya tidak harus sama atau berjumlah 100%.

Karena itu, selisih angka pada contoh ini bukan perbedaan antara `p_H` dan win rate historis yang sama jenisnya. Label dan tata letak uji kini memisahkan probabilitas model dari win rate historis. Perubahan itu hanya ada di `new/index.html`.

## 2. Periksa sumber dan keterlacakan mode model

File prediksi terbaru tersebut tidak memiliki kolom `prediction_mode`. Tanpa kolom ini, mode model yang menghasilkan angka AC Milan–Bologna tidak dapat dipastikan dari file tersebut. Telusuri pembuatan file prediksi dan pilihan file terbaru sebelum menyimpulkan ada kesalahan model.

## 3. Tampilkan semua prediksi valid dari CSV

Perbandingan berdasarkan tanggal dan kedua nama tim menemukan:

- CSV terbaru memuat **226** baris berstatus `OK` atau `OK_WITH_WARNING`.
- `index.html` utama menampilkan **190** kartu.
- Semua 190 kartu yang tampil cocok dengan baris prediksi yang sama untuk hasil 1X2; **tidak ditemukan perbedaan angka** pada kartu yang dibandingkan.
- Ada **36** baris prediksi valid yang tidak tampil di halaman HTML. Contoh: Carrarese–Arezzo dan Juve Stabia–Hellas Verona.
- Generator HTML terbaru, saat keluarannya dialihkan khusus ke `new/index.html`, menghasilkan **226 kartu**. Artinya, halaman uji menampilkan semua baris valid dari CSV terbaru.

Penyebab `index.html` utama masih berisi 190 kartu belum diketahui; hasil uji mengarah pada snapshot utama yang tidak dibangun ulang dari CSV terbaru. Jangan regenerasi atau mengganti halaman utama sebelum hasil halaman uji ditinjau. Tombol scan di halaman uji sengaja dimatikan karena endpoint saat ini menulis ulang `index.html` utama.

## Kriteria sebelum dianggap selesai

- Setiap nilai prediksi di kartu dan tabel cocok dengan kolom `p_H`, `p_D`, atau `p_A` pada baris prediksi untuk tanggal, tim, dan liga yang sama.
- Semua baris berstatus `OK` atau `OK_WITH_WARNING` dari CSV terbaru muncul satu kali di HTML, kecuali bila ada alasan filter yang terdokumentasi.
- Tabel 1X2 menampilkan Home, Draw, dan Away; probabilitas bersumber dari baris prediksi yang sama dan totalnya konsisten setelah pembulatan.
- Statistik historis diberi label jelas dan dihitung dari file tim yang benar dengan cutoff sebelum tanggal pertandingan.
- File prediksi baru menyertakan `prediction_mode`; jika tidak tersedia, UI harus menyebutkannya, bukan menebak.
- Pengujian mencakup AC Milan–Bologna dan pertandingan lain dengan mode/odds berbeda.
- Halaman utama baru diperbarui setelah hasil uji ditinjau.

## Batas isolasi

- Gunakan `new/index.html` untuk percobaan visual.
- Tombol scan pada halaman uji sengaja dinonaktifkan. Endpoint `/api/scan` membangun ulang halaman utama, sehingga tidak aman dipanggil dari uji terisolasi.
- Jangan ubah `index.html` atau `build_html_dashboard.py` utama selama tahap investigasi ini.
