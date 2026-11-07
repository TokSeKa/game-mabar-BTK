# Panduan Bot: Angka Dua Pertiga

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Semua menebak angka 0–100. Target = faktor × rata-rata tebakan; yang paling dekat menang. Faktornya rahasia tiap ronde dan tebakan kembar gugur, jadi ikut-ikutan orang lain tidak aman.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap ronde semua pemain menebak satu angka bulat dari 0 sampai *batas* (default 100), bersamaan.
- **Target = faktor × rata-rata semua tebakan.** Pemain yang tebakannya paling dekat dengan target mendapat **1 poin**
  (kalau dua tebakan berbeda sama dekatnya, keduanya dapat 1).
- **Faktor acak & rahasia** (default): setiap ronde faktor diambil di antara 0,5 dan 1,5 (bisa diatur) dan **baru diumumkan setelah semua
  menebak**. Kadang target di bawah rata-rata, kadang di atas. Host bisa memilih faktor tetap (klasik ⅔).
- **Tebakan kembar gugur** (default): angka yang dipilih dua orang atau lebih tidak bisa menang, walaupun paling dekat. Tetap ikut dihitung
  di rata-rata.
- Semua tebakan dan faktor dibuka setelah ronde (kecuali opsi *tebakan lawan rahasia*). Poin terbanyak setelah semua ronde menang.
- Opsi host: **acuan median** (target = faktor × median, bukan rata-rata), **poin 3-2-1** (tiga tebakan sah terdekat), **angka terlarang**
  (diumumkan di awal ronde; tebakan di angka itu gugur).

**Kenapa begini:** di versi klasik semua orang cepat sadar jawabannya selalu turun ke 0 (faktor < 1), naik ke batas (faktor > 1),
atau berkumpul di tengah (faktor 1), lalu semua menebak sama dan permainan jadi membosankan. Dengan faktor rahasia, kamu harus
menebak *ke mana* rata-rata akan jatuh tanpa tahu persis pengalinya; dengan aturan kembar gugur, berkumpul di angka yang "jelas"
malah membuat semua yang di sana kalah. Kamu harus dekat dengan target **dan** berbeda dari orang lain.

## Aksi yang dikembalikan

Satu angka bulat, misalnya `33`.

## Isi `info()`

```
{ "ronde": 2, "ronde_total": 10, "batas": 100,
  "mode_faktor": "acak", "faktor": None, "faktor_min": 0.5, "faktor_max": 1.5, "faktor_rata": 1.0,
  "kembar_gugur": True, "acuan": "rata", "poin_mode": "satu", "terlarang": [13, 40], "tebakan_rahasia": False,
  "skor": {"Budi": 1, ...},
  "riwayat": [ {"ronde": 1, "tebakan": {"Budi": 33, "Ani": 50, "Citra": 50}, "rata": 44.3, "faktor": 1.12,
                "target": 49.6, "gugur": ["Ani", "Citra"], "pemenang": ["Budi"]} ] }
```
- `faktor` = faktor ronde ini kalau sudah diketahui (mode tetap), `None` kalau masih rahasia (mode acak).
- `faktor_rata` = faktor rata-rata yang bisa diharapkan (tengah-tengah batas bawah & atas, atau faktor tetap).
- `gugur` = pemain yang tebakannya kembar dengan orang lain atau kena angka terlarang (tidak bisa menang).
- `terlarang` = angka terlarang ronde ini (diumumkan di awal ronde). Riwayat juga berisi `poin` per pemain ronde itu.
- Kalau tebakan lawan rahasia, `tebakan` & `gugur` di riwayat hanya berisi milikmu.

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
| Dasar | Jumlah ronde (`ronde`) | 10 |  |
| Dasar | Angka maksimal (`batas`) | 100 |  |
| Aturan | Faktor tiap ronde (`mode_faktor`) | acak | Acak: faktor ronde ini diambil di antara batas bawah dan atas, baru diumumkan setelah semua menebak. |
| Aturan | Faktor acak: batas bawah (`faktor_min`) | 0.5 |  |
| Aturan | Faktor acak: batas atas (`faktor_max`) | 1.5 |  |
| Aturan | Faktor tetap (`faktor`) | 0.667 | Klasik: ⅔. |
| Aturan | Tebakan kembar gugur (`kembar_gugur`) | True | Angka yang ditebak lebih dari satu orang tidak bisa menang (tetap ikut dihitung di rata-rata). |
| Aturan | Acuan target (`acuan`) | rata | Median tidak terpengaruh satu-dua tebakan ekstrem. |
| Aturan | Pembagian poin (`poin_mode`) | satu |  |
| Informasi (kabut) | Tebakan lawan rahasia (`tebakan_rahasia`) | False | Setelah ronde hanya rata-rata/median, target, dan pemenang yang dibuka; tebakan orang lain tidak. |
| Kejutan | Angka terlarang tiap ronde (`terlarang`) | 0 | Sekian angka acak diumumkan di awal ronde. Tebakan di angka itu gugur (tidak bisa menang). |

**Preset:** *Klasik ⅔* (mode_faktor=tetap, kembar_gugur=False); *Kabut* (tebakan_rahasia=True); *Kacau* (acuan=median, poin_mode=bertingkat, terlarang=5)

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

### Sepertiga

Selalu 33 (anggap orang lain menebak di sekitar 50).

```python
def aksi():
    return 33
```

### Berpikir Dua Lapis

Menganggap lawan menebak tengah-tengah, lalu dikali faktor yang diharapkan dua kali.

```python
def aksi():
    i = info()
    f = i["faktor_rata"]
    return min(i["batas"], int(f * f * i["batas"] / 2))
```

### Pengejar Target

Menebak target ronde lalu dikali faktor yang diharapkan.

```python
def aksi():
    i = info()
    if not i["riwayat"]:
        return 30
    return min(i["batas"], int(i["riwayat"][-1]["target"] * i["faktor_rata"]))
```

### Si Beda Sendiri

Menebak acuan ronde lalu × faktor yang diharapkan, digeser sesuai nomor kursi supaya tidak kembar, dan menghindari angka terlarang.

```python
def aksi():
    i = info()
    dasar = i["batas"] // 2
    if i["riwayat"]:
        dasar = int(i["riwayat"][-1]["rata"] * i["faktor_rata"])
    geser = (saya() + 1) // 2
    if saya() % 2 == 1:
        geser = -geser
    x = max(0, min(i["batas"], dasar + geser * 3))
    while x in i["terlarang"] and x < i["batas"]:
        x = x + 1
    return x
```

