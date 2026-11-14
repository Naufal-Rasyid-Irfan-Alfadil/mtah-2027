# Hasil perbaikan V2 — 7 November 2026

**Tahap 1–4 selesai. R lolos seleksi J03WQQ dan penilaian tambahan J03WMX.
Bundle V2 siap untuk inferensi lokal oleh pengguna.** Inferensi resmi belum
dijalankan oleh agent.

**Pembaruan audit adapter:** kesimpulan sebelumnya bahwa sumber pembagian babak
tidak tersedia dikoreksi. `DATA.md` dan `games.py:half_video_blocks()` sudah
mempublikasikan scope per babak pada timeline video. Adapter lama tidak
menyediakan pilihan sumber itu. Revisi terpisah
`external_artifacts/v2/inference-bundle-v2-r1/` menambahkan
`--period-source organizer-public --game BAR-ATH`, dengan pemisahan babak tetap
aktif, model/decoder tetap identik, dan tanpa membaca file GT atau data resmi.
Audit lengkap, bukti dan command ada di
[audit_adapter_half_bounds.md](audit_adapter_half_bounds.md). Bundle awal dan
provenance eksperimennya dipertahankan; inferensi resmi belum dijalankan agent.

## Perubahan yang diuji

R menggabungkan dua classifier yang sudah dilatih pada data eksternal. Model C
digunakan ketika observasi bola dan pemain memadai menurut protokol yang
ditetapkan lebih dahulu; pada frame lain digunakan posterior A. Hasilnya
melewati decoder V1 yang tetap. Tidak ada training ulang classifier, perubahan
fitur, tuning decoder lanjutan, atau pemilihan parameter berdasarkan skor resmi.
Model C sendiri tetap ditolak; yang diuji untuk rilis adalah komposisi R.

Modus jumlah pemain lengkap dari kedua pertandingan training adalah 11 per tim.
Angka ini menjadi referensi cakupan pengamatan, bukan asumsi bahwa pertandingan
selalu memiliki 11 pemain. Saat pengamatan lebih sedikit, R memakai A. Aturan
tersebut juga dapat berlaku pada kartu merah atau lineup yang lebih sedikit;
sebagian manfaat C dapat hilang. Jendela keteramatan bola tetap kausal dan
direset pada gap atau batas babak.

## Seleksi pengembangan: kedua babak J03WQQ

| Kondisi | Metrik | A/V1 | R |
| --- | --- | ---: | ---: |
| Bersih | Spell F1 | 0.446316 | 0.502508 |
| Bersih | Macro F1 | 0.863894 | 0.875228 |
| Bola hilang beruntun | F1 D | 0.943398 | 0.942203 |
| Sebagian pemain hilang | Transition F1 @12 | 0.385044 | 0.385103 |

R memenuhi seluruh batas seleksi: kenaikan Spell F1 bersih minimal 0,01 dan
batas penurunan 0,01 untuk metrik pengaman/per babak/kondisi stres yang sudah
ditetapkan. Tidak ada batas yang dilonggarkan. J03WQQ dipakai ulang untuk
pengembangan; hasil ini bukan test independen. F1 bukan persentase akurasi.

Sebelum evaluasi R, protokol, komponen model, dan source diikat hash di
`external_artifacts/v2/refinement-run1/protocol.json`. Keluaran baru beserta
keputusan tersimpan pada direktori yang sama. Seluruh 101 tes sintetis lulus,
termasuk router, bundle 18 fitur, penolakan rilis tanpa penilaian tambahan,
penolakan perubahan source, serta pemblokiran akses direktori resmi.

## Penilaian tambahan: kedua babak J03WMX

| Model | Spell F1 bersih | Macro F1 bersih |
| --- | ---: | ---: |
| A/V1 | 0.414365 | 0.886097 |
| R/V2 | 0.451830 | 0.893676 |

J03WMX memiliki 145.967 frame: babak pertama 70.708 dan babak kedua 75.259.
Parser tidak menemukan gap nomor frame. Ukuran, MD5 katalog dan SHA-256 kedua
XML telah diverifikasi. Kontrak observasi/target tetap terpisah. Timeline DFL
memakai panjang aktual, bukan dipaksakan menjadi 199.319. Kolom `split` warisan
parser mengikuti penamaan babak; peran eksperimen yang berlaku adalah assessment
untuk **kedua** babak J03WMX. Tidak ada babak J03WMX yang masuk training atau
pemilihan aturan R.

