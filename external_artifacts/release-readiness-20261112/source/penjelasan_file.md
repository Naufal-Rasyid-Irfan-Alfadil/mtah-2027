# Penjelasan file dalam proyek

## Lanjutan perbaikan V2: router observasi

Penambahan 7 November 2026 melanjutkan eksperimen V2 awal yang menolak C.
R lolos pengembangan J03WQQ dan penilaian tambahan J03WMX. Bundle siap di
`external_artifacts/v2/inference-bundle-v2/`, ZIP tersedia di direktori yang
sama. Hasil, keterbatasan riwayat J03WMX, dan command pengguna ada di
[hasil_refinement_v2.md](docs/hasil_refinement_v2.md).

| File baru | Fungsinya | Alasan dibuat |
| --- | --- | --- |
| `external_baseline/atd_periods.py` | Memisahkan sumber periode provider dan scope publik `games.py`, lalu menormalisasi indeks secara eksplisit. | Parser lama memaksa dua field periode provider dan melewatkan sumber scope publik yang sudah ada; babak tetap dipisahkan. |
| `tests/test_atd_period_sources.py` | Menguji nilai kosong/nol, konversi endpoint, counter raw, reset state antar-babak, X mask, dan bundle revisi dengan checksum aktif. | Mencegah salah indeks dan penyambungan babak ketika sumber metadata diganti. |
| `docs/audit_adapter_half_bounds.md` | Mencatat akar masalah, pembanding kloppy, kontrak timeline, bukti tes, serta command revisi V2 r1. | Mengoreksi kesimpulan ketersediaan metadata sebelumnya berdasarkan audit source, bukan inspeksi data resmi. |
| `check_atd_metadata.py` | Pemeriksaan lokal yang hanya mencetak jumlah batas babak nol/negatif/kosong dan kategori masalah rentang; tidak mencetak nilainya. | Mendiagnosis `invalid half bounds` tanpa agent membuka metadata resmi atau menebak batas babak. |
| `tests/test_metadata_preflight.py` | Menguji kategori batas sintetis, namespace, kerahasiaan nilai, serta import/help tanpa membuka dataset. | Mencegah angka nol otomatis dianggap batas valid dan mencegah alat diagnostik membocorkan nomor frame. |
| `external_baseline/observation_router.py` | Memakai posterior C saat observasi memadai dan A saat pengamatan berkurang; decoder tetap. | Menguji satu solusi terbatas untuk dua kegagalan ketahanan C, tanpa melatih ulang classifier. |
| `external_baseline/v2_refinement.py` | Menjalankan diagnosis, mencatat protokol, mengevaluasi R, menilai pertandingan tambahan, dan membekukan kandidat yang memenuhi syarat. | Memisahkan urutan keputusan dari evaluasi dan mencatat hash serta hasil penolakan/kelulusan. |
| `external_baseline/external_guard.py` | Membatasi proses ke data eksternal yang disebutkan dan fixture sintetis; memblokir akses resmi termasuk listing direktori tactical. | Menjaga batas akses ketika pipeline dijalankan otomatis. |
| `tests/test_observation_router.py` | Menguji routing, urutan kelas, missing, kelengkapan metrik, paket sintetis, kesamaan source, dan guard akses. | Mencegah kandidat berbeda dikemas sebagai model yang sudah dievaluasi atau kandidat gagal diluluskan. |
| `docs/protokol_refinement_v2.md` | Menjelaskan satu kandidat, dasar aturan, ambang kelulusan, dan kebijakan pertandingan tambahan sebelum penilaian. | Membatasi eksperimen dan menghindari perubahan aturan setelah melihat skor. |
| `docs/hasil_refinement_v2.md` | Menyajikan hasil dan keterbatasan eksperimen lanjutan. | Memberikan status yang mudah dibaca tanpa membuka artefak biner atau prediksi resmi. |
| `docs/verifikasi_v2.md` | Merekam pemeriksaan eksperimen V2 awal, sebelum perbaikan R. | Menjelaskan mengapa keberadaan `model_C.joblib` belum berarti model itu layak dirilis. |

`inference_bundle.py` juga diperketat agar source yang dikemas identik dengan
source evaluasi dan router baru hanya dirilis setelah penilaian tambahan.
Action `revise-adapter` membuat revisi parser terpisah dari bundle beku,
mempertahankan provenance seleksi lama, mengikat source runtime baru pada
manifest revisi, dan memverifikasi bahwa model/decoder tidak berubah. Rilis
adapter saat ini: `external_artifacts/v2/inference-bundle-v2-r1/`.
Bagian berikut merekam eksperimen V2 awal dan tahap proyek sebelumnya.

## Tambahan v2

Eksperimen lokal `external_artifacts/v2/run1/` sudah selesai (status ready).
Model C meningkatkan Spell F1 bersih J03WQQ dari 0,446316 menjadi 0,507111,
tetapi gagal dua batas robustness yang ditetapkan sebelum eksperimen. Semua B
juga ditolak. Kandidat aktif tetap A/v1; tidak ada bundle v2 yang dipromosikan,
perluasan pencarian, atau evaluasi pertandingan resmi. Lihat `selection.json`
untuk alasan penolakan dan `metrics.json` untuk seluruh metrik pendamping.

`external_baseline/v2.py` menjalankan satu protokol eksperimen eksternal terbatas:
A baseline beku, lima variasi decoder B dengan posterior identik A, dan satu
kandidat C dengan empat fitur konteks observasi jika diagnosis missing mendukung.
Training hanya J03WOH/J03WPY; seleksi hanya J03WQQ yang sudah dipakai untuk
pengembangan. Tidak ada test independen baru atau akses aset resmi.

`ContextFeatureExtractor` dalam `features.py` menambahkan proporsi keteramatan
bola, umur observasi bola, serta median jarak Home/Away pada jendela kausal satu
detik. Missing tetap kosong; state diputus pada babak/pertandingan/gap.
`temporal.py` mendukung skor versi 2 tanpa mengubah default versi 1.
`tests/test_v2.py` memeriksa risiko transisi pendek yang dihapus smoothing,
pemetaan kelas, missing, isolasi waktu, dan penolakan kandidat yang merugikan.

`external_artifacts/v2/` menyimpan runtime terpisah, protokol, hasil eksperimen,
dan log baru. `inference_bundle.build_v2` hanya membekukan kandidat yang lolos;
jika semua kandidat ditolak, baseline A dipertahankan. Bundle v1 tidak ditimpa.
Panduan command dan kontrak lengkap ada pada bagian v2 di `docs/external_baseline.md`.

Dokumen ini menjelaskan **fungsi file, alasan file tersebut ada, dan bagaimana hubungannya dengan alur proyek**, menggunakan bahasa yang lebih sederhana.

Penjelasan mengikuti kondisi proyek setelah pekerjaan diagnosis sample Metrica, packaging model, dan pembuatan adapter tactical. Pada pengujian terakhir, **89 tes sintetis lulus**. Penulisan dokumen ini tidak menjalankan training, inferensi, atau pengujian ulang.

## 1. Cara memahami isi proyek

Proyek ini memprediksi penguasaan bola pada setiap frame:

- **H:** tim Home menguasai bola saat permainan hidup.
- **A:** tim Away menguasai bola saat permainan hidup.
- **D:** permainan berhenti atau bola mati.
- **X:** abstain atau frame di luar cakupan yang diproses.

Model classifier dilatih untuk H/A/D. Pada adapter tactical, X dipakai untuk frame di luar rentang babak yang dinyatakan metadata, bukan sebagai kelas hasil training classifier.

Alurnya secara sederhana:

