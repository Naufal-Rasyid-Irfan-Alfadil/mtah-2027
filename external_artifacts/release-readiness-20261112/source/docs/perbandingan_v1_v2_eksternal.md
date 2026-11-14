# Perbandingan V1 versus V2 pada data eksternal

**Keputusan tetap R/V2.** Perhitungan ulang keputusan dari metrik beku mengonfirmasi kelulusan seluruh 37 kriteria J03WQQ dan 37 kriteria penilaian tambahan J03WMX. Tidak ada pelonggaran batas atau pemilihan kandidat menggunakan skor pertandingan resmi.

Laporan ini membaca artefak eksternal yang sudah ada, memverifikasi hash metrik/protokol, dan menghitung ulang kriteria. Tidak dilakukan training, inferensi, scoring ulang dari GT per frame, atau akses data/hasil resmi. Skor bukan hasil eksperimen baru. Semua tabel utama membandingkan keluaran setelah decoder, bukan keluaran raw.

Spell F1 adalah rata-rata possession-spell F1 pada IoU 0,3/0,4/0,5/0,6/0,7. Macro F1 merata-ratakan F1 kelas H/A/D. Toleransi transisi @12 dan @25 adalah 12/25 frame, setara 0,48/1 detik pada 25 Hz.

## Model dan pembagian data

| Komponen | V1 — A | V2 — R |
| --- | --- | --- |
| Classifier | Expanded HGB 14 fitur | Router tetap atas A 14 fitur dan C 18 fitur |
| Fitur C tambahan | — | Cakupan bola, umur observasi, median jarak Home/Away dalam jendela 25 frame |
| Aturan R | — | C jika jendela bola lengkap dan jumlah pemain lengkap memenuhi referensi training; lainnya A |
| Referensi pemain | — | Modus observasi training: 11 Home dan 11 Away |
| Decoder | V1, prior/transisi dari training | Sama dengan A; parameter tidak diubah |
| Fitting saat perbaikan R | — | Tidak ada; kedua classifier sudah dilatih pada data eksternal |

A adalah expanded baseline yang dipaketkan dalam inference-bundle-v1, bukan model lama sebelum penambahan J03WPY. C berdiri sendiri bukan kandidat yang dirilis.

| Data | Peran | Cakupan |
| --- | --- | --- |
| J03WOH + J03WPY | Training classifier/augmentasi dan estimasi prior/transisi | Kedua babak setiap pertandingan |
| J03WQQ | Validation antarpertandingan untuk pengembangan | Kedua babak; 142.345 frame; sudah dipakai ulang |
| J03WMX | Penilaian tambahan setelah R dibekukan | Kedua babak; 145.967 frame; riwayat proyek lama tidak diketahui |

J03WQQ berbeda dari pertandingan training, tetapi sudah digunakan untuk diagnosis dan pengembangan; bukan untouched test. Protokol R ditetapkan setelah diagnosis C pada J03WQQ dan sebelum evaluasi R, bukan sebelum seluruh pengembangan pernah melihat J03WQQ. J03WMX dinilai sekali pada rangkaian ini tanpa menyesuaikan R setelah hasilnya; ketidakpastian riwayat lama mencegah klaim test yang dipastikan belum pernah dipakai. J03WOY/J03WR9 tidak digunakan untuk pemilihan R dalam rangkaian ini.

## Kriteria yang ditetapkan sebelum evaluasi kandidat

| Kriteria | J03WQQ pengembangan | J03WMX penilaian tambahan |
| --- | --- | --- |
| Spell F1 overall bersih | Δ minimal +0,010000 | Δ minimal 0,000000 |
| Macro F1, F1 D, Transition F1 @12/@25 overall pada setiap kondisi | Δ minimal −0,010000 | Δ minimal −0,010000 |
| Spell F1 bersih pada masing-masing babak | Δ minimal −0,010000 | Δ minimal −0,010000 |
| Spell F1 overall pada masing-masing kondisi stres | Δ minimal −0,010000 | Δ minimal −0,010000 |

Δ = V2 − V1 dalam satuan metrik F1. F1 bukan persentase akurasi. Batas dievaluasi pada nilai penuh dengan toleransi numerik 1e−12; tampilan dibulatkan enam desimal. Ada 37 perbandingan per pertandingan: 28 pengaman Macro/D/transisi, 7 Spell overall termasuk bersih, serta 2 Spell per babak. Tidak ada gate baru yang ditambahkan untuk memilih ulang kandidat dalam laporan ini.

## Hasil bersih: metrik utama dan per kelas

### J03WQQ

| Metrik | V1 | V2 | Δ V2 − V1 |
| --- | --- | --- | --- |
| Spell F1 | 0.446316 | 0.502508 | +0.056192 |
| Macro F1 | 0.863894 | 0.875228 | +0.011334 |
| F1 H | 0.793685 | 0.817518 | +0.023833 |
| F1 A | 0.837909 | 0.849787 | +0.011878 |
| F1 D | 0.960087 | 0.958379 | -0.001708 |
| Transition F1 @12 | 0.415254 | 0.436300 | +0.021046 |
| Transition F1 @25 | 0.501695 | 0.547993 | +0.046298 |

