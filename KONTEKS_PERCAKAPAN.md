# Konteks percakapan dan serah terima proyek MTAH 2027

Dokumen dibuat pada 12 November 2026 untuk agent Codex dan pengembang yang melanjutkan proyek. Ini adalah ringkasan terstruktur dari percakapan, bukan transkrip verbatim. Status di bawah berlaku pada saat serah terima; periksa source dan manifest sebelum menganggapnya masih berlaku.

**Keputusan terbaru dalam dokumen ini mengesampingkan rencana lama yang bertentangan. Instruksi pengguna berikutnya dapat memperbarui keputusan, tetapi jangan menganggap percakapan lama sebagai izin menjalankan semua tahap sekaligus.**

## 1. Mulai dari sini

1. Baca dokumen ini dan `HANDOFF.md` bila berada pada repository handoff.
2. Baca `penjelasan_file.md`, `docs/perbandingan_v1_v2_eksternal.md`, dan `docs/audit_adapter_half_bounds.md`.
3. Baca README dan manifest `external_artifacts/v2/inference-bundle-v2-r1/` tanpa menelusuri direktori data lain.
4. Verifikasi keadaan source, inventaris artifact, provenance, dan mesin eksekusi secara read-only.
5. Laporkan cabang yang layak, penghambat, serta pekerjaan terkecil berikutnya. Jangan langsung membuat detector, fusion, training, menginstal dependensi, atau menjalankan inferensi resmi hanya karena dokumen ini menyebut pekerjaan tersebut.

**Kandidat pengumpulan yang tersedia adalah V2/R dengan revisi adapter 1. V3 belum diimplementasikan atau dilatih dalam rangkaian percakapan ini.**

## 2. Tujuan dan kontrak output

Proyek mengerjakan Initial Challenge More Than a Hack 2027: prediksi possession per frame.

| Label | Arti |
| --- | --- |
| H | Home menguasai bola ketika permainan hidup. |
| A | Away menguasai bola ketika permainan hidup. |
| D | Permainan tidak hidup/dead ball. |
| X | Token abstain/di luar cakupan sesuai kontrak evaluator. Bukan kelas supervised tambahan. |

Untuk output tactical resmi: header `frame,label`, tepat 199.319 baris data, frame 0 sampai 199318 berurutan. Panjang timeline dataset eksternal mengikuti data aktual, tidak dipaksa menjadi panjang pertandingan resmi.

Spell F1 Mean adalah metrik utama. Macro F1, F1 per kelas terutama D, transisi, fragmentasi, durasi, dan latency membantu diagnosis. F1 bukan persentase akurasi. Penggunaan X dan cakupan evaluasi harus mengikuti kontrak evaluator; bola hilang bukan alasan otomatis menghasilkan D atau X.

Target internal pengguna adalah paket siap dikumpulkan maksimal **15 November 2026**. Pengguna menyebut jendela pengumpulan 14–17 November; tanggal internal tersebut bukan verifikasi deadline resmi panitia.

## 3. Aturan panitia dan batas akses agent

Menurut klarifikasi email yang diberikan pengguna, email panitia mengalahkan dokumentasi/email/jawaban lama yang bertentangan.

Yang dilarang untuk pengembangan:

- Memeriksa output terhadap video resmi.
- Membuat atau memakai hand labels/data manual mengenai pertandingan resmi.
- Mengunggah data resmi ke layanan AI.
- Training, fitting, calibration, tuning, pemilihan fitur/model/threshold/aturan menggunakan GT possession atau video resmi.
- Self-training, pseudo-label training, self-supervised fitting, atau kalibrasi berbasis pertandingan resmi dengan mengandalkan izin dokumentasi lama.
- Menggunakan skor publik resmi untuk memilih kandidat atau membuka kembali tuning.

Video, automatic tracking, homography, Smart Tagging, dan generated data resmi dapat menjadi input algoritma yang sudah ditetapkan secara sah. Ini tidak mengizinkan fitting komponen visual pada video resmi.

**Batas agent pada proyek ini lebih ketat:** jangan membuka atau memproses video, frame, screenshot, klip, ATD TXT/XML, homography, Smart Tagging, GT publik/private, cache, prediksi, overlay, atau ekspor per-frame pertandingan resmi. Jangan meminta pengguna mengunggah file tersebut. Inferensi resmi dijalankan operator sendiri secara lokal setelah pipeline dibekukan.

Lokasi yang pernah dinyatakan berisi data/hasil resmi mencakup:

- `external_artifacts/inference-bundle-v1/tactical/`
- `external_artifacts/inference-bundle-v2/tactical/`
- `local_official_artifacts/`
- `evaluation/gt/` dan keluaran evaluasi resmi.

Daftar ini bukan daftar lengkap. Nama direktori baru tidak membuktikan provenance eksternal. Jangan membaca seluruh `data/` atau `external_artifacts/` secara rekursif. Tentukan asal file sebelum membukanya.

Source, dokumentasi publik, konfigurasi, fixture sintetis, ringkasan agregat yang diberikan pengguna, serta dataset eksternal yang sumbernya jelas boleh digunakan. Audit efek samping import, notebook, test, dan `--help` sebelum menjalankannya. Hasil resmi agregat pernah diberikan pengguna untuk diagnosis; tidak digunakan dalam dokumen ini sebagai dasar pemilihan V3.

## 4. Riwayat baseline dan pembagian data

Proyek fresh dibuat untuk menghindari pemindahan otomatis parameter/keputusan dari proyek lama yang provenance-nya belum jelas. Fresh repository sendiri tidak membuktikan semua keputusan bebas pengaruh eksperimen sebelumnya.

Urutan historis:

1. Parser DFL, pemisahan observasi/target, fitur, classifier HGB, evaluator, dan decoder temporal dibangun melalui data eksternal.
2. J03WPY ditambahkan untuk training, J03WQQ untuk validation/development. Parser dan integritas datanya divalidasi.
3. Baseline expanded A menggunakan J03WOH dan J03WPY, kedua babak.
4. Metrica sample Game 1/2 digunakan untuk kompatibilitas observasi. Tidak ada klaim F1 possession tanpa target padat independen.
5. V2 membandingkan kandidat decoder dan fitur konteks pada data eksternal. R dipilih; C sendiri dan kandidat decoder B tidak menjadi rilis.
6. Revisi adapter 1 memperbaiki sumber batas babak secara terpisah, tanpa mengubah model/fitur/router/parameter decoder.
7. V3 baru sampai audit kelayakan dan revisi rencana.

| Pertandingan | Peran yang harus dinyatakan |
| --- | --- |
| J03WOH + J03WPY | Training classifier/augmentasi dan estimasi prior/transisi, kedua babak. |
| J03WQQ | Development antarpertandingan yang sudah dipakai ulang; bukan untouched test. |
| J03WMX | Penilaian tambahan setelah R dibekukan; riwayat pemakaian proyek lama belum terverifikasi. |
| J03WOY/J03WR9 | Sudah pernah digunakan dalam rangkaian proyek. Jangan menyebutnya untouched lagi. |
| J03WN1 | Tidak ditemukan pada lokasi unduhan lokal yang diperiksa saat audit; riwayat lama belum diketahui. Ketiadaan file bukan bukti belum pernah digunakan. |

Rencana awal pembagian babak pertama/dua pada satu pertandingan sudah berkembang menjadi pembagian pertandingan di atas. Jangan menghidupkan kembali split awal sebagai deskripsi eksperimen R.

Tidak ada random split frame berdekatan atau GroupKFold dengan grup palsu. Semua preprocessing yang fit, prior/transisi, parameter detector, association, confidence, toleransi garis, dan fusion harus berasal dari data eksternal yang perannya dinyatakan.

## 5. Model V2 yang benar dan bukti hasilnya

**[High confidence]** Berdasarkan source, manifest, dan laporan eksternal yang diaudit:

- A adalah expanded HGB dengan 14 fitur; A inilah pembanding V1 pada laporan, bukan model sebelum penambahan J03WPY.
- C adalah HGB dengan 18 fitur. Empat tambahan: coverage bola, umur observasi bola, dan median jarak Home/Away pada jendela temporal pendek.
- R adalah `coverage_router_v1` atas A/C. C dipakai bila jendela bola yang tersedia lengkap dan jumlah observasi lengkap kedua tim memenuhi referensi training 11/11; selain itu A.
- R menerima 18 fitur dengan urutan tetap; A menggunakan proyeksi 14 fitur. Jangan menambahkan kolom visual/tagging ke model beku tersebut.
- R tidak melakukan fitting baru ketika router dipasang. Decoder rilis tetap decoder A dengan prior/transisi training.
- Slot/record bukan identitas pemain permanen atau jumlah pemain unik. Tidak ada kecepatan antarslot anonim.
- Missing tetap missing; tidak diisi jarak nol, tidak clipping bola outside, dan fitur temporal tidak menyambungkan babak/gap.