```text
Pengembangan dengan DFL:
XML eksternal → observasi dan target terpisah → fitur → training
             → probabilitas mentah → decoder → evaluasi eksternal

Percobaan sample Metrica:
CSV tracking Home/Away → adapter → fitur → model beku → decoder → prediksi
Event sample ────────────────────────────────────────────────→ diagnosis saja

Inferensi tactical oleh pengguna:
Metadata XML + tracking TXT → adapter ATD → model/decoder beku → frame,label
```

Beberapa istilah yang sering muncul:

| Istilah | Arti sederhana |
| --- | --- |
| Observasi | Informasi input yang teramati, seperti posisi pemain dan bola. |
| Target atau GT | Jawaban acuan yang dipakai untuk melatih atau menilai model. |
| Fitur | Angka hasil pengolahan observasi, misalnya jarak bola ke pemain terdekat. |
| Classifier/model | Bagian yang menghasilkan prediksi H/A/D dari fitur. |
| Probabilitas mentah | Angka keluaran classifier untuk H/A/D, sebelum decoder. |
| Decoder | Bagian yang memilih rangkaian label berdasarkan probabilitas dan hubungan antarframe. Bisa menstabilkan prediksi, tetapi juga bisa menghasilkan rangkaian yang keliru. |
| Augmentasi | Membuat variasi gangguan pada input training, seperti bola tidak terlihat atau posisi berisik. Ini bukan pertandingan baru. |
| Snapshot/freeze | Salinan kandidat dan konfigurasi yang dikunci sebelum test. |
| Hash | Sidik jari isi file untuk mendeteksi perubahan. Hash bukan bukti bahwa prediksi benar. |
| Manifest | Catatan asal, versi, hash, konfigurasi, dan status hasil proses. |
| Artefak | File hasil proses, seperti database fitur, model, prediksi, atau laporan. |
| `ready` | Proses selesai sesuai pemeriksaan teknisnya. Tidak berarti model akurat atau kandidat otomatis dipilih. |

**Tidak semua file dibuat oleh saya.** Ada tiga kelompok asal:

1. **Bawaan MTAH:** kode, contoh, evaluator, dan dokumen kompetisi dari repository resmi.
2. **Warisan agent sebelumnya:** pipeline eksternal dan eksperimen sampai stage 9, ditambah persiapan data J03WPY/J03WQQ.
3. **Kelanjutan saya:** training multi-pertandingan, test J03WR9, adapter sample Metrica, diagnosis, bundle, adapter tactical, pengujian, dan dokumentasinya.

Asal tersebut didasarkan pada riwayat pekerjaan. Status `modified` di Git tidak otomatis berarti sebuah file dibuat atau diubah fungsional oleh saya; pada beberapa file bawaan pernah terdeteksi perbedaan akhir baris setelah pemindahan lintas sistem operasi.

File internal Python/library dalam venv tidak dijelaskan satu per satu karena dibuat oleh alat instalasi, bukan source aplikasi yang saya tulis. File hasil yang berulang di banyak folder dijelaskan berdasarkan nama/jenisnya, lalu foldernya dipetakan ke tahap eksperimen.

## 2. Source inti yang sudah ada dari agent sebelumnya

Semua file berikut berada dalam `external_baseline/`. Saya mempelajari dan memakai ulang file-file ini. Saya tidak membangun ulang pipeline stage 1–9 dari nol.

| File | Fungsinya untuk apa? | Mengapa dipisahkan menjadi file ini? |
| --- | --- | --- |
| `__init__.py` | Menandai folder sebagai package Python agar modul dapat dipanggil dengan `python -m external_baseline.nama_modul`. | Agar struktur kode dapat diimpor dan dijalankan secara konsisten. Bukan model atau pengolah dataset tersendiri. |
| `contracts.py` | Mendefinisikan identitas frame, bentuk observasi, bentuk target, aturan 25 Hz, dan pemetaan target DFL ke H/A/D. | Supaya parser, fitur, training, dan evaluasi memakai definisi yang sama. Ini membantu mencegah salah join dan kebocoran target ke input. |
| `dfl.py` | Membaca metadata dan positions XML DFL secara bertahap, memeriksa tim/pemain/frame/waktu/koordinat, lalu mengisi database observasi dan target. | XML pertandingan besar. Pembacaan bertahap menjaga penggunaan memori dan menempatkan aturan format DFL di satu tempat. |
| `prepare.py` | Pintu masuk persiapan DFL: menerima dua path XML, memanggil parser, menghitung hash, dan membuat manifest serta laporan validasi. Juga menyediakan helper hash dan pencatatan resource. | Memisahkan pembacaan format dari pengaturan sebuah proses lengkap yang bisa diaudit dan diulang. |
| `features.py` | Mengubah posisi pemain/bola menjadi 16 fitur observasi: keteramatan, posisi bola, kecepatan bola, jumlah pemain teramati, jarak terdekat per tim, dan konteks batas lapangan. | Fitur yang sama harus bisa digunakan dari DFL maupun adapter lain. File ini tidak membaca target untuk membuat fitur. |
| `training.py` | Menyimpan parameter HGB tetap, daftar fitur, pembacaan fitur-target dengan join ketat, training baseline, prediksi mentah, dan helper evaluasi timeline eksternal. | Membuat aturan model dan evaluasi konsisten. Entrypoint training historisnya masih memakai babak pertama untuk training dan babak kedua untuk validation. |
| `diagnostics.py` | Menganalisis pola kesalahan terhadap target eksternal, pergantian label, confidence, dan rangkaian frame yang benar-benar kontigu. | Skor saja tidak cukup menjelaskan masalah. File ini membantu mencari jenis kesalahan tanpa menambah aturan model secara diam-diam. |
| `temporal.py` | Menghitung prior/transisi dari training historis dan menjalankan decoder Markov/Viterbi. | Memisahkan keputusan per frame dari keputusan rangkaian waktu. Prior/transisi tidak boleh dipelajari dari validation/test. |
| `robustness.py` | Membuat gangguan observasi yang sudah ditentukan: bola hilang, pemain hilang, koordinat parsial, jitter posisi, dan gap frame. Menilai model yang parameternya tetap. | Data tracking nyata tidak selalu bersih. Ketahanan terhadap gangguan perlu diperiksa secara terpisah dari hasil pada data bersih. |
| `augmented.py` | Membuat training pool dari tujuh variasi observasi dan melatih satu model augmentasi pada eksperimen historis. | Memakai ulang jenis gangguan untuk training, tanpa mencampurkan validation ke fitting. Implementasi historisnya khusus babak pertama dan mempertahankan decoder pembanding yang sama. |
| `holdout.py` | Membekukan kandidat historis dan mengevaluasi kandidat beku pada pertandingan eksternal yang berbeda. Memastikan semua prediksi dibuat sebelum target test dimuat untuk penilaian. | Test harus berbeda dari data pengembangan. File ini menjaga pembekuan kandidat, pemisahan peran data, dan pemeriksaan hash. Evaluatornya juga dipakai ulang untuk J03WR9. |

**Perbedaan penting:** `diagnostics.py` memakai target eksternal untuk diagnosis kesalahan. `sample_review.py`, yang dijelaskan berikutnya, tidak punya GT possession sample Metrica dan hanya meninjau prediksi dengan referensi event terbatas.

## 3. Source yang saya tambahkan

### `external_baseline/multimatch.py`

**Fungsi:** melatih satu kandidat baru menggunakan kedua babak dari beberapa pertandingan training, lalu membandingkannya dengan model lama pada pertandingan validation yang terpisah.

Pada eksperimen yang sudah dijalankan:

- Training: J03WOH dan J03WPY, kedua babak.
- Development validation: J03WQQ, kedua babak.
- Classifier memakai 14 fitur dan parameter HGB yang sama.
- Gangguan training memakai resep augmentasi yang sama.
- Hitungan prior/transisi decoder berasal dari timeline training bersih, bukan dari penggandaan sampel augmentasi.

