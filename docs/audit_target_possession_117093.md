# Audit target dan clock raw SoccerTrack 117093

SHA256 XML yang ditranskripsikan operator dari halaman penerbit:
`43f45382e667959f2fc5904f87f65b597de103eb225616c0e6309b2144a9a7c1`.
Ukuran 216.067.470 byte dan hash lokal cocok sebelum XML diparse. Evidence
tetap operator transcription, bukan hash publisher yang diambil mandiri agent.
Manifest bukti baru `soccertrack_v1_2_117093_possession_verified.json` menyimpan
hash/evidence tanpa mengubah manifest akuisisi awal atau artifact V2.

## Fakta payload

| Pemeriksaan | Babak 1 | Babak 2 |
| --- | ---: | ---: |
| Frame raw | 67.650 | 70.475 |
| HOME | 28.750 | 22.242 |
| AWAY | 17.183 | 26.570 |
| BALLOUT | 18.463 | 18.025 |
| NEUTRAL | 3.254 | 3.638 |
| Frame berisi 22 pemain | 67.609 | 70.428 |
| Player ID tidak dikenal di metadata | 0 | 0 |
| Lokasi pemain hilang/invalid pada record yang ada | 0 | 0 |

Frame yang berisi kurang dari 22 pemain tetap missing coverage, tidak diisi nol.
Koordinat pemain ternormalisasi mencakup nilai outside [-0,06..1,08] untuk x
dan [-0,09..1,10] untuk y pada kedua babak; tidak dilakukan clipping. Ini
rentang numerik, bukan verifikasi orientasi atau ketelitian koordinat.
ID elemen ball selalu literal ball (138.125 record), bukan ID pemegang bola.
ballStatus tidak boleh menjadi fitur ketika diuji sebagai calon target.

Temuan ini memperbarui status sebelumnya: **label status tim per frame memang
tersedia**, tetapi kesesuaian definisi dan kualitas target independennya belum
dinyatakan lulus. Dugaan HOME->H/AWAY->A dan BALLOUT->D masih hipotesis semantik;
NEUTRAL tetap unknown/masked, tidak otomatis D/X. Perlu dibuktikan khususnya
apakah BALLOUT mewakili seluruh dead-ball, termasuk penghentian di dalam lapangan.

Report lengkap:
`external_artifacts/v3/117093-possession-readiness-20261113/payload-report.json`.

## Clock yang berbeda

Raw player_nodes dan raw event JSON dicocokkan menurut periode, waktu, label
event dan actor. Keduanya telah lulus Git blob. BAS v1.2 memiliki actor dan
frame video yang terikat source checksum. Jendela identitas clock adalah
plus/minus 5 detik dari origin periode metadata, tanpa membaca skor model.

- Babak 1: mode selisih raw_time - released_position = **1040 ms**, sebanyak
  1086 pasangan anchor. Empat event BAS tidak memiliki actor dan tidak dipaksa
  menjadi pasangan. Anchor lain/same-actor repeats tidak dibuang dari histogram.
- Babak 2: mode **2700007 ms**, sebanyak 1080 pasangan anchor. Ini clock raw
  absolut dikurangi waktu relatif rilis; jangan mengartikan angka ini sebagai
  offset video tambahan 45 menit. Dua event tidak memiliki actor.
- Grid internal XML tepat 40 ms per frame pada masing-masing periode.
- Konsensus di atas berasal dari provider yang sama. Ini bukti lineage/clock
  internal, belum validasi visual independen atau pembuktian label possession.

Babak 1 memiliki 25 frame raw lebih banyak daripada video 67.625 frame yang
sudah diperiksa. Konsensus 1040 ms adalah 26 langkah pada grid 40 ms; menyamakan
frame raw pertama dengan video frame 0 tetap salah. Jangan menganggap selisih
panjang file sebagai offset. Coverage ujung harus diperiksa tersendiri; posisi
di luar raw coverage tetap unknown, tidak di-carry-forward.

Alat `tools/audit_soccertrack_target_clock.py` hanya menghasilkan audit dan
interval status pada clock raw. Tidak menghasilkan label H/A/D produksi atau
memilih model. Tujuh pemeriksaan sintetis/konsistensi lulus, termasuk origin
babak kedua, actor missing, offset ambigu dan coverage interval terhadap XML.
Report/histogram/pasangan di `external_artifacts/v3/117093-target-clock-audit-20261113/`.

## Pemeriksaan visual pilot berikutnya

Paket `external_artifacts/v3/117093-possession-review-pilot-20261113/` disiapkan
dari video eksternal yang hash-nya diverifikasi ulang. Enam klip 12 detik pada
resolusi lapangan asli, dengan header nomor frame terpisah; frame TARGET pada
detik 6.00. Empat sampel berasal dari interval status provider terpanjang yang
masih di dalam cakupan video, dua dari waktu tetap 7500/37500; urutan diacak.
Sampling ini untuk menemukan kegagalan semantik/clock, bukan estimasi akurasi
atau prevalensi seluruh pertandingan. Dua waktu kontrol sudah pernah dilihat
untuk geometri; tidak disebut untouched test.

Operator menilai live/dead/uncertain dan warna tim penguasa bila terlihat,
tanpa membuka label provider atau key pemilihan. Jangan menebak Home/Away
dari arah atau warna. Nomor punggung jika jelas membantu pemeriksaan mapping
tim tersendiri. Reviewer pembuat paket sudah melihat label provider; blinding
mandiri tidak diklaim. CSV pengukuran pilot awal kosong, belum ada GT baru.

Keberhasilan pilot kecil tidak mengesahkan seluruh label: tetap perlu definisi
target, pemeriksaan independen batas transisi, coverage/sinkronisasi, anggaran
error komponen dan penilaian antarpertandingan sebelum produksi. Tidak ada
training, inferensi model, scoring kandidat, atau akses data resmi. V2/R r1 tetap
kandidat pengumpulan. Tidak menjanjikan V3 siap pada target internal 15 November.