| Diagnosis | V1 | V2 |
| --- | --- | --- |
| Possession GT (H/A) | 401 | 401 |
| Possession prediksi (H/A) | 549 | 516 |
| Durasi rata-rata possession prediksi (detik) | 6.425792 | 6.843411 |
| Fragmentation | 1.368000 | 1.300000 |
| Frame dinilai | 142345 | 142345 |

### J03WMX

| Metrik | V1 | V2 | Δ V2 − V1 |
| --- | --- | --- | --- |
| Spell F1 | 0.414365 | 0.451830 | +0.037465 |
| Macro F1 | 0.886097 | 0.893676 | +0.007579 |
| F1 H | 0.818469 | 0.837664 | +0.019195 |
| F1 A | 0.852382 | 0.861940 | +0.009557 |
| F1 D | 0.987440 | 0.981423 | -0.006017 |
| Transition F1 @12 | 0.448513 | 0.459200 | +0.010687 |
| Transition F1 @25 | 0.547674 | 0.568000 | +0.020326 |

| Diagnosis | V1 | V2 |
| --- | --- | --- |
| Possession GT (H/A) | 511 | 511 |
| Possession prediksi (H/A) | 575 | 500 |
| Durasi rata-rata possession prediksi (detik) | 5.956591 | 6.891680 |
| Fragmentation | 1.141694 | 1.042345 |
| Frame dinilai | 145967 | 145967 |

Skor overall dihitung pada gabungan timeline dengan batas babak terjaga; bukan rata-rata sederhana skor dua babak. Metrik diagnosis tidak dijadikan gate tambahan.

## Hasil bersih per babak

| Data | Babak | Frame dinilai | Spell V1 | Spell V2 | Δ Spell | Macro V1 | Macro V2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J03WQQ | half_1 | 69204 | 0.494118 | 0.563431 | +0.069314 | 0.896111 | 0.905674 |
| J03WQQ | half_2 | 73141 | 0.401629 | 0.445570 | +0.043940 | 0.825573 | 0.837490 |
| J03WMX | half_1 | 70708 | 0.418426 | 0.454280 | +0.035854 | 0.901417 | 0.907970 |
| J03WMX | half_2 | 75259 | 0.410619 | 0.449624 | +0.039005 | 0.865180 | 0.875008 |

## Ketahanan pada tujuh kondisi berpasangan

### J03WQQ

| Kondisi | Frame dinilai | Spell V1 | Spell V2 | Δ Spell | Macro V1 | Macro V2 | Δ Macro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bersih | 142345 | 0.446316 | 0.502508 | +0.056192 | 0.863894 | 0.875228 | +0.011334 |
| Bola dihilangkan acak 20% | 142345 | 0.086244 | 0.086313 | +0.000069 | 0.821504 | 0.821950 | +0.000447 |
| Bola hilang 2 detik tiap 20 detik | 142345 | 0.421317 | 0.455567 | +0.034251 | 0.850457 | 0.858352 | +0.007895 |
| Koordinat x bola hilang acak 20% | 142345 | 0.086025 | 0.086094 | +0.000069 | 0.820715 | 0.821185 | +0.000470 |
| Pemain dihilangkan acak 20% | 142345 | 0.416427 | 0.415984 | -0.000443 | 0.869607 | 0.870117 | +0.000510 |
| Jitter posisi σ=0,25 meter | 142345 | 0.365798 | 0.428632 | +0.062835 | 0.621131 | 0.648137 | +0.027007 |
| Gap 1 detik tiap 60 detik | 139945 | 0.494253 | 0.544698 | +0.050445 | 0.864354 | 0.875691 | +0.011337 |

### J03WMX

| Kondisi | Frame dinilai | Spell V1 | Spell V2 | Δ Spell | Macro V1 | Macro V2 | Δ Macro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bersih | 145967 | 0.414365 | 0.451830 | +0.037465 | 0.886097 | 0.893676 | +0.007579 |
| Bola dihilangkan acak 20% | 145967 | 0.437291 | 0.437255 | -0.000037 | 0.887313 | 0.887432 | +0.000119 |
| Bola hilang 2 detik tiap 20 detik | 145967 | 0.416015 | 0.444990 | +0.028975 | 0.881901 | 0.885858 | +0.003957 |
| Koordinat x bola hilang acak 20% | 145967 | 0.420769 | 0.420365 | -0.000404 | 0.884985 | 0.884942 | -0.000043 |
| Pemain dihilangkan acak 20% | 145967 | 0.402754 | 0.404117 | +0.001363 | 0.893220 | 0.894255 | +0.001035 |
| Jitter posisi σ=0,25 meter | 145967 | 0.388454 | 0.420729 | +0.032275 | 0.808946 | 0.827774 | +0.018829 |
| Gap 1 detik tiap 60 detik | 143492 | 0.454530 | 0.490811 | +0.036281 | 0.885922 | 0.892885 | +0.006962 |

