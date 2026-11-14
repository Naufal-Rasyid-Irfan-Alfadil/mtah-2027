# Audit `invalid half bounds` dan revisi adapter V2

## Akar masalah dan bukti

**Fakta, confidence tinggi:** adapter V2 lama hanya menerima dua interval
`ProviderGlobalParameters` sebagai sumber babak. Ia tidak menyediakan jalur
untuk scope per babak yang sudah dipublikasikan dalam source/dokumentasi resmi
repository. Kesimpulan sebelumnya bahwa tidak tersedia sumber batas babak
terlalu luas dan ditarik sebelum audit sumber tersebut selesai.

Sumber publik itu tersedia: `DATA.md`, bagian **Frame alignment / Which frames
are graded**, mempublikasikan dua blok scope pada timeline video;
`games.py:half_video_blocks(game)` menghasilkan blok yang sama. Ini metadata
scope yang disediakan panitia dalam kode publik, bukan pembacaan file GT
H/A/D. Pemakaiannya dibatasi pada scope dan reset temporal saat inferensi;
tidak ada training, pemilihan model, kalibrasi offset, atau tuning berdasarkan
pertandingan resmi. Scope publik tidak disebut waktu kickoff yang diinferensi.

**Pemicu error spesifik, confidence tinggi:** di source bundle V2 lama,
`atd_inference.py:68–70` menjalankan `int(parameters[...])`, lalu menolak
`start < 1` atau `end < start`. Nilai awal nol memicu error itu sebelum parser
memeriksa babak kedua. Audit ini tidak membaca XML resmi; deskripsi isi metadata
berasal dari ringkasan pengguna dan tidak membuktikan ketiadaan field lain.

## 1. Elemen, atribut, fallback, dan kondisi error

Parser menghapus namespace tag, lalu mencari root `Metadata` atau `main/Metadata`.

| Bagian | Jalur/atribut yang dibaca | Perilaku lama |
| --- | --- | --- |
| FPS | `Metadata/GlobalConfig/FrameRate` | Harus 25; missing menjadi NaN lalu ditolak. |
| Dimensi | `Metadata/.../FieldSize/Width`, `Height` | Harus positif dan finite, dalam meter. |
| Parameter babak | `Metadata/GlobalConfig/ProviderGlobalParameters/ProviderParameter` dengan anak `Name` dan `Value` | Nama tepat `first_half_start`, `first_half_end`, `second_half_start`, `second_half_end`; dua pasangan wajib. |
| Tim | `Teams/Team@id`, `MatchParameters/Score@idLocalTeam`, `@idVisitingTeam` | Score menentukan Home/Away; fallback urutan tim jika Score tidak ada. Tidak menentukan periode. |
| Layout raw | `main/DataFormatSpecifications/DataFormatSpecification@startFrame`, `@endFrame`, `@separator` | Rentang layout slot/channel, bukan bukti pergantian babak. |
| Urutan pemain | `PlayerChannelRef@playerChannelId` dan deklarasi `PlayerChannels` | Mengikuti channel reference, bukan urutan roster. |

Tidak ada pencarian periode alternatif dalam `Sessions` pada adapter lama.
Tidak ada fallback metadata babak di V2. Source paket V1 memang memiliki opsi
eksplisit `--scope full-recording`, tetapi opsi itu melebur rekaman menjadi satu
segmen dan tidak dikembalikan pada revisi ini. Pilihan pengguna untuk tetap
memisahkan babak dipertahankan.

Kondisi error lama lainnya: key hilang, nilai kosong/noninteger; interval
terbalik; overlap kedua babak; extra-time tidak didukung; layout tidak valid;
frame raw tidak sesuai urutan atau tidak tercakup layout.

## 2. Apakah kegagalan parsing diam-diam menjadi nol?

