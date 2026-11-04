# Panduan Bot: Pasar Malam Sepi

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Datang ke pasar malam atau di rumah? Asyik kalau sepi, sumpek kalau terlalu ramai. Kalau semua berpikir sama, semua rugi.**

Pemain: 2–12. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap malam semua pemain memilih **datang** ke pasar malam atau **rumah**, bersamaan.
- Kalau yang datang **tidak lebih dari kapasitas** (default 60% pemain, dibulatkan ke bawah, minimal 1), semua yang datang dapat **+1** (asyik).
- Kalau yang datang **melebihi kapasitas**, semua yang datang dapat **−1** (sumpek). Yang di rumah selalu 0.
- Semua pilihan dibuka setelah malam selesai. Skor tertinggi setelah semua malam menang.

## Aksi yang dikembalikan

Teks `"datang"` atau `"rumah"` (atau `True`/`False`).

## Isi `info()`

```
{ "malam": 4, "malam_total": 20, "kapasitas": 3, "skor": {"Budi": 2, ...},
  "riwayat": [ {"malam": 1, "datang": ["Budi", "Ani"], "jumlah": 2, "ramai": false} ] }
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
| Jumlah malam | 20 |  |
| Kapasitas nyaman (%) | 60 | Persentase pemain yang boleh datang supaya tetap nyaman. |

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

### Kebalikan Kemarin

Kalau kemarin ramai, di rumah. Kalau sepi, datang.

```python
def aksi():
    i = info()
    if not i["riwayat"]:
        return "datang"
    return "rumah" if i["riwayat"][-1]["ramai"] else "datang"
```

### Peramal 3 Malam

Memperkirakan pengunjung dari rata-rata 3 malam terakhir.

```python
def aksi():
    i = info()
    r = i["riwayat"][-3:]
    if not r:
        return "datang"
    perkiraan = sum(x["jumlah"] for x in r) / len(r)
    return "datang" if perkiraan < i["kapasitas"] else "rumah"
```

### Selang-seling

Datang di malam ganjil, di rumah di malam genap.

```python
def aksi():
    return "datang" if info()["malam"] % 2 == 1 else "rumah"
```

### Bergiliran Kursi

Memakai nomor kursi supaya tiap malam yang datang pas kapasitas (kalau semua memakai cara ini).

```python
def aksi():
    i = info()
    return "datang" if (i["malam"] + saya()) % jumlah_pemain() < i["kapasitas"] else "rumah"
```

