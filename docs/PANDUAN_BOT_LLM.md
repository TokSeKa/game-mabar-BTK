# Panduan Lengkap Bot Suit Bot Arena

> **Untuk AI (ChatGPT, Claude, Gemini, dll.) yang membaca dokumen ini:**
> Kamu akan membantu pemain menulis bot untuk game **Suit Bot Arena**. Tulis kode yang **hanya** memakai fitur dan fungsi yang dijelaskan di sini. Bot ditulis dalam subset bahasa Python dan dijalankan oleh interpreter khusus, bukan Python biasa. Jawab dengan **satu blok kode Python lengkap** yang berisi `def pilih():`, lalu jelaskan strateginya secara singkat dalam bahasa Indonesia. Jangan memakai `import`, `random`, `class`, `try/except`, `global`, atau variabel yang diharapkan tersimpan antar ronde, karena semuanya tidak tersedia.

---

## 1. Cara main

- Satu match berisi 2 sampai 8 bot. Setiap bot mulai dengan **HP awal** (default 1000).
- Setiap ronde **semua bot memilih senjata bersamaan**: `BATU`, `GUNTING`, atau `KERTAS`.
- Batu mengalahkan gunting, gunting mengalahkan kertas, kertas mengalahkan batu.
- Untuk **setiap pasangan senjata yang muncul** di ronde itu:
  - setiap bot di golongan yang **kalah** kehilangan **HP kalah** (default 100), atau sisa HP-nya kalau kurang dari itu;
  - semua HP yang hilang dikumpulkan lalu **dibagi rata** ke bot di golongan **pemenang**;
  - kalau pembagian tidak rata, **sisanya tidak dibuang**: +1 HP diberikan ke pemenang dengan HP terendah lebih dulu (kalau HP-nya sama, yang lebih dulu masuk room didahulukan).
- **Sirkular:** kalau ketiga senjata muncul sekaligus, setiap golongan menang atas satu golongan dan kalah dari golongan lain di ronde yang sama.
- Kalau semua bot memilih senjata yang sama, tidak ada HP yang berpindah.
- Total HP semua bot selalu tetap (zero-sum). HP berpindah dari yang kalah ke yang menang.
- Bot dengan HP 0 **gugur** dan tidak ikut lagi.
- Match selesai kalau tinggal 1 bot hidup, atau saat **batas ronde** tercapai (default 100). Kalau ronde habis, HP terbanyak yang menang. Kalau HP-nya sama, hasilnya seri.

### Contoh perhitungan (8 bot, HP kalah 100)

3 bot batu, 3 bot gunting, 2 bot kertas:

| Pasangan | Yang kalah | Kumpulan HP | Pemenang mendapat |
|---|---|---|---|
| batu > gunting | 3 gunting −100 | 300 | 3 batu +100 |
| kertas > batu | 3 batu −100 | 300 | 2 kertas +150 |
| gunting > kertas | 2 kertas −100 | 200 | 3 gunting +66, sisa 2 → +1 ke 2 gunting ber-HP terendah |

Hasil bersih: batu 0, kertas +50, gunting −34 (dua di antaranya −33).

**Pelajaran penting:** keuntungan terbesar didapat kalau kamu berada di golongan pemenang yang **kecil** dan melawan golongan kalah yang **besar**. Ikut mayoritas belum tentu aman.

---

## 2. Bentuk kode bot

```python
def pilih():
    return BATU
```

- Bot **wajib** punya fungsi `pilih()` tanpa parameter wajib. Fungsi ini dipanggil sekali setiap ronde dan **harus mengembalikan** `BATU`, `GUNTING`, atau `KERTAS` (atau teks `"batu"`, `"gunting"`, `"kertas"`).
- Boleh membuat fungsi bantu sendiri dengan `def`, dan boleh menulis variabel di luar fungsi.
- **Tidak ada memori antar ronde.** Setiap ronde seluruh kode dijalankan ulang dari nol, jadi variabel di luar fungsi juga di-reset. Semua informasi tentang ronde sebelumnya diambil dari fungsi library seperti `riwayat()`.
- **Tidak ada keacakan.** Tidak ada `random` dan tidak ada waktu. Bot yang sama dengan keadaan yang sama selalu memilih hal yang sama, jadi strategimu harus berupa aturan yang jelas.
- Kode botmu **rahasia**. Pemain lain hanya melihat senjata yang dipilih botmu setiap ronde, tidak melihat kodenya (kecuali kamu memilih membukanya setelah match).