**Tidak pada jalur batas babak.** `(findtext('Value') or '').strip()` menghasilkan
string kosong untuk `<Value/>`, bukan angka nol. `int('')` dan `int('bad')`
melempar exception. Key tidak ada juga melempar exception. Tidak ada `except:
return 0`, `int(value or 0)`, atau default numerik sejenis pada jalur ini.

**Ada default nol pada jalur berbeda:** layout lama memakai
`int(spec.get('startFrame', '0'))` dan bentuk serupa untuk akhir. Atribut hilang
menjadi nol lalu ditolak sebagai layout tidak didukung. Itu tidak dapat
menyebabkan traceback `invalid half bounds`, karena layout diproses sesudah
batas babak. Revisi menggantinya dengan lookup atribut wajib dan pesan khusus
untuk batas layout hilang/noninteger.

Layout yang secara eksplisit mulai pada nol kini boleh mencakup raw ID 1 tanpa
mengubah nomor raw. Tidak dibuat frame nol: counter raw tetap wajib 1..N.
Kasus ini diuji terpisah dari atribut layout yang tidak ada.

## 3. Pembanding loader bawaan dan sumber publik

`starter/load_atd.py:load()` mendelegasikan ke
`kloppy.metrica.load_tracking_epts()`. `requirements-starter.txt` memin versi
**3.18.0**. Wrapper tersebut tidak membangun sendiri pembagian dua babak.

Source wheel kloppy 3.18.0 diambil dari PyPI, diverifikasi SHA-256 terhadap
metadata registry, lalu hanya diekstrak untuk dibaca; tidak diinstal atau
diimport. Source dan manifest audit disimpan pada
`external_artifacts/v2/adapter-audit-v1/`.

Pada `metrica_epts/metadata.py`, `_load_provider_parameters()` menyaring Value
kosong. `_load_periods()` menambah periode selama key start tersedia dan
berhenti saat key berikutnya tidak tersedia. Tidak ada syarat start >= 1.
Dengan demikian, library dapat menerima awal nol dan satu periode. Itu
menjelaskan kompatibilitas membaca file, tetapi bukan bukti bahwa library
memulihkan dua babak fisik dari satu interval.

Pada `metrica_epts/reader.py`, layout memakai kondisi `frame_id <= end_frame_id`
dan berganti setelah endpoint diproses; periode memakai perbandingan inklusif
pada kedua ujung timestamp. Source frame timestamp-nya adalah `frame_id/fps`,
lalu dibuat relatif terhadap periode. Pipeline kita tidak mencampurkan
timestamp relatif library itu dengan timestamp video global.

