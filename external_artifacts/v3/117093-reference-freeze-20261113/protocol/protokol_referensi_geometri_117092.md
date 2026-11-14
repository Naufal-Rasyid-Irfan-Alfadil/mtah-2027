# Protokol pembuatan referensi geometri eksternal 117092

Status: protokol konstruksi referensi, belum dataset evaluasi beranotasi.
Tidak ada gate akurasi yang dinyatakan lulus dan tidak ada scoring possession.

## Tujuan dan data tetap

Ukur kesesuaian geometri terhadap pengukuran piksel baru, terpisah dari 65
keypoints fitting penerbit. Hanya video training eksternal 117092 babak pertama
SoccerTrack v1.2 dipakai. Hash video/kalibrasi dan commit sudah dipin pada
manifest download; kalibrasi tetap selama pengumpulan anotasi.

Paket berisi PNG raw ukuran asli untuk frame video 0-based **7500, 37500, 60000**
(menit 5, 25, 40 pada 25 fps). Gambar tidak diberi overlay prediksi. Memilih tiga
waktu ini tidak membuat tiga kamera atau pertandingan independen: seluruhnya
tetap satu kamera training. Jangan menyebutnya untouched cross-match test.

## Anotasi yang diperlukan

Isi `reference-task/annotations.csv` dari gambar raw. Untuk masing-masing gambar,
pilih tiga piksel pada pusat garis cat yang terlihat untuk tiap fitur:

- Touchline dekat kamera: y=68 m.
- Touchline jauh: y=0 m.
- Garis tengah: x=52,5 m.
- Sisi tegak kotak penalti kiri: x=16,5 m, y dalam 13,84..54,16 m.
- Sisi tegak kotak penalti kanan: x=88,5 m, rentang y yang sama.
- Lingkaran tengah: pusat (52,5;34), radius nominal 9,15 m. Radius nominal
  perlu ditandai sebagai asumsi dimensi garis, bukan hasil survey lapangan.

Jumlah maksimum 54 slot. `pixel_x`/`pixel_y` memakai PNG asli 3840×1906 dengan
origin sudut kiri atas. Catat `visibility` sebagai visible/occluded/ambiguous,
identitas annotator, dan apakah annotator sudah melihat proyeksi. Slot yang
tidak jelas dibiarkan tanpa koordinat; jangan menebak posisi di balik pemain.
Pilih lokasi yang tersebar; hindari hanya menandai bagian tengah fitur.

Annotator tidak menggunakan output H/pose, hasil tracking, atau snap ke prediksi
untuk menentukan piksel. Catat jika blind annotation tidak dapat dipenuhi;
jangan mengklaim blind secara otomatis. `used_for_fitting` wajib false.
Pengukuran yang berjarak kurang dari 20 piksel raw terhadap salah satu 65
keypoints fitting dikeluarkan dari set baru; ini hanya aturan pemisahan lokasi,
bukan jaminan independensi statistik penuh. Jangan menggeser anotasi supaya
lolos aturan; pilih lokasi baru dari gambar raw jika fitur jelas.

## Validasi sebelum evaluasi

Referensi belum boleh dinilai sampai koordinat/visibility diperiksa, hash gambar
dan provenance lengkap, serta representasi koordinat fitur terbukti. Anotasi
berulang perlu ditinjau untuk ketidakpastian piksel; nilai yang tidak jelas
tetap missing. Manifest tugas sekarang mencatat nol anotasi valid.

Metrik yang direncanakan adalah jarak piksel anotasi ke kurva lapangan yang
diproyeksikan, dilaporkan median/p95 per fitur dan per frame. Ground-plane error
dalam meter perlu inverse projection dan pemeriksaan conditioning tersendiri.
Round-trip tidak menjadi pengganti target. Titik lingkaran hanya diuji terhadap
kurva lingkaran; tidak diasumsikan punya sudut/world-coordinate yang diketahui.

Dua representasi tetap untuk diagnosis: H rilis + redistortion, dan pose tersimpan
melalui fisheye.projectPoints. H yang diturunkan secara aljabar dari pose hanyalah
pemeriksaan ekuivalensi, bukan konfigurasi ketiga. Tidak refit atau tuning pada
referensi ini. Hasil nanti hanya evaluasi komponen pada satu kamera training;
tidak cukup untuk promosi possession.

Ambang numerik produksi belum ditetapkan karena ketidakpastian anotasi dan
target downstream belum tersedia. Bekukan anggaran error/geometri sebelum
scoring kandidat atau keputusan promosi. Selama itu, hasil hanya diagnosis dan
cabang produksi tetap terblokir; tidak melonggarkan ambang setelah hasil dilihat.

Paket tugas tidak berisi GT H/A/D atau anotasi bola. Dataset possession
independen yang tersinkron tetap menjadi gate berbeda. V2/R tidak berubah.
