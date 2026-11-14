# Hasil audit kontrak homography dan kamera SoccerTrack 117092

12 November 2026 sekitar 21.16 WIB. Audit hanya memakai artifact/video eksternal
yang sudah cocok checksum. Tidak ada fitting, penggantian parameter, detector,
fusion, atau akses data resmi. V2/R adapter r1 tetap kandidat pengumpulan.

## Temuan terverifikasi

**Knew konsisten dengan kamera dan ukuran video.** Menghitung ulang operasi
`estimateNewCameraMatrixForUndistortRectify` pada K/D tersimpan, dimensi
3840×1906 dan balance=1 menghasilkan Knew yang sama persis (selisih maksimum 0).
Ini rekonstruksi operasi deterministik pada parameter tetap, bukan calibration
fitting baru. Salah ukuran canvas pada operasi ini bukan penjelasan residual.

**Pose tersimpan mereproduksi RMS penerbit.** Dari rvec/tvec yang sudah ada,
fisheye.projectPoints menghasilkan RMS 30,63214334 px, dibanding nilai tersimpan
30,63214407 px. Median residual 23,30 px, p95 57,04 px. Ketiganya dihitung pada
65 titik fitting, sehingga bukan akurasi holdout.

Pose bertipe object-array tidak di-unpickle. Setelah seluruh archive cocok
SHA-256, alat membaca header NPY dan memeriksa literal tiga float menggunakan
pickletools tanpa mengeksekusi opcode. Tidak ada pickle.load/loads, pemanggilan
REDUCE/BUILD, atau import dinamis dari payload. Metode ini khusus untuk struktur
artifact terverifikasi tersebut, bukan loader umum untuk data bertipe objek.

**H rilis berbeda dari homography plane kamera tersimpan.** Untuk z=0,
homography diturunkan secara aljabar sebagai `Knew @ [R[:,0], R[:,1], t]`, dengan
R dari Rodrigues(rvec). Proyeksinya setelah redistortion sama dengan direct pose
hingga maksimum 6,37×10⁻¹² px pada titik yang diperiksa. H rilis tidak sama
dengan matriks ini. Kedua rantai berbeda median 68,82 px dan p95 330,01 px dalam
piksel raw. Pada titik fitting, H rilis tetap memiliki median 70,47 px dan p95
331,27 px.

Ini membuktikan perbedaan dua representasi kamera, bukan membuktikan kapan atau
mengapa H dibuat berbeda. Homography yang diestimasi terpisah dari noisy
keypoints memang dapat berbeda dari pose; selisih matriks saja bukan bukti
file rusak. H rilis tidak otomatis diganti dengan H turunan karena residual fit
lebih rendah. Tidak ada kandidat produksi yang dipilih.

## Penelusuran source primer dan batas provenance

Commit kode dipin ke `a752d294df2a0e816e827b70f284980698f5a50e`, terpisah dari
commit dataset v1.2 `325bd4c57ee8e135ab652f3921d274526ada496b`. Source diambil
hanya untuk dibaca, tidak dieksekusi. URL dan SHA-256 tiap source ada di
`external_artifacts/v3/geometry-contract-source-20261112/manifest.json`.

- `src/calibration/generate_calibration_mappings.py` menyimpan K/D/Knew,
  rvec/tvec, RMS dan maps, tetapi tidak menyimpan H.
- `scripts/calibration/calculate_homography.py` membaca calibrated keypoints
  dari jalur terpisah dan mengestimasi H world→undistorted dengan RANSAC 5 px.
  Calibrated keypoints, mask inlier dan log proses yang menghasilkan H rilis
  belum tersedia dalam paket yang diperiksa.
- `src/coordinate_conversion/convert_pitch_plane_to_image_plane.py` memakai H
  lalu inverse Knew dan fisheye untuk kembali ke raw pixels. Kontrak diagnosis
  sebelumnya sesuai jalur ini. Tidak ada alasan menganggap H langsung berlaku
  pada panorama raw.
- `scripts/calibration/project_tracking_to_image.py` mendokumentasikan direct
  fixed pose untuk world→raw tanpa H. Ini mendukung pemeriksaan aljabar sebagai
  representasi kamera yang sudah tersimpan, bukan alasan mempromosikannya.
- `scripts/calibration/calibrate_all_from_keypoints.py` mempunyai canvas baru
  dan menyimpan intrinsics/maps, tanpa H. Ini menunjukkan potensi pencampuran
  hasil proses bila file digabung tanpa manifest, tetapi **belum membuktikan**
  itulah asal pasangan H/Knew rilis 117092.
- `scripts/create_ground_truth.sh` menyebut wrapper kalibrasi yang tidak ada
  pada lokasi tersebut dalam tree yang diperiksa, dan tidak memperlihatkan
  langkah pembentukan H eksplisit sebelum proyeksi. Wrapper/path generik tidak
  cukup untuk mereproduksi provenance artifact rilis ini.

