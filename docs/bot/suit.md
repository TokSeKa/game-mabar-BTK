# Panduan Bot: Suit Live

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def pilih():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Batu-gunting-kertas sirkular rame-rame. Manusia memilih tiap ronde, bot memakai kode Suit Bot Arena yang sama.**

Pemain: 2–8. Fungsi wajib: `def pilih():`.

## Aturan

- Setiap ronde semua pemain memilih **BATU, GUNTING, atau KERTAS** bersamaan.
- Setiap pemain yang senjatanya dikalahkan kehilangan *HP hilang saat kalah* (default 100). HP itu dikumpulkan lalu dibagi rata ke golongan yang mengalahkannya. Sisa pembagian: +1 ke pemenang ber-HP terendah dulu.
- **Sirkular**: kalau ketiga senjata keluar, setiap golongan sekaligus menang atas satu golongan dan kalah dari golongan lain.
- HP 0 = gugur. Yang terakhir hidup menang, atau HP terbanyak saat batas ronde.
- **Mode event** (diatur host): *Taruhan Ganda* (HP kalah ×2), *Pikun* (ingatan bot 3 ronde), *Kilat* (maks 30 ronde),
  *Darah Tipis* (HP awal 30%), *Kabut* (pilihan tiap pemain tidak terlihat, hanya jumlah per senjata), *Kejutan* (salah satunya diundi).
- **HP lawan samar** (opsi): HP lawan dibulatkan ke kelipatan 10% HP awal. **Batas ronde rahasia** (opsi): ±25%, tidak diumumkan.
- **Pemimpin jadi buruan** (opsi): pemain dengan HP tertinggi yang kalah kehilangan HP ekstra, dibagi ke yang mengalahkannya.
- **Kejutan tiap ronde** (opsi), diumumkan di awal ronde: *Ronde Ganda* (HP kalah ×2), *Ronde Terbalik* (batu kalah dari gunting,
  gunting kalah dari kertas, kertas kalah dari batu), *Senjata Terlarang* (yang memakainya kehilangan HP kalah, dibagi ke semua yang
  tidak memakainya; tidak ikut adu senjata ronde itu).

## Aksi yang dikembalikan

Kembalikan teks `BATU`, `GUNTING`, atau `KERTAS` dari `def pilih():` (sama persis dengan bot Suit Bot Arena).

## Isi `info()`

