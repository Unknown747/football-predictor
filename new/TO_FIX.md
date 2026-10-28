# Yang Masih Perlu Diuji atau Diperbaiki

Status: cakupan halaman utama sudah diperbaiki dan diuji. Selisih AC Milan–Bologna bukan bug model yang terkonfirmasi. Penyebab kolom `prediction_mode` tidak ada sudah ditemukan; CSV lama tetap tidak aman untuk diberi mode hasil tebakan.

## 1. Selidiki perbedaan angka AC Milan–Bologna

Keluhan yang perlu diuji: kartu menampilkan **Home Win 49%**, sedangkan panel tim menampilkan **AC Milan menang kandang 59%** dan **Bologna menang tandang 35%**.

Pemeriksaan pada snapshot data yang tersedia menemukan:

- File prediksi terbaru berdasarkan timestamp nama file adalah `predictions/predictions_20261028_030931.csv`.
- Baris AC Milan–Bologna (`2026-10-28`, `Italy-SA`) berstatus `OK` dan berisi `p_H=0.4896`, `p_D=0.0975`, `p_A=0.4128`, `pred_1x2=H`.
- Nilai kartu **49.0%** dan tabel **Away Win 41.3%** cocok dengan probabilitas model tersebut setelah pembulatan.
- Angka **59%** dan **35%** berasal dari tingkat kemenangan historis di `data/ac_milan/home.csv` dan `data/bologna/away.csv`; masing-masing dihitung dari 98 pertandingan sebelum tanggal target. Itu statistik historis, bukan probabilitas 1X2 model, jadi angkanya tidak harus sama atau berjumlah 100%.

Karena itu, selisih angka pada contoh ini bukan perbedaan antara `p_H` dan win rate historis yang sama jenisnya. Label yang memisahkan probabilitas model dari win rate historis kini sudah diterapkan ke halaman utama dan generatornya.

## 2. Mode pada CSV lama — penyebab ditemukan, nilai tetap tidak tercatat

Perbandingan versi memastikan:

- CSV terbaru berisi **49 kolom** dan cocok persis dengan skema predictor lama.
- Skema `predict.py` saat ini memiliki **50 kolom**; satu-satunya kolom tambahan adalah `prediction_mode`.
- Predictor lama memuat model dan daftar fitur Mode B untuk semua baris. Kolom `used_odds_input=none` pada CSV lama **tidak** berarti prediksi itu memakai Mode A.
- Endpoint scan saat ini menjalankan `predict.py` yang menulis `prediction_mode` sebagai `A_NO_ODDS` atau `B_WITH_ODDS`; file baru dari jalur ini akan mencatat mode.

Mode pada CSV historis tidak akan ditebak atau ditulis ulang. Untuk menghasilkan prediksi dengan skema dan model saat ini dibutuhkan proses prediksi baru; proses itu tidak dijalankan karena ada instruksi agar tidak mengulang pipeline dari awal.

## 3. Cakupan seluruh prediksi valid — sudah diperbaiki

Sebelum regenerasi, perbandingan berdasarkan tanggal dan kedua nama tim menemukan:

- CSV terbaru memuat **226** baris berstatus `OK` atau `OK_WITH_WARNING`.
- `index.html` utama menampilkan **190** kartu.
- Semua 190 kartu yang tampil cocok dengan baris prediksi yang sama untuk hasil 1X2; **tidak ditemukan perbedaan angka** pada kartu yang dibandingkan.
- Ada **36** baris prediksi valid yang tidak tampil di halaman HTML. Contoh: Carrarese–Arezzo dan Juve Stabia–Hellas Verona.
- Generator yang sama menghasilkan **226 kartu** di `new/index.html`; setelah hasil uji ditinjau, generator diterapkan dan `index.html` utama dibangun ulang.

Sekarang halaman utama menampilkan **226 kartu**, cocok dengan seluruh baris CSV valid, tanpa selisih nilai probabilitas. Kesenjangan 36 baris sudah ditutup dengan regenerasi. Untuk mencegah snapshot tertinggal lagi, pastikan proses yang menghasilkan CSV juga memanggil generator HTML.

## Pemeriksaan regresi ke depan

- Setiap nilai prediksi di kartu dan tabel cocok dengan kolom `p_H`, `p_D`, atau `p_A` pada baris prediksi untuk tanggal, tim, dan liga yang sama.
- Semua baris valid saat ini sudah muncul satu kali di halaman utama; pertahankan pemeriksaan ini saat generator atau pipeline berubah.
- Tabel 1X2 menampilkan Home, Seri/Draw, dan Away; nilai bersumber dari baris prediksi yang sama.
- Statistik historis di halaman utama sudah diberi label jelas dan dihitung dari file tim sebelum tanggal pertandingan.
- CSV baru dari endpoint scan menyertakan `prediction_mode`; jika tidak tersedia, UI harus menyebutkannya, bukan menebak.
- Pengujian mencakup AC Milan–Bologna dan pertandingan lain dengan mode/odds berbeda.

## Batas isolasi

- Gunakan `new/index.html` untuk percobaan visual berikutnya sebelum menerapkannya ke halaman utama.
- Tombol scan pada halaman uji sengaja dinonaktifkan. Endpoint `/api/scan` membangun ulang halaman utama, sehingga tidak aman dipanggil dari uji terisolasi.
- Halaman utama memakai tombol scan aktif dan dibangun dari `build_html_dashboard.py`.
- Jangan mengisi mode CSV lama dari `used_odds_input`; file itu dibuat oleh predictor Mode B lama.