**Mengapa saya membuatnya:** kode training lama mengikat peran data ke nomor babak. Kebutuhan baru mengikat peran ke pertandingan. File baru memungkinkan eksperimen itu tanpa mengubah perilaku dan hasil historis entrypoint lama.

File ini juga menyimpan training pool di disk agar tidak harus menumpuk seluruh variasi pertandingan di RAM.

### `external_baseline/freeze_expanded.py`

**Fungsi:** membekukan kandidat baru dan model lama sebagai pembanding sebelum test J03WR9.

Yang disalin antara lain model, decoder, source, requirements, kontrak fitur, dan provenance. Keduanya mempertahankan decoder masing-masing.

**Mengapa saya membuatnya:** fungsi freeze historis dibuat untuk pasangan model eksperimen lama yang berbagi decoder yang sama. Kandidat baru memiliki decoder yang dihitung dari training multi-pertandingan, sehingga perlu pembungkus snapshot yang sesuai tanpa mengubah evaluator lama.

Konfirmasi riwayat pertandingan yang belum dipakai harus eksplisit. Ketiadaan file lokal tidak dianggap bukti bahwa pertandingan belum pernah digunakan.

**Arti nama kandidat pada snapshot J03WR9:**

| Nama dalam protokol/evaluator | Makna sebenarnya |
| --- | --- |
| `original` | Model **lama yang sudah memakai augmentasi**, beserta decoder lamanya. |
| `augmented` | Model **expanded/multi-pertandingan baru**, sebagai kandidat utama yang sudah ditetapkan sebelum test. |

Nama tersebut mempertahankan kompatibilitas evaluator lama. Jangan menganggap `original` di snapshot J03WR9 berarti baseline tanpa augmentasi.

### `external_baseline/metrica_sample.py`

**Fungsi:** membaca pasangan CSV tracking Home/Away dari Sample Game 1 dan 2 Metrica, membuat fitur, dan menjalankan model serta decoder beku.

File ini mengurus konversi koordinat 0–1 ke meter, pencocokan stream berdasarkan babak/frame, missing, gap, dan penolakan koordinat bola yang bertentangan. Nama seperti `Player26` dan `Player 26` dipetakan ke jersey yang sama.

**Mengapa saya membuatnya:** format CSV sample Metrica berbeda dari XML DFL. Yang perlu diubah adalah pembaca inputnya, bukan model yang sudah dilatih.

CSV hasilnya mempertahankan frame sumber dan waktu relatif sample. Itu bukan CSV tactical 199.319 baris. Event tidak menjadi input model dan tidak dibuat menjadi GT possession. File ini tidak menghitung F1 tanpa GT possession per frame.

### `external_baseline/sample_review.py`

**Fungsi:** meninjau prediksi sample yang sudah tersimpan, membandingkan label mentah dengan hasil decoder, mengelompokkan perubahan menurut keteramatan bola, dan menambahkan referensi event.

Keluarannya mencakup laporan JSON dan timeline HTML interaktif. File ini tidak memanggil model untuk membuat prediksi baru, tidak melakukan fitting, dan tidak mengubah prediksi yang dibacanya.

**Mengapa saya membuatnya:** decoder mengurangi prediksi D secara besar pada sample Metrica. Kita perlu melihat kapan perubahan terjadi dan konteksnya, bukan langsung menebak bahwa decoder benar atau salah.

Interval BALL OUT ke SET PIECE berikutnya hanya bahan review. Event tidak diubah menjadi target D untuk seluruh interval, karena ada ketidakpastian dan RECOVERY juga dapat menjadi restart.

### `external_baseline/inference_bundle.py`

**Fungsi:** membuat, memverifikasi, dan memuat paket inferensi yang bisa dipindahkan ke lokasi lain.

Paket berisi salinan model/decoder beku, source, kontrak fitur, requirements, provenance, dan petunjuk eksekusi. Pemeriksaan hash dan versi dependency dilakukan sebelum model dimuat.

**Mengapa saya membuatnya:** menjalankan model seharusnya tidak bergantung pada seluruh folder eksperimen, path komputer lama, atau ingatan tentang file model mana yang harus dipilih.

File ini menyalin kandidat yang sudah ditetapkan; tidak melatih ulang atau memilih pemenang berdasarkan test.

### `external_baseline/atd_inference.py`

**Fungsi:** adapter untuk pengguna menjalankan inferensi tactical dari metadata XML dan tracking ATD TXT secara lokal.

Tugasnya antara lain:

- Membaca FPS, dimensi lapangan, identitas tim, batas babak, dan deklarasi format dari metadata.
- Memetakan slot melalui referensi kanal, bukan menebak dari urutan roster.
- Mendukung perubahan layout slot yang dinyatakan metadata.
- Mengubah koordinat menjadi meter dan membuat fitur yang sama.
- Mengubah ATD ID 1-based menjadi frame submission 0-based.
- Membuat CSV `frame,label`, dengan default tepat 199.319 baris.
- Menjalankan decoder terpisah untuk tiap babak dan menulis X di luar cakupan metadata.

**Mengapa saya membuatnya:** model DFL tidak bisa langsung membaca file ATD. Kita membutuhkan jembatan format dan pemeriksaan alignment, tanpa mengubah model berdasarkan pertandingan resmi.

Adapter ini sudah diuji dengan fixture sintetis, termasuk kontrak penuh 199.319 baris. Metadata EPTS sample publik juga diperiksa sebagai referensi format. **Input resmi sebenarnya belum dibuka atau diuji oleh agent.** Format yang tidak didukung akan ditolak, bukan ditebak atau dikalibrasi otomatis.

## 4. File pengujian dalam `tests/`

File test berisi data buatan kecil dengan jawaban yang diketahui, bukan data pertandingan resmi. Tujuannya mencegah kesalahan kode dan pemisahan data; lulus test bukan bukti bahwa possession pada pertandingan nyata pasti benar.

| File | Yang diperiksa | Mengapa perlu? | Asal |
| --- | --- | --- | --- |
| `test_external_dfl.py` | Parser DFL, pemetaan target, tim/babak, duplikasi, missing, frame/time, pemisahan target, dan batas memori parsing. | Salah membaca input dapat membuat seluruh eksperimen tidak sah meskipun model berjalan. | Agent sebelumnya. |
| `test_observation_features.py` | Jarak dan kecepatan yang dihitung manual, missing/partial/outside, gap, batas babak, dan isolasi target. | Mencegah jarak nol palsu, kecepatan lintas gap, dan fitur yang bocor dari jawaban target. | Agent sebelumnya. |
| `test_external_training.py` | Join fitur-target, valid mask, konfigurasi model, prediksi mentah, dan evaluasi timeline. | Mencegah training pada frame salah, validation tersembunyi, atau penilaian yang memadatkan gap. | Agent sebelumnya. |
| `test_external_diagnostics.py` | Perhitungan diagnosis dan pembagian rangkaian kontigu. | Memastikan laporan tidak menyimpulkan masalah berdasarkan hitungan yang salah. | Agent sebelumnya. |
| `test_external_temporal.py` | Hitungan prior/transisi, hasil Viterbi pada contoh kecil, probabilitas, dan reset temporal. | Decoder bekerja pada rangkaian; satu sambungan lintas gap dapat mengubah banyak label. | Agent sebelumnya. |
| `test_external_robustness.py` | Penghilangan record/axis, jitter, frame gap, dan evaluasi model tetap. | Membedakan gangguan input yang memang disengaja dari bug yang mengubah target/model. | Agent sebelumnya. |
| `test_external_augmented.py` | Training pool augmentasi, label sumber, satu fitting, dan decoder historis yang tetap. | Memastikan variasi observasi tidak membuat target baru atau memasukkan validation ke training. | Agent sebelumnya. |
| `test_external_holdout.py` | Snapshot dan evaluasi test historis, konfirmasi riwayat, hash, dan urutan inferensi sebelum pembacaan target. | Mencegah data pengembangan dianggap test baru atau kandidat berubah setelah melihat hasil. | Agent sebelumnya. |
| `test_external_multimatch.py` | Peran per pertandingan, kedua babak training, pooling hitungan decoder, disk-backed pool, dan independensi dari label validation. | Kebutuhan multi-pertandingan berbeda dari kode babak-1/babak-2 lama. | Saya. |
| `test_freeze_expanded.py` | Snapshot kandidat baru, decoder berbeda, deklarasi primary, larangan pertandingan yang sudah dipakai, dan kompatibilitas evaluator lama. | Memastikan adapter snapshot baru tidak melemahkan pembatas test. | Saya. |
| `test_metrica_sample.py` | Konversi koordinat, header/jersey, stream Home/Away, bola ganda, missing, waktu, dan hasil inferensi berulang. | Format provider lain bisa terbaca tanpa error tetapi menghasilkan fitur yang salah. | Saya. |
| `test_sample_review.py` | Hitungan perubahan label, gap, event end=0, referensi event, dan import/help yang aman. | Diagnosis tidak boleh membuat GT palsu atau salah menghitung efek decoder. | Saya. |
| `test_local_inference.py` | Bundle portabel, hash, kanal/slot, batas babak, raw ID, format CSV 199.319 baris, reproduksi, dan kegagalan yang aman. | Memastikan mekanisme adapter tactical benar tanpa membuka data resmi. | Saya. |