Bot Suit memakai library Suit Bot Arena: `ronde()`, `hp_saya()`, `lawan()`, `jumlah_terakhir()`, `pilihan_terakhir(nama)`,
`riwayat()`, `pengalah(s)`, `korban(s)`, `terbanyak(d)`, `hitung_hasil(pilihan)`, `senjata_terbaik()`, dst. `info()` juga tersedia dan berisi
`ronde`, `ronde_maks` (perkiraan kalau `ronde_pasti` False), `hp` (dict nama → HP; dibulatkan untuk lawan kalau HP samar),
`riwayat` (ronde-ronde terakhir sebanyak ingatan; `perubahan` lawan None kalau HP samar), `kejutan` (kejutan ronde ini atau None:
`{"jenis": "ganda" | "terbalik" | "terlarang", "senjata": "batu" (untuk terlarang)}`), dan `pemimpin` (nama yang sedang diburu).

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `BATU` | Senjata batu. Mengalahkan gunting. |
| `GUNTING` | Senjata gunting. Mengalahkan kertas. |
| `KERTAS` | Senjata kertas. Mengalahkan batu. |
| `SENJATA` | List [BATU, GUNTING, KERTAS]. |
| `nama_saya()` | Nama botmu. |
| `hp_saya()` | HP botmu di awal ronde ini. |
| `ronde()` | Nomor ronde sekarang, mulai dari 1. |
| `ronde_maks()` | Batas ronde match ini. |
| `hp_awal()` | HP setiap pemain saat match dimulai. |
| `hp_kalah()` | HP yang hilang setiap kali kalah. |
| `ingatan()` | Berapa ronde terakhir yang bisa dilihat di riwayat. |
| `semua_pemain()` | Nama semua peserta (termasuk yang sudah gugur dan dirimu). |
| `pemain_hidup()` | Nama peserta yang masih hidup, termasuk dirimu. |
| `lawan()` | Nama lawan yang masih hidup. |
| `hp(nama)` | HP pemain itu di awal ronde (0 kalau sudah gugur). |
| `terkuat()` | Nama lawan dengan HP tertinggi. |
| `terlemah()` | Nama lawan dengan HP terendah. |
| `jumlah_terakhir()` | Jumlah pemilih tiap senjata di ronde lalu, misalnya {"batu": 3, "gunting": 2, "kertas": 3}. |
| `riwayat_jumlah()` | List jumlah tiap senjata per ronde (sebanyak ingatan, terbaru di akhir). |
| `pilihan_terakhir(nama)` | Senjata pemain itu di ronde lalu (None kalau belum ada). |
| `riwayat_pilihan(nama)` | List senjata pemain itu per ronde dalam ingatan. |
| `perubahan_terakhir(nama)` | Perubahan HP pemain itu di ronde lalu (+ untung, - rugi). |
| `riwayat_perubahan(nama)` | List perubahan HP pemain itu per ronde dalam ingatan. |
| `riwayat()` | List lengkap per ronde: {"ronde", "jumlah", "pilihan", "perubahan", "hp"}. |
| `pengalah(senjata)` | Senjata yang MENGALAHKAN senjata itu. pengalah(BATU) = KERTAS. |
| `korban(senjata)` | Senjata yang DIKALAHKAN senjata itu. korban(BATU) = GUNTING. |
| `terbanyak(dict_atau_list)` | Kunci dengan nilai terbesar, atau isi list yang paling sering muncul. Seri: batu, gunting, kertas. |
| `tersedikit(dict_atau_list)` | Kebalikan terbanyak(). |
| `hitung(list, nilai)` | Berapa kali nilai muncul di list. |
| `total_jumlah(list_dict)` | Menjumlahkan list dict, misalnya total_jumlah(riwayat_jumlah()). |
| `hitung_hasil(pilihan)` | Simulasi satu ronde: masukkan {nama: senjata}, keluar {nama: perubahan HP}. |
| `senjata_terbaik()` | Senjata paling untung untukmu kalau semua lawan mengulang pilihan ronde lalu. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | HP awal (`hp_awal`) | 1000 |  |
| Dasar | HP hilang saat kalah (`hp_kalah`) | 100 |  |
| Dasar | Batas ronde (`ronde_maks`) | 40 |  |
| Dasar | Ingatan bot (ronde) (`ingatan`) | 10 |  |
| Kejutan | Mode event (`event`) | normal | Variasi aturan: taruhan ganda, pikun, kilat, darah tipis, kabut, atau kejutan acak. |
| Informasi (kabut) | HP lawan samar (`hp_samar`) | False | HP lawan dibulatkan ke kelipatan 10% HP awal, dan perubahan HP lawan tiap ronde tidak terlihat. HP-mu sendiri tetap pasti. |
| Informasi (kabut) | Batas ronde rahasia (`ronde_rahasia`) | False | Batas ronde sebenarnya acak ±25% dari pengaturan dan tidak diumumkan. |
| Aturan | Pemimpin jadi buruan (%) (`buruan`) | 0 | Kalau pemain dengan HP tertinggi (satu orang) kalah, ia kehilangan HP ekstra sekian persen dari HP kalah; ekstranya dibagi ke yang mengalahkannya. |
| Kejutan | Kejutan tiap ronde (%) (`kejutan_ronde`) | 0 | Peluang tiap ronde mendapat kejutan yang diumumkan di awal ronde: Ronde Ganda, Ronde Terbalik, atau Senjata Terlarang (yang memakainya kehilangan HP kalah, dibagi ke semua yang tidak memakainya). |

**Preset:** *Kabut* (hp_samar=True, ronde_rahasia=True, event=kabut); *Kacau* (kejutan_ronde=40, buruan=50)

## Bahasa bot (sama untuk semua game)

- Bot ditulis dalam **subset Python** dan dijalankan interpreter khusus (bukan Python biasa).
- Boleh: variabel, `+ - * / // % **`, perbandingan, `and/or/not`, `if/elif/else`, `for`, `while`, `break`, `continue`,
  `def` (fungsi bantu), `lambda`, list, dict, tuple, comprehension, f-string, dan fungsi bawaan
  `len, range, min, max, sum, abs, round, int, float, str, bool, list, dict, tuple, sorted, reversed, enumerate, zip, any, all, print`.
- Method list: `append, extend, insert, pop, remove, index, count, copy, reverse, sort, clear`.
  Method dict: `get, keys, values, items, copy, pop, setdefault, update, clear`. Method teks: `upper, lower, strip, split, join, replace, find, count, startswith, endswith`.