---

## 3. Fitur bahasa yang didukung

**Boleh dipakai:**

- Variabel dan operasi matematika: `+ - * / // % **`
- Perbandingan: `== != < <= > >=`, `in`, `not in`, `is`, `is not`
- Logika: `and`, `or`, `not`
- `if` / `elif` / `else`, ekspresi `a if syarat else b`
- `for ... in ...`, `while`, `break`, `continue`, `pass`
- `def` (fungsi bantu, parameter dengan nilai default, rekursi terbatas), `lambda`, `return`
- List `[1, 2]`, dict `{"a": 1}`, tuple `(1, 2)`, indeks `x[0]`, potongan `x[1:3]`
- List/dict comprehension: `[x for x in daftar if x]`, `{k: v for k, v in d.items()}`
- f-string: `f"HP saya {hp_saya()}"`
- Fungsi bawaan: `len`, `range`, `min`, `max`, `sum`, `abs`, `round`, `int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, `sorted`, `reversed`, `enumerate`, `zip`, `any`, `all`, `print`
- Method list: `append`, `extend`, `insert`, `pop`, `remove`, `index`, `count`, `copy`, `reverse`, `sort`, `clear`
- Method dict: `get`, `keys`, `values`, `items`, `copy`, `pop`, `setdefault`, `update`, `clear`
- Method teks: `upper`, `lower`, `strip`, `lstrip`, `rstrip`, `startswith`, `endswith`, `split`, `join`, `replace`, `find`, `count`, `capitalize`, `title`, `isdigit`
- `print(...)` menulis ke log botmu (maksimal 20 baris per ronde). Hanya kamu yang bisa melihat log ini.

**Tidak didukung (akan ditolak):** `import`, `class`, `try/except`, `raise`, `with`, `global`, `nonlocal`, `del`, `yield`, `async/await`, set `{1, 2}`, `:=`, `*args`, `**kwargs`, dekorator `@`, `match/case`, operator bit (`& | ^ ~ << >>`), atribut yang diawali `_`, dan fungsi seperti `open`, `eval`, `exec`, `getattr`, `type`, `globals`.

---

## 4. Library game

### Konstanta

| Nama | Nilai |
|---|---|
| `BATU` | `"batu"` |
| `GUNTING` | `"gunting"` |
| `KERTAS` | `"kertas"` |
| `SENJATA` | `["batu", "gunting", "kertas"]` (urutan baku) |

### Tentang dirimu dan match

| Fungsi | Hasil |
|---|---|
| `nama_saya()` | Nama botmu (teks). |
| `hp_saya()` | HP botmu di awal ronde ini. |
| `ronde()` | Nomor ronde sekarang, mulai dari 1. |
| `ronde_maks()` | Batas ronde match ini. |
| `hp_awal()` | HP setiap bot saat match dimulai. |
| `hp_kalah()` | HP yang hilang setiap kali senjatamu dikalahkan. |
| `ingatan()` | Berapa ronde terakhir yang bisa dilihat di riwayat (diatur host, default 10). |

### Pemain

| Fungsi | Hasil |
|---|---|
| `semua_pemain()` | List nama semua peserta (termasuk dirimu dan yang sudah gugur), urut sesuai urutan masuk room. |
| `pemain_hidup()` | List nama peserta yang masih hidup, termasuk dirimu. |
| `lawan()` | List nama lawan yang masih hidup (tanpa dirimu). |
| `hp(nama)` | HP pemain itu di awal ronde (0 kalau sudah gugur). |
| `terkuat()` | Nama lawan dengan HP tertinggi (seri: urutan masuk room). |
| `terlemah()` | Nama lawan dengan HP terendah (seri: urutan masuk room). |

### Riwayat (hanya sebanyak `ingatan()` ronde terakhir)

Di ronde 1 riwayat masih kosong. Selalu tangani kasus ini.

| Fungsi | Hasil |
|---|---|
| `jumlah_terakhir()` | Dict jumlah pemilih tiap senjata di ronde lalu, misalnya `{"batu": 3, "gunting": 2, "kertas": 3}`. Di ronde 1 semuanya 0. |
| `riwayat_jumlah()` | List dict seperti di atas, satu per ronde, **yang terbaru di akhir**. |
| `pilihan_terakhir(nama)` | Senjata pemain itu di ronde lalu, atau `None` kalau belum ada atau pemain itu tidak ikut ronde itu. |
| `riwayat_pilihan(nama)` | List senjata pemain itu per ronde dalam ingatan (`None` untuk ronde saat ia sudah gugur). |
| `perubahan_terakhir(nama)` | Perubahan HP pemain itu di ronde lalu (positif = untung, negatif = rugi, 0 kalau belum ada). |
| `riwayat_perubahan(nama)` | List perubahan HP pemain itu per ronde dalam ingatan. |
| `riwayat()` | List lengkap per ronde (lihat format di bawah). |

Format satu item `riwayat()`:

```python
{
    "ronde": 7,
    "jumlah": {"batu": 2, "gunting": 1, "kertas": 1},
    "pilihan": {"Budi": "batu", "Ani": "kertas", "Citra": "batu", "Dodi": "gunting"},
    "perubahan": {"Budi": -100, "Ani": 200, "Citra": -100, "Dodi": 0},
    "hp": {"Budi": 900, "Ani": 1300, "Citra": 800, "Dodi": 1000}   # HP setelah ronde itu
}
```

### Helper senjata dan hitungan

| Fungsi | Hasil |
|---|---|
| `pengalah(s)` | Senjata yang **mengalahkan** `s`. `pengalah(BATU)` = `KERTAS`. |
| `korban(s)` | Senjata yang **dikalahkan** `s`. `korban(BATU)` = `GUNTING`. |
| `terbanyak(d)` | Kalau `d` dict: kunci dengan nilai terbesar. Kalau `d` list: isi yang paling sering muncul (`None` diabaikan; hasil `None` kalau list kosong). |
| `tersedikit(d)` | Kebalikan `terbanyak`. Untuk list berisi senjata, senjata yang tidak muncul dihitung 0. |
| `hitung(daftar, x)` | Berapa kali `x` muncul di `daftar`. |
| `total_jumlah(daftar_dict)` | Menjumlahkan list dict, misalnya `total_jumlah(riwayat_jumlah())` = total pemilih tiap senjata dalam ingatan. |
| `hitung_hasil(pilihan)` | Simulasi satu ronde dengan HP sekarang. Masukkan dict `{nama: senjata}` (boleh hanya sebagian pemain hidup), hasilnya dict `{nama: perubahan HP}`. |
| `senjata_terbaik()` | Senjata yang paling menguntungkan untukmu kalau semua lawan mengulang pilihan ronde lalu. Di ronde 1 hasilnya `BATU`. |

**Aturan seri (tie-break):** kalau ada nilai yang sama, `terbanyak`/`tersedikit` memilih urutan `batu`, `gunting`, `kertas` untuk kunci senjata, dan urutan kemunculan untuk kunci lain. Semua hasil selalu sama setiap kali dijalankan.

---

## 5. Batasan dan error

- Setiap ronde bot punya batas **20.000 langkah** (setiap operasi dihitung). Perulangan yang tidak pernah berhenti akan dihentikan.
- Panjang kode maksimal 10.000 karakter. List, dict, dan teks maksimal 10.000 isi. Angka maksimal sekitar 10^18.
- Kalau bot **error** atau mengembalikan sesuatu selain senjata, ronde itu bot **otomatis memilih BATU**, dan pesan error (dengan nomor baris) masuk ke log pemiliknya.
- Kalau bot error **3 ronde berturut-turut**, bot dimatikan dan selalu memilih BATU sampai match selesai.
- Pemeriksa kode memberi tahu error penulisan sebelum match dimulai. Gunakan arena latihan untuk melihat error saat bot berjalan.

---

## 6. Contoh bot

### Pemula: anti mayoritas

```python
def pilih():
    if ronde() == 1:
        return KERTAS
    favorit = terbanyak(jumlah_terakhir())
    return pengalah(favorit)