Angka **89** adalah jumlah kasus test pada pengujian terakhir, bukan jumlah file test dan bukan penjumlahan seluruh pengujian ulang sepanjang sesi.

## 5. Konfigurasi, dependency, dan dokumentasi

| File | Fungsinya | Mengapa ada / mengapa diubah? | Asal |
| --- | --- | --- | --- |
| `requirements.txt` | Dependency minimum evaluator: NumPy dan pandas. | Agar pengguna bisa menjalankan komponen evaluasi tanpa seluruh tooling tambahan. | Bawaan MTAH. |
| `requirements-starter.txt` | Dependency opsional starter dan notebook, termasuk kloppy dan matplotlib. | Memisahkan kebutuhan notebook dari kebutuhan minimum. Tidak semuanya diperlukan pipeline eksternal kita. | Bawaan MTAH. |
| `requirements-external-training.txt` | Enam versi library yang dipin untuk training eksternal. | Membantu menjaga kompatibilitas model tersimpan dan hasil eksperimen historis. | Agent sebelumnya; dipakai ulang dan diverifikasi. |
| `requirements-multimatch-training.txt` | Memakai requirements training sebelumnya dan menambahkan pin dependency transitif yang terpasang pada eksperimen multi-pertandingan. | Agar reproduksi tidak diam-diam mendapatkan versi berbeda untuk dependency tambahan. | Saya. |
| `.gitignore` | Mengecualikan raw data, artefak, venv, dan file yang tidak semestinya masuk Git. | Saya menambahkan pengecualian `local_official_artifacts/` untuk hasil inferensi resmi yang nantinya dibuat pengguna. Aturan lain sudah ada sebelumnya. | Bawaan dan perubahan proyek, termasuk perubahan saya. |
| `docs/external_baseline.md` | Catatan lengkap kontrak, metode, command, eksperimen, hasil, provenance, dan keterbatasan. | Menjaga keputusan dan hasil tetap bisa ditelusuri. Saya menambahkan tahap kelanjutan; catatan lama dipertahankan. | Agent sebelumnya, lalu diperbarui saya. |
| `penjelasan_file.md` | Panduan file yang sedang dibaca ini. | Dibuat atas permintaan pengguna agar struktur dan alasan pembagian file mudah dipahami. | Saya. |
| `ringkasan_model.json` | Ringkasan model untuk manusia: jenis classifier, 14 fitur beserta artinya, kelas, iterasi, parameter, dan konfigurasi decoder. | Agar informasi model dapat dibaca di IDE tanpa membuka file biner `.joblib`. Ini bukan pengganti model; mengeditnya tidak mengubah model tersimpan. | Saya. |

### Venv dan file konfigurasi pip

| Lokasi/file | Fungsinya | Mengapa dibuat? |
| --- | --- | --- |
| `.venv/` | Lingkungan Python lokal untuk tahap fitur yang hanya membutuhkan standard library. | Memisahkan lingkungan proyek dari instalasi Python pengguna. |
| `.venv/pip.conf` | Menonaktifkan cache pip, pemeriksaan versi pip otomatis, dan mewajibkan virtual environment untuk instalasi lewat pip. | Mengikuti permintaan agar instalasi/cache tidak memenuhi home dan tidak memakai user-site. |
| `external_artifacts/local-runtime/training-venv/` | Venv training/inferensi Python 3.11 dengan versi library yang sesuai model. | Dependency training membutuhkan lingkungan berbeda dari venv fitur awal. Semuanya tetap di drive proyek. |
| `external_artifacts/local-runtime/training-venv/pip.conf` | Pengaturan pip lokal dengan cache dinonaktifkan dan kewajiban venv. | Menjaga kebijakan instalasi yang sama pada venv training. |
| `pyvenv.cfg`, `bin/python`, `bin/activate`, `bin/pip`, dan `site-packages/` di dalam venv | File standar lingkungan Python dan library yang diinstal. | Dibuat oleh Python/pip. Bukan modul tambahan model dan tidak perlu diedit manual. |
| `external_artifacts/local-runtime/training-requirements.lock.txt` | Hasil `pip freeze` dari lingkungan training. | Bukti versi yang benar-benar terpasang, sebagai pendamping requirements yang ditulis di source. |
| `external_artifacts/local-runtime/tmp/` | Tempat file sementara proses dan fixture test. | Menjaga file sementara di drive proyek. |
| `external_artifacts/local-runtime/pip-cache/` | Lokasi cache lokal yang telah disiapkan. | Jika dibutuhkan, lokasinya tersedia di proyek; pada pekerjaan ini cache pip dinonaktifkan. |

Venv adalah **lingkungan menjalankan program**, bukan file model. `model.joblib` adalah **hasil training model**. Keduanya memiliki fungsi berbeda.

## 6. Script pembantu yang saya buat

Script ini membantu menjalankan satu tahap historis dengan path dan output yang sudah ditentukan. Entrypoint yang lebih umum tetap modul dalam `external_baseline/`.

**Jangan menjalankan ulang semua script ini secara berurutan tanpa membaca argumennya.** Beberapa memakai nama output historis yang sengaja tidak boleh ditimpa. Untuk reproduksi, gunakan command modul dari dokumentasi dengan output baru.