Sumber utama: `external_baseline/observation_router.py`, `features.py`, `multimatch.py`, `temporal.py`, `atd_inference.py`, `v2_refinement.py`, dan `docs/perbandingan_v1_v2_eksternal.md`.

Angka tersimpan, **bukan eksperimen baru dalam serah terima**:

| Dataset/kondisi | Spell F1 A | Spell F1 R | Macro F1 A | Macro F1 R |
| --- | ---: | ---: | ---: | ---: |
| J03WQQ bersih | 0,446316 | 0,502508 | 0,863894 | 0,875228 |
| J03WMX bersih | 0,414365 | 0,451830 | 0,886097 | 0,893676 |
| J03WQQ bola dihilangkan acak 20% | 0,086244 | 0,086313 | 0,821504 | 0,821950 |

R lolos 37 gate J03WQQ dan 37 gate penilaian tambahan J03WMX dalam laporan yang tersedia. C sendiri ditolak karena regresi pengaman walaupun Spell bersihnya lebih tinggi. Kelulusan relatif terhadap A tidak menyelesaikan kelemahan absolut pada tracking bola hilang.

**[Medium confidence]** Bukti generalisasi masih terbatas. J03WQQ adalah development berulang; status untouched J03WMX tidak terbukti. Jangan menjanjikan peningkatan pada pertandingan resmi.

## 6. Bundle beku, indeks, dan adapter

Bundle handoff: `external_artifacts/v2/inference-bundle-v2-r1/`.

Identitas artifact:

```text
model SHA-256:
04e2510928af168c7cd1e3d9ebb698591b336f52a2344853dce1fd8acd0fa88f

decoder SHA-256:
2aa5b5f1c777fe9c2c71b7bdb894082b22b967dae5b67664be9b5c7871bafa74
```

**[High confidence]** Pemeriksaan pada 12 November 2026 mencocokkan seluruh 48 file dalam inventaris bundle tanpa mismatch. Ini pemeriksaan hash, bukan pengulangan training, inferensi, atau seluruh suite test. Angka test lama dalam dokumen adalah hasil historis.

Masalah historis `ValueError: invalid half bounds` tidak boleh disederhanakan menjadi “batas babak tidak tersedia”. Audit membedakan asumsi parser dari metadata publik yang benar-benar tersedia.

- `atd_periods.py` menyediakan mode provider yang ketat dan mode eksplisit `organizer-public`.
- Metadata provider tidak diam-diam diubah menjadi satu rekaman jika tidak menggambarkan dua babak yang sah.
- Scope publik berasal dari source `games.py:half_video_blocks`, bukan GT atau penandaan video.
- Raw ATD 1-based; video/submission 0-based. Konversi raw ID = video frame + 1. Endpoint scope publik inklusif.
- Babak dipisahkan untuk ekstraksi fitur dan pemanggilan decoder; di luar scope menghasilkan X sesuai kontrak.
- Pengguna memilih mempertahankan pemisahan babak, bukan fallback satu rekaman.

Jangan mengubah bundle beku di tempat. Gunakan packaging resmi dan checksum, termasuk verifikasi source yang dievaluasi. Revisi parser terpisah tidak boleh mengubah model, schema fitur, threshold router, atau parameter decoder tanpa eksperimen baru.

## 7. Audit sumber eksternal V3

Status berikut berdasarkan dokumentasi/katalog publik yang dilihat pada 11–12 November 2026. Belum ada unduhan besar pada tahap V3. Periksa ulang akses dan revisi sebelum akuisisi.

### DFL/Sportec

- **[High confidence]** Katalog Figshare versi 1 berisi 21 XML: metadata, posisi, dan event. Tidak ada video atau kalibrasi kamera dalam katalog tersebut.
- Data CC BY 4.0; atribusi Deutsche Fußball Liga dan publikasi Bassek dkk. wajib dicatat.
- Target awal: BallStatus inactive menjadi D; active dengan possession Home/Away menjadi H/A. Ambigu/tidak tersedia memakai valid mask, bukan carry-forward atau otomatis D.
- BallStatus/BallPossession dan turunannya tidak masuk observasi.
- DFL events bukan Smart Tagging Metrica.

Sumber primer:

- https://github.com/spoho-datascience/idsse-data
- https://doi.org/10.6084/m9.figshare.28196177
- https://www.nature.com/articles/s41597-025-04505-y

### Metrica sample-data

- **[High confidence]** Versi proyek dipasang ke commit `e706dd506b360d69d9d123d5b8026e7294b13996`.
- README menyatakan tracking dan event tersinkron, koordinat normalized, lapangan 105 × 68 m.
- **[Medium confidence]** README meminta penggunaan bertanggung jawab dan atribusi; izin kompetisi/redistribusi yang lebih lengkap belum terverifikasi. Jangan menyebut lisensinya CC BY atau MIT tanpa bukti.
- Video pasangan, homography, tagging otomatis sebanding, dan target possession padat belum terverifikasi. Event tidak otomatis menjadi GT H/A/D.

Sumber primer: https://github.com/metrica-sports/sample-data/tree/e706dd506b360d69d9d123d5b8026e7294b13996

### SoccerTrack v2

- **[High confidence]** Dataset card menyebut rilis v1.2, dengan revisi README yang terlihat `325bd4c57ee8e135ab652f3921d274526ada496b`. Akses revisi/isi berkas belum sepenuhnya terverifikasi.
- Dataset CC BY 4.0; kode MIT. Katalog menampilkan video, GSR, BAS, bola, raw calibration, dan MOT.
- Halaman host menyatakan gated: daftar terlihat, akses isi belum tersedia untuk sesi audit.
- Lintasan bola adalah rekonstruksi yang ditambatkan ke event dan diinterpolasi; sebagian match mengalami clipping ke lapangan. Bukan GT independen untuk out/restart atau observasi bola per frame.
- **[Medium confidence]** Kontrak aktual perlu dicek: dokumen GSR memperingatkan perbedaan schema spesifikasi versus berkas yang dirilis. Basis waktu BAS pada dataset card/dokumen format belum konsisten.
- Kalibrasi panoramik mencakup distorsi; jangan menganggap satu homography langsung berlaku pada gambar mentah.
- Kandidat pengujian geometri, bukan sumber siap pakai untuk pembuktian Spell F1.

Sumber primer:

- https://huggingface.co/datasets/atomscott/soccertrack-v2/blob/main/README.md
- https://huggingface.co/datasets/atomscott/soccertrack-v2/tree/main
- https://github.com/AtomScott/SoccerTrack-v2/blob/main/LICENSE-DATA
- https://raw.githubusercontent.com/AtomScott/SoccerTrack-v2/main/docs/format-gsr.md
- https://raw.githubusercontent.com/AtomScott/SoccerTrack-v2/main/docs/format-bas.md
- https://raw.githubusercontent.com/AtomScott/SoccerTrack-v2/main/docs/calibration.md

### Metrica SAMPLEGAME4 dan sumber lain

- **[Medium confidence]** Pengumuman 14 Oktober 2022 menawarkan sample Automatic Tagging melalui account/aplikasi. Versi paket, checksum, inventaris ekspor, hak penggunaan/redistribusi, akses sekarang, dan target independen belum terverifikasi.
- https://www.metrica-sports.com/blog/automatic-tagging-detect-patterns-that-occur-in-the-game
- SoccerNet GSR berfokus pada individu/posisi/identitas. Belum memenuhi bukti kebutuhan bola dan possession; lisensi kode tidak dianggap lisensi video. Belum diprioritaskan: https://www.soccer-net.org/tasks/game-state-reconstruction dan https://www.soccer-net.org/data
- Alfheim pernah ditelusuri lewat publikasi yang menyebut anotasi possession, tetapi ketersediaan file anotasi, kelengkapan input, dan lisensi belum terverifikasi; situs dataset gagal diakses saat audit. Bukan sumber terpilih: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251970

Belum ada bobot pretrained visual yang dipilih. Sebelum memilih, catat URL penerbit, versi, hash bobot, lisensi kode/bobot, asal/domain training yang diketahui, dan kebutuhan runtime. Jangan mengarang kemampuan model atau menganggap lisensi library mencakup semua bobot.

## 8. Keputusan terbaru mengenai lingkup V3

