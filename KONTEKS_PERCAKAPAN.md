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
