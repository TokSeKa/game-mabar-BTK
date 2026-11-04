# Panduan Bot: Poker Hold'em

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Texas Hold'em no-limit untuk 2–8 orang. Dek diacak dari seed yang hash-nya diumumkan dulu dan dibuka di akhir.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap pemain mulai dengan chip yang sama. Tiap **tangan**, semua mendapat 2 kartu tertutup; 5 kartu meja dibuka bertahap
  (*flop* 3 kartu, *turn* 1, *river* 1). Tangan terbaik dari 5 kartu (gabungan kartu sendiri + meja) menang.
- Urutan tangan: Straight Flush > Empat Sejenis > Full House > Flush > Straight > Tiga Sejenis > Dua Pasang > Satu Pasang > Kartu Tinggi.
  As boleh jadi kartu tertinggi atau terendah (A-2-3-4-5).
- Dua pemain di kiri dealer memasang *small blind* dan *big blind*. Lalu bergiliran: **fold** (menyerah), **check** (lewat kalau tidak ada taruhan),
  **call** (menyamakan taruhan), **raise** (menaikkan; minimal sebesar kenaikan terakhir atau big blind), **all-in** (semua chip).
- *No-limit*: boleh menaikkan sampai seluruh chip. Pemain yang all-in hanya bisa memenangkan bagian pot yang ia ikuti (*side pot*).
- Satu tangan selesai kalau tinggal satu pemain (yang lain fold) atau sampai *showdown* setelah river. Pot seri dibagi rata.
- Blind naik ×1,5 setiap beberapa tangan. Pemain yang chipnya habis tersingkir. Permainan selesai saat tinggal satu pemain
  atau batas tangan tercapai; peringkat menurut chip (yang tersingkir belakangan lebih tinggi).
- **Keadilan dek:** hash seed (`hash_dek`) diumumkan dari awal; seed dibuka di layar hasil supaya bisa dicek ulang.
- Waktu habis = check kalau bisa, kalau tidak fold.

## Aksi yang dikembalikan

Salah satu:
- `"fold"`, `"check"`, `"call"`, `"allin"` (boleh juga `"lipat"`, `"cek"`, `"ikut"`)
- `{"aksi": "raise", "ke": 120}` = naikkan taruhanmu di jalan ini **menjadi** 120 (bukan menambah 120). Fungsi `naik(120)` membuat bentuk ini.
- Raise di bawah minimal dinaikkan otomatis ke minimal; raise melebihi chipmu dianggap all-in. `call` saat tidak ada taruhan dianggap `check`.

## Isi `info()`

