# Hasil pengukuran ulang referensi 117093

Sebanyak 18/18 pasangan valid; missing 0, exposure sesi ulang 0 berdasarkan
self-report operator. Tidak membuka koordinat pertama atau overlay selama
sesi ulang dikonfirmasi dengan jawaban "tidak keduanya". Blinding tidak
diverifikasi mandiri; operator sebelumnya sudah pernah melihat/mengukur gambar.

| Lingkup | n | Median absolut (px) | p95 absolut (px) | Maksimum (px) |
| --- | ---: | ---: | ---: | ---: |
| Semua pasangan | 18 | 1.00 | 2.15 | 3.00 |
| center_circle | 3 | 0.00 | 0.90 | 1.00 |
| far_touchline_y0 | 3 | 1.00 | 1.00 | 1.00 |
| halfway_x52.5 | 3 | 2.00 | 2.00 | 2.00 |
| left_penalty_edge_x16.5 | 3 | 0.00 | 0.00 | 0.00 |
| near_touchline_y68 | 3 | 2.00 | 2.90 | 3.00 |
| right_penalty_edge_x88.5 | 3 | 0.00 | 0.90 | 1.00 |
| Frame 7500 | 6 | 1.00 | 2.75 | 3.00 |
| Frame 37500 | 6 | 0.00 | 2.00 | 2.00 |
| Frame 60000 | 6 | 0.50 | 1.75 | 2.00 |

Selisih bertanda = pengukuran kedua dikurangi pertama pada sumbu yang
diukur ulang. Median selisih bertanda keseluruhan 0 px. p95 menggunakan
interpolasi linear indeks 0,95*(n-1), sesuai protokol sebelum pengukuran.

Hasil hanya deskriptif pada point 2 dari enam fitur di tiga frame satu kamera.
Tidak mengukur akurasi absolut, jarak normal kurva, error dalam meter, atau
bias bersama. Tiga pasangan per fitur tidak memberi estimasi tail yang kuat.
Crop dilokalisasi memakai pengukuran pertama; independensi penuh tidak diklaim.
Reviewer assistant telah melihat diagnosis model dan koordinat pertama.

Tidak ada refit, penyesuaian anotasi pertama, pembacaan model atau scoring
geometri. Maksimum 3 px bukan toleransi produksi. Kebutuhan downstream masih
diperlukan untuk menetapkan anggaran error sebelum evaluasi kandidat. Target
possession independen tersinkron belum tersedia. Tidak ada bukti kenaikan
Spell F1. V2/R adapter r1 tetap kandidat pengumpulan.

Snapshot referensi pertama dan raw source tidak diubah. report.json memuat
semua pasangan, kelompok, provenance dan hash source. Salinan input CSV, jurnal,
protokol, manifest task dan source alat analisis disimpan di sini.
Sebelas pemeriksaan validator/statistik lulus, termasuk penolakan input tidak
valid dan cross-check median/p95 terhadap implementasi statistics Python.

Reproduksi dari root proyek dengan output baru (direktori parent harus ada):

```powershell
& runtime/v2-r1-venv/Scripts/python.exe -I -B tools/audit_annotation_repeatability.py --task external_artifacts/v3/117093-repeatability-task-20261113 --output external_artifacts/v3/117093-repeatability-analysis-20261113/reproduced-report.json
```

Hasil reproduksi adalah file tambahan dan tidak termasuk snapshot manifest awal.
Data eksternal SoccerTrack v1.2, CC BY 4.0, kredit AtomScott dan kontributor;
dataset/source commit dan URL primer berada pada manifest download 117093
yang diikat snapshot referensi. Pengukuran kedua dilakukan operator proyek.