| File | Fungsinya | Mengapa dibuat? |
| --- | --- | --- |
| `external_artifacts/run_development_features_v1.py` | Memverifikasi input J03WPY/J03WQQ, menjalankan ekstraksi fitur, memeriksa hasil, dan menulis manifest gabungan. | Supaya tahap fitur punya pemeriksaan menyeluruh dan pembatas akses target/model selama eksekusi. |
| `external_artifacts/local-runtime/run_external_multimatch.py` | Memanggil CLI multi-pertandingan dengan audit hook yang menolak akses raw/official input tertentu. | Menambahkan penjagaan saat eksperimen eksternal dijalankan, bukan mengganti algoritma training. |
| `external_artifacts/local-runtime/download_j03wr9.py` | Memeriksa snapshot, membaca katalog Figshare, mengunduh dua XML J03WR9, melanjutkan lewat byte ranges, lalu memverifikasi file lengkap. | Unduhan sempat lambat. Script menjaga bagian yang sudah lengkap agar tidak perlu mengulang semuanya dan mencegah parser memakai file parsial. Opsi probe hanya memeriksa transfer. |
| `external_artifacts/local-runtime/run_j03wr9_assessment.py` | Memverifikasi unduhan/snapshot, lalu menjalankan prepare, features, dan evaluasi kandidat beku. | Menjaga urutan test dan pemeriksaan hash sebelum/sesudah proses. |
| `external_artifacts/local-runtime/download_metrica_samples.py` | Mengunduh README dan empat CSV tracking Game 1/2 pada commit GitHub yang dipin. | Menjaga sumber input tetap jelas dan memverifikasi ukuran, Git blob SHA-1, serta SHA-256. |
| `external_artifacts/local-runtime/run_metrica_samples.py` | Memeriksa unduhan, menjalankan regression suite, lalu inferensi kedua game dengan output final v2. | Menyatukan verifikasi dan eksekusi sample secara berurutan. File ini pernah diperbarui dari output v1 ke v2 setelah dukungan nama `Player 26` ditambahkan. |
| `external_artifacts/local-runtime/download_metrica_diagnostics.py` | Mengunduh dua CSV event, PDF definisi event, dan metadata publik Game 3. Juga memeriksa sintaks baris pertama tracking publik Game 3. | Diagnosis memerlukan definisi event; desain adapter perlu referensi format EPTS eksternal. Tidak mengunduh atau memproses input resmi. |
| `external_artifacts/local-runtime/check_review_html.js` | Memeriksa sintaks JavaScript dan mencoba kontrol timeline memakai stub DOM/canvas di Node. | Menangkap error pada pemilihan babak, navigasi waktu, event jump, dan perintah menggambar. Ini smoke test, bukan penilaian possession. |
| `external_artifacts/local-runtime/metrica_sample_v1_source.py` | Salinan source adapter sebelum penyesuaian header Game 2. | Menjaga jejak implementasi awal. Bukan entrypoint utama dan bukan model kedua. |

Script pembantu berada di folder artefak yang diabaikan Git. Jika hendak menjadikan suatu langkah sebagai workflow permanen, utamakan modul/command yang terdokumentasi; jangan menggantungkan reproduksi hanya pada script lokal ad hoc.

## 7. Jenis file hasil proses

Nama yang sama dapat muncul di banyak folder. Artinya mengikuti jenis dan tahap prosesnya; isinya tidak otomatis sama.

| Nama file | Isi/fungsi | Mengapa dibuat? |
| --- | --- | --- |
| `observations.sqlite` | Database frame dan posisi pemain/bola, terpisah dari target. | Mengolah input besar tanpa membaca XML berulang dan menjaga jawaban tidak ikut masuk fitur. |
| `targets.sqlite` | Label eksternal H/A/D, valid mask, kode target sumber, dan alasan label tidak valid. | Supervised training dan evaluasi perlu jawaban acuan yang terpisah secara struktural. |
| `features.sqlite` | Angka fitur per frame beserta identitas temporal. | Menggunakan ulang fitur yang sama dan memeriksa alignment. Schema waktu berbeda antara DFL, sample CSV, dan adapter tactical; jangan dianggap saling tertukar otomatis. |
| `validation_report.json` | Hasil pemeriksaan parser: jumlah frame, gap, duplikasi, kualitas koordinat, dan target. | Mengetahui apakah data layak dipakai sebelum training/inferensi. |
| `feature_report.json` | Coverage dan statistik fitur per babak. | Mengetahui berapa banyak fitur yang tersedia atau missing tanpa memakai target untuk membuatnya. |
| `config.json` | Konfigurasi suatu training/decoder historis. | Menyimpan parameter yang dipakai, bukan hanya mengandalkan nilai default di kepala pengembang. |
| `protocol.json` | Rancangan eksperimen/test, kandidat, peran pertandingan, dan aturan yang dibekukan. | Mencegah pemilihan kandidat atau konfigurasi diam-diam setelah melihat test. |
| `manifest.json` | Status, hash input/output/source, versi, dan provenance tahap tersebut. | Menghubungkan hasil dengan sumber dan kode yang benar-benar dipakai. |
| `FAILED.json` | Alasan proses gagal setelah folder output dibuat. | Menandai hasil parsial agar tidak disangka sudah siap. Folder gagal bukan model atau hasil evaluasi yang sah. |
| `model.joblib` | Classifier yang sudah dilatih dan metadata konfigurasi/urutan fiturnya. | Inilah bobot/struktur model yang digunakan untuk prediksi; tidak perlu training ulang setiap inferensi. |
| `decoder_parameters.json` | Prior kelas, transisi, dan konfigurasi numerik decoder. | Memastikan decoder memakai hitungan training yang sudah ditetapkan, bukan belajar dari test. |
| `predictions.sqlite` | Prediksi per frame; pada tahap tertentu mencakup raw probabilities, label raw, label decoded, atau beberapa kandidat. | Menyimpan hasil dengan kunci frame yang bisa diverifikasi. Kolom persisnya bergantung pada versi/tahap. |
| `predictions.csv` | Ekspor prediksi sample Metrica dengan babak, frame sumber, waktu, raw/decoded label, dan probabilitas. | Memudahkan pengguna membaca hasil tanpa membuka SQLite. Ini bukan CSV submission tactical. |
| `metrics.json` | Spell F1, Macro F1, metrik kelas/transisi, dan statistik lain pada dataset yang memiliki target. | Menilai hasil secara terukur. F1 bukan persentase akurasi. |
| `comparison.json` | Ringkasan perbandingan kandidat atau varian. | Membaca perbedaan hasil tanpa menelusuri semua laporan rinci. |
| `diagnostic_report.json` | Diagnosis baseline terhadap target eksternal pada tahap historis. | Mencari pola kesalahan yang tidak tampak dari satu angka F1. |
| `robustness_report.json` | Hasil pada berbagai gangguan observasi yang sudah ditentukan. | Memeriksa ketahanan model terhadap tracking yang tidak sempurna. |
| `training_audit.json` | Jumlah frame/sampel, label training, dan kontribusi tiap variasi augmentasi. | Memastikan training pool berasal dari data yang benar dan tidak ada validation/test yang ikut fitting. |
| `training-X.bin` | Matriks fitur training multi-pertandingan yang disimpan di disk. | Mengurangi kebutuhan menumpuk seluruh matriks dalam RAM. Bukan file raw pertandingan atau bobot model. |
| `training-y.bin` | Label yang sejajar dengan baris `training-X.bin`. | Menjaga pasangan fitur-label pada pool training. Bukan GT resmi. |
| `report.json` | Ringkasan inferensi sample atau pemeriksaan format lokal, sesuai tahap. | Menampilkan coverage/count tanpa berpura-pura punya skor jika GT tidak tersedia. |
| `summary.json` | Ringkasan diagnosis perubahan label decoder dan referensi event sample. | Menunjukkan bagian yang perlu ditinjau secara agregat. |
| `event_references.json` | Event sample dan anchor yang dipasangkan ke frame asli. | Memeriksa konteks tanpa mengubah event menjadi GT possession padat. |
| `timeline.html` | Visualisasi interaktif raw label, decoded label, keteramatan bola, perubahan D, dan event. | Membantu manusia memahami rangkaian waktu. Tidak memerlukan server atau library web tambahan. |
| `submission.csv` | CSV decoded dengan kolom `frame,label` pada adapter tactical. | Format akhir yang nantinya dibuat pengguna lokal dari input resmi. Dalam pekerjaan agent, file ini hanya dibuat untuk fixture sintetis. |
| `submission_raw.csv` | CSV label classifier sebelum decoder pada adapter tactical. | Pembanding teknis lokal; tidak dipilih otomatis sebagai submission utama. Dalam pekerjaan agent hanya dibuat dari fixture sintetis. |
| `*.sqlite-journal`, `*-wal`, `*-shm` | File pendamping SQLite yang dapat muncul selama database dipakai. | Dibuat otomatis oleh SQLite untuk transaksi; bukan fitur, model, atau output ilmiah tersendiri. |