- **Dilarang/tidak ada:** `import`, `random`, `class`, `try/except`, `global`, `with`, `yield`, set `{1,2}`, atribut berawalan `_`, `open/eval/exec/getattr/type`.
- **Tidak ada memori antar langkah.** Setiap kali bot dipanggil, seluruh kode dijalankan dari nol. Semua informasi diambil dari `info()`.
- **Tidak ada keacakan.** Bot yang sama dengan info yang sama selalu memberi aksi yang sama.
- Batas: 20.000 langkah per pemanggilan, list/teks maks 10.000 isi. Kalau bot error atau aksinya tidak valid, langkah itu memakai **aksi bawaan**.
  Error 3 kali berturut-turut → bot dimatikan dan selalu memakai aksi bawaan.
- `print(...)` ditulis ke log botmu (hanya kamu yang bisa melihat, muncul di layar hasil).

## Contoh bot

### Si Batu

Selalu memilih batu. Bot paling sederhana.

```python
def pilih():
    return BATU
```

### Pemutar

Berputar batu, kertas, gunting, lalu kembali ke batu.

```python
def pilih():
    urutan = [BATU, KERTAS, GUNTING]
    # ronde 1 -> indeks 0, ronde 2 -> indeks 1, dst.
    return urutan[(ronde() - 1) % 3]
```

### Anti Mayoritas

Melawan senjata yang paling banyak dipilih di ronde lalu.

```python
def pilih():
    if ronde() == 1:
        return KERTAS
    favorit = terbanyak(jumlah_terakhir())
    return pengalah(favorit)
```

### Minoritas

Memilih senjata yang paling sepi di ronde lalu, supaya kalau menang bagiannya besar.

```python
def pilih():
    if ronde() == 1:
        return GUNTING
    return tersedikit(jumlah_terakhir())
```

### Peniru Juara

Meniru pilihan terakhir lawan yang HP-nya paling tinggi.

```python
def pilih():
    if ronde() == 1:
        return BATU
    juara = terkuat()
    tiruan = pilihan_terakhir(juara)
    if tiruan is None:
        return BATU
    return tiruan
```

### Pemburu Juara

Menyerang lawan ber-HP tertinggi dengan senjata yang mengalahkan pilihan terakhirnya.

```python
def pilih():
    if ronde() == 1:
        return KERTAS
    target = terkuat()
    tebakan = pilihan_terakhir(target)
    if tebakan is None:
        return KERTAS
    return pengalah(tebakan)
```

### Pengamat

Menjumlahkan semua ronde dalam ingatan, lalu melawan senjata yang paling sering muncul.

```python
def pilih():
    if ronde() == 1:
        return BATU
    total = total_jumlah(riwayat_jumlah())
    return pengalah(terbanyak(total))
```

### Pembalas

Kalau ronde lalu untung, ulangi. Kalau rugi, pakai senjata yang mengalahkan penakluknya.

```python
def pilih():
    if ronde() == 1:
        return GUNTING
    saya = nama_saya()
    terakhir = pilihan_terakhir(saya)
    if perubahan_terakhir(saya) >= 0:
        return terakhir
    penakluk = pengalah(terakhir)
    return pengalah(penakluk)
```

### Hati-hati

Melawan mayoritas. Kalau HP tinggal sepertiga, sembunyi di senjata paling sepi.

```python
def pilih():
    if ronde() == 1:
        return BATU
    jumlah = jumlah_terakhir()
    if hp_saya() < hp_awal() / 3:
        return tersedikit(jumlah)
    return pengalah(terbanyak(jumlah))
```

### Ahli Hitung

Menganggap semua lawan mengulang pilihannya, lalu menghitung senjata yang paling untung.

```python
def pilih():
    if ronde() == 1:
        return GUNTING
    tebakan = {}
    for nama in lawan():
        tebakan[nama] = pilihan_terakhir(nama)
    terbaik = BATU
    skor_terbaik = -999999
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor = hitung_hasil(tebakan)[nama_saya()]
        if skor > skor_terbaik:
            terbaik = s
            skor_terbaik = skor
    return terbaik
```

### Pembaca Pola

Menebak pilihan tiap lawan dari senjata favoritnya dalam ingatan, lalu memilih senjata yang paling untung.

```python
def tebak(nama):
    favorit = terbanyak(riwayat_pilihan(nama))
    if favorit is None:
        return BATU
    return favorit

def pilih():
    if ronde() <= 2:
        return [KERTAS, BATU][ronde() - 1]
    tebakan = {}
    for nama in lawan():
        tebakan[nama] = tebak(nama)
    skor = {}
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor[s] = hitung_hasil(tebakan)[nama_saya()]
    return terbanyak(skor)
```

