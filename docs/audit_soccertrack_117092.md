# Audit paket SoccerTrack 117092 yang diunduh pengguna

12 November 2026. Input eksternal yang dinyatakan pengguna:
`Soccertrack V2/`. Hanya delapan path dalam manifest download yang dibuka.
Rilis dataset dipin ke v1.2, commit
`325bd4c57ee8e135ab652f3921d274526ada496b`, CC BY 4.0.
Tidak ada data resmi, inferensi model, fitting, atau detector/fusion.

## Integritas dan akses

Delapan berkas tersedia, total 487.760 byte. Enam berkas non-LFS cocok persis
ukuran dan **Git blob SHA-1** katalog penerbit. Dua payload NumPy cocok ukuran
dan SHA-256 yang pengguna salin dari bagian Git LFS Details Hugging Face pada
12 November 2026. Bukti ini merupakan transkripsi pengguna, bukan pengambilan
hash penerbit secara mandiri oleh agent. Git OID pointer LFS tidak diperlakukan
sebagai hash payload. **Integritas delapan berkas lolos.**

| Payload LFS | Ukuran | SHA-256 cocok dengan transkripsi pengguna dari penerbit |
| --- | --- | --- |
| 117092_camera_intrinsics.npz | 1.996 byte | 4f6db409ac8f5b36b62898ac279247add16cc1ff905583440ac71f45c6a167fb |
| 117092_homography.npy | 200 byte | 26dcb723a362e9be1acad852313e9f55565d49260a2a68f6e39481e4e0bf2cc3 |

Semua hash input tetap sama setelah inspeksi. Input pengguna tidak diubah dan
direktorinya diabaikan Git. Penerimaan berkas kecil membuktikan pengguna dapat
memperoleh delapan berkas ini; bukan bukti akses atau ketersediaan semua video.

Laporan mesin:
`external_artifacts/v3/soccertrack-117092-package-audit-20261112-r2/report.json`.
Report awal tetap utuh sebagai riwayat sebelum hash penerbit diterima.
Uji perubahan satu byte dengan ukuran tetap pada salinan sementara homography
ditolak sebelum output dibuat; berkas asli tidak diubah.
Alat audit: `tools/audit_soccertrack_package.py`.

## Kontrak aktual yang kini diketahui

- Keypoints berisi 65 pasangan koordinat lapangan ke piksel. Koordinat lapangan
  0..105 dan 0..68, berpusat di sudut; berbeda dari GSR berpusat di tengah.
  Tidak menebak arah sumbu GSR dari koordinat keypoints saja.
- NPZ memuat numerik `K`, `D`, `Knew`, `rms`, serta object-array `rvecs`/`tvecs`.
  Hanya numerik dibaca dengan `allow_pickle=False`; object-array hanya diperiksa
  headernya. Nilai RMS tersimpan 30,632 px merupakan diagnostik fitting penerbit,
  bukan akurasi independen. Homography finite 3×3 dan rank penuh; itu tidak
  membuktikan benar pada gambar/video.
- BAS memakai `actions`, bukan `annotations`; label uppercase seperti `PASS`,
  `OUT`, `FREE KICK`. Ada 2.085 kejadian: 1.029 babak 1 dan 1.056 babak 2.
  `team` hanya `left`/`right`, belum berarti Home/Away.
- Kedua babak lolos konsistensi internal frame/waktu: seluruh event dalam rentang
  frame changelog, selisih `(frame-1)*40` terhadap `position` maksimal 20 ms.
  Gunakan `frame` bawaan **1-based**, kemudian indeks decoded video = frame−1.
  Delapan kejadian tepat setengah frame menunjukkan alasan menghindari
  recompute rounding. Pemeriksaan ini tidak membuktikan alignment empiris video.
- XML raw provider memakai root `metadata`, dengan periode bernama, termasuk
  extra period. Ini bukan schema XML Metrica adapter V2. Padding/raw provider
  clock bukan scope video rilis. Jangan menerapkan offset raw ke BAS v1.2.

Changelog v1.2 yang byte-nya cocok mengoreksi sebagian dokumentasi main lama:
timestamp BAS relatif first decoded frame setiap babak; array bola 1-based;
frame/GSR/BAS rilis sudah diselaraskan. Changelog sendiri melaporkan alignment
hingga tiga frame pada beberapa babak dan match 117092 belum dapat diukur.
117092 babak kedua mempunyai video stream start 1 detik; seek timestamp perlu
memperhitungkan ini, sedangkan decoded frame indexing tidak berubah. Belum
diverifikasi melalui video lokal. Changelog memuat koreksi schema/dimensi pada
rilis terbaru; jangan menerapkan koreksi lama lagi tanpa membaca file versi sama.

## Audit geometri dan batas evaluasi

Empat source/dokumen primer penerbit dibaca statis pada commit kode
`a752d294df2a0e816e827b70f284980698f5a50e`, terpisah dari commit dataset.
URL dan hash disimpan dalam
`external_artifacts/v3/soccertrack-source-audit-20261112/manifest.json`.

Source `generate_calibration_mappings.py` memakai model OpenCV fisheye, K/D dan
Knew untuk mengubah keypoints raw ke piksel undistorted. Script
`calculate_homography.py` memetakan titik lapangan ke piksel undistorted.
Source yang dibaca menjelaskan kontrak; belum membuktikan script versi itu
persis yang menghasilkan payload rilis ini. Tidak ada source penerbit dijalankan.

Pemeriksaan numerik eksploratif dengan kontrak tersebut menghasilkan residual
reprojection raw pada 65 titik yang tersedia: median sekitar 70,47 px dan p95
331,27 px. Ini **diagnostik bersyarat** pada asumsi kontrak transformasi,
bukan akurasi independen, bukan gate kelulusan, dan tidak
menyebabkan pemilihan/penyetelan transformasi alternatif. Perbedaan model/ruang
koordinat serta provenance payload perlu diselesaikan sebelum implementasi.

Titik keypoints dipakai untuk fitting kalibrasi penerbit. Menguji homography
rilis pada titik-titik itu bukan holdout. Refit baru setelah memisahkan titik
tetap harus mengisolasi fitting intrinsics/distorsi juga; memisahkan homography
saja sambil memakai intrinsics hasil seluruh titik tetap bocor untuk klaim
independensi penuh. Geometri komponen belum lolos.

## Langkah berikutnya

1. Integritas dua payload numerik selesai berdasarkan transkripsi SHA-256
   penerbit oleh pengguna; pemeriksaan checksum kini diberlakukan oleh alat audit.
2. Ambil satu video eksternal 117092 babak pertama (6.687.957.167 byte), versi
   tetap dalam `docs/soccertrack_v1_2_video_download.json`, dan catat SHA-256
   penerbitnya sekaligus. Ini untuk verifikasi decoded stream dan kontrak
   geometri; bukan persetujuan loader produksi atau bukti target independen.
   Setelah video tersedia, periksa frame count/FPS/dimensi dan tandai kebutuhan
   anotasi geometri eksternal baru yang tidak dipakai fitting. Tidak ada
   video besar diunduh otomatis oleh agent.
3. Jangan mengunduh GSR 2,71 GB sebagai pengganti anotasi bola/possession.
   BAS bukan Smart Tagging otomatis; bola rekonstruksi event bukan GT independen
   untuk evaluasi out/restart yang diturunkan dari event sama. Target H/A/D
   padat independen tetap belum tersedia, jadi detector/fusion possession
   belum dibuat dan tidak ada klaim kenaikan Spell F1.

V2/R r1 tetap kandidat pengumpulan. Audit ini memajukan bukti akses/schema,
belum mempromosikan kandidat V3.