R memenuhi seluruh kriteria rilis: Spell F1 bersih minimal sama dengan A,
batas regresi 0,01 pada metrik pengaman dan babak bersih, serta pemeriksaan
ketujuh kondisi stres. Tidak ada pelanggaran. Semua prediksi disimpan sebelum
target dimuat untuk penilaian; tidak ada penyesuaian model setelah skor J03WMX
diketahui. Keputusan lengkap ada pada
`external_artifacts/v2/J03WMX-refined-assessment-v1/decision.json`.

## Penelusuran pertandingan tambahan

Katalog publik Figshare versi 1 mencantumkan tujuh pertandingan. Lima yang
sudah digunakan adalah J03WOH/J03WPY/J03WQQ/J03WOY/J03WR9. J03WMX/J03WN1 tidak
ditemukan dalam catatan pemakaian source/dokumentasi, nama artefak eksternal,
lokasi unduhan eksternal, atau riwayat Git yang tersedia sebelum eksperimen.
J03WMX dipilih berdasarkan urutan ID, tanpa melihat skor atau targetnya.

Riwayat proyek lama tidak diketahui. Karena itu, J03WMX dilaporkan sebagai
penilaian eksternal tambahan; bukan test yang dipastikan belum pernah dipakai.
Hasilnya tidak digunakan untuk penyesuaian model. Protokol penilaian dan
persyaratan rilis ditetapkan sebelum unduhan tracking dan scoring.

## Penguatan packaging

Pembuat bundle sekarang memverifikasi kesamaan seluruh source algoritma dengan
source yang dievaluasi, termasuk penambahan/penghapusan modul. Source yang
berubah ditolak sebelum output dibuat. Source hasil salinan diperiksa kembali
sebelum bundle dinyatakan siap. R memerlukan penilaian eksternal tambahan yang
memenuhi syarat, terikat ke hash eksperimen dan source yang sama.

Pemutaran ulang model R tersimpan pada semua 14 kombinasi babak/kondisi
pengembangan menghasilkan label identik dengan artefak evaluasi. Perbedaan
probabilitas maksimum 2,220446049250313e-16. Import dan CLI help modul baru
juga diperiksa tanpa memuat dataset atau library model.

Bundle akhir diuji melalui `run_tactical.py` dalam proses Python mandiri,
menggunakan XML/TXT sintetis dengan 22 pemain. Empat frame dalam cakupan
menjalankan kedua cabang router: dua C dan dua A. Probabilitas sesuai dengan
artefak model. Pemeriksaan fixture pertama sempat gagal karena atribut pemisah
XML pada fixture tidak terisi; fixture diperbaiki tanpa mengubah source/model
eksperimen, lalu pemeriksaan ulang berhasil. Log kedua percobaan dipertahankan.
Verifikasi runtime mandiri lulus. ZIP berisi 45 file dengan seluruh hash cocok;
integritas ZIP dan verifikasi setelah ekstraksi ke lokasi lain juga lulus.

Decoder V1 tetap dipakai. Kelulusan relatif terhadap A tidak membuktikan bahwa
seluruh kelemahan V1 pada observasi hilang panjang telah selesai, maupun bahwa
skor pertandingan resmi akan meningkat. Bukti sample Metrica sebelumnya tidak
memiliki target H/A/D per frame dan tidak memberi skor F1 pembanding.

Folder `external_artifacts/inference-bundle-v1/tactical` tidak dibuka, dipindai,
atau diproses. Eksekusi eksperimen lanjutan memakai guard akses yang menolak
direktori tersebut, dataset resmi lain, dan artefak di luar daftar yang aman.
Venv yang sudah ada dan berkas sementara tetap berada di drive proyek.

## Paket untuk langkah 5

- Folder: `external_artifacts/v2/inference-bundle-v2/`.
- ZIP portable: `external_artifacts/v2/inference-bundle-v2.zip`.
- Identitas rilis dan hash: `external_artifacts/v2/release-v2.json`.
- Bukti ZIP/relokasi: `external_artifacts/v2/release-archive-verification.json`.
- Bukti serialisasi: `external_artifacts/v2/refinement-serialization-verification.json`.

