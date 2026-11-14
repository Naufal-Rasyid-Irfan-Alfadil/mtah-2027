# Konstruksi referensi geometri 117093

Dataset eksternal SoccerTrack v1.2 dipin pada manifest download 117093. Peran
lokal external geometry development, publisher split validation. Prosedur
konstruksi pada protokol 117092 dipakai kembali dengan penggantian identitas
dan ukuran yang eksplisit berikut; label/pengukuran 117092 tidak dipakai ulang.

- Paket tugas: `external_artifacts/v3/117093-reference-task-20261113/`.
- PNG raw 4096×1080, origin kiri atas; frame 0-based 7500/37500/60000.
- Enam fitur per gambar, maksimum tiga titik per fitur. Mulai dari satu gambar;
  tidak perlu menebak atau memaksakan 54 titik bila garis tidak terlihat.
- Isi pixel_x/y dari gambar raw, visibility visible/occluded/ambiguous,
  annotator dan annotator_seen_predictions. used_for_fitting tetap false.
- Jangan memakai gambar preview, overlay proyeksi, lokasi pemain/bola, atau
  perpanjangan garis tersembunyi untuk mengisi referensi.
- Untuk pemisahan lokasi, ukur jarak dari keypoints fitting **117093**, bukan
  117092. Di bawah 20 piksel raw dikeluarkan. Aturan ini bukan bukti independensi
  statistik penuh; tiga frame tetap satu kamera.
- Garis dekat y=68, jauh y=0; halfway x=52,5; sisi kotak penalti x=16,5/88,5
  pada rentang y=13,84..54,16. Center circle berpusat 52,5/34 dan radius nominal
  9,15 m adalah asumsi ukuran; tidak dianggap hasil survey lapangan.

Pengukuran baru harus diperiksa ketidakpastian/repeatability dan provenance-nya.
Bekukan anggaran error sebelum scoring/promosi; belum ada gate numerik produksi
yang dinyatakan lulus. Metrik yang direncanakan tetap median/p95 jarak anotasi
ke kurva terproyeksi per fitur/frame; tidak mengubah posisi anotasi agar cocok
prediksi. Direct pose dan H rilis hanya dua representasi tetap tanpa refit.

Template awal kosong. Tidak ada GT H/A/D atau bukti manfaat possession dalam
paket ini. V2 tetap kandidat pengumpulan setelah cutoff kandidat baru terlewati.