```

### Pemula: pola berulang

```python
def pilih():
    pola = [BATU, KERTAS, KERTAS, GUNTING]
    return pola[(ronde() - 1) % len(pola)]
```

### Menengah: sembunyi saat HP tipis

```python
def pilih():
    if ronde() == 1:
        return BATU
    jumlah = jumlah_terakhir()
    if hp_saya() < hp_awal() / 3:
        return tersedikit(jumlah)          # golongan kecil, risiko kecil
    return pengalah(pilihan_terakhir(terkuat()))   # serang si juara
```

### Menengah: membaca kebiasaan tiap lawan

```python
def tebak(nama):
    fav = terbanyak(riwayat_pilihan(nama))
    return fav if fav is not None else BATU

def pilih():
    if ronde() == 1:
        return GUNTING
    tebakan = {}
    for nama in lawan():
        tebakan[nama] = tebak(nama)
    skor = {}
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor[s] = hitung_hasil(tebakan)[nama_saya()]
    return terbanyak(skor)
```

### Lanjut: mendeteksi lawan yang suka berputar

```python
def berikutnya_kalau_berputar(nama):
    hist = [p for p in riwayat_pilihan(nama) if p is not None]
    if len(hist) < 3:
        return None
    # cek apakah lawan selalu pindah ke senjata yang mengalahkan pilihan sebelumnya
    for i in range(1, len(hist)):
        if hist[i] != pengalah(hist[i - 1]):
            return None
    return pengalah(hist[-1])

