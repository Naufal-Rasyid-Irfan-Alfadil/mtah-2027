# Verifikasi eksperimen V2 — 7 November 2026

Laporan ini merekam audit awal sebelum perbaikan R. Pekerjaan lanjutannya
dicatat di [hasil_refinement_v2.md](hasil_refinement_v2.md); keputusan tentang
C di bawah tetap merupakan hasil eksperimen awal, bukan keputusan atas R.

**Keputusan: belum ada kandidat V2 yang lolos untuk menggantikan V1.**
Eksperimen selesai dan hasilnya dapat diperiksa ulang, tetapi seleksi akhirnya
mempertahankan A, yaitu model V1. `model_C.joblib` adalah kandidat eksperimen
yang ditolak, bukan model rilis yang siap diuji pada pertandingan resmi.

## Ruang lingkup dan batas akses

Verifikasi membaca source, fixture sintetis, tiga pertandingan DFL eksternal
yang sudah teridentifikasi, serta file model/source/provenance V1 yang disebut
secara eksplisit dalam manifest. Tidak ada penelusuran rekursif bundle V1.
Folder `external_artifacts/inference-bundle-v1/tactical` tidak dibuka, dipindai,
atau diproses. Audit hook memblokir akses ke folder itu, dataset yang tidak
diizinkan, dan artefak di luar daftar yang ditentukan.

Skor agregat pertandingan resmi dari pengguna tidak digunakan untuk mengubah
model, fitur, decoder, ambang seleksi, atau pilihan kandidat. Tidak ada training
ulang DFL, unduhan, instalasi dependensi, maupun inferensi resmi. Tes membuat
model kecil dari data sintetis. Runtime memakai venv yang sudah tersedia di
`external_artifacts/local-runtime/training-venv`; berkas sementara berada di
drive proyek, bukan direktori home.

## Kandidat yang diperiksa

| Kandidat | Perubahan terhadap V1 | Spell F1 bersih | Macro F1 bersih | Keputusan |
| --- | --- | ---: | ---: | --- |
| A | Model dan decoder V1 | 0.446316 | 0.863894 | Dipertahankan |
| B terbaik pada validasi bersih | Koreksi prior 0,5; bobot transisi 1; classifier tetap | 0.422869 | 0.862752 | Ditolak |
| C | Empat fitur konteks tambahan; decoder tetap | 0.507111 | 0.879104 | Ditolak oleh pemeriksaan ketahanan |

Angka ini berasal dari **J03WQQ eksternal**, kedua babak, 142.345 frame.
J03WQQ sudah dipakai untuk pengembangan; angka ini bukan hasil test independen
dan bukan skor pertandingan resmi. F1 bukan persentase akurasi.

Kelima variasi B menggunakan posterior yang sama, sehingga perbandingannya
memisahkan pengaruh decoder dari classifier. C menggunakan 18 fitur: 14 fitur
V1 ditambah cakupan bola dalam 25 frame terakhir, umur observasi bola lengkap,
dan median jarak pemain Home/Away terdekat selama jendela tersebut. Semua fitur
berasal dari observasi posisi/keteramatan; tidak ada masukan video, homography,
Smart Tagging, BallStatus, atau BallPossession ke fitur.

Training C tercatat memakai kedua babak J03WOH dan J03WPY, sebanyak 1.979.175
sampel setelah tujuh variasi augmentasi. Decoder berasal dari hitungan training
V1 dan tidak diestimasi ulang dari target validation. J03WOY dan J03WR9 sudah
pernah digunakan untuk penilaian historis dan tidak menjadi test baru di sini.

## Mengapa C ditolak

Aturan eksperimen mengizinkan penurunan maksimum 0,01 satuan F1 pada metrik
pengaman. C melampaui batas itu dalam dua kondisi eksternal:

| Kondisi | Metrik | A | C | Perubahan |
| --- | --- | ---: | ---: | ---: |
| Bola hilang beruntun selama 2 detik | F1 kelas D | 0.943398 | 0.929799 | -0.013599 |
| Sebagian observasi pemain dihilangkan | Transition F1, toleransi 12 frame | 0.385044 | 0.372197 | -0.012846 |

Peningkatan C pada data bersih tidak menghapus kegagalan tersebut. Seleksi yang
dihitung ulang dari seluruh metrik tersimpan memberikan keputusan dan alasan
penolakan yang sama. Batas pengaman tidak dilonggarkan setelah melihat hasil.
Pemanggilan pembuat bundle pada eksperimen ini juga ditolak dengan pesan
`no accepted v2 candidate to freeze`, tanpa menghasilkan direktori bundle baru.