File `model.joblib` dan `decoder_parameters.json` adalah pasangan. Jangan mengambil model dari satu eksperimen lalu decoder dari folder lain tanpa protokol yang memang menyatakan pasangan tersebut.

## 8. Folder artefak dan tahap pembuatannya

Tabel ini menjelaskan untuk apa setiap keluarga folder hasil. Nama file di dalamnya mengikuti tabel jenis file di atas.

### Artefak yang diwarisi dari agent sebelumnya

| Folder di `external_artifacts/` | Perannya |
| --- | --- |
| `J03WOH-v1/`, `J03WOH-run2/`, `J03WOH-v1-verified/` | Versi persiapan/validasi data awal J03WOH. Menyimpan observasi, target, manifest, dan laporan parser. |
| `J03WOH-features-v1/`, `J03WOH-features-run2/` | Hasil fitur J03WOH yang menjadi dasar eksperimen historis. |
| `J03WOH-hgb-v1/` | Baseline classifier 16 fitur dan prediksi mentahnya. |
| `J03WOH-diagnostics-v1/`, `J03WOH-diagnostics-run2/` | Diagnosis hasil classifier awal. |
| `J03WOH-hgb-no-signed-position-v1/`, `J03WOH-hgb-no-signed-position-run2/` | Eksperimen 14 fitur yang mengeluarkan posisi bola x/y bertanda dari input model. |
| `J03WOH-markov-v1/`, `J03WOH-markov-run2/` | Percobaan decoder temporal untuk baseline historis. |
| `J03WOH-robustness-v1/` | Stress test model historis dengan gangguan observasi. |
| `J03WOH-augmented-v1/` | Eksperimen training dengan augmentasi; subfolder `classifier/`, `decoder/`, dan `stress/` memisahkan peran hasilnya. |
| `J03WOY-holdout-pending-v1/` | Snapshot awal yang belum mempunyai konfirmasi riwayat untuk evaluasi. Bukan hasil test yang sah. |
| `J03WOY-holdout-frozen-v1/` | Kandidat/protokol yang dibekukan untuk assessment J03WOY setelah konfirmasi. |
| `J03WOY-prepared-v1/`, `J03WOY-features-v1/` | Persiapan dan fitur pertandingan assessment historis. |
| `J03WOY-holdout-results-v1/` | Hasil assessment historis pada J03WOY. Pertandingan ini sudah digunakan untuk assessment kandidat lama. |
| `J03WPY-prepared-v1/`, `J03WQQ-prepared-v1/` | Hasil download/parser yang sudah diselesaikan agent sebelumnya dan kemudian saya verifikasi. |
| `development-data-v1/` | Manifest gabungan validasi input tambahan dan rencana pembagian pertandingan. |

`run2` atau `verified` tidak otomatis berarti model lebih baik. Itu nama versi proses/validasi. Rujuk manifest dan provenance untuk mengetahui isinya.

### Artefak yang saya buat pada kelanjutan ini

| Folder/file di `external_artifacts/` | Perannya dan alasan dibuat |
| --- | --- |
| `J03WPY-features-v1/` | Fitur 146.211 frame J03WPY, memakai ekstraktor yang sudah ada. |
| `J03WQQ-features-v1/` | Fitur 142.345 frame J03WQQ, memakai ekstraktor yang sama. |
| `development-features-v1/manifest.json` | Bukti gabungan bahwa kedua hasil fitur lolos pemeriksaan timeline, satuan, dan hash. |
| `development-multimatch-v1/` | Model expanded, decoder, training pool, prediksi, metrik, dan protokol eksperimen multi-pertandingan. |
| `J03WR9-expanded-frozen-v1/` | Snapshot model baru/pembanding dan source sebelum test J03WR9 diproses. |
| `J03WR9-expanded-prepared-v1/` | Observasi dan target J03WR9 yang diparsing setelah snapshot. |
| `J03WR9-expanded-features-v1/` | Fitur J03WR9 untuk inferensi kandidat beku. |
| `J03WR9-expanded-results-v1/` | Prediksi dan skor test kedua kandidat pada 146.810 frame J03WR9. |
| `metrica-sample-game1-v1/` | Hasil awal Game 1 sebelum dukungan variasi header Game 2 ditambahkan. Tetap dipertahankan sebagai jejak pekerjaan. |
| `metrica-sample-game2-v1/` | Percobaan yang gagal karena header `Player 26` belum didukung. Memiliki `FAILED.json`, bukan manifest siap. |
| `metrica-sample-game1-v2/` | Hasil final Game 1: 145.006 frame. Fitur/prediksinya identik byte-per-byte dengan v1. |
| `metrica-sample-game2-v2/` | Hasil final Game 2: 141.156 frame setelah pembaca header mendukung variasi tersebut. |
| `metrica-sample-inference-v2.json` | Ringkasan kedua hasil inferensi dan keterkaitannya dengan unduhan yang dipin. |
| `metrica-game1-review-v1/`, `metrica-game2-review-v1/` | Timeline, ringkasan perubahan decoder, dan referensi event untuk masing-masing sample. |
| `inference-bundle-v1/` | Paket inferensi portabel yang sudah dipisahkan dari folder eksperimen. |
| `inference-bundle-v1.zip` | Arsip paket yang sama agar mudah dipindahkan. Tidak berisi raw data atau venv. |
| `inference-bundle-v1-release.json` | Hash arsip/model/decoder dan catatan pemeriksaan portabilitas serta fixture. |

J03WOY dan J03WR9 sekarang adalah **assessment yang sudah digunakan**, bukan cadangan test yang masih belum disentuh. Field `reserved_test` di protokol lama adalah keadaan historis saat protokol itu dibuat, bukan daftar ketersediaan test saat ini.

## 9. File khusus snapshot

File berikut muncul pada snapshot expanded J03WR9. Semuanya bertujuan menjaga kandidat dan asalnya, bukan menciptakan model baru.

| File/lokasi | Fungsi dan alasan dibuat |
| --- | --- |
| `protocol.json` | Mengunci identitas test, primary, pembanding, aturan evaluasi, runtime, dan konfirmasi riwayat. |
| `snapshot_manifest.json` | Hash seluruh file salinan snapshot agar integritas snapshot bisa diperiksa. |
| `augmented/model.joblib` dan `augmented/decoder_parameters.json` | Salinan persis kandidat expanded utama. |
| `original/model.joblib` dan `original/decoder_parameters.json` | Salinan persis model lama yang sudah di-augmentasi, sebagai pembanding. |
| `development_protocol.json` | Salinan rancangan eksperimen yang menghasilkan kandidat expanded. |
| `expanded_manifest.json` | Salinan bukti asal model expanded, termasuk hash dan provenance. |
| `old_classifier_manifest.json` | Salinan bukti asal classifier pembanding. |
| `old_decoder_manifest.json` | Salinan bukti asal decoder pembanding dan hubungannya dengan classifier. |
| `requirements-external-training.txt` dan `requirements-multimatch-training.txt` | Versi dependency yang menyertai kandidat. |
| `source/` | Salinan source pipeline/metrik yang dibekukan. Nama file yang sama di dalamnya adalah salinan, bukan implementasi lain. |

## 10. Isi paket inferensi

Semua path berikut relatif terhadap `external_artifacts/inference-bundle-v1/`.

