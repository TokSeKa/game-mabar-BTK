# Panduan Bot: Tenggelamkan Kapal

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**1 lawan 1. Susun armada di papan rahasia, lalu bergantian menembak. Tenggelamkan semua kapal lawan lebih dulu.**

Pemain: 2–2. Fungsi wajib: `def aksi():`.

## Aturan

- **Fase susun:** kedua pemain menyusun armadanya secara rahasia di papan (default 10×10). Kapal lurus (mendatar atau menurun), tidak boleh keluar papan atau bertumpuk. Boleh bersentuhan.
- **Fase tembak:** pemain bergantian menembak satu petak papan lawan. Hasilnya: *meleset*, *kena*, atau *tenggelam* (kalau semua petak kapal itu sudah kena). Ukuran kapal yang tenggelam diumumkan.
- Yang pertama menenggelamkan seluruh armada lawan menang. Siapa yang menembak duluan ditentukan undian di awal.
- Kalau waktu habis: susunan diacak otomatis / tembakan diarahkan ke petak acak yang belum ditembak.

## Aksi yang dikembalikan

- Fase `susun`: list posisi untuk setiap kapal sesuai urutan `armada`, masing-masing `[baris, kolom, arah]` dengan arah `"H"` (mendatar ke kanan) atau `"V"` (menurun ke bawah). Baris & kolom mulai dari 0.
  Contoh armada standar: `[[0,0,"H"], [2,0,"H"], [4,0,"H"], [6,0,"H"], [8,0,"H"]]`.
- Fase `tembak`: `[baris, kolom]`, misalnya `[3, 7]`.

## Isi `info()`

```
{ "fase": "susun" | "tembak", "ukuran": 10, "armada": [5,4,3,3,2], "giliran": "Budi",
  "papan_saya": ["K.....", ...],    # baris teks: K = kapalku, x = tembakan lawan meleset, o = kapalku kena, # = kapalku tenggelam
  "papan_tembak": ["..x.o#", ...],  # tembakanku ke lawan: . belum, x meleset, o kena, # tenggelam
  "kapal_lawan_sisa": [5,3,2],      # ukuran kapal lawan yang belum tenggelam
  "riwayat": [ {"penembak": "Budi", "baris": 3, "kolom": 7, "hasil": "kena" | "meleset" | "tenggelam", "ukuran": 3} ] }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `belum_ditembak()` | List [baris, kolom] petak lawan yang belum pernah kamu tembak. |
| `tetangga(baris, kolom)` | Petak atas/bawah/kiri/kanan yang masih di dalam papan. |
| `susunan_valid(susunan)` | True kalau susunan kapal itu sah. |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| Ukuran papan | 10 |  |
| Armada | standar |  |
| Kena = tembak lagi | False | Kalau aktif, tembakan yang kena memberi giliran tambahan. |

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

### Pemburu Papan Catur

Menembak pola papan catur; kalau ada yang kena, memburu petak di sekitarnya.

```python
def aksi():
    i = info()
    n = i["ukuran"]
    if i["fase"] == "susun":
        hasil = []
        baris = 0
        for ukuran in i["armada"]:
            hasil.append([baris, (baris * 3) % (n - ukuran + 1), "H"])
            baris += 2
        return hasil
    p = i["papan_tembak"]
    # buru di sekitar petak yang kena tapi kapalnya belum tenggelam
    for r in range(n):
        for c in range(n):
            if p[r][c] == "o":
                for t in tetangga(r, c):
                    if p[t[0]][t[1]] == ".":
                        return t
    for t in belum_ditembak():
        if (t[0] + t[1]) % 2 == 0:
            return t
    return belum_ditembak()[0]
```

### Penyapu Baris

Menembak baris demi baris dari pojok kiri atas.

```python
def aksi():
    i = info()
    if i["fase"] == "susun":
        return [[k * 2, 0, "H"] for k in range(len(i["armada"]))]
    return belum_ditembak()[0]
```

