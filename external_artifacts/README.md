# Artifact untuk melanjutkan proyek

Folder ini ikut Git untuk source rilis, laporan audit eksternal, referensi
anotasi, serta klip review yang provenance-nya sudah diperiksa. File manifest
dan artifact lama tidak diedit. Git mempertahankan byte folder audit/rilis
tanpa konversi line ending agar checksum tetap cocok setelah clone.

Mulai dengan `KONTEKS_PERCAKAPAN.md` dan `HANDOFF.md` di root proyek.

- `release-readiness-20261112/source/`: salinan handoff yang byte-nya dipulihkan
  dan terikat manifest. Bundle V2/R r1 ada di dalamnya.
- `release-readiness-20261112/validation-final/`: hasil pemeriksaan sintetis,
  verifier dan ZIP rilis yang sudah diverifikasi.
- `v3/`: bukti audit eksternal, source penerbit terpin, referensi geometri,
  pengukuran ulang dan pilot review possession. Tidak ada model possession V3
  yang sudah dilatih atau dipromosikan.
- `v3/117093-possession-review-pilot-20261113/`: enam klip Q01-Q06 tersedia
  setelah clone. Review masih kosong; TARGET berada pada detik 6.00.

Video/gambar SoccerTrack dan turunannya menggunakan CC BY 4.0, kredit AtomScott
dan kontributor. Dataset commit
325bd4c57ee8e135ab652f3921d274526ada496b:
https://huggingface.co/datasets/atomscott/soccertrack-v2/tree/325bd4c57ee8e135ab652f3921d274526ada496b
Lisensi dan source penerbit tersimpan pada direktori audit source. Perubahan
lokal berupa ekstraksi frame/klip, header frame pada klip, anotasi operator dan
laporan; PNG raw tanpa overlay disimpan terpisah. Klip tidak memuat audio.

Runtime/venv dan payload mentah pada `Soccertrack V2/` tetap lokal. Teman yang
melanjutkan perlu menyiapkan runtime sesuai requirements dan memperoleh berkas
dataset melalui akun sendiri; URL, ukuran dan checksum ada di `docs/`.
Data resmi, GT, output per-frame resmi, salinan repo lain dan arsip belum
diaudit tetap diabaikan. Jangan menghilangkan pemeriksaan checksum atau
memakai skor resmi untuk pengembangan.

`handoff-inventory-20261114.json` mencatat ukuran/SHA256 file eksternal yang
disertakan pada commit handoff ini. Inventory tidak memasukkan dirinya sendiri.
