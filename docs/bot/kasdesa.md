# Panduan Bot: Dilema Kas Desa

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Tiap ronde dapat 10 koin. Sumbang ke kas desa (dilipatgandakan lalu dibagi rata) atau simpan sendiri. Kerja sama atau khianat?**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap ronde setiap pemain mendapat *pendapatan* (default 10 koin) dan memilih berapa yang **disumbang** ke kas desa (0 sampai 10).
- Total kas **dikali pengali** (default 1,6) lalu **dibagi rata** ke semua pemain, termasuk yang tidak menyumbang.
- Koin yang tidak disumbang langsung masuk tabunganmu. Tabungan terbanyak setelah semua ronde menang.
- Kalau semua menyumbang penuh, semua untung besar. Tapi yang tidak menyumbang selalu untung lebih banyak dari yang menyumbang di ronde itu.

## Aksi yang dikembalikan

Satu angka bulat 0 sampai pendapatan, misalnya `10`.

## Isi `info()`

```
{ "ronde": 3, "ronde_total": 12, "pendapatan": 10, "pengali": 1.6, "terbuka": true,
  "skor": {"Budi": 31.2, ...},
  "riwayat": [ {"ronde": 1, "sumbangan": {"Budi": 10, "Ani": 0}, "total": 10, "bagian": 8.0} ] }
```
Kalau `terbuka` mati, `sumbangan` berisi `None`.

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
| Jumlah ronde | 12 |  |
| Koin per ronde | 10 |  |
| Pengali kas | 1.6 | Kas dikali angka ini sebelum dibagi rata. |
| Sumbangan tiap orang terlihat | True | Kalau mati, hanya total kas yang terlihat. |

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

Selalu menyumbang penuh.

```python
def aksi():
    return info()["pendapatan"]
```

### Balas Setara

Menyumbang sebesar rata-rata sumbangan ronde lalu.

```python
def aksi():
    i = info()
    if not i["riwayat"]:
        return i["pendapatan"]
    r = i["riwayat"][-1]
    return int(r["total"] / jumlah_pemain())
```

### Akhir Pelit

Kerja sama penuh, kecuali 2 ronde terakhir.

```python
def aksi():
    i = info()
    if i["ronde"] > i["ronde_total"] - 2:
        return 0
    return i["pendapatan"]
```

