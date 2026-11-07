# Daftar Game & Cara Main

Satu server, tiga pintu masuk di halaman depan:

| Pintu | Isi | Alamat |
|---|---|---|
| **Arena Mabar** | 11 game main bareng. Setiap kursi boleh manusia atau bot, boleh dicampur. | `#main` |
| **Suit Bot Arena** | Adu bot batu-gunting-kertas dengan editor blok/Python, replay animasi, turnamen, liga. | `#suit` |
| **Kilas Pasar** | Simulasi trading dengan candle asli kripto & saham. | `#pasar` |

Isi dokumen:

- [Arena Mabar: cara kerja room, kursi, dan bot](#arena-mabar-cara-kerja)
- Game Arena Mabar:
  [Suit Live](#1-suit-live) ·
  [Poker Hold'em](#2-poker-holdem) ·
  [Tenggelamkan Kapal](#3-tenggelamkan-kapal) ·
  [Arena Robot Grid](#4-arena-robot-grid) ·
  [Petualangan Kartu Nusantara](#5-petualangan-kartu-nusantara) ·
  [Pasar Malam Tycoon](#6-pasar-malam-tycoon) ·
  [Lelang Rahasia](#7-lelang-rahasia) ·
  [Rebutan Lahan](#8-rebutan-lahan) ·
  [Dilema Kas Desa](#9-dilema-kas-desa) ·
  [Angka Dua Pertiga](#10-angka-dua-pertiga) ·
  [Pasar Malam Sepi](#11-pasar-malam-sepi)
- [Suit Bot Arena](#suit-bot-arena)
- [Kilas Pasar](#kilas-pasar)

Panduan bot lengkap per game (untuk ditempel ke AI) ada di [docs/bot/](bot/README.md), dan juga bisa disalin dari tombol
**📋 Salin panduan untuk AI** di dalam game.

---

## Arena Mabar: cara kerja

### Membuat dan bergabung ke room

1. Buka **Arena Mabar**, pilih game, isi nama, atur aturan (atau biarkan default), lalu **Buat room**.
2. Bagikan **kode 5 huruf** atau tombol **Salin link undangan**. Teman membuka link itu, atau mengetik kode di halaman Arena Mabar
   lalu menekan **Gabung**. **Tonton saja** masuk sebagai penonton.
3. Host menekan **▶ Mulai** setelah kursinya cukup.

### Kursi: manusia, bot, atau campur

- Setiap orang yang bergabung otomatis mendapat **kursi manusia**: kamu sendiri yang memutuskan setiap langkah lewat tombol di layar.
- **🤖 Pakai bot** mengganti kursimu menjadi bot. Kamu menulis kodenya di editor (atau memilih template), lalu tinggal menonton.
  **🙂 Main sendiri** mengembalikannya.
- **Tambah bot** mengisi kursi kosong dengan bot tambahan, dari template atau dari kodemu. Satu orang boleh menambah sampai 7 bot.
- Jadi semua kombinasi boleh: semua manusia, semua bot, atau campur. Contoh: 2 teman main poker langsung melawan 3 bot buatan teman lain.
- Kalau semua kursi bot dan **jeda langkah bot = 0**, server langsung menghitung match sampai selesai lalu memutar replay.

### Waktu dan aksi bawaan

- Manusia punya waktu per langkah (default per game, bisa diatur host). Hitung mundurnya disamakan dengan jam server, jadi tetap tepat
  walaupun jam HP-mu tidak pas.
- **Submit otomatis:** kalau waktu habis sebelum kamu menekan tombol kirim, pilihan yang sedang terlihat di layar (angka di pemilih,
  alokasi pasukan, tawaran, dagangan, susunan kapal) dikirim otomatis, **termasuk angka awal yang belum kamu ubah** (misalnya tawaran 0 di
  Lelang, sepertiga batas di Dua Pertiga). Kalau layar belum berisi pilihan, **aksi bawaan** yang dipakai, misalnya check/fold di poker,
  tutup lapak di tycoon, diam di robot, bagi rata di Rebutan Lahan yang masih 0 semua.
- **Jawaban ditandai nomor langkah.** Klik yang terlambat (dikirim tepat setelah ronde ditutup) ditolak dengan pesan *Terlambat* dan
  tidak terbawa ke ronde berikutnya. Dulu klik telat seperti itu bisa membuat ronde berikutnya macet: tombol tidak bisa dipilih dan
  refresh/login ulang tidak menolong. Sekarang tinggal pilih lagi untuk ronde yang sedang berjalan.
- **Ubah jawaban:** setelah mengirim, muncul **✅ Jawabanmu: …** dan tombol **✏️ Ubah**. Selama ronde belum ditutup, kamu boleh
  mengganti jawaban; yang dipakai adalah jawaban terakhir.
- **⏸ Jeda match** (host): waktu semua pemain berhenti sampai host menekan **▶ Lanjutkan match**.
- **🔔 Notifikasi giliran** (tombol di kepala room): HP bergetar, bunyi "bip", dan judul tab berkedip saat giliranmu. Tekan 🔕 untuk mematikan.
- **Masuk lagi dengan nama yang sama** (dari link undangan atau kode room) mengembalikanmu ke kursimu sendiri, juga dari HP/tab lain.
  Kalau kursi itu masih tersambung di tempat lain, kamu ditanya dulu apakah mau mengambil alih (koneksi lama diputus). Nama yang dipakai
  akun lain tidak bisa diambil.
- **Koneksi putus** (layar HP mati, pindah aplikasi, sinyal hilang): browser memeriksa koneksi tiap 5 detik dan langsung menyambung ulang
  saat tab dibuka lagi. Selama putus, tombol aksi disembunyikan dan muncul tulisan "menyambung ulang", jadi tidak ada klik yang hilang
  diam-diam. Server menunggu pemain yang baru putus sampai 10 detik per langkah sebelum memakai pilihan terakhirnya/aksi bawaan;
  yang keluar dengan sengaja atau putus lebih dari 30 detik tidak ditunggu.
- **Jeda lihat hasil** (game ronde: Suit, Poker, Tycoon, Lelang, Rebutan Lahan, Kas Desa, Dua Pertiga, Pasar Malam Sepi): setelah setiap
  ronde semua pemain melihat hasilnya dulu (default 3–8 detik, bisa diatur host 0–30). Waktu ronde berikutnya baru mulai setelah jeda,
  jadi semua orang punya waktu berpikir yang sama. Tekan **Lanjut ▶** kalau sudah selesai melihat; kalau semua pemain manusia sudah
  menekan, ronde berikutnya langsung mulai.
- Game yang dimainkan bersamaan (lelang, suit, tycoon, dst.) menunggu semua manusia, lalu semua aksi dibuka sekaligus.
  Game bergiliran (poker, kapal) hanya menunggu pemain yang gilirannya.
- **Petualangan Kartu** berjalan **sendiri-sendiri**: setiap pemain jalan di petualangannya sendiri tanpa menunggu orang lain.

### Aturan kustom, kabut, dan preset

Setiap game punya banyak pengaturan selain jumlah ronde/pemain. Di lobby, host melihatnya dalam beberapa kelompok:

| Kelompok | Isi |
|---|---|
| **Dasar** | jumlah ronde, modal, ukuran papan, dan sejenisnya |
| **🌫️ Informasi** | *kabut perang*: apa saja yang disembunyikan (tawaran lawan, HP lawan, jadwal barang, jumlah pengunjung, …) |
| **⚖️ Aturan** | variasi cara menang/menghitung (median, harga kedua, benteng, sanksi, …) |
| **🎲 Kejutan** | kejadian acak dari seed (malam spesial, medan misteri, barang minus, power-up, …) |

- **Preset** satu klik: *Standar*, lalu preset tiap game seperti *Klasik*, *Kabut*, dan *Kacau*. **💾 Simpan preset** menyimpan
  pengaturanmu sendiri di browser ini untuk dipakai lagi.
- Semua pemain melihat **Aturan aktif**: daftar chip pengaturan yang berbeda dari bawaan, di lobby dan selama match, jadi tidak ada aturan
  tersembunyi. Yang dirahasiakan hanya *isinya* (misalnya tawaran lawan), bukan aturannya.
- Bot mendapat informasi yang sama dengan manusia di kursi itu: yang dirahasiakan berisi `None` di `info()`, dan fungsi bantu yang
  membutuhkan info rahasia juga mengembalikan `None`. Keacakan opsi kejutan tetap milik game (dari seed), bukan bot.
- Setelah match semua rahasia dibuka. Di replay ada pilihan **Sudut pandang**: *Semua rahasia terbuka*, *Penonton (berkabut)*, atau
  *Seperti dilihat <nama>* untuk memutar ulang match persis seperti yang dilihat satu pemain.

### Penonton dan reaksi

- Penonton melihat tampilan umum: kartu tertutup lawan, kapal, dan rahasia lain tetap tersembunyi. Host bisa mengaktifkan
  **Penonton melihat semua rahasia** (enak untuk siaran/nobar, tapi jangan dipakai kalau ada pemain yang ikut menonton dari HP lain).
- Semua orang di room bisa mengirim reaksi emoji (👏 😂 😮 🔥 😭 🤝 💀 🎉) yang melayang di layar semua orang.

### Setelah match

- Peringkat, skor, dan perubahan **rating liga** (kalau masuk akun).
- **Klasemen sesi** di lobby: kalau main beberapa match berturut-turut di room yang sama, setiap match memberi poin (juara = jumlah
  pemain − 1, terakhir = 0), plus jumlah juara dan jumlah main. Host bisa menekan **Ulang** untuk mulai dari nol.
- **Replay** langkah demi langkah dengan tombol putar, maju/mundur, dan kecepatan. Setiap frame menampilkan keadaan pada saat itu
  (termasuk riwayat sampai ronde itu saja).
- Rahasia yang dibuka di akhir: seed dek poker (bisa dicek di browser), susunan armada kapal, dek akhir kartu.
- **Log bot** milikmu: error per langkah, isi `print()`, dan jumlah langkah. Hanya pemilik bot yang melihatnya.

### Menulis bot

- Bot ditulis dengan **Python sederhana**. Setiap langkah, server memanggil fungsi `def aksi():` (Suit Live memakai `def pilih():`)
  dan memakai nilai yang dikembalikannya sebagai aksi.
- Semua yang boleh diketahui bot ada di `info()`. Setiap game juga punya **fungsi bantu**, misalnya `ekuitas()` di poker atau
  `langkah_ke(baris, kolom)` di robot. Daftarnya ada di tombol **Daftar fungsi** di editor.
- **Tanpa keacakan dan tanpa memori.** Tidak ada `random`, dan setiap langkah kode dijalankan dari nol. Bot yang sama dengan info yang sama
  selalu memilih aksi yang sama. Keacakan yang ada (kocokan kartu, peta, cuaca) milik **game**, diturunkan dari seed match.
- Bot error atau aksinya tidak valid → langkah itu memakai aksi bawaan. Error 3 kali berturut-turut → bot dimatikan sampai match selesai.
- **Latihan bot** (tab di halaman game) menjalankan botmu melawan template pilihanmu dan menampilkan replay serta log, tanpa perlu room.
- **Panduan bot** (tab di halaman game) berisi dokumen lengkap untuk ditempel ke AI: aturan, isi `info()`, fungsi, contoh bot.

### Akun dan liga

Masuk akun lewat menu **Kilas Pasar → Akun** (satu akun untuk semua game). Setiap match di room memperbarui **rating ELO** (mulai 1200)
per game untuk pemain yang masuk akun, termasuk kursi yang dimainkan bot milikmu. Papan peringkat ada di tab **Liga** tiap game.

---

## 1. Suit Live

**2–8 pemain · bersamaan · `def pilih():`**

Batu-gunting-kertas sirkular rame-rame, sama seperti Suit Bot Arena, tetapi bisa dimainkan langsung oleh manusia.

- Setiap ronde semua memilih **BATU**, **GUNTING**, atau **KERTAS** bersamaan (tekan salah satu dari tiga tombol besar).
- Setiap pemain yang senjatanya dikalahkan kehilangan HP (default 100). HP itu dibagi rata ke golongan yang mengalahkannya;
  sisa pembagian +1 ke pemenang ber-HP terendah. Kalau ketiga senjata keluar, setiap golongan sekaligus menang dan kalah.
- HP 0 = gugur. Yang terakhir hidup menang, atau HP terbanyak saat batas ronde (default 40).
- **Mode event** (diatur host): Taruhan Ganda, Pikun, Kilat, Darah Tipis, Kabut, Kejutan (lihat [Suit Bot Arena](#mode-event)).
- Bot Suit Bot Arena bisa dipakai apa adanya: library-nya sama (`pengalah`, `jumlah_terakhir`, `senjata_terbaik`, dst.).

Tips: di room kecil, golongan senjata yang sedikit mendapat bagian HP paling besar. Lihat jumlah tiap senjata di ronde lalu.

Opsi kustom: **HP lawan samar** (dibulatkan ke kelipatan 10% HP awal), **batas ronde rahasia** (±25%), **pemimpin jadi buruan**
(HP tertinggi yang kalah kehilangan HP ekstra), **kejutan ronde** (ronde ganda, ronde terbalik: siapa mengalahkan siapa dibalik, atau senjata
terlarang: yang memakainya kehilangan HP).

## 2. Poker Hold'em

**2–8 pemain · bergiliran · `def aksi():`**

Texas Hold'em no-limit. Default: 1000 chip, blind 10/20 naik ×1,5 setiap 10 tangan, maksimal 40 tangan.

- Dua kartu tertutup per pemain, lalu flop (3 kartu), turn, river. Tangan terbaik dari 5 kartu menang.
- Di giliranmu: **Fold**, **Check**/**Call**, **All-in**, atau geser **Raise ke** lalu tekan tombol raise.
  Tombol cepat: Min, ½ pot, Pot.
- Side pot dihitung otomatis untuk pemain yang all-in. Pemain yang chipnya habis tersingkir. Peringkat akhir menurut chip.
- **Keadilan dek:** sebelum tangan pertama, hash dari seed diumumkan (`hash dek` di pojok meja). Di layar hasil, seed dibuka dan tombol
  **Cek sendiri di browser** menghitung ulang hash-nya, jadi urutan kartu terbukti tidak diatur di tengah permainan. Semua kartu tertutup
  setiap tangan juga dibuka di akhir.
- Waktu habis: check kalau bisa, kalau tidak fold.

Fungsi bot andalan: `kekuatan_awal()` (0..1 sebelum flop), `nilai_tangan()`, `ekuitas(sampel)` (peluang menang lewat simulasi tetap),
`peluang_pot()` (harga call dibanding pot), `naik(ke)`.

Opsi kustom: **short deck** (kartu 2–5 dibuang; flush mengalahkan full house, A-6-7-8-9 straight), **ante** (% big blind dari semua
pemain tiap tangan), **bounty** (setiap pemain yang tersingkir menambah skor pemenang pot terbesar di tangan itu; skor = chip + bounty),
**chip lawan samar** (dibulatkan ke kelipatan 5× big blind; taruhan dan pot tetap pasti).

## 3. Tenggelamkan Kapal

**2 pemain · bergiliran · `def aksi():`**

- **Fase susun:** pilih kapal di daftar, atur arah (mendatar/menurun), lalu klik papanmu. **Acak** menyusun otomatis, **Siap!** mengirim.
  Kapal tidak boleh bertumpuk atau keluar papan.
- **Fase tembak:** bergantian klik petak di papan lawan. Hasilnya meleset (titik biru), kena (oranye), atau tenggelam (merah).
  Ukuran kapal yang tenggelam diumumkan.
- Yang pertama menenggelamkan seluruh armada lawan menang. Pengaturan: ukuran papan 6–12, armada kecil/standar/besar, dan opsi
  "kena = tembak lagi".
- Waktu habis: armada disusun acak / tembakan ke petak acak yang belum ditembak.

Tips bot: tembak pola papan catur dulu, lalu buru petak di sekitar tembakan yang kena (`tetangga(baris, kolom)`).

Opsi kustom: **kabar tenggelam** (ukuran diumumkan / hanya "tenggelam" / tidak diumumkan), **salvo** (tembakan per giliran = jumlah
kapalmu yang masih hidup), **sonar** (sekian kali per pemain; memakai satu tembakan untuk menghitung petak kapal lawan yang belum kena di area 3×3),
**ranjau** (menembak ranjau lawan = sisa tembakanmu hangus dan giliranmu berikutnya dilewati).

## 4. Arena Robot Grid

**2–8 pemain · real-time (semua bergerak bersamaan) · `def aksi():`**

- Peta petak dengan tembok, simetris supaya adil. Default 120 giliran, nyawa 3, 8 kristal.
- Kontrol: **panah/WASD** jalan, **Shift+panah** atau **IJKL** tembak, **spasi** diam. Ada juga tombol di layar.
- **Urutan tiap giliran: semua robot bergerak dulu, baru tembakan dihitung.** Tembakan lurus mengenai robot pertama di garis itu
  **setelah** lawan bergerak: kena +1 poin, menghancurkan +3. Senjata perlu 3 giliran untuk siap lagi. Jadi lawan yang sudah segaris
  masih bisa kabur, dan penembak yang jeli menembak ke **petak tujuan** lawan (memprediksi gerakannya).
- Kristal ◆ = +2 poin, lalu muncul kristal baru (posisinya dari seed, sama untuk semua).
- Robot hancur bangkit lagi di posisi awal setelah 8 giliran (bisa diatur; 0 = hancur permanen).
- Dua robot menuju petak yang sama atau bertukar tempat: keduanya batal bergerak.
- Waktu manusia default 8 detik per giliran. Waktu habis = diam.

Fungsi bot: `langkah_ke(baris, kolom)` (jalur terpendek), `kristal_terdekat()`, `musuh_terdekat()`, `bisa_kena()`, `terancam()`,
dan untuk memprediksi: `tebak_langkah(nama)` (petak tujuan lawan kalau ia menuju kristal terdekatnya), `petak_mungkin(nama)`,
`arah_tembak_ke(baris, kolom)`. Template **Penembak Jitu** memakai ketiganya.

Opsi kustom: **kabut perang** (robot, kristal, dan power-up hanya terlihat dalam jarak pandang tertentu; tembok dan skor tetap terlihat),
**power-up** (⚡ senjata langsung siap, 🛡️ perisai menahan satu tembakan, ❤️ nyawa +1), **zona badai** (setelah sekian persen giliran,
zona aman menyempit bertahap; robot di luar zona kehilangan 1 nyawa tiap giliran).

## 5. Petualangan Kartu Nusantara

**1–8 pemain · sendiri-sendiri · `def aksi():`**

Deck-builder roguelike. Semua pemain menempuh 10 lantai dengan **seed yang sama**: musuh dan pilihan hadiah sama untuk semua orang.

- Tiap giliran: 3 energi dan 5 kartu. Klik kartu untuk memainkannya (kalau musuh lebih dari satu, klik kartu lalu klik musuhnya),
  lalu **Akhiri giliran**. Musuh bertindak sesuai **niat** yang terlihat di atas kartunya.
- Blok menahan serangan sampai giliranmu berikutnya. Racun mengurangi HP tiap giliran lalu berkurang 1. Lemah = serangan 25% lebih kecil.
  Kuat = setiap serangan bertambah.
- Menang pertarungan → pilih 1 dari 3 kartu hadiah (atau lewati). Lantai 4 dan 7 tempat istirahat: pulihkan 35% HP atau buang satu kartu.
  Lantai 6 dan 9 dijaga elit (HP maksimal +6 kalau menang). Lantai 10: bos Raksasa Batu.
- Skor = lantai selesai × 100 + sisa HP + 500 kalau bos kalah. Papan **Balapan** menampilkan kemajuan semua pemain.

Tips: racun sangat kuat melawan bos ber-HP besar; jangan lupa blok saat `perkiraan_serangan()` besar.

Opsi kustom: **niat musuh** (terlihat / hanya jenisnya / rahasia; `perkiraan_serangan()` lalu memakai serangan terburuk),
**tingkat kesulitan** (+15% HP & serangan musuh per tingkat), **berkah awal** (satu berkah acak yang sama untuk semua: Keris Pusaka,
Jimat Penjaga, Kantong Ajaib, Ilmu Kebal, Rezeki Nomplok), **kartu kutukan** di dek awal (tidak bisa dimainkan, bisa dibuang di tempat istirahat).

## 6. Pasar Malam Tycoon

**2–8 pemain · bersamaan · `def aksi():`**

Semua pedagang berjualan di pasar malam yang sama selama 15 hari, modal Rp200.000.

- Tiap hari pilih dagangan (Sate, Es Teh, Bakso, Mainan), lalu geser **Harga**, **Iklan**, dan **Jumlah** barang. Biaya modal dibayar di muka.
  Tekan **Buka lapak** atau **Tutup hari ini**.
- Pembeli tiap produk dibagi ke penjual yang paling menarik: makin murah dan makin banyak iklan, makin banyak pembeli. Harga 2× wajar = tidak laku.
- Barang yang tidak laku basi. Kalau daganganmu habis, separuh pembeli yang kecewa pindah ke penjual lain.
- Permintaan dipengaruhi cuaca (diumumkan pagi hari), akhir pekan, acara khusus, dan gejolak acak ±15%. Ramalan cuaca besok benar ±75%.
- Layar menampilkan **perkiraan pembeli** (dengan asumsi pesaing seperti kemarin) dan perkiraan untung sebelum kamu buka lapak.
- Dagangan, harga, dan iklan terakhirmu diingat untuk hari berikutnya.
- **Riwayat lengkap** di bawah grafik uang: rekap per pedagang (total untung, hari buka, laku/beli, basi, dagangan andalan, hari terbaik)
  dan rincian **setiap hari** (dagangan, harga, iklan, beli, laku, basi, untung, uang akhir, gejolak permintaan malam itu). Rincian yang
  sama muncul di replay (sampai hari yang sedang diputar) dan di layar hasil.
- Uang terbanyak di akhir menang.

Opsi kustom: **dagangan pesaing rahasia** (produk, harga, iklan, dan hasil jualan orang lain tidak dibuka; yang terlihat hanya jumlah
penjual & pembeli tiap produk), **ketepatan ramalan** (0 = tanpa ramalan), **stok tahan sehari** (barang yang tidak laku bisa dijual lagi
besok kalau produknya sama, dijual lebih dulu, setelah itu basi), **kejadian pasar** (razia: satu produk dilarang hari itu, viral:
permintaan ×2,5, bahan naik: modal ×1,5, subsidi: modal separuh; diumumkan pagi hari).

## 7. Lelang Rahasia

**2–8 pemain · bersamaan · `def aksi():`**

- 12 barang dilelang satu per satu. Default: **nilai semua barang sudah diumumkan dari awal** (strip jadwal di atas).
- Setiap ronde semua menawar tertutup, maksimal koin yang dimiliki (modal 100, tidak bertambah kecuali opsi *koin tiap ronde*).
- Penawar tertinggi membayar dan mendapat poin barang itu. Tawaran tertinggi **seri** = barang hangus, tidak ada yang dapat.
- Skor = poin barang + koin sisa × 0,1.

Opsi kustom:

- **Jadwal terlihat N barang ke depan** (0–30; 0 = lelang rahasia penuh: kamu baru tahu barangnya saat dilelang). Barang yang sudah
  lewat tetap terlihat di riwayat.
- **Nilai barang**: pasti / **taksiran pribadi** (tiap pemain melihat angka yang sedikit berbeda, ±selisih) / rahasia sampai terjual.
- **Koin lawan rahasia**, **tawaran dibuka**: semua / hanya pemenang & harga / tidak dibuka.
- **Jenis lelang**: harga pertama, **harga kedua** (pemenang membayar tawaran tertinggi kedua), atau **semua bayar**.
- **Koin seri ikut hangus (%)**: kalau tawaran tertinggi seri, para penawar seri kehilangan sekian persen tawarannya.
- **Barang minus**: barang kutukan bernilai −1 sampai −8. Tidak ada yang bayar, tapi poin minusnya kena ke penawar **tertinggi** dan
  **terendah** (semua yang seri di ujung ikut kena), plus penawar **tengah** kalau jumlah pemain ganjil dan lebih dari 3.
- **Bonus set** (3 barang satu kategori: Pusaka, Seni, Kriya, Harta) dan **koin tiap ronde**.

Tips: perhatikan dompet lawan. Kalau semua lawan tinggal sedikit koin, barang bagus bisa didapat murah. Untuk barang minus, posisi
tawaranmu yang menentukan: jangan di ujung, jangan di tengah.

## 8. Rebutan Lahan

**2–8 pemain · bersamaan · `def aksi():`**

- Tiap ronde bagi 100 pasukan ke 5 medan. Setiap medan bernilai 1–5 (nilai ronde ini dan ronde berikutnya terlihat).
- Pasukan terbanyak di sebuah medan mendapat nilainya; seri dibagi rata. Pasukan penuh lagi setiap ronde.
- Alokasi dimulai dari **0 di semua medan**. Isi jumlah per medan (tombol −5/+5), lalu **Kirim alokasi**. **Bagi rata** dan
  **Nol semua** untuk cepat. Waktu habis: alokasi terakhirmu dikirim (sisa pasukan tidak dipakai); belum diubah sama sekali = dibagi rata.

Tidak ada strategi yang selalu menang: semuanya tergantung tebakan alokasi lawan (lihat tabel alokasi ronde lalu).

Opsi kustom: **alokasi lawan rahasia** (setelah ronde hanya penguasa tiap medan yang dibuka), **nilai ronde berikutnya** boleh
disembunyikan, **benteng** (penguasa tunggal ronde lalu dihitung +X% di medan itu), **pasukan menyusut** (pasukan di medan yang kalah
hilang, ditambah bala bantuan tiap ronde), **medan kejutan** (⭐ nilai ganda atau 🌫️ misteri −3 sampai 6 yang baru dibuka setelah ronde).

## 9. Dilema Kas Desa

**2–8 pemain · bersamaan · `def aksi():`**

- Tiap ronde semua dapat 10 koin. Sumbang berapa pun ke kas desa; kas dikali 1,6 lalu dibagi rata ke semua orang.
- **Target gotong royong:** kalau kas ronde itu mencapai target (default 50% dari total pendapatan semua pemain, misalnya 4 pemain → 20 koin),
  **semua** pemain dapat **bonus +10**. Kurang satu koin saja, bonusnya hilang.
- **Ronde terakhir dirahasiakan:** jumlah ronde sebenarnya ±25% dari pengaturan, jadi "khianat di ronde terakhir" berisiko.
- Sumbangan tiap orang terlihat setelah ronde (bisa dimatikan host). Koin terbanyak menang.

Kenapa menyumbang bisa masuk akal: tanpa target, setiap koin yang disumbang hanya kembali 1,6/jumlah pemain, jadi menyumbang 0 selalu
paling untung. Dengan target, kalau kas kurang sedikit, menutup kekurangannya justru menguntungkanmu sendiri (bonusmu lebih besar dari
koin yang kamu keluarkan). Tapi kalau orang lain sudah menutup target, menyumbang lebih lagi kembali rugi. Jadi pertanyaannya: siapa yang
menutup target, dan apakah kamu percaya mereka? Host bisa kembali ke versi klasik dengan target 0 dan akhir tidak dirahasiakan.

Opsi kustom: **pengali kas rahasia** (tiap ronde acak ½×–1½×, dibuka setelah ronde), **sumbangan tertutup**, **fase sanksi** setelah
sumbangan dibuka: **denda** (bayar 1 koin → tabungan orang itu −X) dan **voting usir** (yang dipilih lebih dari separuh pemain lain
tidak bisa menyumbang dan tidak dapat bagian kas maupun bonus di ronde berikutnya), **bencana** (target gagal 2× berturut-turut →
semua kehilangan sekian persen tabungan). Preset *Desa Tegas* menyalakan sanksi dan bencana.

## 10. Angka Dua Pertiga

**2–8 pemain · bersamaan · `def aksi():`**

- Semua menebak angka 0–100. Target = faktor × rata-rata semua tebakan. Yang paling dekat target dapat 1 poin.
- **Faktor rahasia** (default): tiap ronde faktornya acak antara 0,5 dan 1,5 dan baru diumumkan setelah semua menebak.
- **Tebakan kembar gugur** (default): angka yang dipilih dua orang atau lebih tidak bisa menang (tetap dihitung di rata-rata).
- Garis angka menampilkan tebakan semua orang, target, dan faktor ronde lalu; tebakan kembar dicoret.
- Host bisa kembali ke versi klasik: faktor **tetap** ⅔ (atau 0,1–2,0) dan kembar tidak gugur.

Kenapa diubah: di versi klasik tebakan cepat berkumpul di satu titik (0 kalau faktor < 1, batas kalau > 1, tengah kalau = 1) dan permainan
jadi membosankan. Sekarang kamu harus dekat target **dan** berbeda dari orang lain.

Opsi kustom: **acuan median** (target = faktor × median, tidak terpengaruh satu-dua tebakan ekstrem), **poin 3-2-1** untuk tiga tebakan
sah terdekat, **tebakan lawan rahasia** (setelah ronde hanya rata-rata/median, target, dan pemenang yang dibuka), **angka terlarang**
(sekian angka acak diumumkan di awal ronde; tebakan di angka itu gugur).

## 11. Pasar Malam Sepi

**2–12 pemain · bersamaan · `def aksi():`**

- Tiap malam pilih **🎡 Datang** atau **🏠 Di rumah**. Asyik kalau yang datang paling banyak 60% pemain (+1); kalau lebih, sumpek (−1).
  Di rumah = 0.
- Grafik batang menampilkan pengunjung tiap malam dan kapasitas malam itu (garis kuning).
- Opsi kustom: **beberapa tempat** (🎡 Pasar Malam +1, 🎤 Konser +2 dengan kapasitas separuhnya, 🍢 Bazar Kuliner +3 dengan kapasitas
  kecil), **kapasitas berubah** tiap malam (diumumkan sore hari, atau rahasia sampai malam selesai), **hadiah/hukuman**, **malam spesial**
  (🎉 Festival: kapasitas ×1,5 dan hadiah ×2, 🌧️ Hujan: kapasitas separuh), **jumlah pengunjung rahasia** (hanya diumumkan nyaman/sumpek).
- Bot yang semuanya berpikir sama akan datang bersamaan dan rugi bersama. Template **Bergiliran Kursi** memakai nomor kursi (`saya()`)
  supaya tiap malam yang datang pas kapasitas.

---

## Suit Bot Arena

Pemain tidak memilih senjata sendiri: **algoritma botmu** yang memilih, setiap ronde, tanpa unsur acak.

- **Room** sampai 8 pemain plus penonton (**Tonton saja**). Setiap pemain mengirim bot (blok visual atau Python), menekan **Siap!**,
  lalu host memulai match. Replay animasi diputar untuk semua orang di room, termasuk penonton.
- **Reaksi emoji** di header room melayang di layar semua orang.
- **Turnamen 1 lawan 1** (host, minimal 3 pemain siap): setiap pasangan bertanding sekali. Menang 3, seri 1, kalah 0; poin seri dipecah
  selisih HP. Hasilnya klasemen dan matriks; klik kotak matriks untuk menonton replay pasangan itu.
- **Debugger langkah demi langkah** di bawah replay (latihan dan room): pilih ronde, tekan **🐞 Debug ronde ini**. Server menjalankan ulang botmu
  dengan info yang sama persis seperti saat match, lalu kamu bisa menelusuri baris demi baris beserta isi variabel dan nilai `return`.
  Debugger memakai kode di editormu sekarang, jadi bisa dipakai untuk mencoba perbaikan.
- **Liga** (menu Liga): rating ELO untuk pemain yang masuk akun, dari setiap match dan turnamen di room.
- **Arena latihan** melawan 11 bot contoh, dengan pilihan aturan dan event.

### Mode event

Diatur host di **Aturan room** (atau di latihan):

| Event | Efek |
|---|---|
| Normal | Aturan biasa. |
| Taruhan Ganda | HP yang hilang saat kalah dikali 2. |
| Pikun | Ingatan bot hanya 3 ronde terakhir. |
| Kilat | Paling lama 30 ronde. |
| Darah Tipis | HP awal hanya 30% (minimal 100). |
| Kabut | Bot tidak melihat pilihan per pemain; hanya jumlah tiap senjata, perubahan HP, dan HP. |
| Kejutan | Salah satu event di atas diundi saat match dimulai (di turnamen, diundi sekali untuk semua pasangan). |

Panduan bot Suit Bot Arena untuk AI: [docs/PANDUAN_BOT_LLM.md](PANDUAN_BOT_LLM.md).

---

## Kilas Pasar

Simulasi trading di chart pasar **asli** (kripto, saham IDX, saham US). Kamu dilempar ke satu titik di masa lalu, candle berikutnya belum terlihat,
lalu memutuskan beli/jual sambil memajukan waktu. Mode: main sendiri, tantangan harian, dan balapan bareng teman.

Produk: **Spot** (semua pasar), **Futures perpetual** (kripto; long/short, leverage bertingkat, cross/isolated, funding, likuidasi),
dan **Margin + short** (saham US dengan aturan Reg T, saham IDX dengan aturan short selling BEI). "Aturan bebas" membuka short
dan futures untuk semua saham. Penjelasan lengkap (jenis order, cara eksekusi, fee, likuidasi, funding, bunga, mode buta, data)
ada di halaman **Cara main** di dalam Kilas Pasar.
