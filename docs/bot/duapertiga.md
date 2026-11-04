# Panduan Bot: Angka Dua Pertiga

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Semua menebak angka 0–100. Yang paling dekat dengan ⅔ rata-rata tebakan menang ronde itu.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap ronde semua pemain menebak satu angka bulat dari 0 sampai *batas* (default 100), bersamaan.
- **Target = faktor × rata-rata semua tebakan** (default ⅔).
- Pemain yang tebakannya paling dekat dengan target mendapat **1 poin** (kalau seri, semua yang seri dapat 1).
- Semua tebakan dibuka setelah ronde. Poin terbanyak setelah semua ronde menang.
- Intinya: menebak apa yang ditebak orang lain, yang juga sedang menebak tebakanmu.

## Aksi yang dikembalikan

Satu angka bulat, misalnya `33`.

## Isi `info()`

```
{ "ronde": 2, "ronde_total": 10, "faktor": 0.667, "batas": 100, "skor": {"Budi": 1, ...},
  "riwayat": [ {"ronde": 1, "tebakan": {"Budi": 33, "Ani": 50}, "rata": 41.5, "target": 27.7, "pemenang": ["Budi"]} ] }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| Jumlah ronde | 10 |  |
| Faktor target | 0.667 | Target = faktor × rata-rata tebakan. |
| Angka maksimal | 100 |  |

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

Selalu 33 (anggap lawan menebak acak di sekitar 50).

```python
def aksi():
    return 33
```

### Berpikir Dua Lapis

Menganggap lawan menebak 33, jadi menebak ⅔ dari 33.

```python
def aksi():
    i = info()
    return int(i["faktor"] * i["faktor"] * i["batas"] / 2)
```

### Pengejar Target

Menebak ⅔ dari target ronde lalu (lawan cenderung makin kecil).

```python
def aksi():
    i = info()
    if not i["riwayat"]:
        return 30
    return int(i["riwayat"][-1]["target"] * i["faktor"])
```

