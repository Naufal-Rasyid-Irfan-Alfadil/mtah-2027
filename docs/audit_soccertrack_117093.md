# Audit awal SoccerTrack 117093, 13 November 2026

Ketiga SHA-256 LFS ditranskripsikan pengguna dari Hugging Face. Video,
camera_intrinsics dan homography lokal diperiksa ulang dan cocok, begitu pula
empat Git blob non-LFS. Ketujuh berkas kini lolos integritas terhadap bukti itu.
Hash primer merupakan transkripsi pengguna, bukan fetch mandiri agent.

Data tetap eksternal, dataset v1.2 commit
`325bd4c57ee8e135ab652f3921d274526ada496b`. Publisher split validation; peran
proyek adalah pengembangan geometri, tidak diklaim untouched test.

## Video dan schema

- Container/backend: 4096×1080, 25 fps, 67.625 frame sesuai changelog.
- Sampel 0/7500/30000/67624 berhasil didekode, bukan decode seluruh video.
- Start stream absolut 1 detik merupakan informasi changelog; OpenCV relative
  timestamps belum memverifikasinya secara terpisah. Gunakan decoded frame
  indices untuk pengambilan sampel.
- Sampel frame 7500 menunjukkan lapangan terang dan garis dekat/jauh yang lebih
  mudah dilihat daripada sampel malam 117092 yang diperiksa sebelumnya. Ini
  penilaian visual sampel, bukan jaminan anotasi semua area atau seluruh video.
- BAS memakai actions, 2.252 event: 1.138 babak pertama dan 1.114 babak kedua.
  Konsistensi internal frame/waktu maksimal 20 ms; tidak ada event di luar
  rentang changelog. Alignment terhadap kontak bola video belum diuji.
- BAS bukan Smart Tagging otomatis atau target H/A/D padat independen.

## Diagnosis kalibrasi tetap

Seluruh parameter berasal dari 117093; tidak ada koordinat/kalibrasi/anotasi
117092 dipakai. Numerik dimuat tanpa pickle; pose tersimpan diperiksa melalui
literal statis seperti audit sebelumnya, tanpa mengeksekusi pickle.

| Pemeriksaan pada titik fitting penerbit | Hasil |
| --- | --- |
| Jumlah keypoints | 65, koordinat sudut 0..105 / 0..68 m |
| Knew dihitung ulang dari K/D, ukuran aktual, balance=1 | Selisih maksimum 0 |
| RMS tersimpan | 8,637339 px |
| RMS direct pose direproduksi | 8,637342 px |
| Direct pose median / p95 residual raw | 8,16 / 13,03 px |
| H rilis + redistortion median / p95 residual raw | 6,39 / 29,98 px |
| Direct pose versus H turunan aljabar | Maksimum 4,55e-12 px |

Residual di atas seluruhnya pada titik fitting, bukan evaluasi independen.
Tidak ada fitting baru, pemilihan representasi produksi, atau klaim Spell F1.
H dan pose tetap dua representasi yang berbeda; median/p95 tidak menjadi alasan
memilih salah satunya sebelum target independen/gate memadai.

Report, checksum, schema, stream dan sampel raw:
`external_artifacts/v3/117093-camera-audit-20261113/report.json`.
`frame-7500-preview.jpg` hanya preview 1600×422, bukan gambar untuk mengukur
koordinat. PNG raw tetap 4096×1080, tanpa overlay prediksi.

## Referensi baru dan status rilis

Paket `external_artifacts/v3/117093-reference-task-20261113/` berisi tiga PNG raw
frame 7500/37500/60000, manifest, dan CSV 54 slot kosong. Tidak menyalin label
117092 dan tidak membuat GT dari prediksi. Validator kini mengikat task ke
manifest source, match dan revision, sehingga kalibrasi fit-point yang berbeda
tidak bisa terpakai diam-diam. Preflight task baru dan task historis lolos;
task baru tetap nol anotasi dan belum siap scoring.

Protokol: `docs/protokol_referensi_geometri_117093.md`. Cukup mulai dari satu
frame dan titik garis yang terlihat; jangan memakai koordinat preview atau
mengisi bagian tidak jelas. Tidak perlu download tambahan untuk konstruksi
referensi geometri ini. Target possession padat independen tetap belum tersedia.

Saat audit dimulai 13 November 18.22 WIB, cutoff kandidat baru pukul 18.00 telah
terlewati. Hasil ini tetap audit komponen, tidak mempromosikan V3 atau mengubah
gate. V2/R adapter r1 tetap prioritas pengumpulan internal maksimal 15 November,
dan verifier runtime-nya tetap lulus. Data resmi tidak dibuka.

## Pembaruan referensi setelah pengukuran operator

Seluruh 54 koordinat pada tiga frame sudah terisi, dengan self-report operator
belum melihat overlay prediksi. Preflight akhir lulus dan review visual seluruh
titik selesai; koordinat operator tidak diubah. Reviewer assistant telah melihat
diagnosis model. Blinding mandiri dan ketidakpastian pusat garis belum terbukti.

Snapshot referensi: `external_artifacts/v3/117093-reference-freeze-20261113/`.
`freeze-manifest.json` mengikat 73 berkas dengan SHA256; verifikasi seluruhnya
lulus. Status `unannotated` pada task-template-manifest merupakan riwayat awal;
gunakan `annotation-progress.json` dan `preflight-all-54-complete.json` untuk
status snapshot. CSV berisi 54 anotasi; tiga frame tetap satu kamera.

Pengukuran ulang tanpa overlay untuk mengukur ketidakpastian dan penetapan
anggaran error sebelum scoring menjadi pekerjaan berikutnya. Belum ada scoring
atau pemilihan representasi geometri. Evaluasi possession tetap terblokir oleh
target independen tersinkron yang belum tersedia. V2/R adapter r1 tetap kandidat.

Paket pengukuran ulang tersedia pada
`external_artifacts/v3/117093-repeatability-task-20261113/`: 18 crop raw cocok
pixel-exact dengan source. CSV hasil kedua kini terisi 18/18; pengguna telah
mengonfirmasi tidak melihat koordinat pertama/overlay selama sesi ulang.
Konfirmasi adalah self-report, bukan verifikasi blind mandiri. Prosedur
ditetapkan di `docs/protokol_pengukuran_ulang_117093.md`. Ini belum hasil
kelulusan geometri atau batas error produksi.

Analisis pasangan selesai sesuai protokol: 18 valid, missing/exposed 0 menurut
self-report, median/p95/maksimum selisih absolut 1/2,15/3 px. Ini selisih pada
sumbu ukur, satu operator/kamera; akurasi absolut dan bias bersama tidak diukur.
Sebelas pemeriksaan input/statistik lulus. Snapshot analisis dan seluruh hasil
per fitur/frame: `external_artifacts/v3/117093-repeatability-analysis-20261113/`.
Sembilan anggota snapshot cocok checksum. Alat audit
`tools/audit_annotation_repeatability.py` tidak membaca model/kalibrasi.

Angka maksimum 3 px tidak menjadi toleransi produksi. Anggaran error perlu
dasar kebutuhan downstream sebelum scoring kandidat; geometri dan possession
belum dinyatakan lulus. Tidak ada fitting, scoring model, atau perubahan V2.
