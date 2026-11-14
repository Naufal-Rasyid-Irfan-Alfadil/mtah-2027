# Pengukuran ulang referensi 117093

Status: protokol pengumpulan ditetapkan sebelum pengukuran kedua dan sebelum
scoring geometri. Paket ini hanya audit anotasi eksternal; V2/R r1 tetap kandidat.

## Sampel dan provenance

Gunakan snapshot `external_artifacts/v3/117093-reference-freeze-20261113/`,
manifest SHA256 `f8d2092da58461126ba21bea7d000008a28e358ce49c3566fb1b4e847f12819f`.
Pilih point 2 dari enam fitur pada masing-masing frame 7500/37500/60000:
18 dari 54 anotasi, satu kamera. Pemilihan menurut slot, bukan residual model.
Urutan diacak deterministik dengan seed 117093. Tidak membaca H/pose/prediksi.

Crop raw berasal dari PNG yang cocok checksum snapshot. Lokalisasi crop memakai
pengukuran pertama; ini bukan anotasi independen sepenuhnya. Koordinat yang
diukur ulang dan marker lama tidak ditampilkan pada lembar kerja. Operator
sudah pernah mengukur gambar yang sama; efek ingatan tidak dapat dihilangkan.
Reviewer assistant telah melihat diagnosis model dan koordinat sebelumnya.

## Pengukuran yang diperlukan

Ambil kembali pusat garis cat yang terlihat pada irisan piksel tetap:

- Touchline dekat/jauh dan sisi kotak penalti: cari y pada x crop = 128.
- Halfway: cari x pada y crop = 64.
- Lingkaran: cari x pada y crop = 64, pada sisi kanan lingkaran yang tampak.

Crop berukuran 256 x 128 piksel asli, tidak di-resize, origin kiri atas (0,0).
PNG `*-raw.png` tidak memuat marker atau overlay. Lembar panduan terpisah hanya
memberi panah pada margin di lokasi irisan; tidak menandai hasil pengukuran.
Pakai koordinat crop raw dari status bar Paint, bukan koordinat contact sheet
atau PNG panduan. Boleh zoom Paint; sistem koordinat harus tetap piksel gambar.

Jangan membuka anotasi lama, review bertanda atau prediksi selama pengukuran
ulang. Catat jika itu terjadi, siapa annotator, serta apakah overlay terlihat
pada sesi ulang. Riwayat paparan sebelumnya tetap dicatat; tidak diklaim blind.
Jika garis tidak jelas/tertutup, isi ambiguous/occluded dan biarkan koordinat
kosong. Jangan menebak. Hasil pengukuran pertama tidak diubah; semua pengukuran
kedua dicatat terpisah dan `used_for_fitting=false`.

## Analisis yang ditetapkan sebelum hasil kedua

Pasangkan sample_id dengan slot pertama melalui manifest. Validasi checksum
snapshot, crop, identitas, batas koordinat, irisan tetap, visibility dan
provenance sebelum analisis. Untuk titik terlihat, ubah koordinat crop ke raw
dengan menambahkan crop_origin_x/y. Selisih bertanda adalah koordinat kedua
dikurangi pertama pada sumbu yang diukur ulang; laporkan juga nilai absolut.

Laporkan n valid/missing/exposed, selisih median/p95 absolut dan maksimum secara
keseluruhan serta per fitur/frame. p95 memakai interpolasi linear pada indeks
0,95*(n-1) data terurut. Statistik hanya deskriptif: tiga pasangan per fitur
tidak memberikan estimasi tail atau confidence interval yang kuat. Jangan
menyamakan variasi sumbu ini dengan jarak normal kurva atau error dalam meter.
Tidak membagi selisih dengan sqrt(2) untuk mengklaim noise absolut; independensi
dua pengukuran belum terbukti. Bias bersama dan error identitas fitur tetap
tidak terukur. Hasil bukan target possession atau bukti kenaikan Spell F1.

Jika exposure terjadi, tampilkan terpisah; jangan menghapus diam-diam atau
mencampur sebagai tanpa paparan. Jangan mengisi hasil kedua dari koordinat
pertama, fitting penerbit, segmentasi otomatis, atau prediksi model.

## Batas error dan langkah sesudahnya

Belum ada angka kelulusan geometri/produksi yang dapat dibenarkan. Setelah
pengukuran ulang, laporkan ketelitian yang teramati dan keterbatasannya. Bekukan
anggaran error yang memiliki dasar kebutuhan downstream sebelum membuka skor
kandidat. Jangan menetapkan toleransi hanya agar H atau pose tertentu lolos.
Tanpa kebutuhan downstream yang memadai, evaluasi numerik/promosi tetap
tertahan. Target possession independen tersinkron adalah gate terpisah.
