# Panduan Bot: Arena Robot Grid

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Robot bergerak bersamaan di peta petak: ambil kristal, tembak lawan, hindari tembakan. Poin terbanyak menang.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Peta berupa petak (default 15×15) dengan tembok. Semua robot bertindak **bersamaan** setiap giliran (default 120 giliran).
- Aksi: bergerak 1 petak (`atas/bawah/kiri/kanan`), `diam`, atau **menembak** lurus ke satu arah (`tembak_atas`, dst.).
- Tembakan mengenai robot pertama di garis itu (terhalang tembok) **setelah semua robot bergerak**. Setelah menembak, senjata perlu
  **3 giliran** untuk siap lagi.
- Kena tembak: nyawa −1, penembak +1 poin. Menghancurkan robot: +3 poin tambahan. Robot hancur **bangkit lagi** di posisi awalnya
  dengan nyawa penuh setelah 8 giliran (bisa diatur; 0 = hancur permanen dan permainan berhenti kalau tinggal satu robot).
- **Kristal** (◆): masuk petaknya = +2 poin, lalu kristal baru muncul di tempat lain (posisi ditentukan seed, sama untuk semua).
- Dua robot yang menuju petak yang sama, atau bertukar tempat, sama-sama batal bergerak. Bergerak ke tembok atau robot yang diam = tetap di tempat.
- **Urutan dalam satu giliran: gerakan dulu, baru tembakan, lalu kristal.** Robot yang menembak diam di tempat; sinarnya dihitung ke
  posisi lawan **setelah** lawan bergerak. Jadi lawan yang sudah segaris masih bisa kabur, dan penembak yang jeli **menembak ke arah
  petak tujuan lawan** (memprediksi gerakannya), bukan ke tempat lawan sekarang.
- Peta simetris supaya posisi awal adil. Poin terbanyak menang; seri dipecah jumlah hancur paling sedikit, lalu sisa nyawa.
- **Kabut perang** (opsi jarak pandang): robot, kristal, dan power-up lawan hanya terlihat kalau dalam jarak tertentu dari robotmu.
- **Power-up** (opsi): ⚡ senjata langsung siap, 🛡️ perisai menahan satu tembakan (penembaknya tidak dapat poin), ❤️ nyawa +1.
- **Zona menyempit** (opsi): setelah sekian persen giliran, pinggir peta jadi badai dan zona aman mengecil bertahap; robot di luar zona
  kehilangan 1 nyawa tiap giliran (tidak ada yang dapat poin). Robot yang bangkit muncul di petak aman terdekat dari posisi awalnya.

## Aksi yang dikembalikan

Teks: `"atas"`, `"bawah"`, `"kiri"`, `"kanan"`, `"diam"`, `"tembak_atas"`, `"tembak_bawah"`, `"tembak_kiri"`, `"tembak_kanan"`.

## Isi `info()`