Bundle memuat source, dua classifier, aturan router, decoder tetap, kontrak
fitur, requirement yang dipin, atribusi, dan provenance eksperimen/assessment.
Tidak memuat dataset resmi atau DFL mentah. Kualitas pada data resmi belum
diketahui. Adapter ATD hanya diuji dengan fixture sintetis; metadata harus
memenuhi kontrak 25 Hz, koordinat normalized, serta batas dua babak eksplisit.
Tidak ada fallback seluruh rekaman untuk menebak batas.

Pengguna menjalankan langkah 5 sendiri. Dari root proyek, ganti placeholder
berikut dengan path input lokal dan gunakan direktori output baru:

```sh
external_artifacts/local-runtime/training-venv/bin/python -B \
  external_artifacts/v2/inference-bundle-v2/verify_bundle.py --runtime

external_artifacts/local-runtime/training-venv/bin/python -B \
  external_artifacts/v2/inference-bundle-v2/run_tactical.py \
  --bundle external_artifacts/v2/inference-bundle-v2 \
  --metadata /path/ke/metadata_atd.xml \
  --tracking /path/ke/tracking_atd.txt \
  --output local_official_artifacts/v2-run1 \
  --operator-local
```

Tanpa override, kontrak output tactical adalah header `frame,label`, 199.319
baris data, frame 0–199318 berurutan. Keluaran utama `submission.csv` dan
pembanding `submission_raw.csv`. Agent tidak menjalankan command kedua pada
input resmi dan tidak membuka hasil resminya. Skor resmi nantinya bukan sumber
training, tuning, atau pemilihan parameter/kandidat.

## Kode dan bukti pekerjaan

Untuk error operator `ValueError: invalid half bounds`, gunakan alat terpisah
`python -B check_atd_metadata.py --metadata PATH_XML` di root proyek. Alat ini
dijalankan pengguna sendiri; keluaran hanya kategori dan hitungan struktur,
tanpa nomor frame, identitas, koordinat atau prediksi. Tujuh tes sintetis lulus;
metadata publik Metrica Sample Game 3 juga diperiksa. Pesan error kini
membedakan `metadata_file_not_found`, `metadata_path_is_directory`,
`metadata_permission_denied`, `metadata_malformed_xml`, dan `metadata_io_error`,
tanpa menampilkan isi exception yang mungkin mengandung path/fragmen XML. Ini
bukan bukti kompatibilitas metadata resmi. Alat ini tidak mengubah bundle dan
tidak mengonversi indeks nol atau menebak batas babak yang tidak tersedia.
Pola satu rentang dengan start nol dan babak kedua kosong kini dilaporkan
sebagai `one_range_zero_start_empty_second_half`; ini tidak dianggap dua babak
atau bukti konvensi indeks tertentu.

Untuk melanjutkan dengan pemisahan babak, sumber metadata perlu menyatakan
dua rentang beserta konvensinya: identitas rekaman, nomor babak, awal/akhir,
timeline ATD atau video, basis indeks, dan apakah akhir inklusif/eksklusif.
Sumbernya harus metadata/dokumentasi penyedia atau panitia yang sah, bukan
pembacaan file GT, anotasi video manual oleh agent/pengguna, atau titik tengah
rekaman. Audit lanjutan menemukan source scope publik yang sudah tersedia;
penggunaannya untuk inferensi dicatat terpisah dari data training/seleksi.
Loader Smart Tagging publik menjelaskan interval fase
otomatis; itu belum membuktikan adanya rentang dua babak yang lengkap. Source
loader hanya dibaca, tidak dijalankan pada input resmi.

`observation_router.py` menyimpan aturan pemilihan posterior; `v2_refinement.py`
menyimpan diagnosis/protokol/evaluasi/assessment/freeze; `external_guard.py`
membatasi proses ke data eksternal yang disebutkan. Penguatan source dan
syarat assessment ada di `inference_bundle.py`. Tes baru berada di
`tests/test_observation_router.py`, dengan penyesuaian fixture source binding
pada `tests/test_v2.py`. Tidak ada dependency baru yang diinstal.

Log/artefak pendukung ada di `external_artifacts/v2/`, termasuk katalog,
script unduhan J03WMX, script pipeline berurutan, log regresi 101 tes, dan log
verifikasi serialisasi/paket. Raw J03WMX ada di `data/external_dfl/J03WMX/`;
hasil parser dan fitur ada di `external_artifacts/J03WMX-refined-prepared-v1/`
dan `external_artifacts/J03WMX-refined-features-v1/`.

Protokol: [protokol_refinement_v2.md](protokol_refinement_v2.md).
