# Pelaksanaan tahap data possession 117093

Pengguna meminta pekerjaan dimulai sekarang. Kandidat pengumpulan tetap V2/R
adapter r1; pekerjaan ini menyiapkan kelayakan data eksternal untuk V3, tanpa
mempromosikan kandidat setelah cutoff internal atau mengubah artifact beku.

## Yang dikerjakan

- Memeriksa katalog dataset dan source tree yang dipin beserta checksum.
- Mengambil lima berkas source/lisensi penerbit yang kecil dan memverifikasi
  Git blob. Code revision a752d294df2a0e816e827b70f284980698f5a50e.
- Mencoba dua payload kecil melalui URL dataset versi tetap; keduanya HTTP 401
  tanpa login. Tidak membaca kredensial atau menjalankan kode penerbit.
- Membuat manifest akuisisi tiga berkas eksplisit, total 217.000.782 byte.
- Membuat auditor riset yang memverifikasi checksum sebelum parsing, memakai
  streaming XML dan ast.literal_eval untuk koordinat, tanpa eval kode penerbit.
- Menjalankan 13 pemeriksaan sintetis. Report lokal menunjukkan tiga berkas
  baru masih missing; tidak ada label possession yang dihasilkan.

Bukti berada di `external_artifacts/v3/117093-possession-source-20261113/`
dan `external_artifacts/v3/117093-possession-readiness-20261113/`.
Percobaan jaringan sandbox yang gagal disimpan terpisah pada direktori network1.

## Temuan baru dan batas bukti

Class Frame pada source penerbit mendeklarasikan ballStatus per frame serta
matchTime/frameNumber/eventPeriod, pemain dan bola. Ini alasan memeriksa raw
tracking sebelum meminta GSR besar. Keberadaan field pada source belum
membuktikan payload v1.2 memuatnya secara lengkap, semantiknya sesuai live/dead,
atau asal anotasinya independen. Class tersebut tidak mendeklarasikan target
H/A possession padat. Berkas event raw tetap perlu diperiksa, bukan otomatis
dijadikan target melalui interpolasi.

Parser penerbit membaca XML seluruhnya dan memiliki dua pemanggilan eval untuk
koordinat. Source hanya diperiksa statis; auditor proyek tidak mengeksekusinya.
Timebase raw metadata tidak otomatis sama dengan frame video v1.2 yang telah
dipangkas. Jangan menyalin offset nominal atau menyimpulkan alignment dari nama
file. Origin koordinat raw/GSR/geometri harus dibuktikan terhadap payload.

## Berkas yang diperlukan dari akun operator

Dataset SoccerTrack v1.2, commit
325bd4c57ee8e135ab652f3921d274526ada496b, CC BY 4.0. Kredit AtomScott dan
kontributor. Match 117093 adalah publisher validation, peran lokal development.

Simpan ketiganya pada `Soccertrack V2/raw/117093/`:

| File | Ukuran | URL versi tetap |
| --- | ---: | --- |
| 117093_player_nodes.csv | 550.228 byte | [Unduh](https://huggingface.co/datasets/atomscott/soccertrack-v2/resolve/325bd4c57ee8e135ab652f3921d274526ada496b/raw/117093/117093_player_nodes.csv) |
| 117093_12_class_events.json | 383.084 byte | [Unduh](https://huggingface.co/datasets/atomscott/soccertrack-v2/resolve/325bd4c57ee8e135ab652f3921d274526ada496b/raw/117093/117093_12_class_events.json) |
| 117093_tracker_box_data.xml | 216.067.470 byte | [Unduh](https://huggingface.co/datasets/atomscott/soccertrack-v2/resolve/325bd4c57ee8e135ab652f3921d274526ada496b/raw/117093/117093_tracker_box_data.xml) |

JSON berasal dari raw/, berbeda dari BAS 479.053 byte yang sudah ada. Dua berkas
non-LFS diperiksa memakai Git blob dari katalog. Untuk XML, operator perlu
menyalin SHA256 dari Git LFS Details pada [halaman XML versi tetap](https://huggingface.co/datasets/atomscott/soccertrack-v2/blob/325bd4c57ee8e135ab652f3921d274526ada496b/raw/117093/117093_tracker_box_data.xml).
Git oid pointer bukan hash payload. Hash lokal saja tidak membuktikan kecocokan
dengan penerbit. Manifest lengkap: `soccertrack_v1_2_117093_possession_inputs.json`.

Setelah file dan SHA penerbit tersedia, agent memeriksa ukuran/hash dahulu,
lalu menjalankan auditor ke report baru:

```powershell
& runtime/v2-r1-venv/Scripts/python.exe -I -B tools/audit_soccertrack_possession_inputs.py --tracking-sha256 SHA256_DARI_PENERBIT --output external_artifacts/v3/117093-possession-readiness-20261113/payload-report.json
```

## Keputusan setelah pemeriksaan payload

1. Buktikan observasi pemain/tim, missing, period/frame/timebase dan domain
   koordinat. Belum melakukan konversi produksi atau penyesuaian offset.
2. Pisahkan calon target ballStatus dari fitur observasi. Verifikasi definisi,
   coverage, asal independen, serta keselarasan terhadap video eksternal.
3. Jika H/A/D independen tidak tersedia, siapkan protokol anotasi video
   eksternal: interval frame dengan batas eksplisit, team mapping terverifikasi,
   bagian ambigu tetap unknown/masked dan pemeriksaan silang annotator. Jangan
   mengisi label dari BAS/interpolasi bola/prediksi sendiri. Target yang tidak
   teramati tidak otomatis D atau X.
4. Bekukan peran pertandingan dan protokol. Pilot 117093 adalah development;
   tiga bagian satu pertandingan tidak menggantikan penilaian antarpertandingan.
5. Baru setelah kelayakan target/observasi dan gate komponen lengkap, bangun
   detector/fusion/kandidat. Gate end-to-end sebelumnya tetap berlaku, termasuk
   fallback identik V2 ketika modalitas tambahan tidak tersedia.

Tidak ada training, detector/fusion produksi, scoring kandidat, atau akses data
resmi dalam pekerjaan ini. V2 tetap tersedia. Tenggat internal kandidat baru
13 November 18.00 telah lewat; permintaan melanjutkan V3 tidak dianggap
kelulusan atau penghapusan gate. Tidak menjanjikan V3 siap 15 November atau
kenaikan skor.
