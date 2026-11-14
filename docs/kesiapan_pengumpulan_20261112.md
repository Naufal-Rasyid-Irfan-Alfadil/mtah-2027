# Kesiapan pengumpulan V2/R pada 12 November 2026

Kandidat tetap **V2/R, adapter revisi 1**. Tidak ada perubahan classifier,
fitur, router, parameter decoder, maupun manifest rilis lama. Tidak ada akses
data resmi atau scoring resmi. Target internal tetap maksimal 15 November 2026;
ini bukan konfirmasi deadline panitia.

## Hasil pemulihan dan verifikasi

HEAD sumber pemulihan: `5b0240c2480f482e381cd54970c47fb8c9425270`.
Working tree awal mempunyai 43/48 checksum bundle berbeda karena CRLF/LF;
handoff mempunyai 107/136 perbedaan serupa. Semua blob Git HEAD cocok dengan
hash asli. `core.autocrlf=true` menjelaskan konversi pada checkout Windows.
Model biner tetap cocok; decoder JSON working tree awal tidak cocok byte.

`tools/restore_handoff.py` mengambil hanya inventory handoff yang diketahui
provenance-nya melalui `git cat-file`, memeriksa semua hash sebelum menulis,
menolak output yang sudah ada, dan menulis byte tanpa konversi. Tidak menyalin
dataset, direktori ekstra, atau output operator. Pemulihan tidak mengesahkan
working tree lama dan tidak membuat hash pengganti.

Salinan hasil berada di
`external_artifacts/release-readiness-20261112/source/`.
Seluruh 136 berkas manifest cocok. `.gitattributes` mengatur checkout berikutnya
agar byte teks LF tetap LF, sementara berkas biner/CRLF asli tidak dikonversi.
Jangan menjalankan renormalisasi massal atau mengubah artifact lama.

Identitas rilis:

- Model: `04e2510928af168c7cd1e3d9ebb698591b336f52a2344853dce1fd8acd0fa88f`.
- Decoder: `2aa5b5f1c777fe9c2c71b7bdb894082b22b967dae5b67664be9b5c7871bafa74`.
- Manifest bundle: `faad034cc3189422fa6fa389d4741eb5ef966e235c103a137fcf3befd6191940`.

Environment baru: `runtime/v2-r1-venv/`; pip cache `runtime/pip-cache/` dan
temporary file `runtime/tmp/`. Instalasi memakai requirement asli, tanpa
melonggarkan pin. Python 3.11.6 Windows 64-bit. Seluruh delapan versi manifest
terpasang; `pip check` dan verifier `--runtime` lulus. Interpreter global
sebelumnya berbeda pada python-dateutil dan tzdata, sehingga bukan runtime rilis.

Pemeriksaan terakhir direkam di
`external_artifacts/release-readiness-20261112/validation-final/report.json` dan
`synthetic-tests.log`. Pemeriksaan meliputi 26 tes sintetis adapter/router,
preflight, kontrak 199.319 baris sintetis, penolakan checksum rusak, serta import
tanpa data. Model kecil dalam unit test hanya memakai fixture sintetis.
R beku juga diuji pada delapan frame buatan tanpa fitting/scoring. Posterior R
pada observasi missing identik dengan A; ini belum merupakan uji dataset DFL.

ZIP di direktori `validation-final/` berisi hanya 48 anggota inventory dan
manifest asli. Seluruh 49 anggota diverifikasi, lalu hasil ekstraksi ke lokasi
temporary berbeda diperiksa dengan verifier asli dan runtime ketat. Hash ZIP
dicatat dalam `report.json`; jangan memakai ZIP lain yang provenance-nya belum
diaudit. Status ini **validasi sintetis**, bukan bukti kompatibilitas seluruh
variasi data resmi atau kualitas prediksinya.

## Mesin yang benar-benar diperiksa

