# Protokol perbaikan V2: satu router observasi

Protokol ini ditetapkan setelah diagnosis kegagalan C pada J03WQQ, sebelum
evaluasi kandidat R. Skor resmi tidak dipakai untuk memilih aturan atau ambang.

Hanya satu kandidat baru dievaluasi: R memakai posterior C pada frame dengan
jendela bola lengkap dan jumlah pemain teramati memadai; selain itu memakai
posterior A. Posterior yang dipilih diteruskan ke decoder V1 yang sama. Kedua
classifier HGB tetap; tidak ada training ulang, learned blending, atau sweep.

Jendela bola memakai `ball_xy_fraction_1s == 1` dari 25 frame terakhir yang
tersedia. Jendela termasuk frame sekarang, dapat lebih pendek di awal run,
dan direset pada batas pertandingan/babak atau gap frame/waktu. Jumlah pemain
lengkap dibandingkan dengan modus per tim dari observasi training J03WOH dan
J03WPY saja. Kedua pertandingan training memberikan modus 11 untuk kedua tim.
Missing tidak diisi; tidak ada pelacakan identitas slot anonim. Empat fitur
konteks C tidak diubah. Input tetap posisi/keteramatan yang dapat dihitung dari
ATD. Video, homography, Smart Tagging, dan target bukan fitur masukan.

Hipotesis eksternal: C memperoleh manfaat dari konteks jarak ketika observasi
memadai, sedangkan A lebih stabil pada kehilangan observasi. Diagnosis burst
menunjukkan 3.667 frame target D dengan bola tidak lengkap menjadi H/A oleh C,
dibanding 293 oleh A. Ini diagnosis J03WQQ, bukan estimasi pada pertandingan resmi.
Aturan tersebut konservatif dan dapat membuang sebagian manfaat C pada tim
yang memang bermain dengan lebih sedikit pemain; risiko ini akan dilaporkan.

Seleksi memakai kembali kedua babak J03WQQ, berpasangan pada ketujuh kondisi
stres lama dan seed 2027. Minimum kenaikan Spell F1 bersih adalah 0,01. Macro
F1, F1 D, Transition F1 toleransi 12/25 frame, setiap babak bersih, dan Spell F1
setiap kondisi stres mempertahankan batas regresi maksimum 0,01. Tidak ada
pelonggaran batas atau kandidat susulan jika R gagal. Prediksi disimpan sebelum
target dimuat untuk penilaian.

J03WMX dipilih sebagai penilaian eksternal tambahan berdasarkan urutan ID dari
dua pertandingan katalog yang belum ditemukan dalam catatan yang tersedia,
tanpa melihat performanya. Katalog publik Figshare artikel 28196177 versi 1
menyediakan J03WMX dan J03WN1; keduanya tidak ditemukan pada dokumentasi/source,
nama artefak eksternal, lokasi raw eksternal, maupun pencarian riwayat Git yang
dilakukan sebelum eksperimen. Riwayat proyek lama tidak diketahui. Karena itu,
hasil J03WMX tidak akan disebut test yang dipastikan belum pernah digunakan.

Penilaian J03WMX dilakukan sekali setelah R lolos pengembangan. Model, source,
dan decoder diikat hash sebelum prediksi. Seluruh prediksi A/R untuk kedua babak
dan tujuh kondisi disimpan sebelum target dipakai untuk scoring. Kriteria rilis:
Spell F1 bersih R minimal sama dengan A; metrik pengaman dan skor per babak
mempertahankan batas regresi 0,01. Hasilnya hanya meluluskan/menolak rilis;
tidak digunakan untuk penyesuaian kandidat. Jika gagal, tidak ada bundle R
yang dipromosikan.

Bundle yang lulus akan memuat kedua classifier, aturan router, decoder tetap,
kontrak fitur, paket dependency yang sudah dipin, source yang sama dengan
eksperimen, serta provenance penilaian. Pembuat bundle menolak source yang
ditambah, dihapus, atau diubah setelah evaluasi dan menolak router tanpa
penilaian tambahan yang memenuhi syarat. Pengguna menjalankan inferensi resmi
secara lokal setelah paket siap.

Sumber dataset dan atribusi: Bassek, Rein, Weber, dan Memmert (2025),
*An integrated dataset of spatiotemporal and event data in elite soccer*,
Scientific Data 12:195, DOI 10.1038/s41597-025-04505-y; data DFL/Sportec melalui
Figshare DOI 10.6084/m9.figshare.28196177. Katalog yang diambil pada 7 November
2026 menyatakan CC BY 4.0. Metadata katalog tersimpan di
`external_artifacts/v2/catalog-20261107.json`; atribusi DFL dan publikasinya
dipertahankan dalam provenance.
