# Panduan Bot: Dilema Kas Desa

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Tiap ronde dapat 10 koin. Sumbang ke kas desa atau simpan sendiri. Kalau kas mencapai target, semua dapat bonus; kalau kurang, sumbangan terasa sia-sia. Siapa yang mau menutup kekurangannya?**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap ronde setiap pemain mendapat *pendapatan* (default 10 koin) dan memilih berapa yang **disumbang** ke kas desa (0 sampai 10).
- Total kas **dikali pengali** (default 1,6) lalu **dibagi rata** ke semua pemain, termasuk yang tidak menyumbang.
- **Target gotong royong:** tiap ronde desa punya target kas (default 50% dari total pendapatan semua pemain, misalnya 4 pemain → 20 koin).
  Kalau kas ronde itu **mencapai target**, **semua** pemain mendapat **bonus** (default +10 koin). Kalau kurang sedikit saja, bonusnya hilang.
- Koin yang tidak disumbang langsung masuk tabunganmu. Tabungan terbanyak setelah semua ronde menang.
- **Ronde terakhir dirahasiakan** (default): jumlah ronde sebenarnya ±25% dari angka di pengaturan, jadi strategi "khianat di ronde terakhir" berisiko.
- **Fase sanksi** (kalau host mengaktifkan denda atau voting usir): setelah sumbangan dibuka, semua bersamaan memilih **denda** (bayar koin
  untuk menghapus tabungan orang lain, misalnya bayar 1 → orang itu −3) dan/atau **usir** (satu nama). Yang dipilih lebih dari separuh pemain
  lain diusir di ronde berikutnya: tidak bisa menyumbang dan tidak dapat bagian kas maupun bonus.
- **Bencana** (opsi): target gagal 2 ronde berturut-turut → semua kehilangan sebagian tabungan.

**Kenapa menyumbang bisa masuk akal:** tanpa target, setiap koin yang kamu sumbang hanya kembali 1,6/jumlah pemain (selalu rugi untukmu).
Dengan target, kalau kas kurang sedikit dari target, menutup kekurangannya justru menguntungkanmu karena bonus untukmu sendiri lebih besar
daripada koin yang kamu keluarkan. Tapi kalau orang lain sudah menutup target, menyumbang lebih banyak lagi kembali rugi. Jadi pertanyaannya:
**siapa yang menutup target, dan apakah kamu percaya mereka?** Denda dan voting usir membuat penumpang gelap bisa dihukum.

## Aksi yang dikembalikan

- Fase `sumbang`: satu angka bulat 0 sampai pendapatan, misalnya `10`.
- Fase `sanksi`: `{"denda": {"Budi": 2}, "usir": "Budi"}` (keduanya boleh kosong / `None`). Mengembalikan angka atau `None` di fase ini
  dianggap tanpa sanksi, jadi bot lama tetap jalan.

## Isi `info()`

```
{ "fase": "sumbang", "ronde": 3, "ronde_total": 12, "akhir_pasti": False, "pendapatan": 10, "pengali": 1.6, "terbuka": True,
  "target": 20, "bonus": 10, "pemain": 4, "denda": 0, "usir_aktif": False, "dikucilkan": [],
  "skor": {"Budi": 31.2, ...},
  "riwayat": [ {"ronde": 1, "sumbangan": {"Budi": 10, "Ani": 0}, "total": 22, "bagian": 8.8, "pengali": 1.6,
                "target": 20, "tercapai": True, "bonus": 10, "dikucilkan": [],
                "sanksi": {"denda": {"Budi": {"Ani": 2}}, "usir": {"Budi": "Ani"}, "diusir": ["Ani"]}} ] }
```
- `pengali` None kalau pengali rahasia (dibuka di riwayat setelah ronde); `pengali_kisaran` = [terkecil, terbesar] yang mungkin.
  `dikucilkan` = pemain yang diusir di ronde ini.