```
{ "tangan": 3, "tangan_maks": 40, "sb": 10, "bb": 20, "dealer": "Budi", "hash_dek": "9f2c...",
  "jalan": "flop",                      # preflop | flop | turn | river | selesai
  "meja": ["Kh", "7d", "2c"],           # kartu meja (teks: angka 2-9 T J Q K A + s ♠ h ♥ d ♦ c ♣)
  "kartu_saya": ["As", "Kd"],
  "chip": {"Budi": 950, ...},           # chip di depan pemain (belum termasuk yang sudah masuk pot)
  "taruhan": {"Budi": 40, ...},         # taruhan di jalan ini
  "masuk": {"Budi": 60, ...},           # total yang sudah dimasukkan di tangan ini
  "status": {"Budi": "main" | "fold" | "allin" | "keluar"},
  "pot": 180, "taruhan_tertinggi": 40, "untuk_ikut": 20, "min_raise_ke": 60, "maks_raise_ke": 990,
  "aksi_valid": ["fold", "call", "raise", "allin"], "giliran": "Budi",
  "aksi_tangan": [ {"pemain": "Ani", "aksi": "raise", "jumlah": 40, "ke": 40, "jalan": "preflop"} ],
  "riwayat": [ {"no": 2, "meja": [...], "pot": 300, "menang": {"Ani": 300}, "showdown": {"Ani": {"kartu": [...], "tangan": "Flush"}}, "aksi": [...]} ] }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `kartu_saya()` | Dua kartu tertutupmu, misalnya ['As', 'Kd']. |
| `meja()` | Kartu meja yang sudah terbuka (0, 3, 4, atau 5 kartu). |
| `nilai_tangan(kartu=None)` | Nilai tangan terbaik: {'kategori': 0-8, 'nama': 'Dua Pasang', 'skor': [...]}. Tanpa argumen = kartumu + meja. 'skor' bisa dibandingkan dengan < >. |
| `kekuatan_awal(kartu=None)` | Kekuatan dua kartu awal 0..1 (AA = 1). Berguna sebelum flop. |
| `ekuitas(sampel=150)` | Perkiraan peluang menang 0..1 melawan semua lawan yang belum fold (simulasi tetap/deterministik). Mahal: ±300 langkah. |
| `untuk_ikut()` | Chip yang dibutuhkan untuk call sekarang (0 = boleh check). |
| `pot()` | Total chip di pot sekarang. |
| `peluang_pot()` | untuk_ikut / (pot + untuk_ikut): ekuitas minimal supaya call menguntungkan. |
| `aksi_valid()` | Aksi yang boleh sekarang, misalnya ['fold', 'call', 'raise', 'allin']. |
| `min_raise()` | Taruhan minimal kalau mau raise (nilai 'ke'). |
| `maks_raise()` | Taruhan maksimal (= all-in). |
| `naik(ke)` | Membuat aksi raise: naik(100) sama dengan {'aksi': 'raise', 'ke': 100}. |
| `lawan_aktif()` | Nama lawan yang belum fold di tangan ini. |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| Chip awal | 1000 |  |
| Small blind awal | 10 | Big blind = 2 × small blind. |
| Blind naik tiap (tangan) | 10 | Blind dikali 1,5 setiap sekian tangan. 0 = tetap. |
| Batas tangan | 40 | Berhenti setelah sekian tangan; peringkat menurut chip. |

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

### Batu Karang

Ketat: hanya main kartu awal kuat, lalu bertaruh kalau tangannya bagus.

```python
def aksi():
    i = info()
    valid = aksi_valid()
    if i["jalan"] == "preflop":
        k = kekuatan_awal()
        if k >= 0.7 and "raise" in valid:
            return naik(min_raise() + i["bb"] * 2)
        if k >= 0.45 and untuk_ikut() <= i["bb"] * 3:
            return "call"
        return "check" if "check" in valid else "fold"
    t = nilai_tangan()
    if t["kategori"] >= 2 and "raise" in valid:
        return naik(min_raise() + pot() // 2)
    if t["kategori"] >= 1:
        return "call"
    return "check" if "check" in valid else "fold"
```

### Kalkulator Ekuitas

Membandingkan peluang menang dengan harga call (pot odds).

```python
def aksi():
    valid = aksi_valid()
    e = ekuitas(120)
    if e > 0.75 and "raise" in valid:
        return naik(min_raise() + pot())
    if e > 0.55 and "raise" in valid and untuk_ikut() == 0:
        return naik(min_raise() + pot() // 2)
    if "check" in valid:
        return "check"
    if e > peluang_pot() + 0.05:
        return "call"
    return "fold"
```

### Pemanggil Setia

Hampir selalu call. Fold hanya kalau harganya lebih dari separuh chip.

```python
def aksi():
    i = info()
    saya = nama_saya()
    if untuk_ikut() > i["chip"][saya] // 2 and kekuatan_awal() < 0.6:
        return "fold"
    return "call"
```

### Si Nekat

Agresif: sering raise, all-in dengan tangan bagus.

```python
def aksi():
    valid = aksi_valid()
    t = nilai_tangan()
    if t["kategori"] >= 3 or kekuatan_awal() >= 0.85:
        return "allin"
    if "raise" in valid and (kekuatan_awal() >= 0.5 or t["kategori"] >= 1):
        return naik(min_raise() * 2)
    return "check" if "check" in valid else "call" if untuk_ikut() <= info()["bb"] else "fold"
```