| Komponen | Hasil pada sekitar 19.46 WIB |
| --- | --- |
| OS | Windows 11 Home Single Language |
| CPU | AMD Ryzen 7 170 with Radeon Graphics; 8 core / 16 logical processor |
| RAM terlihat | 15,19 GiB; bebas sekitar 4,26 GiB saat pembacaan |
| GPU | NVIDIA GeForce RTX 3050 6GB Laptop GPU; VRAM 6.144 MiB |
| Driver | 621.14 |
| Disk D | 300 GiB; bebas sekitar 192,56 GiB sebelum instalasi |

Tidak ada PyTorch pada interpreter yang diaudit; tidak ada bobot visual dipilih
atau benchmark throughput. Informasi CUDA driver bukan verifikasi toolkit.
Spesifikasi laptop agent lama tidak digunakan.

## Register kelayakan sumber

| Sumber / versi / URL primer | Lisensi dan akses | Sinkronisasi, target, dan keputusan |
| --- | --- | --- |
| DFL/Sportec: [penerbit](https://github.com/spoho-datascience/idsse-data), [Figshare](https://doi.org/10.6084/m9.figshare.28196177), [publikasi](https://www.nature.com/articles/s41597-025-04505-y); v1 menurut handoff | CC BY 4.0, atribusi DFL dan Bassek dkk. Repo penerbit dapat dibaca; endpoint katalog tidak berhasil dibaca ulang. Tepat 21 XML adalah bukti audit lama, belum diverifikasi ulang. Dataset lokal belum terbukti tersedia. | Tujuh pertandingan posisi/event/metadata menurut penerbit. Tidak ada bukti paket video/kalibrasi/tagging otomatis yang sesuai. Layak untuk fallback tracking setelah akuisisi terverifikasi. BallStatus/BallPossession hanya target, bukan fitur. |
| Metrica [sample-data](https://github.com/metrica-sports/sample-data/tree/e706dd506b360d69d9d123d5b8026e7294b13996), commit e706dd506b360d69d9d123d5b8026e7294b13996 | README tersedia, meminta penggunaan bertanggung jawab dan atribusi. Lisensi kompetisi/redistribusi lebih lengkap belum terbukti; bukan otomatis MIT/CC BY. | README menyatakan tracking/event tersinkron, normalized, lapangan 105×68 m. Video pasangan, homography, tagging otomatis, GT H/A/D padat independen belum terbukti. Hanya kandidat kompatibilitas. |
| [SoccerTrack v2 card](https://huggingface.co/datasets/atomscott/soccertrack-v2/blob/main/README.md), v1.2, revisi card 325bd4c57ee8e135ab652f3921d274526ada496b | [Data CC BY 4.0](https://github.com/AtomScott/SoccerTrack-v2/blob/main/LICENSE-DATA), kode MIT. Card dapat dibaca; raw endpoint mengembalikan 401, payload belum terakses. Katalog bukan bukti dataset lokal tersedia. | Card v1.2 mengklaim alignment per frame, video/GSR/BAS/bola/raw calibration. Bola merupakan rekonstruksi event dan interpolasi, sebagian clipping. Tidak menjadi GT out/restart independen. Potensial geometri, belum lolos produksi/possession. |
| Metrica [SAMPLEGAME4](https://www.metrica-sports.com/blog/automatic-tagging-detect-patterns-that-occur-in-the-game), pengumuman 14 Oktober 2022 | Akses melalui akun/aplikasi. Versi ekspor, hash, hak kompetisi/redistribusi, dan akses berkas belum terbukti. Tidak mengirim pesan atau membuat akun. | Penawaran sample otomatis bukan GT possession. Ekspor sebanding, mapping tim, basis waktu, dan target independen belum tersedia. Cabang tagging terblokir. |
| [SoccerNet GSR](https://www.soccer-net.org/tasks/game-state-reconstruction), [Alfheim/publikasi](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251970) | Sumber cadangan dari handoff; akses payload, versi, lisensi data, dan kelengkapan belum diverifikasi ulang pada implementasi ini. | Tidak dipilih dan tidak boleh membuka cabang produksi berdasarkan penyebutan sumber saja. |

Dokumen [GSR SoccerTrack](https://github.com/AtomScott/SoccerTrack-v2/blob/main/docs/format-gsr.md)
memperingatkan schema aktual berbeda, dimensi gambar bermasalah, dan basis waktu
BAS berbeda dari sebagian spesifikasi. Card v1.2 mengklaim perbaikan alignment;
kontrak payload rilis tetap harus diperiksa sebelum membuat loader.
[Kalibrasi](https://github.com/AtomScott/SoccerTrack-v2/blob/main/docs/calibration.md)
melibatkan distorsi dan undistortion; satu homography bukan pengganti tahap itu.
Revisi main dokumentasi yang bergerak tidak dianggap versi berkas yang diunduh.

Model R berasal dari artifact lokal yang terikat manifest; data training DFL
J03WOH/J03WPY, development J03WQQ. J03WMX adalah penilaian tambahan dengan riwayat
lama belum terbukti, bukan untouched test. Lisensi kode tidak otomatis menjadi
lisensi semua data/bobot. Belum ada model visual pretrained terpilih; URL bobot,
versi, hash, lisensi bobot, domain training, dan kebutuhan runtime masih kosong.

## Gate dan pekerjaan yang masih terbuka

V2 lolos kesiapan sintetis. Uji fallback DFL nyata menunggu akuisisi eksternal
dengan provenance dan peran data yang dinyatakan; tidak ada klaim dataset ikut
terunduh. Jangan membaca arsip/salinan repo/direktori data yang belum diaudit.
Video, tagging, homography produksi, aturan restart lengkap, dan fusion tetap
terblokir kelayakan; tidak dibuat detector atau scaffolding cabang tersebut.

Evaluasi komponen dipisahkan: geometri memakai titik kontrol independen yang
tidak dipakai fitting; deteksi bola memakai anotasi independen; tagging memakai
kejadian dan waktu independen. Round-trip geometri hanya konsistensi numerik.
Tidak ada bukti kenaikan Spell F1 dari keberhasilan komponen.

Manfaat possession multimodal hanya dinilai bila observasi pasangan dan target
H/A/D independen tersedia. Bekukan protokol sebelum scoring, maksimal dua
konfigurasi per cabang. Gate konteks terbaru tetap berlaku: ATD/tagging minimum
Spell +0,01; video pada missing yang ditetapkan minimum +0,02, bersih tidak turun
lebih dari 0,01; pengaman Macro/D/transisi/per-babak tidak turun lebih dari 0,01.
Tanpa modalitas tambahan, DFL menguji fallback identik V2, bukan kenaikan skor.
Skor resmi tidak menjadi dasar pemilihan atau pengembangan.

Cutoff kelayakan 12 November 12.00 sudah terlewati. Hingga 13 November 18.00,
pekerjaan cabang baru dibatasi audit bukti akses/kontrak; kandidat yang belum
sepenuhnya tervalidasi tidak dipromosikan. Pada 14 November operator memeriksa
paket/input lokal; target internal pengumpulan maksimal 15 November. Paket V2
yang terverifikasi tetap tersedia, tanpa menjanjikan peningkatan skor.

## Command operator

Dari root proyek, PowerShell. Perintah verifikasi berikut tidak membaca data:

```powershell
$python = '.\runtime\v2-r1-venv\Scripts\python.exe'
$bundle = '.\external_artifacts\release-readiness-20261112\source\external_artifacts\v2\inference-bundle-v2-r1'
& $python -I -B "$bundle\verify_bundle.py" --runtime
```

Operator sendiri menjalankan inferensi resmi setelah pipeline dibekukan,
mengganti placeholder dengan path lokal dan memakai direktori output baru:

```powershell
& $python -I -B "$bundle\run_tactical.py" --bundle $bundle `
  --metadata 'PATH_XML_LOKAL' --tracking 'PATH_TXT_LOKAL' `
  --period-source organizer-public --game BAR-ATH `
  --output '.\local_official_artifacts\v2-r1-operator-run1' --operator-local
```

Jangan mengirim input/output resmi ke agent. Operator memvalidasi format CSV
secara lokal menggunakan source validator; jangan menjalankan scorer dengan GT
default. Agent hanya memvalidasi CSV sintetis pada tahap ini.
