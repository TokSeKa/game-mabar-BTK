# Panduan Bot: Arena Robot Grid

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Robot bergerak bersamaan di peta petak: ambil kristal, tembak lawan, hindari tembakan. Poin terbanyak menang.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Peta berupa petak (default 15×15) dengan tembok. Semua robot bertindak **bersamaan** setiap giliran (default 120 giliran).
- Aksi: bergerak 1 petak (`atas/bawah/kiri/kanan`), `diam`, atau **menembak** lurus ke satu arah (`tembak_atas`, dst.).
- Tembakan langsung mengenai robot pertama di garis itu (terhalang tembok). Setelah menembak, senjata perlu **3 giliran** untuk siap lagi.
- Kena tembak: nyawa −1, penembak +1 poin. Menghancurkan robot: +3 poin tambahan. Robot hancur **bangkit lagi** di posisi awalnya
  dengan nyawa penuh setelah 8 giliran (bisa diatur; 0 = hancur permanen dan permainan berhenti kalau tinggal satu robot).
- **Kristal** (◆): masuk petaknya = +2 poin, lalu kristal baru muncul di tempat lain (posisi ditentukan seed, sama untuk semua).
- Dua robot yang menuju petak yang sama, atau bertukar tempat, sama-sama batal bergerak. Bergerak ke tembok atau robot yang diam = tetap di tempat.
- Urutan dalam satu giliran: semua tembakan dihitung dulu (dari posisi awal), lalu gerakan, lalu kristal.
- Peta simetris supaya posisi awal adil. Poin terbanyak menang; seri dipecah jumlah hancur paling sedikit, lalu sisa nyawa.

## Aksi yang dikembalikan

Teks: `"atas"`, `"bawah"`, `"kiri"`, `"kanan"`, `"diam"`, `"tembak_atas"`, `"tembak_bawah"`, `"tembak_kiri"`, `"tembak_kanan"`.

## Isi `info()`

```
{ "giliran": 12, "giliran_total": 120, "ukuran": 15,
  "peta": ["...#....", ...],          # baris teks: '#' tembok, '.' kosong (robot & kristal tidak digambar di sini)
  "robot": {"Budi": {"baris": 3, "kolom": 4, "nyawa": 3, "poin": 5, "siap_tembak": 0, "hidup": True,
                     "hancur": 1, "bangkit_dalam": None}, ...},   # bangkit_dalam: giliran sampai bangkit (kalau sedang hancur)
  "kristal": [[7, 7], [2, 12], ...],  # [baris, kolom]
  "kejadian": [ ... ]                 # tembakan & kristal di giliran sebelumnya
}
```
`siap_tembak` = berapa giliran lagi sampai bisa menembak (0 = siap). Baris 0 di atas, kolom 0 di kiri.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `posisi(nama=None)` | [baris, kolom] robotmu (atau robot bernama itu). |
| `langkah_ke(baris, kolom)` | Arah langkah pertama jalur terpendek ke petak itu (menghindari tembok & robot), atau 'diam' kalau tidak ada jalan. |
| `jarak(baris, kolom)` | Panjang jalur terpendek dari robotmu ke petak itu (-1 kalau tidak terjangkau). |
| `kristal_terdekat()` | [baris, kolom] kristal dengan jalur terpendek, atau None. |
| `musuh_terdekat()` | Nama robot musuh hidup yang paling dekat (jalur), atau None. |
| `bisa_kena()` | Arah tembakan yang sekarang akan mengenai musuh, misalnya 'kanan', atau None. |
| `terancam()` | True kalau ada musuh segaris tanpa halangan yang senjatanya siap sekarang atau giliran depan. Tembakan dihitung sebelum gerakan, jadi menghindar menyelamatkanmu untuk giliran berikutnya. |
| `bisa_jalan(arah)` | True kalau petak di arah itu bukan tembok/robot/luar peta. |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| Ukuran peta | 15 |  |
| Jumlah giliran | 120 |  |
| Nyawa robot | 3 |  |
| Kristal di peta | 8 |  |
| Kepadatan tembok (%) | 12 |  |
| Bangkit lagi setelah (giliran) | 8 | Robot hancur muncul lagi di posisi awal dengan nyawa penuh setelah sekian giliran. 0 = hancur permanen. |

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

### Pemungut Kristal

Fokus mengambil kristal terdekat, menembak kalau ada musuh segaris.

```python
def aksi():
    arah = bisa_kena()
    if arah != None and info()["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
```

### Pemburu

Mengejar robot terdekat dan menembak begitu segaris.

```python
def aksi():
    i = info()
    saya = i["robot"][nama_saya()]
    arah = bisa_kena()
    if arah != None and saya["siap_tembak"] == 0:
        return "tembak_" + arah
    m = musuh_terdekat()
    if m == None:
        k = kristal_terdekat()
        return "diam" if k == None else langkah_ke(k[0], k[1])
    r = i["robot"][m]
    return langkah_ke(r["baris"], r["kolom"])
```

### Penghindar

Menghindar dari garis tembak musuh, mengambil kristal kalau aman.

```python
def aksi():
    arah = bisa_kena()
    if arah != None and info()["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    if terancam():
        for a in ["atas", "kiri", "bawah", "kanan"]:
            if bisa_jalan(a):
                return a
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
```