[Dokumentasi OpenCV 4.10](https://docs.opencv.org/4.10.0/db/d58/group__calib3d__fisheye.html)
menjadi rujukan model fisheye dan projectPoints. Hubungan z=0 di atas merupakan
turunan aljabar, bukan fitting terhadap label atau hasil resmi.

## Bukti tersimpan dan pemeriksaan

Alat: `tools/audit_geometry_contract.py`. Report final:
`external_artifacts/v3/geometry-contract-audit-20261112-r2/report.json`.
Input cocok checksum sebelum dan sesudah audit; H turunan hanya dicatat sebagai
diagnosis di report, tidak menggantikan `.npy` penerbit.

Tiga tes sintetis pada `tests/test_geometry_contract_audit.py` lulus: ekstraksi
literal tanpa unpickling; penolakan shape/nonfinite; ekuivalensi proyeksi pose
dengan homography plane turunan. Tidak ada dataset dibuka oleh tes tersebut.

## Referensi independen: paket tugas siap, anotasi belum tersedia

Paket `reference-task/` di direktori report final memuat tiga PNG raw ukuran
asli dari frame 7500/37500/60000, hash gambar, manifest provenance, dan CSV
54 slot kosong. Tidak ada overlay prediksi pada gambar tugas atau koordinat
label yang dibuat dari H/pose. Video diperiksa checksum lagi sebelum ekstraksi.

Prosedur ada di `docs/protokol_referensi_geometri_117092.md`. Paket ini belum
menjadi dataset beranotasi: **nol anotasi valid**, belum ada annotator atau
jaminan blind review. Pengukuran baru harus dilakukan dari garis yang terlihat,
terpisah dari lokasi 65 keypoints fitting. Pengulangan tiga waktu tetap satu
kamera; tidak menambah jumlah pertandingan independen.

Metrik dan anggaran error produksi belum dibekukan karena ketidakpastian
pengukuran belum diketahui. Jangan scoring/promosi pada template kosong, jangan
menganggap test aljabar sebagai validasi geometri lapangan, dan jangan menilai
possession tanpa target H/A/D independen.

## Keputusan berikutnya

Audit kontrak berhasil mempersempit penyebab: Knew/pose konsisten, sedangkan H
rilis adalah hasil estimasi lain yang proses pembentukannya belum terikat
provenance lengkap. Penyebab historis pasti masih belum terbukti. Cabang tetap
pada evaluasi komponen; tidak ada perbaikan H produksi atau klaim Spell F1.

Pekerjaan konkret yang masih diperlukan adalah pengisian/review referensi raw
oleh annotator yang provenance-nya tercatat, lalu pembekuan kriteria evaluasi
sebelum membandingkan dua representasi tetap. Tidak perlu download dataset lain
untuk tahap ini. Ketersediaan target possession independen tetap gate terpisah.

## Pembaruan referensi operator sekitar 22.02 WIB

Pada frame 7500 pengguna memberikan tiga titik near_touchline_y68:

| Titik | X | Y | Jarak dari keypoint fitting terdekat |
| --- | --- | --- | --- |
| Kiri | 1427 | 1442 | 146,11 px |
| Tengah | 2055 | 1442 | 69,72 px |
| Kanan | 3224 | 1167 | 56,86 px |

Pengguna mengonfirmasi frame dan menyatakan belum melihat overlay prediksi
sebelum memilih titik. Ini self-report, bukan pembuktian blind review mandiri.
Titik lama (1983,1450) dan (3669,988) disimpan sebagai pengukuran yang dikeluarkan
karena terlalu dekat dengan keypoints fitting. Garis jauh dilaporkan tidak
terlihat jelas: tiga slotnya ambiguous dengan koordinat kosong. Bagian lainnya
masih belum dianotasi; tidak otomatis dianggap tidak terlihat.

`tools/validate_geometry_annotations.py` mengonfirmasi integritas tiga PNG,
identitas frame/gambar, slot unik, bounds, provenance annotator,
used_for_fitting=false, dan pemisahan lokasi dari fit points. Hasil: tiga titik
terisi, tiga ambiguous, 48 belum ditinjau. Tujuh pemeriksaan negatif menolak
bounds salah, kontaminasi fitting, hash gambar salah, penggunaan fit point,
koordinat pada baris ambiguous, provenance kosong, dan slot duplikat/hilang.
Validator tidak membaca prediksi model atau menghitung residual kandidat.

Review visual crop raw menunjukkan ketiga tanda operator berada pada garis
cat. Reviewer assistant sudah pernah melihat diagnosis model; hal ini dicatat,
bukan diklaim sebagai review blind. Koordinat tidak disesuaikan. Ketidakpastian
dan repeatability belum diukur; belum ada gate produksi atau scoring baru.

Preflight, negative checks, crop dan review ada di
`external_artifacts/v3/operator-annotation-review-20261112/`. Progress terbaru
berada di `reference-task/annotation-progress.json`; manifest tugas asli tetap
merekam keadaan awal tanpa anotasi.

**Keputusan:** tiga pengukuran pada satu garis/satu frame belum cukup untuk
mengesahkan geometri seluruh lapangan. Target possession padat independen
belum ditemukan. Cabang produksi V3 tetap terblokir; jangan membuat detector/
fusion atau mengklaim perbaikan skor dari kelulusan preflight. Langkah data
berikutnya adalah referensi terukur pada fitur/area lain dan pemeriksaan
ketidakpastian, lalu pembekuan anggaran error sebelum scoring. V2 tetap kandidat.