[Contoh metadata publik Metrica yang dipin](https://raw.githubusercontent.com/metrica-sports/sample-data/e706dd506b360d69d9d123d5b8026e7294b13996/data/Sample_Game_3/Sample_Game_3_metadata.xml)
memiliki dua rentang berurutan dengan ujung inklusif. Itu contoh provider
yang didukung, bukan bukti konvensi semua ekspor Metrica/FIFA.
[Paket kloppy yang diperiksa](https://pypi.org/project/kloppy/3.18.0/) mengikuti
versi yang dipin repository, bukan versi latest yang diasumsikan sama.

`games.py` dan bagian publik `DATA.md` juga diperiksa terhadap HEAD Git:
`git diff --ignore-space-at-eol -- games.py DATA.md` tidak menghasilkan diff.
Blob Git: games.py `d330dc11b3c54d9c704f0c9df7de111395f9f1d4`, DATA.md
`6bd2f042c00d06d6391472926ec1bc1a15201a17` pada commit
`e2231bd3922853b2a444bebb322436965fe41cb0`.

## 4. Kontrak indeks dan endpoint

| Timeline | Kontrak yang digunakan | Bukti/konversi |
| --- | --- | --- |
| Raw tracking tactical | ID 1..N | `starter/load_atd.py:video_frame_of` dan `DATA.md:Frame alignment`; juga diperiksa pada setiap baris oleh runner lokal. |
| Video/submission | Indeks 0..N−1 | `video_frame = raw_id - 1`. |
| Scope publik per babak | Video, first dan last inklusif | Nama/implementasi `half_video_blocks`, tabel first/last/count di DATA.md. |
| Scope internal adapter | Raw ATD, first/last inklusif | Tambahkan 1 ke **kedua** endpoint video. Panjang interval tetap `last-first+1`. |
| Timestamp fitur | Global video microseconds | `(raw_id-1) * 40000`, 25 Hz, tanpa memadatkan timeline. |
| IdFrame asal anotasi | Counter berbeda | Tidak dipakai untuk menggeser raw tracking. Fungsi publik sudah mengembalikan koordinat video; setelah itu hanya +1 ke raw ID. |

Konvensi field provider `0 … N` dengan babak berikutnya kosong **tidak
disimpulkan** sebagai 0-based inclusive atau half-open. Jalur `organizer-public`
tidak melakukan konversi heuristik terhadap field tersebut; ia memilih sumber
scope publik lain secara eksplisit. Tidak ada pencarian offset dari skor.

## 5. Konsistensi timeline fitur dan decoder

Hasil kedua sumber dinormalisasi menjadi dua tuple
`(period, first_raw_id, last_raw_id)` dengan ujung inklusif. Validasi menolak ID
babak yang bukan 1/2, interval terbalik atau overlap. Untuk sumber publik,
game, FPS, jumlah frame rekaman, dan batas di dalam rekaman juga diperiksa.

`frames()` mempertahankan setiap baris raw; ia menghasilkan video frame
`raw_id-1`, period yang sesuai, dan timestamp global. Frame di luar kedua
scope tetap X. Tidak ada kompaksi gap.

Ekstraktor menerima `FrameKey(match, period, video_frame)`. Speed dan jendela
konteks yang sudah ada memutus state pada perubahan period/frame/time.
Decoder dipanggil terpisah untuk period 1 dan 2, dengan frame/timestamp yang
sama seperti ekstraksi. Fitur, rumus konteks, threshold router, dan parameter
decoder tidak diubah.

Fixture dengan kedua babak **bersebelahan** membuktikan bahwa reset terjadi
karena period, bukan hanya karena gap: speed pada frame pertama babak kedua
tetap missing dan median konteks tidak membawa jarak babak pertama. Fixture
ber-gap membuktikan endpoint dan X mask pada lattice raw/video yang sama.

## 6. Perbaikan dan pengemasan

Kode baru `external_baseline/atd_periods.py` memisahkan validasi provider dan
pemuatan scope publik. CLI menyediakan pilihan eksplisit:

- `--period-source provider` tetap default; dua rentang provider harus valid.
- `--period-source organizer-public --game BAR-ATH` memakai source publik
  `games.py:half_video_blocks` yang disalin dan dicakup checksum bundle.

Tidak ada fallback otomatis setelah error provider, pembagian berdasarkan
titik tengah, pemakaian video/GT, atau mode satu rekaman. Game/FPS/panjang yang
tidak cocok ditolak.

Revisi dibuat lewat mekanisme packaging repository:

```sh
external_artifacts/local-runtime/training-venv/bin/python -B \
  -m external_baseline.inference_bundle revise-adapter \
  --bundle external_artifacts/v2/inference-bundle-v2 \
  --output external_artifacts/v2/inference-bundle-v2-r1
```

Output aktual sudah tersedia; command di atas untuk reproduksi memerlukan
direktori output baru. Mekanisme hanya menyalin inventory parent yang sudah
diverifikasi, tidak menyalin direktori tambahan atau data operator. Manifest
seleksi model lama disimpan sebagai provenance, tanpa mengaku bahwa source
adapter baru sudah digunakan saat eksperimen lama. Revisi mencatat source
runtime dan perubahan adapter secara terpisah. Semua checksum diverifikasi
sebelum/sesudah pengemasan; tidak ada penonaktifan pemeriksaan.

Model SHA-256 tetap:
`04e2510928af168c7cd1e3d9ebb698591b336f52a2344853dce1fd8acd0fa88f`.
Decoder SHA-256 tetap:
`2aa5b5f1c777fe9c2c71b7bdb894082b22b967dae5b67664be9b5c7871bafa74`.
Source fitur dan router sama byte demi byte dengan parent. Bundle V2 lama
dan manifest parent tetap utuh.

## 7. Hasil verifikasi dan batas kesimpulan

**115 tes berhasil** pada source final. Tujuh tes period-source baru mencakup
zero/empty/noninteger, konversi endpoint, penolakan scope tidak cocok, layout
berawal nol tanpa rebase counter, reset fitur/decoder, X mask, dan penolakan
checksum rusak sebelum pengemasan. Import/help tanpa akses data juga tercakup
oleh regresi yang ada. Tidak ada training model nyata dalam audit ini;
model kecil pada unit test hanya memakai fixture sintetis.

Pemeriksaan tambahan memakai model R beku dan input sintetis melalui runner
mandiri. Dibandingkan parent, jalur provider revisi menghasilkan output yang
identik byte demi byte untuk `submission.csv`, `submission_raw.csv`,
`features.sqlite`, dan `predictions.sqlite`. Jalur publik juga identik ketika
fixture public scope dan fixture provider menyatakan rentang yang sama.
Paket lolos verifikasi runtime setelah dipindahkan; ZIP dan seluruh hash
anggotanya diverifikasi.

Log final: `adapter-audit-v1/regression-v2.log` (115 tes),
`targeted-tests-v2.log` (7 tes periode), `package.log`, dan
`release-verification.log`. Log percobaan pengembangan sebelumnya dipertahankan
dan tidak dipakai sebagai bukti kelulusan source final.

**Belum diverifikasi:** isi serta seluruh variasi schema pada dataset resmi,
hasil inferensi resmi, dan kualitas prediksi pada pertandingan resmi. Audit
tidak membuktikan bahwa field lain pada XML resmi tidak menyediakan informasi
tambahan. Untuk game/rekaman yang tidak cocok dengan metadata publik paket,
masih diperlukan scope dari sumber yang terdokumentasi; parser menolak
mengarangnya. Tidak ada alasan lagi untuk menyatakan bahwa scope publik
pertandingan yang didokumentasikan repository ini tidak tersedia.

Folder tactical, XML/TXT/video resmi, GT, cache/prediksi/per-frame export resmi
tidak dibuka. Yang dibaca: source, dokumentasi publik, source kloppy yang dipin,
metadata contoh Metrica eksternal, dan fixture sintetis.

## Paket dan command operator

- Folder: `external_artifacts/v2/inference-bundle-v2-r1/`.
- ZIP: `external_artifacts/v2/inference-bundle-v2-r1.zip`.
- Manifest rilis: `external_artifacts/v2/inference-bundle-v2-r1-release.json`.
- Log audit/tests/packaging: `external_artifacts/v2/adapter-audit-v1/`.

**Hanya pengguna yang menjalankan inferensi resmi.** Dari root proyek, gunakan
path input yang sama dengan command sebelumnya yang berhasil membuka XML:

```sh
external_artifacts/local-runtime/training-venv/bin/python -B \
  external_artifacts/v2/inference-bundle-v2-r1/verify_bundle.py --runtime

external_artifacts/local-runtime/training-venv/bin/python -B \
  external_artifacts/v2/inference-bundle-v2-r1/run_tactical.py \
  --bundle external_artifacts/v2/inference-bundle-v2-r1 \
  --metadata "/path/yang/sama/BAR-ATH_tactical_atd.xml" \
  --tracking "/path/yang/sama/BAR-ATH_tactical_atd.txt" \
  --period-source organizer-public \
  --game BAR-ATH \
  --output local_official_artifacts/v2-r1-run1 \
  --operator-local
```

Ganti kedua placeholder path, dan gunakan direktori output baru. Command
inferensi di atas tidak dijalankan agent pada input resmi.