| Cabang | Yang dapat dimulai | Status produksi |
| --- | --- | --- |
| V2/ATD | Audit artifact, provenance, fallback, kesiapan pengumpulan. | Sudah tersedia, pertahankan. |
| Aturan IFAB dari ATD | Audit keteramatan aturan dan kebutuhan bukti. | Belum layak hanya dari koordinat planar untuk seluruh out/referee-stop/restart. |
| Homography | Audit akses, versi, schema, distorsi, arah transformasi. | Terblokir akses dan kontrak aktual. |
| Video/bola | Audit sumber bobot, anotasi independen, dan mesin tujuan. | Terblokir kelayakan data/model/runtime. |
| Smart Tagging | Audit ekspor SAMPLEGAME4 dan hak penggunaan. | Terblokir berkas sebanding dan target independen. |
| Fusion | Tidak perlu implementasi sekarang. | Menunggu cabang dengan bukti yang dapat dievaluasi. |

**Koreksi penting:** rencana awal membuat tiga modul V3 sebelum sumber layak sudah dibatalkan. Jangan membuat scaffolding nonaktif atau framework baru untuk cabang terblokir. Tidak ada detector pemain penuh, viewer, dashboard, atau seluruh kombinasi modalitas sekaligus.

Arsitektur konseptual bila kelak layak: observasi → penyelarasan waktu/koordinat → fitur/bukti dengan provenance/confidence/validitas → fusion → decoder per babak/gap → output. Ini bukan instruksi untuk langsung membangunnya.

Homography adalah transformasi, bukan observasi baru. Smart Tagging dapat salah: phase bukan possession, team tag bukan otomatis H/A, set-piece bukan interval D, dan waktunya bukan restart presisi. Pertahankan unknown dan konflik. Loader starter memiliki asumsi last-value-wins untuk tag berulang dan pemeriksaan anchor kickoff; jangan mewarisinya sebagai kalibrasi pada data resmi.

Video diprioritaskan untuk menambah observasi bola. Non-detection bukan D; bola bergerak bukan bukti restart sah. Camera cuts, replay, oklusi, bola kecil, bola dipegang, dan airborne perlu ketidakpastian eksplisit.

## 9. IFAB dan batas penalaran aturan

Sumber primer yang diperiksa menampilkan 2026/27. Edisi aturan harus mengikuti pertandingan rekaman, bukan tahun nama challenge. Aturan yang bergantung edisi dinonaktifkan jika edisinya belum diketahui.

Aturan terbatas yang direncanakan untuk diaudit:

- Seluruh bola melewati garis: perlu konvensi garis, radius bola, posisi dan ketidakpastian; pusat sedikit outside tidak cukup. Proyeksi planar bola airborne tidak membuktikan crossing.
- Penghentian wasit: dugaan foul atau posisi bola tidak membuktikan wasit sudah menghentikan permainan.
- Goal kick: jenis restart dan bukti tendangan/pergerakan sesuai edisi; jangan memakai syarat harus keluar penalty area untuk edisi modern.
- Kick-off, throw-in, dan dropped ball berbeda syaratnya. Tidak ada satu aturan gerak untuk semua restart.

Pisahkan status live/dead, tim yang menguasai ketika live, dan X evaluator. IFAB tidak menggantikan definisi possession kompetisi. Bukti tak cukup menghasilkan unknown pada lapisan bukti, bukan label paksa. Default konsep adalah soft evidence; belum ada bobot fusion yang dipilih.

Sumber: https://www.theifab.com/laws-of-the-game-documents/ ; https://www.theifab.com/laws/latest/the-ball-in-and-out-of-play/ ; https://www.theifab.com/laws/latest/the-goal-kick/ ; https://www.theifab.com/laws/latest/the-start-and-restart-of-play/

## 10. Evaluasi dan gate: revisi terakhir

### A. Kelayakan sumber sebelum kode produksi

Wajib ada akses sah, versi/inventaris, kontrak waktu/koordinat/babak/missing, target independen sesuai evaluasi, split/riwayat pemakaian, serta mesin eksekusi teridentifikasi. Gagal salah satu: lanjut audit saja, tanpa modul produksi cabang tersebut.

Label lemah yang dibuat dari event/heuristik sendiri tidak membuktikan aturan pembuatnya benar.

### B. Evaluasi komponen, bukan possession

- Bola: precision/recall, error lokasi, coverage, false association, kondisi oklusi/airborne.
- Geometri: error terhadap titik kontrol eksternal yang tidak dipakai fitting; laporkan median dan p95. Round-trip hanya konsistensi numerik, bukan akurasi dunia nyata.
- Tagging: precision/recall kejadian dan error waktu terhadap anotasi independen.
- Aturan: fixture menguji logika kode; kejadian eksternal independen menguji validitas empiris.

Gate numerik komponen **belum ditetapkan** karena sumber/schema/resolusi/anotasi belum layak. Bekukan protokol dan gate sebelum hasil kandidat dilihat. Lolos evaluasi komponen tidak berarti Spell F1 meningkat dan tidak cukup untuk promosi rilis possession.

### C. Evaluasi possession per cabang

Berikut adalah gate usulan terakhir untuk eksperimen mendatang, bukan gate historis pemilihan R. Protokol lengkap harus dibekukan sebelum scoring.

| Cabang | Evaluasi relevan | Gate manfaat yang diusulkan |
| --- | --- | --- |
| Aturan berbasis ATD | DFL development dengan observasi aturan yang memang tersedia. | Spell F1 Mean ≥ R + 0,01. Tidak wajib memperbaiki missing bila tidak mempunyai bukti pada missing. |
| Tagging | Tagging otomatis eksternal yang sebanding + target possession independen. | Spell F1 Mean ≥ R + 0,01 pada development berurutan. |
| Video + geometri | Video/kalibrasi, input ATD atau padanan kompatibel, dan target possession independen tersinkron. | Pada kondisi kehilangan bola yang ditetapkan sebelumnya, Spell F1 Mean ≥ R + 0,02; kondisi bersih tidak turun lebih dari 0,01. |

Pengaman pada evaluasi relevan: Macro F1, F1 D, transisi @12/@25, dan Spell per babak tidak turun lebih dari 0,01. Penilaian pertandingan tambahan memakai kandidat beku: gate manfaat utama minimal tidak menurun, pengaman tetap berlaku. Laporkan fragmentasi, latency, coverage, dan hasil negatif.

**DFL untuk video/tagging:** jika input tambahan tidak ada, fallback harus identik dengan V2. Jangan mewajibkan peningkatan DFL dari modalitas yang tidak tersedia. Manfaat multimodal hanya dinilai pada sumber eksternal dengan observasi dan target independen yang sesuai.

Alasan gate: kenaikan minimum membatasi kompleksitas tanpa manfaat terukur; pengaman membatasi regresi; gate missing video mengikuti tujuan cabang. Nilai bukan jaminan signifikansi statistik atau kenaikan resmi. Tidak boleh dilonggarkan setelah melihat hasil.

Anggaran: maksimal dua konfigurasi per cabang. Kandidat gabungan hanya dipertimbangkan setelah kontribusi komponennya terukur dan protokol baru dibekukan; tidak langsung semua kombinasi. Jika data hanya cukup untuk komponen, berhenti pada tingkat B.

## 11. Mesin eksekusi, dependensi, dan jadwal

**[High confidence, berdasarkan pernyataan pengguna]** Teman melanjutkan pada mesin lain yang memiliki GPU. **[Low confidence]** Model GPU/VRAM, CPU, RAM, disk, runtime, dan apakah mesin yang sama dipakai untuk eksperimen serta inferensi akhir belum terverifikasi.

Angka i3-10110U/RAM sekitar 3,45 GiB/disk kosong sekitar 5,5 GB berasal dari mesin agent sebelumnya, **bukan anggaran mesin eksekusi tujuan**. Estimasi runtime dan limit penyimpanan yang sebelumnya memakai angka tersebut dicabut untuk mesin tujuan. Tidak ada benchmark throughput visual yang sudah dijalankan.

Pengguna meminta venv, library, model cache, pip cache, dan temporary file berada di drive proyek, bukan memenuhi home. Jangan memasang dependensi otomatis. Pertahankan versi runtime bundle untuk reproduksi, baca requirement dan source sebelum eksekusi, dan jangan menganggap GPU selalu diperlukan untuk V2.

Jadwal internal terakhir yang diusulkan (WIB, periksa waktu aktual sebelum menerapkannya):

