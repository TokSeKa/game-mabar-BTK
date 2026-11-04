# Panduan Bot: Lelang Rahasia

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Setiap ronde satu barang dilelang. Semua menawar diam-diam dengan modal terbatas. Penawar tertinggi membayar dan mendapat poin barang.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Ada sejumlah **barang** (default 12) yang dilelang satu per satu. **Nilai poin semua barang sudah diumumkan dari awal** (1–10), jadi kamu bisa merencanakan.
- Setiap ronde semua pemain menawar secara **tertutup**, maksimal sebanyak koin yang dimiliki (modal awal default 100 koin, tidak bertambah).
- **Penawar tertinggi** membayar tawarannya dan mendapat poin barang itu. Kalau tawaran tertinggi **seri**, barang **hangus**: tidak ada yang dapat dan tidak ada yang bayar.
- Skor akhir = poin barang + koin sisa × *poin per koin sisa* (default 0,1).

## Aksi yang dikembalikan

Satu angka bulat 0 sampai koinmu, misalnya `25`.

## Isi `info()`

```
{ "ronde": 3, "ronde_total": 12, "barang": {"nama": "Keris Pusaka", "nilai": 8},
  "jadwal": [5, 2, 8, 3, ...],   # nilai semua barang, urut ronde (indeks 0 = ronde 1)
  "koin": {"Budi": 70, ...}, "poin": {"Budi": 5, ...}, "nilai_sisa": 0.1,
  "riwayat": [ {"ronde": 1, "nilai": 5, "tawaran": {"Budi": 30, "Ani": 20}, "pemenang": "Budi", "harga": 30} ] }
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
| Jumlah barang | 12 |  |
| Modal koin | 100 |  |
| Poin per koin sisa | 0.1 | Koin yang tidak terpakai bernilai sekian poin di akhir. |

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

### Proporsional

Menawar sebanding nilai barang dibanding total nilai yang tersisa.

```python
def aksi():
    i = info()
    koin = i["koin"][nama_saya()]
    sisa_nilai = sum(i["jadwal"][i["ronde"] - 1:])
    return int(koin * i["barang"]["nilai"] / sisa_nilai)
```

### Pemburu Barang Mahal

Hanya serius menawar barang bernilai 7 ke atas.

```python
def aksi():
    i = info()
    koin = i["koin"][nama_saya()]
    if i["barang"]["nilai"] >= 7:
        return min(koin, i["barang"]["nilai"] * 5)
    return min(koin, 1)
```

### Pengintai Dompet

Menawar sedikit di atas dompet lawan terkaya untuk barang bagus, kalau masih masuk akal.

```python
def aksi():
    i = info()
    saya = nama_saya()
    koin = i["koin"][saya]
    nilai = i["barang"]["nilai"]
    terkaya = max(v for k, v in i["koin"].items() if k != saya)
    if nilai >= 6 and terkaya + 1 <= koin and terkaya + 1 <= nilai * 8:
        return terkaya + 1
    return min(koin, nilai * 3)
```