## Bukti verifikasi

**Fakta — confidence tinggi:**

- Seluruh 95 tes berhasil, tanpa failure, error, atau skip; durasi 78,153 detik.
  Cakupannya termasuk pemisahan target, missing, gap/batas babak, fitur konteks
  kausal, decoder dibandingkan enumerasi jalur, urutan kelas, seleksi kandidat,
  bundle sintetis 18 fitur, penolakan manipulasi hash, dan kontrak CSV sintetis
  199.319 baris. Tes kontrak CSV tidak membuktikan kualitas prediksi resmi.
- Hash 23 file keluaran eksperimen dan 16 file input cocok dengan manifest.
  Bundle V1 diverifikasi hanya melalui daftar file source/model/provenance
  yang diizinkan; data tambahan lokal tidak diperiksa.
- Model C tersimpan mempunyai 18 fitur dengan urutan dan parameter HGB yang
  sesuai. Audit sampelnya hanya mencantumkan dua pertandingan training.
- Inferensi ulang A dan C pada dua babak validasi bersih menghasilkan label
  mentah dan hasil decoder yang identik dengan artefak sebelumnya. Probabilitas
  tidak identik bit demi bit: selisih absolut maksimum 2,220446049250313e-16,
  masih dalam toleransi 1e-12 dan tanpa perubahan label. Eksperimen awal
  menggunakan Windows/Python 3.11.6; pemeriksaan ini Linux/Python 3.11.17.
- Metrik dihitung ulang dari target DFL dan label tersimpan untuk ketujuh
  kandidat pada kondisi bersih, serta A/C pada dua kondisi penyebab penolakan.
  Seluruh 33 kamus metrik—per babak dan gabungan—cocok dalam toleransi 1e-12.
  Empat kondisi stres lainnya diperiksa hash dan keputusan seleksinya; metriknya
  tidak dihitung ulang dalam audit ini.

**Temuan provenance — confidence tinggi:** hash source saat eksperimen cocok
dengan source sekarang kecuali `external_baseline/inference_bundle.py`.
Dokumentasi sebelumnya mencatat perubahan helper sesudah eksperimen untuk
portabilitas path Windows/Linux. Source fitur, decoder, training, dan driver
V2 tetap cocok. Namun, source sekarang secara keseluruhan tidak identik dengan
source yang tercatat pada awal eksperimen.

**Temuan implementasi — confidence tinggi, dampak pada rilis berikutnya:**
`inference_bundle.build_v2` memeriksa hash keluaran eksperimen, tetapi kemudian
menyalin source saat ini tanpa membandingkannya dengan `source_sha256`
eksperimen. Karena itu, pemeriksaan provenance source harus diperketat sebelum
menerbitkan kandidat baru: ikat source algoritma ke source yang dievaluasi dan
catat perubahan packaging secara terpisah. Temuan ini tidak mengubah hasil
penolakan C; eksperimen sekarang berhenti sebelum tahap packaging tersebut.

**Batas kesimpulan — confidence sedang:** source dan manifest mendukung lineage
eksternal yang dinyatakan. Audit ini tidak dapat membuktikan seluruh riwayat
pengambilan keputusan manusia atau agent sebelumnya hanya dari berkas lokal.
Tidak ada klaim bahwa V2 sudah terbukti lebih baik pada pertandingan lain atau
pada pertandingan resmi.

## Langkah berikutnya

Pertahankan hasil eksperimen beserta penolakannya. Jangan menggunakan
`model_C.joblib` sebagai rilis V2 atau mengulangi uji resmi dengan mengira ada
model baru yang telah lolos. Lanjutkan diagnosis dua kegagalan C pada data
eksternal, lalu tetapkan protokol pengembangan berikutnya sebelum eksperimen
tambahan. Kandidat berikutnya perlu lolos pemeriksaan eksternal dan dibekukan
menjadi bundle yang source serta konfigurasinya terverifikasi sebelum pengguna
menjalankan inferensi resmi secara lokal.

Bukti mesin tersimpan di
`external_artifacts/v2/verification-20261107/`: `tests.json`, `tests.log`,
`artifacts.json`, `artifacts.log`, dan `verify.py`. Pemeriksaan ini menambahkan
laporan serta artefak audit tersebut; tidak mengubah source algoritma,
parameter, model, atau keputusan seleksi.