| File/lokasi | Fungsinya | Mengapa dibuat? |
| --- | --- | --- |
| `run_tactical.py` | Pintu masuk singkat ke adapter tactical yang ada di source paket. | Memudahkan eksekusi tanpa memasang source proyek sebagai package global. |
| `verify_bundle.py` | Memverifikasi paket; opsi `--runtime` juga mengecek versi library. | Menemukan perubahan/kerusakan atau lingkungan yang tidak cocok sebelum inferensi. |
| `README.md` | Petunjuk setup, command lokal, format yang didukung, batas akses, dan keterbatasan kualitas. | Pengguna paket tidak perlu membaca seluruh riwayat eksperimen untuk menjalankannya. |
| `requirements.txt` | Dependency paket yang dipin, termasuk tambahan transitif. | Menyediakan lingkungan yang sesuai model. Ini salinan kebutuhan runtime, bukan model baru. |
| `requirements-external-training.txt` | File dependency dasar yang dirujuk requirements paket. | Menjaga referensi `-r` tetap valid setelah paket dipindah. |
| `feature_contract.json` | Nama/urutan fitur, satuan, FPS, missing, dan aturan scope. | Mencegah input dengan urutan atau satuan keliru dianggap cocok dengan model. |
| `bundle_manifest.json` | Hash file paket, model/decoder, versi dependency, dan status validasi. | Menjaga paket dan kandidat tetap konsisten di lokasi lain. |
| `CODE_LICENSE` | Salinan lisensi kode repository. | Mempertahankan informasi lisensi kode saat paket dipindah. Lisensi data eksternal tetap terpisah. |
| `model/model.joblib` | Salinan classifier expanded yang sudah diuji. | Agar paket tidak bergantung pada path folder training. |
| `model/decoder_parameters.json` | Salinan decoder milik kandidat expanded. | Menjaga pasangan model-decoder yang benar. |
| `src/external_baseline/*.py` | Salinan source modul proyek yang sudah dijelaskan di bagian sebelumnya. | Agar paket bisa dijalankan dari luar folder proyek. Tidak ada training tambahan saat penyalinan. |
| `src/evaluation/possession_metrics.py` | Salinan source metrik untuk kelengkapan provenance source. | Mempertahankan kode acuan; adapter tidak menjalankan evaluator GT resmi. |
| `provenance/protocol.json` | Salinan protokol snapshot sebelum test. | Menelusuri kandidat dan peran test yang sudah ditetapkan. |
| `provenance/snapshot_manifest.json` | Salinan sidik jari snapshot asal. | Menghubungkan paket dengan snapshot yang benar. |
| `provenance/expanded_manifest.json` | Salinan asal training kandidat utama. | Menyimpan jejak sumber model. |
| `provenance/old_classifier_manifest.json` | Salinan asal classifier pembanding pada assessment. | Menjaga konteks perbandingan historis; model pembanding tidak menjadi model aktif paket. |

Paket tidak menyertakan raw pertandingan, GT, venv, atau hasil resmi. Folder `local_official_artifacts/` di root proyek adalah lokasi yang diabaikan Git untuk hasil yang nantinya dibuat pengguna lokal. Agent tidak membuka isinya.

## 11. Laporan verifikasi, log, dan catatan runtime

Semua file berikut berada dalam `external_artifacts/local-runtime/`.

### Laporan dan catatan

| File | Fungsi dan alasan dibuat |
| --- | --- |
| `J03WR9-verification.json` | Hasil pemeriksaan tambahan jumlah frame/baris kandidat, role test, integritas SQLite, timeline, dan referensi hash protokol/hasil. |
| `metrica-sample-verification.json` | Hasil pemeriksaan CSV vs database, alignment fitur/prediksi, hash, dan kesamaan output Game 1 v1/v2. |
| `metrica-decoder-mechanism.json` | Statistik probabilitas ketika bola hilang, prior training, dan rasio posterior/prior untuk memahami efek decoder. |
| `metrica-decoder-mechanism-v2.json` | Menambahkan perhitungan skor jalur tetap yang juga memasukkan self-transition. Versi kedua memperinci diagnosis; tidak mengubah parameter decoder. |
| `metrica-events-definitions.txt` | Hasil ekstraksi teks dari PDF definisi event publik. |

File terakhir dibuat agar definisi event mudah diperiksa tanpa mengulang ekstraksi PDF. Ia bukan source model, GT possession, atau label hasil anotasi agent.

### Log proses

| File | Proses yang dicatat / alasan disimpan |
| --- | --- |
| `multimatch-tests.log` | Output regression suite pada tahap training multi-pertandingan. |
| `expanded-freeze-targeted-tests.log` | Test khusus kompatibilitas snapshot expanded. |
| `expanded-holdout-tests.log` | Regression suite setelah penambahan freeze expanded. |
| `metrica-sample-targeted-tests.log` | Test khusus pembaca/inferensi sample Metrica. |
| `metrica-sample-regression-tests.log` | Regression suite saat adapter sample diselesaikan. |
| `local-inference-tests.log` | Test khusus bundle dan adapter tactical dengan fixture sintetis. |
| `diagnosis-bundle-regression-tests.log` | Regression suite akhir berisi 89 kasus test. |
| `J03WR9-prepare.log` | Keluaran parser dan validasi J03WR9. |
| `J03WR9-features.log` | Keluaran ekstraksi fitur J03WR9. |
| `J03WR9-evaluate.log` | Keluaran evaluator eksternal J03WR9. |
| `metrica-game1.log` | Keluaran inferensi sample Game 1 dari script pembantu. |
| `metrica-game2.log` | Keluaran inferensi sample Game 2 dari script pembantu. |

Log disimpan untuk diagnosis teknis dan bukti eksekusi. Sebagian path log dipakai ulang ketika pengujian diulang; jangan menganggap setiap log merupakan arsip semua percobaan yang pernah terjadi. Manifest dan folder output versi tetap menjadi rujukan utama hasil.

## 12. File data eksternal yang diunduh

File-file ini **bukan saya menulis isi datanya**. Saya atau agent sebelumnya mengunduhnya dari sumber eksternal, kemudian memverifikasi sumber/ukuran/hash. Tidak perlu membaca seluruh isi `data/` untuk memahami source proyek.

| File/pola | Fungsi | Mengapa diperlukan? |
| --- | --- | --- |
| `DFL_02_01_matchinformation_...xml` | Metadata DFL: pertandingan, tim, pemain, dan lapangan. | Menafsirkan identitas dan satuan tracking dengan benar. |
| `DFL_04_03_positions_raw_observed_...xml` | Tracking pemain/bola dan atribut target eksternal DFL. | Menjadi sumber observasi serta jawaban training/evaluasi eksternal yang dipisahkan oleh parser. |
| `download_manifest.json` pada folder unduhan DFL | Sumber URL, file ID, ukuran, checksum, dan atribusi. | Mendeteksi unduhan salah/rusak dan menjaga asal data. |
| `Sample_Game_1_RawTrackingData_Home_Team.csv`, `Sample_Game_1_RawTrackingData_Away_Team.csv` | Tracking Home/Away sample Game 1. | Menguji inferensi pada format provider Metrica yang berbeda dari DFL. |
| `Sample_Game_2_RawTrackingData_Home_Team.csv`, `Sample_Game_2_RawTrackingData_Away_Team.csv` | Tracking Home/Away sample Game 2. | Pemeriksaan integrasi kedua, termasuk variasi jumlah pemain/penamaan kolom. |
| README upstream dalam folder unduhan sample | Keterangan koordinat, dimensi lapangan, penggunaan, dan atribusi sumber. | Mendasari interpretasi format dan acknowledgement. |
| `download_manifest.json` pada akar unduhan sample yang dipin | Commit GitHub, ukuran, hash blob Git, SHA-256, dan URL file. | Menjaga identitas versi data yang dipakai. |
| `Sample_Game_1_RawEventsData.csv`, `Sample_Game_2_RawEventsData.csv` dalam `diagnostic_references/` | Event sample eksternal yang bersifat sparse/interval. | Referensi terbatas untuk diagnosis, bukan fitur model atau GT possession padat. |
| `events-definitions.pdf` dalam `diagnostic_references/` | Definisi jenis/subjenis event dari Metrica. | Menghindari salah menafsirkan BALL OUT, SET PIECE, RECOVERY, dan event lain. |
| `Sample_Game_3_metadata.xml` dalam `diagnostic_references/` | Contoh metadata EPTS publik. | Memahami deklarasi kanal dan perubahan layout untuk desain adapter. Tracking Game 3 penuh tidak diunduh atau diinferensi pada tahap ini. |
| `diagnostic_references/download_manifest.json` | Verifikasi sumber empat file referensi tersebut. | Menjaga provenance referensi diagnosis dan format. |
| `*.partial`, `*.assembled.partial` | File unduhan/gabungan yang belum lolos pemeriksaan lengkap, jika masih ada. | Mencegah file belum lengkap dipakai sebagai input final. |
| `tracking-download-parts/*.bin`, `tracking-download-small-parts/*.bin` | Potongan byte unduhan J03WR9. | Memungkinkan transfer dilanjutkan dan dipercepat. Ini bukan training pool meskipun sama-sama berekstensi `.bin`. |