- Kalau `terbuka` mati, `sumbangan` berisi `None`.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Jumlah ronde (`ronde`) | 12 |  |
| Dasar | Koin per ronde (`pendapatan`) | 10 |  |
| Dasar | Pengali kas (`pengali`) | 1.6 | Kas dikali angka ini sebelum dibagi rata. |
| Aturan | Target kas (%) (`target`) | 50 | Persen dari total pendapatan semua pemain. Kalau kas ronde itu mencapai target, semua dapat bonus. 0 = tanpa target (versi klasik). |
| Aturan | Bonus target (koin/orang) (`bonus`) | 10 | Diterima SEMUA pemain kalau target tercapai. |
| Informasi (kabut) | Ronde terakhir dirahasiakan (`akhir_rahasia`) | True | Jumlah ronde sebenarnya acak di sekitar angka di atas (±25%), jadi tidak ada yang tahu kapan aman berkhianat. |
| Informasi (kabut) | Sumbangan tiap orang terlihat (`terbuka`) | True | Kalau mati, hanya total kas yang terlihat. |
| Informasi (kabut) | Pengali kas rahasia (`pengali_rahasia`) | False | Pengali tiap ronde acak (½× sampai 1½× pengali) dan baru dibuka setelah ronde. |
| Aturan | Denda (koin hilang per koin) (`denda`) | 0 | Menambah fase SANKSI setelah sumbangan dibuka: setiap koin yang kamu bayar menghapus sekian koin tabungan orang yang kamu pilih. Maksimal bayar = pendapatan per ronde. 0 = mati. |
| Aturan | Voting usir (`usir`) | False | Di fase sanksi tiap pemain boleh memilih satu orang. Yang dipilih lebih dari separuh pemain lain diusir di ronde berikutnya: tidak bisa menyumbang dan tidak dapat bagian kas maupun bonus. |
| Kejutan | Bencana (% tabungan) (`bencana`) | 0 | Kalau target kas gagal 2 ronde berturut-turut, banjir datang: semua kehilangan sekian persen tabungan. Perlu target > 0. |

**Preset:** *Klasik* (target=0, akhir_rahasia=False); *Kabut* (terbuka=False, pengali_rahasia=True); *Desa Tegas* (denda=3, usir=True, bencana=30)

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

### Dermawan

Selalu menyumbang penuh, tidak pernah menghukum.

```python
def aksi():
    if info()["fase"] == "sanksi":
        return None
    return info()["pendapatan"]
```

### Penutup Target

Menyumbang bagian adilnya dari target; kalau ronde lalu gagal, menambah sedikit.

```python
def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    bagian = (i["target"] + jumlah_pemain() - 1) // jumlah_pemain()
    if i["riwayat"] and not i["riwayat"][-1]["tercapai"]:
        bagian = bagian + 2
    return min(i["pendapatan"], bagian)
```

### Si Penghitung

Menganggap orang lain menyumbang seperti ronde lalu, lalu hanya menutup kekurangan target (kalau ada).

```python
def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    if not i["riwayat"]:
        return i["pendapatan"] // 2
    r = i["riwayat"][-1]
    saya_lalu = r["sumbangan"][nama_saya()]
    if saya_lalu == None:
        saya_lalu = r["total"] // jumlah_pemain()
    lain = r["total"] - saya_lalu
    kurang = i["target"] - lain
    if kurang <= 0:
        return 0
    return min(i["pendapatan"], kurang)
```

### Penegak Aturan

Menyumbang adil; di fase sanksi mendenda dan memilih usir penyumbang paling pelit.

```python
def aksi():
    i = info()
    adil = (max(i["target"], 1) + jumlah_pemain() - 1) // jumlah_pemain()
    if i["fase"] != "sanksi":
        return min(i["pendapatan"], adil)
    r = i["riwayat"][-1]
    pelit = None
    for nama in r["sumbangan"]:
        v = r["sumbangan"][nama]
        if nama != nama_saya() and v != None and v < adil:
            if pelit == None or v < r["sumbangan"][pelit]:
                pelit = nama
    if pelit == None:
        return None
    hasil = {"denda": {}, "usir": None}
    if i["denda"] > 0:
        hasil["denda"][pelit] = 2
    if i["usir_aktif"] and r["sumbangan"][pelit] == 0:
        hasil["usir"] = pelit
    return hasil
```

### Akhir Pelit

Kerja sama penuh, kecuali 2 ronde terakhir (menurut jumlah ronde di pengaturan).

```python
def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    if i["ronde"] > i["ronde_total"] - 2:
        return 0
    return i["pendapatan"]
```

