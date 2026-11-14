# Kelanjutan V3: gate sumber pada 12 November 2026

Pembaruan pukul 20.22 WIB. Pengguna meminta melanjutkan V3 setelah kesiapan V2.
Kandidat pengumpulan tetap V2/R adapter r1. Tidak ada classifier baru, detector,
fusion, training pertandingan, atau akses data/hasil resmi dalam tahap ini.

## Bukti baru yang benar-benar diperoleh

`tools/audit_v3_sources.py` mengambil katalog/dokumentasi publik dengan batas
respons 2 MiB. Dua XML matchinformation DFL berjumlah **23.677 byte** juga
diambil setelah identitas, lisensi, ukuran dan MD5 penerbit ditentukan.
Tidak ada posisi per-frame, target possession, bobot, atau video diunduh.

Bukti mentah, URL primer, waktu, status HTTP, SHA-256, hasil parser dan keputusan
gate ada pada `external_artifacts/v3/feasibility-20261112-metadata/`:

- `manifest.json`: provenance akses; URL redirect disimpan tanpa signed query.
- `dfl-catalog-v1.response`: katalog JSON resmi versi 1.
- `soccertrack-version.response` dan `soccertrack-file-catalog.response`:
  metadata versi dan daftar berkas; bukan bukti akses payload.
- `metadata-parser-check.json`: pemeriksaan parser metadata eksternal yang ada.
- `gate-summary.json`: cabang dan daftar calon akuisisi, belum diunduh.

Kegagalan jaringan sandbox dan percobaan katalog sebelumnya dipertahankan
terpisah di direktori feasibility-network1/network2; yang relevan berada di
`external_artifacts/v3/feasibility-20261112-network1/` dan
`external_artifacts/v3/feasibility-20261112-network2/`.

## DFL: akses publik dan metadata lolos

