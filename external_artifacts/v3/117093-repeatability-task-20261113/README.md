# Pengukuran ulang 117093

Ada 18 crop dari referensi eksternal yang sudah dibekukan. Tidak ada jawaban
lama atau proyeksi model pada gambar. Semua PNG raw berukuran 256 x 128.

## Mulai dari R01

1. Buka [R01 raw](crops/R01-raw.png) di Paint.
2. Cari pusat garis putih pada baris **y=64**; lihat status bar Paint.
3. Kirim nilai **x** pada posisi tersebut, contoh format: `R01: x=...`.

Koordinat dihitung dari crop ini, bukan dari gambar lapangan 4096 x 1080.
Jangan mengukur contact sheet atau gambar guide. Guide hanya menunjukkan irisan.
Jika garis tidak jelas, jawab `ambiguous`; jika tertutup, jawab `occluded`.
Jangan membuka jawaban lama/prediksi saat mengukur. Setelah sesi, laporkan jika
jawaban lama atau overlay terlihat, dan siapa yang mengukur.

Kamu boleh mengirim beberapa hasil sekaligus. CSV repeats.csv sengaja kosong;
hasil percakapan akan dicatat terpisah. Jangan menyalin angka pengukuran pertama.

| ID | Gambar raw | Pengukuran |
| --- | --- | --- |
| R01 | [Buka](crops/R01-raw.png) | baca **x** pada **y=64** |
| R02 | [Buka](crops/R02-raw.png) | baca **y** pada **x=128** |
| R03 | [Buka](crops/R03-raw.png) | baca **x** pada **y=64** |
| R04 | [Buka](crops/R04-raw.png) | baca **y** pada **x=128** |
| R05 | [Buka](crops/R05-raw.png) | baca **y** pada **x=128** |
| R06 | [Buka](crops/R06-raw.png) | baca **x** pada **y=64** |
| R07 | [Buka](crops/R07-raw.png) | baca **x** pada **y=64** |
| R08 | [Buka](crops/R08-raw.png) | baca **y** pada **x=128** |
| R09 | [Buka](crops/R09-raw.png) | baca **y** pada **x=128** |
| R10 | [Buka](crops/R10-raw.png) | baca **y** pada **x=128** |
| R11 | [Buka](crops/R11-raw.png) | baca **y** pada **x=128** |
| R12 | [Buka](crops/R12-raw.png) | baca **y** pada **x=128** |
| R13 | [Buka](crops/R13-raw.png) | baca **x** pada **y=64** |
| R14 | [Buka](crops/R14-raw.png) | baca **y** pada **x=128** |
| R15 | [Buka](crops/R15-raw.png) | baca **y** pada **x=128** |
| R16 | [Buka](crops/R16-raw.png) | baca **y** pada **x=128** |
| R17 | [Buka](crops/R17-raw.png) | baca **y** pada **x=128** |
| R18 | [Buka](crops/R18-raw.png) | baca **x** pada **y=64** |

## Batas penafsiran

Ini pengukuran ulang operator yang sudah melihat gambar/pengukuran pertama;
blinding dan independensi penuh tidak diklaim. Crop dilokalisasi memakai
pengukuran pertama, tanpa menampilkan nilai sumbu yang diukur ulang.
Tidak mengubah referensi awal, membaca kalibrasi/prediksi, atau melakukan fitting.

Metode pasangan, statistik dan batas penafsiran ditetapkan pada [protocol.md](protocol.md).
Belum ada hasil pengukuran kedua, angka repeatability atau toleransi produksi.
Batas error geometri perlu dasar kebutuhan downstream sebelum scoring kandidat.
V2/R r1 tetap kandidat pengumpulan.