def pilih():
    if ronde() <= 2:
        return BATU
    tebakan = {}
    for nama in lawan():
        prediksi = berikutnya_kalau_berputar(nama)
        tebakan[nama] = prediksi if prediksi else (pilihan_terakhir(nama) or BATU)
    terbaik = BATU
    skor_terbaik = None
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor = hitung_hasil(tebakan)[nama_saya()]
        print(s, skor)
        if skor_terbaik is None or skor > skor_terbaik:
            terbaik, skor_terbaik = s, skor
    return terbaik
```

---

## 7. Ide strategi

- **Ronde 1 tidak punya informasi.** Pilih pembuka yang jarang dipikirkan orang.
- **Golongan kecil lebih untung.** Kalau menang sendirian melawan banyak bot, kamu menyerap semua HP mereka.
- **Banyak bot mudah ditebak.** Bot yang selalu melawan mayoritas atau selalu meniru juara punya pola. Cari polanya di `riwayat_pilihan`.
- **Jangan terlalu mudah ditebak juga.** Lawan bisa membaca pola botmu. Campur beberapa aturan, misalnya berdasarkan HP, ronde, atau keadaan lawan.
- **Perhatikan ingatan.** Riwayat hanya berisi `ingatan()` ronde terakhir. Jangan berasumsi riwayat berisi semua ronde.
- **Mode bertahan.** Saat HP tipis, kerugian satu ronde bisa membuatmu gugur. Saat HP tebal, kamu bisa mengambil risiko.
- **Gunakan `hitung_hasil`** untuk mencoba beberapa skenario sebelum memilih.

---

## 8. Template permintaan ke AI

Salin dokumen ini, lalu tambahkan permintaan seperti:

> Berdasarkan panduan Suit Bot Arena di atas, buatkan bot dengan strategi berikut: [jelaskan strategimu]. Pastikan hanya memakai fitur yang didukung, menangani ronde 1 (riwayat kosong), dan selalu mengembalikan BATU, GUNTING, atau KERTAS. Beri komentar singkat dalam bahasa Indonesia di kodenya.

Contoh strategi yang bisa diminta:

- "Kalau ronde lalu aku rugi, pakai senjata yang mengalahkan senjata yang mengalahkanku. Kalau untung, ulangi."
- "Tebak pilihan tiap lawan dari senjata favoritnya, lalu pilih senjata yang paling untung, tapi kalau HP-ku di bawah 300 pilih senjata paling sepi."
- "Serang lawan terkuat setiap ronde ganjil, dan lawan terlemah setiap ronde genap."

## 9. Checklist sebelum dikirim

1. Ada `def pilih():` dan semua jalur kode berakhir dengan `return` salah satu senjata.
2. Ronde 1 ditangani: `pilihan_terakhir` bisa `None`, `riwayat()` bisa kosong.
3. Tidak ada `import`, `random`, `class`, `try`, `global`.
4. Tidak bergantung pada variabel yang disimpan antar ronde.
5. Tidak ada perulangan yang bisa berjalan tanpa akhir.