[API primer versi 1](https://api.figshare.com/v2/articles/28196177/versions/1)
berhasil diakses HTTP 200. DOI `10.6084/m9.figshare.28196177.v1`, lisensi
CC BY 4.0. Katalog benar-benar berisi **21 XML**: tujuh matchinformation,
tujuh event, tujuh positions. Tidak ada video atau kalibrasi dalam inventory.
Atribusi Deutsche Fußball Liga dan Bassek dkk. tetap wajib.

| Metadata yang diperiksa | ID berkas Figshare | Ukuran | MD5 penerbit | Parser |
| --- | --- | --- | --- | --- |
| J03WOH, training yang sudah digunakan | 51643478 | 11.745 byte | b9710781d400dd812f62b0a6e3d7bce8 | Lulus |
| J03WQQ, development berulang | 51643484 | 11.932 byte | 5979209af316a914ce57347d0633df6c | Lulus |

Kedua payload cocok ukuran dan MD5 sebelum dibaca; SHA-256 lokal tercatat.
`read_match_info` pada source beku mengenali match, dimensi 105×68 m, tim dan
roster. Tidak ada inferensi atau scoring. Lolos metadata tidak membuktikan
integritas positions atau keselarasan event per frame.

[Publikasi primer](https://www.nature.com/articles/s41597-025-04505-y) menjelaskan
BallStatus/BallPossession pada positions. Keduanya hanya target H/A/D, bukan
observasi. Event dan posisi dikumpulkan melalui proses berbeda, sehingga
timestamp event tidak boleh dianggap presisi satu frame tanpa pembuktian.
Event DFL juga bukan Smart Tagging otomatis Metrica.

Akuisisi yang teridentifikasi untuk eksperimen tracking: positions dan
matchinformation J03WOH/J03WPY (training) serta J03WQQ (development), total
**1.076.889.236 byte**, sekitar 1,08 GB desimal. Dua metadata di atas sudah
tersedia; angka total mencakup keduanya. URL, ukuran dan MD5 tercatat di
`gate-summary.json`. Belum ada file positions diunduh. Jangan menyebut ketiga
pertandingan sebagai test independen atau menganggap akses metadata membuktikan
akses seluruh berkas besar. J03WMX tetap penilaian tambahan dengan riwayat lama
belum diketahui; J03WN1 tidak otomatis untouched.

## SoccerTrack: versi dan katalog lolos, payload belum

[API rilis](https://huggingface.co/api/datasets/atomscott/soccertrack-v2/revision/v1.2)
mengikat tag v1.2 ke commit `325bd4c57ee8e135ab652f3921d274526ada496b`.
Flag API `gated=auto`; daftar rekursif menghasilkan 244 record file/direktori.
[Halaman dataset](https://huggingface.co/datasets/atomscott/soccertrack-v2)
meminta persetujuan akses melalui akun. Request isi `CHANGES_v1_2.md`
mengembalikan HTTP 401 meskipun katalog dapat dibaca.

Inventory memuat BAS per pertandingan, GSR, bola, video, keypoints, homography,
intrinsics, distortion maps, metadata tracker dan ekspor raw. Contoh paket
geometri kecil 117092 mempunyai keypoints 3.624 byte, intrinsics 1.996 byte,
homography 200 byte, dan padding 153 byte; maps tetap puluhan MB. Ukuran katalog
bukan bukti berkas sudah tersedia. Hash LFS yang disembunyikan tidak dipakai
sebagai checksum validasi.

[Lisensi data](https://github.com/AtomScott/SoccerTrack-v2/blob/main/LICENSE-DATA)
adalah CC BY 4.0, kode MIT. Card v1.2 mengklaim alignment per frame. Namun
schema/basis waktu harus dipastikan terhadap payload **versi sama**, bukan
ditentukan dari dokumentasi main yang dapat berbeda. Distorsi kamera harus
diperhitungkan. Nilai error homography terhadap titik yang dipakai fitting hanya
diagnosis; bukan evaluasi geometri independen.

Bola yang direkonstruksi dari event/interpolasi tidak menjadi target independen
untuk menilai out/restart yang diturunkan dari event sama. BAS bukan target
possession padat dan bukan output Smart Tagging otomatis. Akses SoccerTrack
sendiri belum menyelesaikan gate possession multimodal.

## Sumber lain dan keputusan cabang

SAMPLEGAME4 tetap memerlukan akses proyek/ekspor, versi, hak penggunaan dan
target independen. Belum ada akun dibuat, pesan dikirim atau aplikasi dipasang.
Untuk Alfheim, [publikasi Welch dkk.](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251970)
menjelaskan anotasi possession dari video, tetapi tracking yang dipakai hanya
sepuluh pemain home, 20 Hz, tanpa kiper. Endpoint dataset masih gagal diakses
dalam pemeriksaan web; akses anotasi, lisensi payload dan input kompatibel
belum terbukti. Bukan sumber siap pakai untuk V2/fusion.

| Cabang | Status setelah pemeriksaan ini | Langkah yang dibutuhkan |
| --- | --- | --- |
| DFL fallback V2 | Akses katalog/metadata lolos; positions belum tersedia | Akuisisi file positions eksplisit, verifikasi ukuran/MD5, preparation eksternal dan uji V2 tanpa modalitas tambahan |
| Eksperimen V3 berbasis ATD | Belum ada kandidat atau protokol eksperimen terpilih | Pastikan observasi mendukung hipotesis dan target independen, bekukan maksimal dua konfigurasi/gate sebelum scoring |
| Homography komponen | Payload gated dan evaluasi independen belum lolos | Persetujuan akses oleh pengguna; paket kecil versi tetap, audit schema/distorsi dan sumber target geometri |
| Video/bola | Data/model/target independen belum lolos | Bukti input pasangan, anotasi bola independen, lisensi/checksum bobot dan runtime |
| Tagging otomatis | Ekspor dan target independen belum lolos | Buktikan akses, schema, sinkronisasi, hak dan target |
| Fusion | Belum layak | Tunggu cabang yang kontribusinya bisa dievaluasi |

Tidak ada modul produksi dibuat untuk cabang terblokir. Pengguna kemudian
memilih **video/geometri: selesaikan akses SoccerTrack dan target independen
terlebih dahulu**, serta menyatakan sudah membuat akun Hugging Face. Akun ada
belum membuktikan gated access disetujui. Akuisisi awal dipersempit menjadi
delapan berkas audit versi tetap untuk match training 117092, total 487.760 byte;
lihat `docs/soccertrack_v1_2_audit_download.json`. Payload belum diterima/diperiksa.
Video penuh, GSR multi-GB, positions DFL dan bobot belum diminta untuk tahap ini.
Deadline internal tetap maksimal 15 November. V2 beku dan paket pulihan tidak berubah.
