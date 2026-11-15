# Daftar Game & Cara Main

Satu server, tiga pintu masuk di halaman depan:

| Pintu | Isi | Alamat |
|---|---|---|
| **Arena Mabar** | 22 game main bareng. Setiap kursi boleh manusia atau bot (kecuali game khusus manusia), boleh dicampur. | `#main` |
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
  [Pasar Malam Sepi](#11-pasar-malam-sepi) ·
  [Wordle Mabar](#12-wordle-mabar) ·
  [Labirin Mabar](#13-labirin-mabar) ·
  [Satu! (gaya UNO)](#14-satu-gaya-uno) ·
  [Evolusi Hex](#15-evolusi-hex) ·
  [Juragan Nusantara (gaya Monopoli)](#16-juragan-nusantara-gaya-monopoli) ·
  [Domino](#17-domino-gaple--draw) ·
  [Ular Mabar](#18-ular-mabar) ·
  [Tembak Jitu](#19-tembak-jitu) ·
  [Hitung Uang](#20-hitung-uang) ·
  [Tebak Gambar](#21-tebak-gambar)
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
4. Host bisa menekan **🗑️ Hapus room** kapan saja (match yang berjalan ikut dihentikan, semua orang dikeluarkan).
5. Room yang **tidak punya satu pun orang online** selama 2 menit (atur dengan `ROOM_IDLE_SECONDS`) dihapus otomatis dari memori,
   termasuk match yang sedang berjalan. Waktu 2 menit itu cukup untuk refresh atau layar HP mati sebentar. Kalau orang terakhir
   menekan **Keluar** di lobby, room langsung dihapus. Hal yang sama berlaku untuk room Suit Bot Arena dan balapan Kilas Pasar.

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
- Di HP, bagian atas room dibuat ringkas: reaksi ada di tombol 😀 dan *Hapus room / Keluar* di tombol ⋯. Bar waktu (dan tombol jeda
  host) menempel di atas layar saat di-scroll.

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
- **Dividen poin** (preset *Investor*): setiap *N* ronde (default 2), poin barang + bonus set yang kamu miliki menghasilkan koin
  sebesar *X%* (misalnya 20 poin × 10% = 2 koin). Pecahan koin disimpan untuk pembayaran berikutnya. Barang yang dibeli lebih awal
  jadi ikut membiayai tawaranmu berikutnya, bukan cuma poin diam.

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

## 12. Wordle Mabar

**1–8 pemain · balapan real-time / serentak / bergiliran · `def aksi():`**

- Tebak kata rahasia **5 huruf bahasa Indonesia**: 🟩 huruf & posisi benar, 🟨 huruf ada di posisi lain, ⬜ tidak ada. Satu match berisi
  beberapa kata (default 3); setelah tiap kata, jawabannya dan semua papan dibuka.
- **Balapan** (default): papan masing-masing, real-time. Benar di baris ke-*k* = (maks tebakan + 1 − *k*) poin, plus **+3 / +2 / +1**
  untuk tiga tercepat. **Anti spam:** setiap baris yang terpakai mengurangi poin, dan setelah tebakan salah kamu harus menunggu
  **3 detik** (bisa diatur host) sebelum boleh menebak lagi. Kata yang tidak ada di kamus ditolak tanpa memakan baris.
- **Serentak**: semua menebak satu kata di setiap langkah, bersamaan. **Bergiliran**: satu papan bersama; menebak benar +5, tebakan
  yang membuka huruf hijau baru +1.
- Opsi: papan lawan (warna saja / huruf & warna / tidak terlihat), **mode sulit**, kata di luar kamus (ditolak / memakan baris /
  bebas), **kata licik** (jawaban belum ditentukan dan terus menghindar, gaya Absurdle), jumlah kata, dan maksimal tebakan.
- Mengetik: di HP dipakai **keyboard bawaan HP** (huruf berwarna tetap terlihat sebagai petunjuk); di laptop keyboard biasa atau papan
  huruf di layar. Bisa ditukar dengan tautan di bawah papan. Kata yang sudah lengkap di layar ikut terkirim kalau waktu habis.
- Setelah satu kata selesai, **semua tebakan semua pemain (huruf + warna)** dibuka, dan bisa dilihat lagi di riwayat kata.
- Kamus memakai daftar kata dasar Sastrawi (lisensi MIT, lihat `backend/app/games/data/LISENSI-KATA.txt`); kata jawaban dipilih dari
  daftar kata umum.

## 13. Labirin Mabar

**1–8 pemain · balapan real-time · `def aksi():`**

- Semua mulai dari pojok kiri atas labirin yang sama dan berlomba ke **pintu keluar** 🚪. Setiap pemain bergerak sendiri-sendiri
  secepat mungkin (panah / WASD, atau tombol di layar). **🏃 Lari** menyusuri lorong sampai persimpangan dengan satu tekan.
- Finis ke-1, ke-2, ... dapat 10 / 7 / 5 / 4 / 3 / 2 / 1 poin, koin 🪙 +1. Ada jatah langkah per labirin, dan begitu ada yang finis yang
  lain tinggal punya 30 langkah.
- **Pandangan**: *terang* (seluruh labirin terlihat), *kabut yang diingat* (jalan yang pernah terlihat tetap terbuka di petamu), atau
  *kabut tanpa ingatan* (hanya sekitarmu: harus hafal jalan). Jarak pandang, posisi lawan, dan kompas pintu keluar bisa diatur.
- Kemampuan terbatas yang terlihat **semua pemain**: 📍 **tanda / gambar** (↑ ↓ ← → ✖ ⭐ ❓ 💀) di petakmu, 🧵 **tali** (jejak jalanmu),
  dan 🔦 **suar** (pandangan jauh sebentar). Tanda bisa menolong... atau menyesatkan lawan.
- Opsi kejutan: koin, **jebakan** tersembunyi (−5 jatah langkah dan tertahan 3 detik), **portal** berpasangan, dan jalan pintas.

## 14. Satu! (gaya UNO)

**2–8 pemain · bergiliran · `def aksi():`**

- Habiskan kartu lebih dulu: mainkan kartu yang **sewarna** atau **sama angka/simbolnya**, atau kartu liar. ⊘ lewati, ⇄ balik,
  +2, 🌈 ganti warna, +4. Tekan **📢 SATU!** saat memainkan kartu kedua terakhir (lupa = tarik 2).
- Pemenang ronde mendapat poin dari sisa kartu lawan (angka = nilainya, aksi 20, liar 50). Default 3 ronde.
- Opsi: **tumpuk +2/+4**, ambil sampai dapat, **aturan 7-0** (7 = tukar kartu, 0 = semua tangan berpindah), jumlah kartu lawan rahasia.
- **Kartu power kustom**: host bisa menambah sampai 8 jenis kartu buatan sendiri di pengaturan room. Efeknya ditulis dengan kode
  `def efek():` (subset Python yang sama dengan bot), misalnya `tukar_tangan(pemain_ini(), target())` atau `for n in lawan(): tarik(n, 1)`.
  Ada contoh siap pakai (Tukar Tangan, Hujan Kartu, Putar Tangan, Hadiah, Lompat Dua, Sial Bersama, Main Lagi, Balas Dendam), tombol
  **🧪 Coba** yang menjalankan kartu di meja contoh, dan **📋 Tempel JSON** untuk kartu buatan AI. Panduan menulis kartu (untuk ditempel
  ke AI) ada di tab **Panduan bot** game ini, bagian *Membuat kartu power kustom*.

## 15. Evolusi Hex

**1–6 pemain · bersamaan per giliran · `def aksi():`**

- Peta heksagonal dengan tanah, 🌿 semak (isi tersembunyi), dan 🪨 batu. Setiap pemain punya satu **spesies** yang mulai dengan 2
  makhluk di sarangnya.
- Giliran 0: **desain spesies**, bagi 15 poin ke 👁️ **pandangan** (melihat lurus ke 6 arah, biaya 0,25×nilai energi per giliran),
  🐾 **kelincahan** (langkah per giliran), dan 🦣 **ukuran** (HP & energi maksimal). Biaya per langkah = **(ukuran/5)³ × (kelincahan/5)**,
  jadi makhluk besar sekaligus cepat sangat boros (seperti simulasi evolusi di video).
- Makanan: 🌱 rumput +12, 🍎 buah +25, 🍖 daging +45 (dari makhluk yang mati). Makhluk yang ukurannya **≥ 1,2×** lawan memangsanya.
  Energi habis = kelaparan (HP turun).
- **Beranak** (toggle per makhluk): kalau energinya cukup, makhluk melahirkan anak dengan desain spesies saat ini, kadang
  **bermutasi** ±1. Makhluk diberi nomor otomatis yang bisa diganti namanya di daftar samping.
- Perintah per makhluk: **🧠 naluri** (otomatis), **🎯 tujuan** (klik petak di peta, makhluk jalan sendiri), **🕹️ manual** (pilih langkah
  satu per satu), atau **⏸ diam**. Pasang **🪨 batu** atau **🌵 duri** tersembunyi di sebelah makhlukmu (jatah 3).
- Poin: makanan 1/2/3, memangsa +5, kelahiran +3, +5 per makhluk yang hidup di akhir. Opsi: kabut, rasio memangsa, semak, batu,
  jebakan, peluang mutasi, kelimpahan makanan, dan bangkit setelah punah.

## 16. Juragan Nusantara (gaya Monopoli)

**2–6 pemain · bergiliran · `def aksi():`**

- Papan 40 petak berisi kota-kota Indonesia (Pacitan sampai Jakarta), 4 transportasi, PLN & PDAM, pajak, Kesempatan, dan Dana Umum.
- Lempar dua dadu, beli properti, tagih sewa, bangun rumah & hotel setelah memiliki satu kelompok warna lengkap, gadai/tebus.
  Dadu kembar = lempar lagi; tiga kali kembar = penjara.
- Properti yang tidak dibeli **dilelang tertutup** ke semua pemain (seperti Lelang Rahasia). **Tukar-menukar**: di gilirannya pemain
  boleh menawarkan properti/uang ke pemain lain, yang lalu menerima atau menolak.
- Tidak bisa bayar = rumah dijual & properti digadai otomatis; masih kurang = bangkrut. Menang: pemain terakhir, atau kekayaan bersih
  terbesar setelah batas putaran (default 25).
- Opsi: uang awal, gaji lewat Mulai, batas putaran, lelang, tukar-menukar, jackpot Parkir Bebas, uang lawan rahasia.

## 17. Domino (Gaple & Draw)

**2–6 pemain · bergiliran · `def aksi():`**

- Tempel kartu di **ujung kiri atau kanan** meja; angkanya harus sama dengan ujung itu. **Gaple**: tidak ada yang cocok = lewat.
  **Draw**: ambil dari tumpukan sampai dapat (tumpukan habis baru boleh lewat).
- Ronde selesai saat ada yang kartunya habis, atau meja **buntu** (semua lewat berturut-turut: sisa mata paling sedikit menang).
  Pemenang mendapat jumlah mata sisa kartu lawan (atau semua kena minus sisa matanya sendiri). Ronde pertama dibuka balak tertinggi.
- **Tim 2 lawan 2** (4 pemain), set **balak 6** atau **balak 9**, target poin.
- **Tantangan**: kartu terbuka (semua tangan terlihat), **bonus tutup balak** ×2, **denda tiap lewat**, kartu **0-0 jadi bom**
  (pemain berikutnya ambil 2 kartu / kena denda).

## 18. Ular Mabar

**1–8 pemain · real-time · `def aksi():`**

- Snake multiplayer: semua ular bergerak **bersamaan terus-menerus** (default 6 langkah per detik, bisa 3–12). Belok dengan panah /
  WASD, geser di layar HP, atau tombol panah.
- 🍎 apel +1 (tumbuh 1), ⭐ emas +3 (tumbuh 2), 🤢 busuk −2 (menyusut 2, opsional).
- **Tidak boleh saling timpa**: menabrak badan ular mana pun, tembok, atau tepi = tumbang (−3, bangkit 2 detik lagi; atau keluar ronde).
  Pemilik badan yang ditabrak +2. Adu kepala: keduanya tumbang (atau yang lebih panjang menang).
- Akhir ronde: yang hidup +3, terpanjang +5. Opsi: tepi tembus, rintangan, jumlah buah, bangkai jadi buah, lama ronde.
- Server melangkah sendiri tiap detak; bot berpikir tiap detak dengan batas 4.000 langkah kode.

## 19. Tembak Jitu

**1–12 pemain · real-time · khusus manusia**

- Lingkaran sasaran muncul satu per satu. **Klik / ketuk sedekat mungkin ke tengah**, secepat mungkin. Poin = **cincin (1–10) × 10 ×
  faktor waktu** (1,0 kalau instan, turun proporsional sampai 0,3 di batas waktu). Meleset atau terlambat = 0, satu peluru per sasaran.
- Semua pemain mendapat urutan sasaran yang sama, mulai serentak dengan hitung mundur, dan **waktu reaksi dihitung di browser
  masing-masing** (koneksi lambat tidak merugikan). Server hanya mengirim sasaran yang sedang aktif.
- Kursor bidik dengan pistol mini, tombol **layar penuh**. Kejutan: sasaran bergerak, menyusut, **sandera** (jangan ditembak),
  dan target ganda.

## 20. Hitung Uang

**1–12 pemain · real-time · khusus manusia**

- Segepok uang rupiah (desain fiktif "Bank Mabar") yang sama untuk semua pemain. Ketuk lembar teratas untuk menggesernya ke tumpukan
  "sudah dihitung", lalu **ketik totalnya**. Mode sebar: semua uang disebar di meja.
- Benar pertama +15, kedua +12, ketiga +10, dan seterusnya. Salah −3 dan hukuman tunggu (maksimal 3 kali salah per gepok).
- Tantangan: uang **berantakan**, **terbalik** (sisi belakang), campur **koin**, uang **palsu** (tanpa pita perak, tidak dihitung),
  dan **kupon / uang mainan** (tidak dihitung).

## 21. Tebak Gambar

**2–10 pemain · bergiliran · khusus manusia**

- Setiap pemain mendapat gambar rahasia yang terlihat oleh semua orang **kecuali dirinya sendiri**. Di giliranmu, tanyakan sesuatu
  ("Apakah aku hewan?"): ketik di kolom pertanyaan, atau ucapkan lewat panggilan suara lalu tekan **Tanya lewat suara**.
- Pemain lain menjawab dengan tombol **Ya / Tidak / Mungkin** (atau 5 pilihan). Semua tanya-jawab tercatat di papan.
- Tebak kapan saja di giliranmu (salah ketik satu huruf masih diterima). Benar = menang (yang lebih dulu poinnya lebih besar);
  salah mengurangi kesempatan. Selesai saat semua sudah menebak/kalah, atau saat ada satu pemenang (opsi).
- Gambar: emoji dari 7 kategori bawaan, **isian tambahan** host (emoji + nama + alias), dan **foto yang diunggah host** (diperkecil
  otomatis, disimpan di memori room dan ikut terhapus bersama room). Nama tertentu bisa dibuang dari kategori bawaan.

## 22. Robot Tarung

**2–4 pemain · real-time 20 detak/detik · `def aksi():` · tampilan 3D (Three.js)**

- **Garasi**: rakit robot dalam batas berat (default 100 kg): sasis (kotak / baji / kubah), roda & motor (ringan / sedang / kuat),
  baterai (kecil / sedang / besar), armor per sisi (depan, kanan, belakang, kiri; 0–8 tingkat), senjata, dan pembalik badan.
  Pratinjau 3D berputar, 6 contoh rakitan, tombol **Sesuaikan berat**, dan rakitan bisa **disimpan** di browser.
- **Senjata**: spinner horizontal (terkuat, perlu waktu berputar), drum vertikal (melontarkan, tetap 70% saat terbalik), flipper
  (melempar dan membalikkan lawan, bisa membalikkan diri sendiri), palu (menembus armor, 2× untuk lawan terbalik), gergaji (menggerus
  terus), atau tanpa senjata (penyeruduk: tabrakan depan 2× untuk lawan).
- **Kerusakan per komponen**: armor sisi yang terkena menahan dulu; kalau habis, yang rusak rangka dan komponen di baliknya
  (depan → senjata, kiri/kanan → motor sisi itu, belakang → baterai). Baji mengangkat roda lawan, kubah memantulkan pukulan samping.
- **Arena** (12–18 m): lubang di pojok (terbuka setelah 45 detik), gergaji lantai, palu arena, dinding berduri (opsi).
- **Menang**: KO (rangka hancur, jatuh ke lubang, atau tidak bergerak 10 detik), atau nilai juri saat waktu habis (kerusakan 50%,
  agresi 25%, kontrol 25%). Poin: menang ronde +10, KO +3, +1 tiap 10 kerusakan.
- **Kendali**: WASD/panah untuk jalan (gaya tank), Spasi untuk senjata (spinner/gergaji: nyala-mati; flipper/palu: tahan),
  E untuk berdiri lagi. Di HP: joystick kiri + tombol senjata/balik. Kamera **Arena / Dekat / Ikuti**, dan layar penuh.
- Fisika berjalan di server (2D dari atas); browser hanya menggambar 3D dan menginterpolasi gerak. Three.js diunduh hanya saat
  game ini dibuka. Bot: 5 template (drum, gasing, pelempar, godam, buldoser), batas 3.000 langkah kode per detak.

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