Perturbasi dilakukan pada observasi sebelum ekstraksi fitur, seed evaluasi 2027 sama untuk kandidat berpasangan. Mask/gap dan label dinilai pada timeline yang sama untuk A/R; hitungan frame dan possession GT antar-kandidat diperiksa sama. Gap mengurangi jumlah frame yang dinilai; bandingkan A/R dalam kondisi yang sama. Kelulusan tidak berarti semua metrik meningkat pada setiap kondisi. Semua pengaman rinci tersedia di CSV.

Kelemahan absolut masih terlihat: Spell F1 J03WQQ pada bola hilang acak dan koordinat x bola hilang acak hanya sekitar 0,086 pada kedua versi. Guard relatif terhadap A tidak menjamin kualitas absolut yang baik. Pada data bersih, F1 D R juga turun 0,001708 pada J03WQQ dan 0,006017 pada J03WMX, masih di dalam batas 0,01. Fakta-fakta ini adalah diagnosis eksternal; kriteria dan keputusan kandidat tidak diubah setelah melihatnya.

## Dua kegagalan C yang menjadi sasaran perbaikan

| Kondisi J03WQQ | Metrik | A/V1 | C sendiri | Δ C−A | R/V2 | Δ R−A | Minimum lolos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bola hilang 2 detik tiap 20 detik | F1 D | 0.943398 | 0.929799 | -0.013599 | 0.942203 | -0.001195 | 0.933398 |
| Pemain dihilangkan acak 20% | Transition F1 @12 | 0.385044 | 0.372197 | -0.012846 | 0.385103 | +0.000059 | 0.375044 |

C sendiri mempunyai Spell F1 bersih lebih tinggi dari R, tetapi tetap ditolak karena dua regresi tersebut. R dipilih karena memenuhi seluruh kriteria, bukan hanya karena peringkat skor bersih tertinggi. Lima kandidat decoder B dari eksperimen awal juga ditolak oleh gate; tidak ada pemilihan B baru dalam laporan ini.

## Audit seluruh batas kelulusan

| Data | Kriteria | Lulus | Margin terkecil pada | Δ aktual | Δ minimum | Sisa margin |
| --- | --- | --- | --- | --- | --- | --- |
| J03WQQ | 37 | 37 | frame_gap1s_every60s / overall / F1 D | -0.001776 | -0.010000 | 0.008224 |
| J03WMX | 37 | 37 | frame_gap1s_every60s / overall / F1 D | -0.006123 | -0.010000 | 0.003877 |

Margin = Δ aktual − Δ minimum. Nilai positif berarti masih di sisi lulus; bukan probabilitas keyakinan statistik. Keputusan yang dihitung ulang identik dengan selection.json dan decision.json tersimpan. Tidak ada seleksi ulang berdasarkan hasil resmi. Confidence tinggi untuk kecocokan artefak/keputusan; generalisasi ke banyak pertandingan atau kualitas resmi belum terbukti oleh dua laporan ini.

## Identitas dan provenance

- V1 model SHA-256: `d1f4fdd7e9d7ea1a18b42e505dd9bef741379ff4bf81a039530f69afcc6a6f10`.
- V2/R model SHA-256: `04e2510928af168c7cd1e3d9ebb698591b336f52a2344853dce1fd8acd0fa88f`.
- Decoder bersama SHA-256: `2aa5b5f1c777fe9c2c71b7bdb894082b22b967dae5b67664be9b5c7871bafa74`.
- Bundle adapter V2 r1 memakai hash model/decoder V2 yang sama. Revisi parser bukan eksperimen classifier baru; angka DFL di atas bukan evaluasi baru adapter pada data resmi.

Sumber utama: `external_artifacts/v2/refinement-run1/{protocol,metrics,selection}.json` dan `external_artifacts/v2/J03WMX-refined-assessment-v1/{protocol,metrics,decision}.json`. Sumber diagnosis C: `external_artifacts/v2/run1/metrics.json`. Hash file yang dipakai diverifikasi terhadap ready manifest masing-masing. Implementasi gate yang digunakan untuk pemeriksaan ulang juga cocok dengan hash source protokol R.

Protokol yang mendahului R: [protokol_refinement_v2.md](protokol_refinement_v2.md). Tidak ada confidence interval atau klaim signifikansi statistik yang baru dihitung. Augmentasi menghasilkan view tambahan dari dua pertandingan training, bukan pertandingan independen tambahan.

Artefak audit laporan: `external_artifacts/v2/external-comparison-v1/summary.json` dan `gate_audit.csv` (74 baris kriteria). Laporan disusun dari bukti eksternal yang sudah dibekukan; model, parameter, threshold, dan file seleksi tidak diubah.