- 12 November pukul 12.00: keputusan kelayakan cabang.
- 13 November pukul 18.00: batas kandidat baru yang lengkap dan tervalidasi.
- 14 November: packaging dan verifikasi paket terpilih/cadangan.
- Maksimal 15 November: target pengumpulan internal.

Jika waktu audit sudah melewati suatu batas, nyatakan secara eksplisit dan prioritaskan paket V2. Jangan memaksakan V3 yang belum tervalidasi atau menganggap pergantian laptop menyelesaikan penghambat target independen.

## 12. Handoff GitHub dan langkah terkecil berikutnya

Repository tujuan pengguna: https://github.com/Naufal-Rasyid-Irfan-Alfadil/mtah-2027

Pengguna menyatakan sudah push dan teman sudah clone. Upload remote tersebut belum diverifikasi ulang oleh agent setelah pernyataan pengguna.

Snapshot terpisah dibuat agar tidak membawa riwayat proyek lama yang memuat jalur data resmi. Snapshot awal berisi 136 file sekitar 3,54 MB: source, tes, dokumentasi, inventaris bundle V2, dan laporan agregat eksternal terpilih. Dataset, hasil resmi per-frame, notebook, cache, dan venv tidak disertakan. Jangan menganggap dataset eksternal terunduh otomatis tersedia di clone. `HANDOFF_MANIFEST.json` mencatat checksum snapshot; verifikasi sebelum memakai artifact.

Pada mesin asal, folder handoff lokal adalah `external_artifacts/github-handoff-20261112/` dengan repository Git terpisah; teman cukup bekerja dari root hasil clone. Jangan menyalin path absolut laptop asal sebagai konfigurasi mesin baru. Menggunakan account Codex yang sama tidak membuat sesi baru otomatis mempunyai seluruh konteks percakapan ini.

**Pekerjaan terkecil berikutnya:** lengkapi register kelayakan sumber dalam dokumentasi yang sudah ada dan verifikasi mesin tujuan secara read-only. Cari bukti akses, schema, sinkronisasi, hak penggunaan, dan target independen. Laporkan cabang yang bisa dimulai/terblokir. Belum ada izin tersirat dari dokumen ini untuk download besar, detector/fusion, training, atau inferensi resmi.

V2 tetap dipakai apabila kelayakan sumber, protokol, hasil eksternal, runtime, atau waktu tidak memenuhi persyaratan. Jangan menjanjikan peningkatan skor.

## 13. Pembaruan implementasi 12 November 2026 pukul 19.59 WIB

Pengguna menyetujui implementasi rencana audit. Kandidat tetap V2/R adapter r1.
Lihat `docs/kesiapan_pengumpulan_20261112.md` untuk register sumber, mesin aktual,
command operator, dan batas bukti. Jangan memakai spesifikasi laptop lama.

Working tree Windows mengonversi CRLF/LF: 43 dari 48 berkas bundle gagal hash;
107 dari 136 berkas handoff gagal hash. Seluruh blob Git HEAD
`5b0240c2480f482e381cd54970c47fb8c9425270` cocok dengan manifest asli. Salinan baru
di `external_artifacts/release-readiness-20261112/source/` memulihkan byte blob
tanpa mengubah artifact/manifest lama. `.gitattributes` mencegah konversi pada
checkout berikutnya; bukan izin mengabaikan hash working tree lama.

Venv `runtime/v2-r1-venv/` terpasang sesuai delapan versi manifest, termasuk
python-dateutil 4.0.0 dan tzdata 2026.6 yang berbeda dari interpreter global.
Verifier runtime dan pip check lulus. Seluruh 26 tes sintetis lulus. Model R
beku diperiksa pada delapan frame buatan; posterior missing identik A.
ZIP `external_artifacts/release-readiness-20261112/validation-final/inference-bundle-v2-r1.zip`
lolos pemeriksaan 49 anggota dan verifier setelah dipindahkan. Report dan log
berada pada direktori yang sama. Ini bukan inferensi atau scoring resmi.

Dataset DFL lokal belum terbukti tersedia; fallback DFL nyata belum diuji.
Video/tagging/homography produksi dan fusion tetap menunggu kelayakan data,
akses payload, sinkronisasi dan target independen. Tidak dibuat modul V3.
Target internal maksimal 15 November tetap berlaku; hanya operator melakukan
inferensi resmi setelah pembekuan, tanpa mengirim input/output resmi ke agent.

## 14. Prioritas V3 setelah pukul 20.17 WIB, 12 November 2026

Pengguna meminta melanjutkan V3, lalu memilih video/geometri dengan penyelesaian
akses SoccerTrack dan target independen terlebih dahulu. Pengguna sudah membuat
akun Hugging Face; persetujuan gated dataset dan akses payload belum terbukti.
DFL tidak dipilih sebagai cabang pengembangan utama pada tahap ini.

Audit API primer mengonfirmasi DFL v1 berisi 21 XML dan SoccerTrack v1.2 menunjuk
commit 325bd4c57ee8e135ab652f3921d274526ada496b dengan gated=auto. Dua XML
matchinformation eksternal DFL (WOH/WQQ), total 23.677 byte, cocok MD5 penerbit
dan lolos parser metadata beku; posisi/video/target per-frame tidak diunduh.
Katalog SoccerTrack dapat dibaca, tetapi CHANGES_v1_2.md masih HTTP 401.

Instruksi akuisisi awal pengguna: delapan file audit kecil dari rilis SoccerTrack
yang dipin, match training 117092, total 487.760 byte. Daftar, URL primer,
ukuran dan batas checksum ada di docs/soccertrack_v1_2_audit_download.json.
Rincian gate di docs/kelayakan_v3_20261112.md. Tidak ada modul produksi V3 atau
klaim target possession independen yang sudah tersedia. V2 tetap beku.

## 15. Paket SoccerTrack pengguna diperiksa, 12 November 2026

Pengguna menaruh delapan berkas yang diminta di `Soccertrack V2/`. Audit
allowlist menemukan seluruh berkas: enam non-LFS cocok persis Git blob rilis
yang dipin; dua NumPy cocok ukuran, SHA-256 penerbit LFS masih menunggu.
Rincian dan batas kesimpulan ada di docs/audit_soccertrack_117092.md; report JSON
di external_artifacts/v3/soccertrack-117092-package-audit-20261112/.

Schema aktual BAS adalah actions, 2.085 event uppercase, frame 1-based.
Seluruh event cocok secara internal dengan waktu relatif babak (maks 20 ms),
tetapi alignment video belum diuji. Keypoints memakai koordinat sudut 0..105,
0..68; bukan koordinat GSR tengah lapangan. Kalibrasi memakai fisheye; NPZ
memuat dua object-array yang tidak di-unpickle. Raw XML provider/padding bukan
scope rilis BAS. Changelog v1.2 yang terverifikasi mengesampingkan dokumentasi
main lama yang bertentangan mengenai schema/waktu/dimensi.

Tidak ada target possession padat independen yang ditemukan. Keypoints
penerbit adalah titik fitting, bukan holdout geometri. Tidak ada modul produksi
dibuat. Berikutnya: cocokkan dua SHA-256 payload LFS penerbit, lalu selesaikan
kontrak dan target geometri independen sebelum akuisisi video besar/implementasi.

## 16. Checksum LFS SoccerTrack dikonfirmasi pengguna

Pada 12 November 2026 sekitar 20.43 WIB pengguna menyalin kedua SHA-256 dari
Git LFS Details: intrinsics 4f6db409ac8f5b36b62898ac279247add16cc1ff905583440ac71f45c6a167fb,
homography 26dcb723a362e9be1acad852313e9f55565d49260a2a68f6e39481e4e0bf2cc3.
Keduanya cocok berkas lokal yang diperiksa ulang. Provenance dicatat eksplisit
sebagai transkripsi pengguna dari penerbit, bukan fetch mandiri agent.
Seluruh delapan berkas kini lolos integritas. Report r2 terpisah dari report awal.

Langkah akuisisi berikutnya dipersempit ke satu video training 117092 babak
pertama, 6.687.957.167 byte, pada commit dataset yang sama. Manifest download
ada di docs/soccertrack_v1_2_video_download.json; SHA-256 video penerbit juga
harus dicatat pengguna. Tidak meminta seluruh dataset, GSR, babak kedua atau
bobot detector. Integritas payload tidak meluluskan geometri atau possession;
target independen dan kontrak proyeksi tetap harus diselesaikan. V2 tidak berubah.

## 17. Video SoccerTrack eksternal sudah diperiksa

