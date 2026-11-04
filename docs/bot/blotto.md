# Panduan Bot: Rebutan Lahan

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Bagi pasukanmu ke beberapa medan. Pasukan terbanyak di sebuah medan menguasainya. Tidak ada strategi yang selalu menang.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap ronde, setiap pemain membagi **pasukan** (default 100) ke beberapa **medan** (default 5), bersamaan dan rahasia.
- Tiap medan punya **nilai** (1–5). Nilai ronde ini dan ronde berikutnya sudah diumumkan.
- Pemain dengan pasukan terbanyak di sebuah medan mendapat nilai medan itu. Kalau seri, nilainya dibagi rata. Medan tanpa pasukan tidak dimiliki siapa pun.
- Pasukan tidak berkurang: setiap ronde semua mulai lagi dengan jumlah pasukan penuh. Semua alokasi dibuka setelah ronde selesai.
- Poin terbanyak setelah semua ronde menang.

## Aksi yang dikembalikan

List angka bulat ≥ 0 sepanjang jumlah medan, totalnya tidak lebih dari jumlah pasukan. Contoh 5 medan: `[30, 30, 20, 10, 10]`.

## Isi `info()`

```
{
  "ronde": 3, "ronde_total": 10, "medan": 5, "pasukan": 100,
  "nilai": [3, 1, 5, 2, 4],          # nilai medan ronde ini
  "nilai_berikut": [2, 2, 1, 5, 3],  # ronde berikutnya (None di ronde terakhir)
  "skor": {"Budi": 12.5, ...},
  "riwayat": [ {"ronde": 1, "nilai": [...], "alokasi": {"Budi": [20, 20, 20, 20, 20], ...},
                "penguasa": [["Budi"], ["Ani", "Citra"], [], ...], "poin": {"Budi": 4.0, ...}} ]
}
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `bagi_rata()` | Alokasi rata ke semua medan (sisa ke medan pertama). |
| `rata_rata_lawan()` | Rata-rata pasukan lawan per medan di ronde lalu (list). |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| Jumlah medan | 5 |  |
| Pasukan per ronde | 100 |  |
| Jumlah ronde | 10 |  |
| Nilai medan berbeda-beda | True | Kalau mati, semua medan bernilai 1. |

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

### Si Rata

Membagi rata ke semua medan.

```python
def aksi():
    return bagi_rata()
```

### Fokus Tiga

Menumpuk pasukan di 3 medan bernilai tertinggi.

```python
def aksi():
    i = info()
    nilai = i["nilai"]
    urut = sorted(range(len(nilai)), key=lambda k: -nilai[k])
    pilihan = urut[:3]
    total = sum(nilai[k] for k in pilihan)
    alokasi = [0] * i["medan"]
    sisa = i["pasukan"]
    for k in pilihan:
        alokasi[k] = i["pasukan"] * nilai[k] // total
        sisa -= alokasi[k]
    alokasi[pilihan[0]] += sisa
    return alokasi
```

### Pembaca Rata-rata

Mengalahkan rata-rata lawan di medan bernilai tinggi, lalu melepas sisanya.

```python
def aksi():
    i = info()
    if i["ronde"] == 1:
        return bagi_rata()
    musuh = rata_rata_lawan()
    nilai = i["nilai"]
    urut = sorted(range(i["medan"]), key=lambda k: -nilai[k] / (musuh[k] + 1))
    alokasi = [0] * i["medan"]
    sisa = i["pasukan"]
    for k in urut:
        butuh = int(musuh[k]) + 1
        if butuh <= sisa:
            alokasi[k] = butuh
            sisa -= butuh
    alokasi[urut[0]] += sisa
    return alokasi
```

