# Audit video eksternal SoccerTrack 117092 babak pertama

12 November 2026 sekitar 21.01 WIB. Input hanya video eksternal training match
117092 yang diunduh pengguna pada lokasi eksplisit dalam manifest. Tidak ada
data resmi, fitting, training, detector atau fusion dijalankan.

## Integritas dan runtime

- Rilis dataset v1.2, commit `325bd4c57ee8e135ab652f3921d274526ada496b`.
- Berkas `Soccertrack V2/videos/117092/117092_panorama_1st_half.mp4`.
- Ukuran tepat 6.687.957.167 byte.
- SHA-256 lokal cocok dengan hash Git LFS Details yang ditranskripsikan pengguna:
  `9fabe074b0c6fc5812a602dd4119f3e6cb724e2f06b8a3a1eb9358b9734c036e`.
  Hash penerbit tidak diambil secara mandiri oleh agent.
- Runtime audit terpisah `runtime/v3-geometry-venv/`: Python 3.11.6, NumPy 2.4.6,
  opencv-python-headless 4.10.0.84. Requirement disimpan pada
  `requirements-v3-audit.txt`; cache/temp tetap di drive proyek. Tidak ada
  bobot pretrained diunduh. Runtime dan artifact V2 tidak diubah.

`tools/audit_soccertrack_video.py` memeriksa hash video dan delapan berkas kecil
sebelum decoder membaca video. Input dibaca dari allowlist manifest; tidak ada
pencarian dataset atau pemilihan file otomatis. Semua output baru berada di
`external_artifacts/v3/soccertrack-video-audit-20261112-r2/`.

## Hasil stream dan decoding

| Pemeriksaan | Hasil |
| --- | --- |
| FPS container/backend | 25 |
| Frame count container/backend | 67.375, sesuai changelog v1.2 |
| Dimensi | 3840 × 1906 |
| Indeks sampel 0-based | 0, 30000, 67374 |
| Decode sampel | Ketiganya berhasil, dimensi sama |
| Seluruh video didekode | Tidak; jangan menganggap 67.375 sebagai hitungan decode penuh |
| Alignment BAS terhadap kontak bola/video | Belum diverifikasi empiris |

Posisi frame/timestamp yang dilaporkan backend disimpan dalam report. Request
seek dan keberhasilan decoding bukan pembuktian independen identitas setiap
frame ataupun ketepatan kejadian BAS. Catatan changelog mengenai clock awal
dan konversi frame 1-based tetap berlaku. Preview berskala setengah, sedangkan
diagnosis numerik dihitung dalam piksel asli.

## Diagnosis proyeksi tetap

Rantai yang diaudit berasal dari source penerbit: koordinat sudut lapangan
→ H → piksel undistorted → inverse Knew → OpenCV fisheye K/D → piksel raw.
Tidak mencoba memilih rantai alternatif berdasarkan residual dan tidak refit.
OpenCV memakai `allow_pickle=False` melalui NumPy untuk membaca parameter;
object-array rvecs/tvecs tetap tidak dibuka.

Pada 65 keypoints penerbit, residual raw median **70,47 px**, p95 **331,27 px**,
maksimum **358,79 px**. OpenCV mereproduksi hasil eksplorasi NumPy sebelumnya.
Overlay pada sampel frame 30000 memperlihatkan pergeseran besar di sisi dekat
kamera untuk rantai tersebut. Ini bukti bahwa proyeksi belum siap dipakai,
bukan bukti mandiri penyebab error. Hash cocok menyingkirkan ketidakcocokan
payload terhadap transkripsi penerbit, tetapi belum memastikan H dan Knew
dibuat sebagai satu kontrak atau model fisheye tunggal memadai pada panorama.

File `geometry-diagnostic.jpg` menampilkan keypoints fitting hijau, proyeksi
tetap merah, dan garis penghubung kuning. Keypoints ini digunakan penerbit
untuk fitting; residualnya **bukan metrik holdout**, bukan akurasi geometri
independen dan bukan gate yang membuktikan peningkatan possession.

## Gate dan langkah berikutnya

Akses video, integritas, dan schema/stream kini lolos pemeriksaan yang disebutkan.
Geometri produksi masih terblokir oleh kontrak transformasi dan target
independen. Tidak perlu mengunduh GSR, babak kedua, pertandingan lain, atau
bobot detector untuk menyelesaikan diagnosis ini.

Pekerjaan terkecil berikutnya: audit kecocokan provenance H/Knew dan susun
referensi geometri pada gambar eksternal yang tidak dipakai fitting. Bila
memerlukan anotasi baru, gunakan gambar raw tanpa overlay proyeksi, catat
provenance annotator/frame/fit=false, dan jangan menyesuaikan target agar
mendekati prediksi. Bekukan metrik dan protokol sebelum menilai referensi itu.
Jika kontrak tidak dapat dibuktikan atau referensi tidak cukup, cabang berhenti
pada diagnosis; tidak dibuat loader produksi berdasarkan tebakan.

Target bola terukur dan possession H/A/D padat independen tetap belum tersedia.
Video dan BAS sendiri belum meluluskan cabang possession multimodal. DFL hanya
menjadi pemeriksaan fallback saat modalitas tambahan tidak tersedia. V2/R r1
tetap kandidat pengumpulan dan lolos verifier runtime setelah audit ini.

Hasil tersimpan: `report.json`, tiga preview frame eksternal, dan
`geometry-diagnostic.jpg`. Input video/kalibrasi tidak diedit. Hasil negatif
dipertahankan dan tidak dipakai untuk klaim skor resmi.