Pengguna mengunduh 117092 babak pertama dan menyalin hash penerbit
9fabe074b0c6fc5812a602dd4119f3e6cb724e2f06b8a3a1eb9358b9734c036e.
Hash/ukuran lokal cocok. Audit pada 12 November sekitar 21.01 WIB menemukan
container 25 fps, 67.375 frame, 3840×1906; decode tiga sampel 0/30000/67374
berhasil. Ini bukan decode seluruh video atau verifikasi empiris BAS.

Runtime audit baru terpisah runtime/v3-geometry-venv (NumPy 2.4.6,
opencv-python-headless 4.10.0.84); V2 tidak diubah. Diagnosis rantai tetap
H/Knew/fisheye OpenCV mereproduksi residual fit-point median 70,47 px dan p95
331,27 px dengan pergeseran sisi dekat kamera. Tidak refit, tidak memilih
transformasi alternatif, tidak membuat detector/fusion. Target geometri dan
possession independen tetap belum tersedia.

Laporan docs/audit_video_soccertrack_117092.md; report/preview eksternal pada
external_artifacts/v3/soccertrack-video-audit-20261112-r2/. Langkah terkecil
berikutnya adalah audit provenance kontrak H/Knew dan referensi geometri baru
yang tidak dipakai fitting, bukan unduhan GSR/bobot/dataset lain. Semua batas
akses resmi dan target internal pengumpulan maksimal 15 November tetap berlaku.

## 18. Audit kontrak H/Knew selesai, 12 November sekitar 21.16 WIB

Pengguna menyetujui penelusuran penyebab geometri. Knew tersimpan sama persis
dengan operasi deterministik K/D, ukuran 3840×1906, balance=1. Pose tersimpan
mereproduksi RMS penerbit 30,63214 px. Literal tiga float rvec/tvec dibaca statis
dengan pickletools dari archive yang hash-nya cocok; tidak mengeksekusi pickle.

H plane diturunkan secara aljabar dari pose yang sama, tanpa fitting. Direct
pose dan H turunan sama hingga 6,37e-12 px. H rilis berbeda; dua rantai berbeda
median 68,82 px dan p95 330,01 px pada keypoints. Source menunjukkan H dihitung
terpisah dari calibrated keypoints; log generating run dan inlier mask rilis
belum tersedia. Jangan menyimpulkan stale H atau file rusak sebagai fakta.
Tidak mengganti artifact atau memilih kandidat berdasarkan residual fitting.

Laporan docs/audit_kontrak_geometri_117092.md; report final pada
external_artifacts/v3/geometry-contract-audit-20261112-r2/. Tiga tes sintetis
audit aljabar/literal lulus. Paket reference-task berisi PNG raw baru pada frame
7500/37500/60000 dan 54 slot CSV kosong, nol anotasi valid. Protokol konstruksi
di docs/protokol_referensi_geometri_117092.md. Referensi masih perlu anotasi/
review dengan provenance; bukan GT otomatis atau untouched cross-match test.
Tidak ada detector/fusion produksi, fitting baru, atau evaluasi possession.

## 19. Tiga anotasi operator diperiksa, 12 November sekitar 22.02 WIB

Pengguna mengonfirmasi frame 7500 dan memberikan near_touchline_y68:
kiri (1427,1442), tengah (2055,1442), kanan (3224,1167). Semuanya lebih dari
20 px dari fit points. Pengguna menyatakan belum melihat overlay prediksi;
dicatat sebagai self-report. Garis jauh tidak terlihat jelas: tiga slot
ambiguous, koordinat kosong. 48 slot lain tetap belum ditinjau.

CSV aktif dan log operator berada dalam reference-task dari audit kontrak r2.
Validator tools/validate_geometry_annotations.py lulus pada input aktual dan
menolak tujuh kasus negatif. Crop raw ditinjau secara kualitatif: ketiga titik
konsisten dengan garis; koordinat tidak diubah. Reviewer assistant sudah pernah
melihat diagnosis model, dicatat eksplisit. Belum ada repeatability, uncertainty,
gate akurasi numerik, atau scoring kandidat pada titik baru. Report pada
external_artifacts/v3/operator-annotation-review-20261112/.

Tiga titik/satu fitur/satu frame belum meluluskan geometri seluruh lapangan.
Target possession padat independen tetap belum tersedia. Tidak ada detector,
fusion, fitting ulang atau kandidat produksi V3. V2/R tetap kandidat pengumpulan;
pekerjaan selanjutnya bergantung pada referensi eksternal yang memadai.

## 20. Pengguna memilih kamera 117093 sebagai pengganti

Pada 12 November 2026 sekitar 22.10 WIB pengguna meminta beralih dari 117092
ke 117093 karena gambar menurut pengguna lebih jelas. Kejelasan 117093 belum
diverifikasi pada payload lokal. Pemeriksaan folder Soccertrack V2/raw dan
videos hanya menemukan 117092 saat keputusan dicatat.

Pertahankan seluruh artifact dan anotasi 117092 sebagai riwayat. Jangan
memindahkan koordinat, kalibrasi, padding, frame count atau hasil auditnya ke
117093. Fokus akuisisi dan referensi baru kini 117093. Manifest eksplisit
docs/soccertrack_v1_2_117093_download.json memuat tujuh file versi tetap:
lima raw metadata/kalibrasi, BAS, dan satu video babak pertama 3.346.094.631 byte.
Paket selain video berjumlah 499.334 byte. README/CHANGES yang telah cocok
checksum dapat dipakai ulang; tidak perlu unduh GSR/maps/babak kedua/bobot.

Dataset card menempatkan 117093 pada publisher split validation. Karena proyek
memilihnya untuk inspeksi/pengembangan geometri, nyatakan local role external
geometry development; jangan menyebutnya untouched test setelah dipakai.
Changelog menyebut 67.625 frame babak pertama pada 25 fps dan stream start
1 detik; gunakan decoded frame indexing dan verifikasi stream aktual sebelum
menetapkan kontrak, bukan menyalin offset 117092. Payload/hash lokal 117093
belum tersedia. Minta SHA-256 LFS video, intrinsics dan H sekaligus dari commit
yang dipin. Semua gate geometri/possession dan batas akses resmi tetap berlaku;
V2/R tetap kandidat pengumpulan.

## 21. Inventory 117093 tersedia, 13 November 2026 pukul 18.18 WIB

Pengguna menyatakan sudah mengunduh 117093 dan meminta pemeriksaan kelengkapan.
Ketujuh path eksplisit manifest ditemukan di Soccertrack V2; seluruh ukuran
cocok, tanpa file hilang atau mismatch yang diketahui. Empat berkas non-LFS
cocok persis Git blob penerbit. README dan CHANGES v1.2 yang digunakan ulang
juga tetap cocok. Tiga payload LFS (intrinsics, H, video) telah dihitung SHA-256
lokalnya, tetapi hash primer dari pengguna/penerbit belum diterima. Karena itu
kelengkapan lolos, integritas penuh penerbit belum dinyatakan lolos.

Report external_artifacts/v3/117093-inventory-20261113/report.json merekam
ukuran, SHA-256 lokal, URL versi tetap, status checksum dan peran data. Video
belum didekode dan geometri 117093 belum dievaluasi pada tahap ini. Tidak ada
file 117092 dipindahkan atau dipakai sebagai kalibrasi/referensi 117093.

Cutoff kandidat baru 13 November 18.00 WIB telah terlewati. Audit inventory
tidak mempromosikan V3 atau mengubah gate; V2/R tetap prioritas pengumpulan
internal maksimal 15 November. Berikutnya cukup cocokkan tiga SHA-256 LFS
penerbit dari commit yang sama sebelum pemeriksaan payload lanjutan.

## 22. Integritas dan kamera 117093 diperiksa, 13 November 18.22 WIB

Pengguna menyalin ketiga SHA-256 LFS; video f50dfebc70743439a8c778abe06953885a50be8b47e3c9d3d1ce8d533fe315c8,
intrinsics fe3f14a96495aa6706e6bf716490d599e0818ed0a48e7bf8e4387e7fe985c720,
H deb667816e2b0a98c536cf65d08d03d0c5d300cc0027425eb1bcee8f0e0426f7.
Semua cocok pada pemeriksaan ulang, dan empat Git blob biasa juga cocok.
Bukti checksum penerbit dicatat sebagai transkripsi operator, bukan fetch agent.

Video 4096×1080, 25 fps, 67.625 frame menurut container; empat sampel berhasil
didekode. Sampel 7500 terang dengan garis lapangan lebih mudah terlihat.
Knew cocok perhitungan ulang; RMS pose 8,63734 px direproduksi. Residual pada
titik fitting: direct pose median/p95 8,16/13,03 px; H rilis 6,39/29,98 px.
Ini diagnosis fitting, bukan evaluasi independen atau pemilihan produksi.