Input resmi, GT resmi, serta hasil resmi pengguna berada di luar penjelasan isi data ini. Agent tidak membukanya untuk menulis panduan ini.

## 13. File bawaan repository MTAH

Bagian ini diberikan sebagai konteks agar jelas mana yang bukan tambahan saya. Penjelasan file data bawaan mengikuti dokumentasi/source, bukan pembacaan isi label GT atau prediksi resmi.

| File | Fungsi / alasan sudah ada dalam repo |
| --- | --- |
| `README.md` | Pintu masuk: tujuan kompetisi, struktur repository, dependency, dan cara mulai. |
| `CHALLENGE.md` | Definisi persoalan dan makna possession/kelas. |
| `DATA.md` | Kontrak format input, koordinat, dan alignment frame. |
| `EVALUATION.md` | Penjelasan metrik dan cara penilaian. |
| `SUBMISSION.md` | Bentuk CSV dan deliverable kompetisi. |
| `RULES.md` | Aturan repository/kompetisi. Klarifikasi email panitia yang diberikan pengguna tetap mengesampingkan aturan lama yang lebih longgar. |
| `FAQ.md` | Jawaban pertanyaan umum. |
| `OVERVIEW.md` | Konteks dan gambaran kompetisi secara keseluruhan. |
| `LICENSE` | Lisensi kode repository; bukan otomatis lisensi semua data. |
| `CITATION.cff` | Informasi sitasi repository. |
| `games.py` | Konstanta dan helper path/alignment per pertandingan/sumber. Adapter baru tidak memakai offset GT untuk menggeser ATD. |
| `starter/baseline.py` | Baseline resmi: pemain terdekat ke bola, dengan variasi smoothing. Disertakan agar ada contoh algoritma yang bisa direproduksi. |
| `starter/load_atd.py` | Helper loader tracking ATD dan pemeriksaan alignment. Tidak saya jalankan pada input resmi. |
| `starter/load_smart_tagging.py` | Helper membaca Smart Tagging resmi. Tidak menjadi input pipeline yang saya jalankan. |
| `starter/load_homography.py` | Helper membaca/proyeksi homography. Tidak menjadi input pipeline yang saya jalankan. |
| `starter/utils.py` | Helper menggambar lapangan/tracking untuk notebook bawaan. |
| `starter/make_dummy_submission.py` | Membuat contoh submission label konstan untuk pemeriksaan format. Bukan model yang digunakan sekarang. |
| `starter/01_smart_tagging.ipynb` | Tutorial Smart Tagging. |
| `starter/02_tracking_atd.ipynb` | Tutorial tracking. |
| `starter/03_first_submission.ipynb` | Tutorial alur submission awal. Notebook tidak saya eksekusi pada data resmi. |
| `evaluation/possession_metrics.py` | Definisi resmi metrik dan pemeriksaan label. Fungsi murninya dipakai ulang untuk evaluasi eksternal atau fixture format tanpa membuka GT resmi. |
| `evaluation/run_evaluation.py` | Scorer bawaan yang dapat membaca CSV dan GT. Default GT publiknya bukan dataset untuk tuning atau evaluasi eksperimen eksternal kita. |
| `evaluation/validate_submission.py` | Validator format CSV; lulus format tidak berarti prediksi benar. Pengujian adapter memakai fungsi validator pada CSV sintetis. |
| `evaluation/gt/BAR-ATH_possession_gt_public.csv` | File GT publik bawaan. Agent tidak membaca atau memakainya sebagai data eksperimen. |
| `evaluation/gt/BAR-ATH_possession_gt_public_meta.json` | Metadata GT publik bawaan; tidak dipakai sebagai input eksperimen ini. |
| `evaluation/results/baseline_raw.csv` | Contoh prediksi baseline mentah bawaan. Bukan hasil model baru. |
| `evaluation/results/baseline_smooth25.csv` | Contoh baseline bawaan dengan smoothing tertentu. |
| `evaluation/results/baseline_smooth50.csv` | Contoh baseline bawaan dengan smoothing tertentu. |
| `evaluation/results/baseline_smooth125.csv` | Contoh baseline bawaan dengan smoothing tertentu. |
| `evaluation/results/README.md` | Penjelasan folder hasil bawaan. |
| `data/README.md` | Petunjuk lokasi data; bukan raw pertandingan. |

## 14. File mana yang perlu dibaca lebih dulu?

Kalau tujuanmu **memahami model sekarang**, urutannya:

1. `contracts.py`: bentuk input dan target.
2. `features.py`: informasi apa yang dihitung dari input.
3. `training.py`: parameter dan daftar fitur model.
4. `multimatch.py`: cara kandidat expanded dilatih dan divalidasi.
5. `temporal.py`: cara probabilitas diubah menjadi rangkaian label.

Kalau tujuanmu **melihat hasil sample**, buka `timeline.html` dan `summary.json` pada folder review. CSV mentah/decoded ada di folder inferensi sample, bukan di folder review.

Kalau tujuanmu **menjalankan paket lokal**, mulai dari `external_artifacts/inference-bundle-v1/README.md`, lalu `verify_bundle.py` dan `run_tactical.py`. Tidak perlu menjalankan ulang seluruh parser/training/test historis hanya untuk memuat model beku.

Kalau tujuanmu **mengubah kode**, mulai dari modul pada `external_baseline/`, lalu test yang sesuai. Jangan mengedit salinan source di snapshot atau bundle untuk mengubah model utama; salinan tersebut sengaja dijaga agar hasil lama tetap dapat ditelusuri.

## 15. Mengapa file dan versinya cukup banyak?

Sebagian besar jumlah file berasal dari **hasil dan salinan**, bukan banyaknya algoritma baru:

- Observasi dan target dipisahkan agar jawaban tidak bocor ke input.
- Fitur disimpan agar tidak perlu dihitung ulang untuk setiap eksperimen.
- Model, decoder, konfigurasi, dan hasil dipisahkan agar tidak tertukar.
- Snapshot menyimpan salinan sebelum test; bundle menyimpan salinan untuk pemakaian portabel.
- Output versi lama/gagal tidak ditimpa agar masalah dan asal hasil bisa diaudit.
- Log serta laporan menyimpan bukti proses dan pemeriksaannya.
- Banyak file di venv adalah library pihak ketiga, bukan kode aplikasi tambahan.

Pemecahan modul juga menjaga perubahan tetap terbatas. Contohnya, variasi header sample Metrica diperbaiki di pembaca CSV; model DFL, rumus fitur inti, dan decoder tidak perlu diganti.

**Keadaan terakhir:** pipeline, diagnosis, dan bundle sudah berjalan serta lolos pengujian teknis. Kecenderungan decoder mengurangi D saat bola hilang sudah didiagnosis, tetapi parameternya belum diubah. Belum ada penilaian kualitas pada pertandingan resmi, dan inferensi resmi tetap merupakan pekerjaan lokal pengguna.