```
{ "giliran": 12, "giliran_total": 120, "ukuran": 15,
  "peta": ["...#....", ...],          # baris teks: '#' tembok, '.' kosong (robot & kristal tidak digambar di sini)
  "robot": {"Budi": {"baris": 3, "kolom": 4, "nyawa": 3, "poin": 5, "siap_tembak": 0, "hidup": True,
                     "hancur": 1, "bangkit_dalam": None}, ...},   # bangkit_dalam: giliran sampai bangkit (kalau sedang hancur)
  "kristal": [[7, 7], [2, 12], ...],  # [baris, kolom]
  "powerup": [{"baris": 3, "kolom": 9, "jenis": "perisai"}, ...],
  "skor": {"Budi": {"poin": 5, "hidup": True, "hancur": 1}, ...},   # semua pemain, selalu terlihat
  "zona": [2, 12],                    # zona aman: baris & kolom dari 2 sampai 12 (None kalau zona mati)
  "zona_berikut": 70,                 # giliran zona menyempit lagi (None kalau tidak lagi)
  "pandang": 0,                       # jarak pandang (0 = tanpa kabut)
  "kejadian": [ ... ]                 # tembakan & kristal di giliran sebelumnya
}
```
Dengan kabut perang, `robot`, `kristal`, `powerup`, dan `kejadian` hanya berisi yang terlihat dari robotmu.
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
| `bisa_kena()` | Arah tembakan yang mengenai musuh di posisinya SEKARANG, misalnya 'kanan', atau None. Ingat: lawan bergerak dulu sebelum tembakan dihitung. |
| `arah_tembak_ke(baris, kolom)` | Arah tembakan dari posisimu yang lurus & tanpa halangan tembok ke petak itu, atau None. Pakai untuk menembak ke petak tujuan lawan. |
| `tebak_langkah(nama)` | Tebakan petak [baris, kolom] robot itu setelah giliran ini, kalau ia berjalan ke kristal terdekatnya (atau diam kalau tidak ada). |
| `petak_mungkin(nama)` | Semua petak [baris, kolom] yang bisa dicapai robot itu giliran ini (diam atau 1 langkah). |
| `terancam()` | True kalau ada musuh segaris tanpa halangan yang senjatanya siap sekarang atau giliran depan. Gerakan dihitung sebelum tembakan, jadi keluar dari garis tembak menyelamatkanmu giliran ini juga (kecuali penembak menebak arah larimu). |
| `bisa_jalan(arah)` | True kalau petak di arah itu bukan tembok/robot/luar peta. |
| `powerup_terdekat()` | {'baris', 'kolom', 'jenis'} power-up terlihat yang paling dekat, atau None. |
| `aman(baris, kolom)` | True kalau petak itu di dalam zona aman sekarang (selalu True kalau zona mati). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Ukuran peta (`ukuran`) | 15 |  |
| Dasar | Jumlah giliran (`tick`) | 120 |  |
| Dasar | Nyawa robot (`hp`) | 3 |  |
| Dasar | Kristal di peta (`kristal`) | 8 |  |
| Dasar | Kepadatan tembok (%) (`tembok`) | 12 |  |
| Dasar | Bangkit lagi setelah (giliran) (`bangkit`) | 8 | Robot hancur muncul lagi di posisi awal dengan nyawa penuh setelah sekian giliran. 0 = hancur permanen. |
| Informasi (kabut) | Jarak pandang (petak) (`pandang`) | 0 | Kabut perang: robot, kristal, dan power-up di luar jarak ini dari robotmu tidak terlihat (tembok selalu terlihat). 0 = terlihat semua. |
| Kejutan | Power-up di peta (`powerup`) | 0 | ⚡ senjata langsung siap, 🛡️ perisai menahan 1 tembakan, ❤️ nyawa +1. Muncul lagi di tempat lain setelah diambil. |
| Kejutan | Zona menyempit mulai (% giliran) (`zona`) | 0 | Setelah sekian persen giliran, pinggir peta berubah jadi badai dan zona aman menyempit bertahap. Robot di luar zona kehilangan 1 nyawa tiap giliran. 0 = mati. |

**Preset:** *Kabut Perang* (pandang=4); *Kacau* (powerup=4, zona=50)

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

Fokus mengambil kristal (atau power-up kalau lebih dekat), menembak kalau ada musuh segaris, menjauhi badai.

```python
def aksi():
    i = info()
    arah = bisa_kena()
    if arah != None and i["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    saya = posisi()
    if not aman(saya[0], saya[1]):
        tengah = (i["zona"][0] + i["zona"][1]) // 2
        return langkah_ke(tengah, tengah)
    k = kristal_terdekat()
    pu = powerup_terdekat()
    if pu != None and (k == None or jarak(pu["baris"], pu["kolom"]) < jarak(k[0], k[1])):
        return langkah_ke(pu["baris"], pu["kolom"])
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

### Penembak Jitu

Menebak ke mana lawan akan melangkah (ke kristal terdekatnya) lalu menembak ke petak itu.

```python
def aksi():
    i = info()
    if i["robot"][nama_saya()]["siap_tembak"] == 0:
        for nama in i["robot"]:
            r = i["robot"][nama]
            if nama == nama_saya() or not r["hidup"]:
                continue
            t = tebak_langkah(nama)
            arah = arah_tembak_ke(t[0], t[1])
            if arah != None:
                return "tembak_" + arah
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
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