Report external_artifacts/v3/117093-camera-audit-20261113/report.json;
laporan docs/audit_soccertrack_117093.md. Paket referensi baru pada
external_artifacts/v3/117093-reference-task-20261113/ memuat PNG raw baru,
manifest dan 54 slot kosong; nol label 117092 dipindahkan. Protokol baru
docs/protokol_referensi_geometri_117093.md. Validator diikat ke match/revision
manifest task agar keypoints antarpertandingan tidak tercampur.

Cutoff kandidat baru 13 November 18.00 sudah lewat. Semua ini tetap audit
komponen, tidak melonggarkan gate atau mempromosikan V3. Target possession
independen belum tersedia; V2/R r1 tetap prioritas pengumpulan dan verifier
runtime-nya lulus. Tidak ada inferensi/fitting/data resmi yang diproses.

## 23. Koordinat referensi frame 7500 pada 117093 telah terisi

Pada 13 November sekitar 18.58 WIB pengguna menyelesaikan 18 koordinat untuk
enam fitur pada frame 7500. Seluruhnya dicatat sebagai pengukuran operator dari
PNG raw; source PNG tetap cocok checksum dan semua jarak dari keypoints fitting
117093 minimal 20 piksel. Anotasi lama 117092 tidak dipakai ulang.

CSV, log pengukuran append-only, backup dan progress berada di
external_artifacts/v3/117093-reference-task-20261113/. Tiga koordinat awal garis
dekat sudah memiliki self-report operator belum melihat overlay. Self-report
untuk keseluruhan sesi 18 titik masih menunggu; 15 kolom exposure sengaja belum
diisi otomatis. Tidak menganggap ini blind review yang dibuktikan mandiri.

Tiga titik terakhir right_penalty_edge_x88.5 adalah (2970,275), (3095,320),
(3268,384). Crop raw ditinjau kualitatif: titik konsisten dengan garis yang
terlihat, meskipun area dekat pemain dan busur penalti. Reviewer assistant
telah melihat diagnosis model, dicatat eksplisit. Koordinat tidak diubah.
Review pada external_artifacts/v3/117093-right-penalty-review-20261113/.

18 koordinat terisi bukan kelulusan geometri: repeatability/uncertainty,
ambang numerik sebelum scoring dan target possession independen masih belum
tersedia. Frame 37500/60000 belum diisi. Jangan scoring/promosi atau membuat
detector/fusion produksi berdasarkan jumlah titik saja. V2 tetap kandidat.

## 24. Self-report dan review frame 7500 pada 117093 lengkap

Pengguna mengonfirmasi belum melihat overlay prediksi sepanjang pengukuran
18 titik frame 7500. Seluruh kolom exposure untuk frame itu kini false dengan
provenance self-report, bukan verifikasi blind mandiri. Preflight lengkap lulus:
18 koordinat pada enam fitur, checksum PNG cocok, bounds/provenance/fit-point
separation lolos. CSV asli dan backup tetap disimpan, tidak refit atau scoring.

Crop raw seluruh 18 titik ditinjau kualitatif, konsisten dengan fitur garis
yang dinamai. Reviewer assistant telah melihat diagnosis model; dicatat tanpa
mengklaim review blind. Koordinat operator tidak disesuaikan; uncertainty dan
repeatability belum dikuantifikasi. Review/contact sheet pada
external_artifacts/v3/117093-frame-7500-annotation-review/.
Task preflight-frame-7500-complete.json dan annotation-progress.json mencatat
status terbaru. Frame 37500 dan 60000 masih kosong (36 slot); ambang numerik
geometri dan target possession independen belum tersedia, sehingga scoring/
produksi V3 tetap belum lolos. V2 tidak berubah.

## 25. Frame 37500 pada 117093 selesai dicatat

Pengguna memberikan 18 koordinat baru pada enam fitur frame 37500 dan
mengonfirmasi belum melihat overlay prediksi selama pengukuran frame itu.
Kolom exposure diisi false berdasarkan self-report; tidak diklaim verifikasi
blind mandiri. Semua pengukuran tersimpan sesuai angka operator, tidak disalin
dari frame 7500, tidak dipakai fitting/scoring. Jarak dari fit points minimal
20 px dan checksum PNG referensi tetap cocok.

Preflight task lulus untuk 36 titik (frame 7500 dan 37500); frame 60000 masih
18 slot kosong. Report task preflight-frames-7500-37500-complete.json dan
annotation-progress.json mencatat keadaan terbaru. Review visual seluruh
frame kedua, uncertainty, dan ambang numerik sebelum scoring masih diperlukan.
Tidak ada kandidat produksi V3 atau klaim kenaikan possession; V2 tetap beku.

## 26. Referensi 117093 lengkap dan snapshot dibekukan

Pengguna menyelesaikan 18 koordinat frame 60000 lalu menjawab "tidak" untuk
paparan overlay prediksi sepanjang sesi frame tersebut. Total 54 koordinat
pada frame 7500/37500/60000 memiliki provenance exposure self-report lengkap;
ini bukan verifikasi blinding mandiri. Backup sebelum konfirmasi dan jurnal
append-only tetap disimpan pada task asal.

Preflight seluruh 54 titik lulus: checksum tiga PNG, identitas match/revision,
bounds, metadata operator, used_for_fitting=false, dan pemisahan lokasi minimum
20 px dari keypoints fitting penerbit. Crop seluruh titik pada dua frame akhir
ditinjau dan tampak konsisten dengan fitur garis; koordinat tidak diubah.
Reviewer assistant telah melihat diagnosis model. Ketepatan pusat garis dan
repeatability belum dikuantifikasi; tiga waktu tetap satu kamera.

Snapshot external_artifacts/v3/117093-reference-freeze-20261113/ menyimpan CSV,
tiga PNG raw, jurnal, protokol, provenance, preflight dan review. Seluruh 73
anggota cocok checksum. Manifest SHA256:
f8d2092da58461126ba21bea7d000008a28e358ce49c3566fb1b4e847f12819f.
CSV SHA256: 96f8f9136da08e236e236f5a955e5dc76b6a9ae5aaf1c392d34cdc78d2c4f252.
Report verifikasi berada di direktori v3 dengan akhiran
117093-reference-freeze-20261113-verification.json.

Ini pembekuan referensi, bukan kelulusan atau pemilihan kandidat. Pekerjaan
berikutnya: kuantifikasi ketidakpastian anotasi melalui pengukuran ulang tanpa
overlay, lalu tetapkan anggaran error dan gate sebelum scoring komponen.
Target possession independen tersinkron tetap belum tersedia; geometri tidak
membuktikan kenaikan Spell F1. Tidak ada fitting, scoring kandidat, detector/
fusion produksi atau akses data resmi. V2/R adapter r1 tetap kandidat pengumpulan.

## 27. Pengukuran ulang disiapkan, belum ada hasil kedua

Atas persetujuan pengguna, protokol pengukuran ulang ditetapkan pada
docs/protokol_pengukuran_ulang_117093.md sebelum pengukuran kedua dan scoring.
Paket external_artifacts/v3/117093-repeatability-task-20261113/ memuat 18 crop
raw 256x128: point 2 dari setiap fitur/frame, urutan shuffle seed 117093.
Seluruh 73 hash referensi beku diverifikasi ulang; 18 crop cocok piksel persis
dengan potongan PNG source, tanpa resize. Manifest, guide terpisah, README dan
CSV kosong tersedia. Tidak ada H/pose/prediksi dibaca untuk persiapan.

Operator membaca ulang pusat garis pada irisan tetap: x lokal=128 untuk
touchline/penalty edge; y lokal=64 untuk halfway/lingkaran sisi kanan. Jawaban
sumbu yang diukur ulang tidak ditampilkan. Lokalisasi crop tetap memakai
pengukuran pertama, dan operator sudah pernah melihat gambar/angka pertama;
ini bukan eksperimen blind independen penuh. Reviewer assistant mengetahui
koordinat lama serta diagnosis model, sehingga tidak menggantikan pengukuran
ulang operator dengan perkiraan assistant atau segmentasi otomatis.

Status awaiting_operator_repeat_measurements, kini 3/18 hasil kedua. Pengguna
menjawab R01 x=115; y=64 berasal dari irisan tetap yang diminta. Angka dicatat
di repeats.csv dan operator-repeat-measurements.jsonl, dengan backup sebelum
edit serta R01-coordinate-preflight.json. Hash task/crop/source PNG/snapshot
manifest dan bounds/irisan diperiksa sebelum pencatatan. Kolom exposure sesi
ulang masih kosong menunggu self-report; tidak otomatis dianggap false.
Selisih terhadap jawaban pertama belum dihitung atau ditampilkan saat koleksi.
R02 kemudian dijawab y=37 pada x tetap=128; pencatatan, backup, jurnal dan
preflight terpisah mengikuti prosedur yang sama. Exposure sesi ulang tetap
pending, tidak dianggap false. R03 dijawab x=89 pada y tetap=64; backup,
jurnal dan preflight disimpan. Pengguna meminta daftar seluruh R04-R18 untuk
diukur sekaligus; berikutnya R04, sisa 15 titik. Ikuti measure_axis/fixed_local_axis
pada manifest, koordinat crop raw, bukan full-frame atau guide. Exposure sesi
ulang belum dikonfirmasi. Ambiguous/occluded tetap missing. Referensi pertama
tidak diubah dan selisih terhadap pengukuran pertama belum ditampilkan.

Analisis mendatang: paired signed/absolute displacement pada sumbu pengukuran,
n valid/missing/exposed dan median/p95/maksimum, per fitur/frame dan total.
Jangan menyebutnya error normal kurva, ketelitian absolut, atau CI tail dari
tiga pasangan per fitur. Belum ada angka repeatability maupun toleransi produksi;
anggaran error tetap perlu dasar downstream sebelum scoring. Target possession
independen belum tersedia; V2/R r1 tetap kandidat pengumpulan.

## 28. Seluruh 18 pengukuran ulang dicatat; konfirmasi exposure masih pending

Pengguna mengirim 15 angka berurutan untuk R04-R18:
38, 38, 89, 89, 31, 59, 58, 52, 57, 114, 33, 58, 59, 37, 114.
Angka dipasangkan persis menurut daftar yang diminta; sumbu tetap mengikuti
manifest. R01=(115,64), R02=(128,37), R03=(89,64) tetap dipertahankan.
Total 18/18 koordinat kedua tercatat, semuanya bounds/irisan tetap lolos.
Semua 73 anggota snapshot referensi dan 18 crop kembali cocok checksum.

Backup repeats-before-R04-R18.csv, jurnal operator append-only dan
all-18-coordinate-preflight.json berada di paket repeatability. CSV SHA256:
a36ee55ef0f628420d53f063dff5345e5271d59c02cb835299a10e0030a1285f.
Kolom exposure sesi ulang masih kosong untuk seluruh 18 titik; tanyakan apakah
operator melihat/mengacu pada koordinat pengukuran pertama atau overlay model
selama sesi R01-R18. Jangan menganggap jawaban angka sebagai konfirmasi blind.
collection-status.json kini awaiting_operator_repeat_exposure_confirmation.

Selisih terhadap referensi pertama/statistik repeatability belum dihitung;
belum ada scoring, fitting atau gate numerik baru. Setelah provenance sesi ulang
lengkap, lanjutkan analisis pasangan sesuai protokol yang sudah ditetapkan,
pisahkan exposure jika ada. V2/R r1 tetap kandidat pengumpulan.

## 29. Pengukuran ulang dianalisis setelah self-report exposure lengkap

Pengguna menjawab "tidak keduanya" untuk paparan koordinat pertama/overlay
sepanjang sesi R01-R18. Kedua kolom exposure diisi false pada 18 baris dengan
provenance self-report; backup CSV dan jurnal konfirmasi append-only disimpan.
Tidak mengklaim blinding terverifikasi atau menghapus riwayat operator sudah
pernah melihat/mengukur gambar. CSV repeat setelah konfirmasi SHA256:
ddc8d8884110d53267bab38f39e2ea77101c65c1db24150c2534e155597de63f.

Analisis pasangan sesuai protokol selesai: 18 valid, missing 0, exposed 0
berdasarkan self-report. Selisih absolut median 1 px, p95 2,15 px, maksimum 3 px;
median bertanda 0 px. Garis dekat memiliki median/p95/maksimum 2/2,9/3 px,
halfway 2/2/2 px; ringkasan seluruh fitur/frame ada pada report. Semua ini
selisih sumbu pengukuran berpasangan pada point 2, bukan jarak normal kurva,
akurasi absolut, error meter, noise independen atau interval kepercayaan tail.
Tiga frame tetap satu kamera, tiga pasangan per fitur.

Alat stdlib tools/audit_annotation_repeatability.py hanya memuat referensi
eksternal dan pengukuran ulang yang diikat checksum. Sebelas pemeriksaan input/
statistik lulus (termasuk kasus invalid dan cross-check median/p95). Tidak
membaca H/pose/model, melakukan refit, atau mengubah referensi beku pertama.

Snapshot analisis external_artifacts/v3/117093-repeatability-analysis-20261113/
memuat report.json, salinan input/protokol/jurnal/source alat dan README hasil.
Sembilan anggota cocok checksum. analysis-inputs-manifest.json SHA256:
98225a7499e549675f4d20431f3febb850d90251046d7da20e6dd4868cfd738d.
Report SHA256 d782d4b60b3a2736bf4e3800f2bb2ed12f5d86ad5e1f469aaacb7d895ccfc1fe.
Verifikasi berada di v3/117093-repeatability-analysis-20261113-verification.json.
collection-status.json sekarang descriptive_repeatability_audit_complete.

Maksimum selisih 3 px tidak dijadikan toleransi produksi. Dasar kebutuhan
downstream untuk anggaran error belum tersedia; numerical_accuracy_gates_frozen,
ready_for_geometry_scoring dan ready_for_possession_evaluation tetap false.
Tidak perlu meminta ulang 18 pengukuran yang sudah lengkap. Pekerjaan berikutnya
adalah membenarkan anggaran error berdasarkan kebutuhan komponen/downstream
sebelum membuka skor kandidat; target possession independen tersinkron tetap
menjadi gate terpisah. V2/R adapter r1 tetap kandidat pengumpulan.

## 30. Pelaksanaan audit input possession eksternal 117093

Pengguna meminta pekerjaan segera dikerjakan, dengan komunikasi singkat.
Kandidat tetap V2/R r1; permintaan ini bukan bukti kelulusan data/cabang atau
izin menghapus gate/cutoff. Audit kelayakan yang masih bisa dikerjakan selesai.

Manifest katalog dan source tree diperiksa hash. Lima source/lisensi penerbit
diambil pada code commit a752d294df2a0e816e827b70f284980698f5a50e; ukuran dan
Git blob semuanya cocok, tanpa menjalankan kode penerbit. Bukti di
external_artifacts/v3/117093-possession-source-20261113/. Dua payload kecil
raw player_nodes/raw events gagal HTTP 401 tanpa login. Kegagalan sandbox awal
disimpan pada 117093-possession-source-network1-20261113; jaringan kemudian
dijalankan dengan izin eskalasi, sehingga 401 adalah pembatasan akses dataset.
Tidak membaca kredensial, tidak mengambil dataset besar.

Temuan source: class Frame mendeklarasikan matchTime/frameNumber/eventPeriod,
ballStatus, players dan ball. Ini calon sumber observasi/status, bukan bukti
payload aktual atau target H/A/D independen. Dua eval koordinat pada parser
penerbit tidak dijalankan. Timebase raw terhadap video v1.2 belum terbukti;
jangan mengadopsi offset metadata secara otomatis.

tools/acquire_possession_audit.py membatasi paket otomatis kurang dari 1 MB.
tools/audit_soccertrack_possession_inputs.py memeriksa checksum sebelum parsing,
memakai streaming XML dan ast.literal_eval yang dibatasi koordinat finite.
Tiga belas pemeriksaan sintetis lulus (schema, period reset, missing/unknown,
penolakan kode ekspresi/nonfinite dan checksum rusak). Report/source findings/
synthetic-checks di external_artifacts/v3/117093-possession-readiness-20261113/.

Tiga berkas baru masih MISSING dan perlu diunduh lewat akun operator ke
Soccertrack V2/raw/117093/:
- 117093_player_nodes.csv: 550228 byte, Git blob terpin.
- 117093_12_class_events.json: 383084 byte, Git blob terpin; ini raw, bukan BAS.
- 117093_tracker_box_data.xml: 216067470 byte, perlu SHA256 payload dari
  Hugging Face Git LFS Details sebelum parsing.
Total 217000782 byte. Manifest URL/versi/hash/peran ada di
docs/soccertrack_v1_2_117093_possession_inputs.json. Tidak meminta GSR 2,71 GB.

Setelah file tersedia dan operator memberi SHA256 XML dari penerbit, verifikasi
ukuran/checksum dahulu lalu audit actual schema, mapping tim, missing, status,
frame/time dan asal target. Tidak menganggap ballStatus sebagai H/A atau bukti
independensi. Jika target H/A/D tidak tersedia, lanjutkan konstruksi anotasi
video eksternal yang terpisah, tanpa BAS/interpolasi/prediksi sebagai GT.
Rincian tindakan dan download: docs/kelanjutan_v3_possession_117093.md.

Tidak ada training, inferensi, detector/fusion produksi, scoring geometri atau
akses resmi. V2 runtime verifier tetap lulus. Penghambat berikutnya adalah
akses tiga payload itu, bukan tambahan anotasi garis.

## 31. Tiga raw payload tersedia; dua kecil terverifikasi, SHA penerbit XML ditunggu

Pengguna sudah mengunduh ketiga file pada path yang diminta dan menanyakan
lokasi SHA256 XML di Hugging Face. Ketiga ukuran tepat sesuai katalog:
550228, 383084, 216067470 byte. Auditor dijalankan tanpa SHA XML; kedua
non-LFS cocok Git blob penerbit dan baru kemudian diperiksa schema-nya.
Report baru: external_artifacts/v3/117093-possession-readiness-20261113/
small-payloads-audit.json. Jangan menimpa report awal yang historis missing.

player_nodes CSV berisi 2581 baris, kolom event_time/event_period/event_types,
player/team IDs dan x/y; tidak otomatis dianggap posisi semua pemain per frame.
JSON raw memakai top-level annotations, berbeda dari BAS v1.2 actions.
Audit nama field belum menemukan kandidat ownership/possession/status pada
dua payload kecil. Ini belum bukti target H/A/D independen tersedia.

XML baru diperiksa existence/size; isinya belum dibaca atau diparse. Status
publisher_payload_checksum_required_not_parsed. Instruksikan pengguna login
lalu membuka blob XML pada commit dataset terpin, mencari SHA256 pada bagian
Git LFS Details (Ctrl+F SHA256) dan menyalin 64 karakter hash penerbit.
Halaman gated tidak dapat dibuka agent melalui web. Jangan mengganti hash
penerbit dengan hash lokal saja atau memakai git oid pointer sebagai SHA payload.
Setelah hash diberikan, lanjut verifikasi XML dan audit streaming yang sudah siap.

## 32. XML terverifikasi; status possession padat ditemukan dan pilot visual siap

Operator memberikan SHA256 XML penerbit
43f45382e667959f2fc5904f87f65b597de103eb225616c0e6309b2144a9a7c1.
Ukuran/hash cocok sebelum parsing. Bukti baru disimpan pada
docs/soccertrack_v1_2_117093_possession_verified.json; manifest akuisisi awal
dan artifact V2 tidak diubah. Evidence tetap transkripsi operator.

Audit 138125 frame raw selesai. Babak 1: HOME 28750, AWAY 17183, BALLOUT
18463, NEUTRAL 3254 (67650 frame). Babak 2: HOME 22242, AWAY 26570,
BALLOUT 18025, NEUTRAL 3638 (70475 frame). Semua player ID dikenal; ada frame
dengan 20/21 pemain, tidak diimputasi. Lokasi yang ada finite; outside tidak
di-clip. ball.playerId selalu literal ball, bukan ID carrier. Report lengkap:
external_artifacts/v3/117093-possession-readiness-20261113/payload-report.json.

Koreksi: calon status tim per frame MEMANG tersedia. HOME/AWAY/BALLOUT belum
dipromosikan menjadi GT H/A/D; definisi live/dead dan asal independen perlu
diperiksa. NEUTRAL tetap unknown/masked, tidak otomatis D/X. ballStatus tidak
menjadi fitur. Tidak perlu unduhan atau tambahan anotasi garis untuk tahap ini.

Lima source lineage tambahan terpin dan Git blob lulus, tidak dieksekusi:
external_artifacts/v3/117093-target-lineage-source-20261113/. Alat
tools/audit_soccertrack_target_clock.py menemukan mode raw_time - waktu rilis
1040 ms pada babak 1 (1086 anchor pairs), 2700007 ms babak 2 (1080). Actor
missing 4/2 tetap dicatat. Ini konsensus provider yang sama, bukan bukti visual
independen. Jangan menyamakan raw frame pertama dengan video frame 0 atau
memakai selisih panjang 25 frame sebagai offset. Coverage ujung tetap unknown,
tidak carry-forward. Grid internal raw tepat 40 ms. Tujuh checks lulus.
Report, histogram/pasangan dan interval status literal raw berada di
external_artifacts/v3/117093-target-clock-audit-20261113/.

Pilot external_artifacts/v3/117093-possession-review-pilot-20261113/ memuat
Q01-Q06.mp4, masing-masing 300 frame/12 detik. TARGET pada frame klip 150
(detik 6.00). Lapangan tetap 4096x1080, header 48 px di luar gambar; PNG target
raw juga tersedia. Label provider/prediksi tidak ditampilkan. Hash enam klip/
PNG dan 18 sampel decode lulus. Total sekitar 372 MB ekstraksi lokal. Tanpa
audio; keadaan yang tidak dapat ditentukan harus uncertain.

Empat sampel dari midpoint interval status provider terpanjang in-bounds,
dua kontrol waktu 7500/37500 yang sudah pernah dilihat untuk geometri; shuffle
seed 117093. Ini sampling kualitas stratified, bukan prevalensi atau untouched
test. Key pemilihan pada target-clock-audit/pilot-selection-key.json jangan
ditampilkan selama review. Reviewer pembuat paket sudah mengetahui status.

review.csv masih KOSONG (0/6). Berikutnya operator menonton klip dan menjawab
keadaan tepat di TARGET sebagai live/dead/uncertain, serta warna tim penguasa
jika live (biru/putih/uncertain); nomor punggung opsional bila jelas. Contoh
Q01: live, biru; Q02: dead; Q03: uncertain. Jangan memaksa Home/Away dari
warna/arah; mapping tim diperiksa tersendiri. Catat exposure sesi review sebelum
membandingkan dengan provider. Pilot kecil belum mengesahkan seluruh label.

Rincian docs/audit_target_possession_117093.md. Tidak ada training, inferensi
model, scoring kandidat, atau akses resmi. V2/R r1 tetap kandidat pengumpulan.

## 33. Serah terima artifact melalui Git pada 14 November

Pengguna meminta commit seluruh pekerjaan agar teman pemilik repo bisa
melanjutkan. Source sebelumnya sudah berada pada commit a174024; tetapi
external_artifacts diabaikan sehingga laporan, referensi dan klip tidak ikut.
Kini .gitignore mengizinkan direktori audit V3 yang diketahui provenance-nya
dan release-readiness-20261112, termasuk keenam klip pilot Q01-Q06. Folder
historis lain tetap diabaikan sampai provenance-nya diperiksa.

external_artifacts/README.md menjelaskan isi dan cara melanjutkan.
external_artifacts/handoff-inventory-20261114.json mengikat 498 file eksternal
dengan ukuran/SHA256 (tidak memasukkan inventory itu sendiri), total 491919520
byte, file terbesar 54719737 byte. Semua 136 anggota manifest source hasil
pemulihan cocok checksum. Artifact lama tidak diubah; .gitattributes baru
mempertahankan byte V3 dan release-readiness tanpa konversi line ending.

Data resmi/GT/results, root bundle V1 yang memuat tactical, arsip/salinan repo
belum diaudit dan tiga notebook starter belum diverifikasi dikeluarkan dari
staging tanpa menghapus file lokal. Runtime serta payload mentah Soccertrack V2
tetap lokal. Snapshot Git menyediakan klip pilot/ref/reports, sedangkan payload
mentah diperoleh teman melalui akun sendiri menurut manifest docs.

Ada token pada konfigurasi nama author dan metadata commit a174024 sebelumnya.
Nilainya tidak dicatat di sini. Nama author lokal diperbaiki menjadi Tirta untuk
commit berikutnya; email dipertahankan. Token perlu dicabut/diganti pemiliknya.
Riwayat commit lama tidak ditulis ulang dalam pekerjaan ini. Jangan mencetak
nilai konfigurasi author lama atau token ke log/dokumen.

Status penelitian tidak berubah: review pilot masih 0/6, belum ada training
atau kandidat possession V3. V2/R r1 tetap kandidat pengumpulan. Pekerjaan Git
tidak mengesahkan target/komponen maupun mengubah batas akses resmi.
