# Panduan Bot: Labirin Mabar

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Balapan keluar dari labirin yang sama secara real-time. Ada kabut, tanda, tali, suar, koin, jebakan, dan portal.**

Pemain: 1–8. Fungsi wajib: `def aksi():`.

## Aturan

- Semua pemain mulai dari **pojok kiri atas** labirin yang sama dan berlomba ke **pintu keluar** 🚪 (petak terjauh dari awal).
- **Real-time:** setiap pemain bergerak sendiri-sendiri secepat mungkin, tidak menunggu yang lain.
  `atas/bawah/kiri/kanan` = 1 langkah, **lari** (`lari_kanan`, dst.) = terus menyusuri lorong sampai persimpangan, jalan buntu,
  atau benda. Menabrak tembok tidak diizinkan.
- Finis ke-1 sampai ke-8 mendapat **10 / 7 / 5 / 4 / 3 / 2 / 1 / 1** poin. **Koin** 🪙 = +1 poin untuk yang pertama mengambil.
- Setiap pemain punya **jatah langkah** per labirin (default 3× jalur terpendek + 20). Begitu ada yang finis, yang lain tinggal punya
  **30 langkah** lagi (bisa diatur host). Jatah habis = tidak finis di labirin itu.
- **Pandangan** (diatur host): *terang* (seluruh labirin terlihat), *kabut yang diingat* (jalan yang pernah terlihat tetap terbuka
  di petamu), atau *kabut tanpa ingatan* (hanya sekitarmu yang terlihat: hafalkan jalannya!). Pandangan menyusuri lorong, tembok
  menghalangi.
- Kemampuan terbatas, terlihat oleh **semua pemain**:
  - 📍 **Tanda / gambar** (↑ ↓ ← → ✖ ⭐ ❓ 💀) di petakmu, misalnya menandai jalan buntu. Pemain lain bisa memanfaatkannya… atau
    tertipu.
  - 🧵 **Tali**: selama menyala, jejak jalanmu tergambar (panjang terbatas). Berguna di kabut tanpa ingatan.
  - 🔦 **Suar**: jarak pandang +4 selama 6 langkah.
- Opsi kejutan: koin, **jebakan** tersembunyi (−5 jatah langkah dan tertahan 3 detik), dan **portal** berpasangan.
- Satu match berisi beberapa labirin (default 2). Setelah setiap labirin, seluruh petanya dibuka. Poin terbanyak menang
  (seri: total langkah paling sedikit).

## Aksi yang dikembalikan

Teks: `"atas"`, `"bawah"`, `"kiri"`, `"kanan"` (1 langkah), `"lari_atas"` dst. (menyusuri lorong),
`"diam"`, `"tali_on"`, `"tali_off"`, `"suar"`, atau dict `{"tanda": "✖"}` (simbol: ↑ ↓ ← → ✖ ⭐ ❓ 💀).

## Isi `info()`

```
{ "ronde": 1, "ronde_total": 2, "ukuran": 10, "pandang": "ingat", "jarak_pandang": 2,
  "peta": [[9, 5, None, ...], ...],      # peta[baris][kolom]: bit tembok (atas 1, kanan 2, bawah 4, kiri 8), None = belum terlihat
  "terlihat": [[0, 0], [0, 1], ...],    # petak yang terlihat SEKARANG (None kalau terang)
  "posisi": [0, 0], "arah_terakhir": "kanan", "keluar": [7, 9],   # keluar None kalau belum diketahui
  "langkah": 12, "sisa_langkah": 58, "selesai": False,
  "pemain": {"Budi": {"posisi": [3, 4], "selesai": False, "urutan": None, "langkah": 15, "sisa": 55, "tali_aktif": True}, ...},
  "tanda": [{"posisi": [2, 3], "simbol": "✖", "oleh": "Budi"}, ...],     # tanda semua pemain (selalu terlihat)
  "tali": {"Budi": [[0, 0], [0, 1], ...], ...},                       # jejak tali semua pemain (selalu terlihat)
  "koin": [[4, 4], ...], "jebakan": [[6, 2]], "portal": [[[1, 8], [8, 1]]],
  "tanda_sisa": 6, "tali_sisa": 40, "tali_aktif": False, "suar_sisa": 1, "suar_aktif": 0,
  "skor": {"Budi": 10, ...}, "riwayat": [ {"ronde": 1, "urutan": ["Ani", "Budi"], "poin": {...}, ...} ] }
```
- Baris 0 di atas, kolom 0 di kiri. Di kabut, posisi lawan `None` kalau tidak terlihat; koin dan portal hanya yang terlihat;
  jebakan hanya yang sudah terinjak.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `bisa_jalan(arah)` | True kalau tidak ada tembok di arah itu dari posisimu. |
| `jalan_terbuka()` | Daftar arah tanpa tembok dari posisimu. |
| `jalur_ke(baris, kolom)` | Daftar arah jalur terpendek ke petak itu lewat petak yang sudah kamu ketahui, atau None. |
| `langkah_ke(baris, kolom)` | Arah pertama jalur_ke(baris, kolom), atau None. |
| `perbatasan()` | Petak [baris, kolom] yang sudah diketahui dan tersambung ke petak yang belum terlihat, urut dari yang terdekat (jalur). |
| `tangan_kanan()` | Arah menurut aturan tangan kanan (berdasarkan arah_terakhir): kanan, lurus, kiri, lalu balik. |
| `tangan_kiri()` | Seperti tangan_kanan() tapi menyusuri tembok kiri. |
| `tanda_di(baris, kolom)` | Simbol tanda di petak itu (tanda terbaru), atau None. |
| `buntu()` | True kalau posisimu jalan buntu (hanya satu arah terbuka). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Ukuran labirin (`ukuran`) | 10 | Jumlah petak per sisi. |
| Dasar | Jumlah labirin (`ronde`) | 2 |  |
| Dasar | Kecepatan bot (langkah per detik) (`bot_kecepatan`) | 3 | Bot bergerak paling cepat sekian langkah per detik, supaya balapan melawan manusia tetap adil. |
| Dasar | Batas langkah per labirin (`batas_langkah`) | 0 | Tiap pemain punya jatah langkah per labirin. 0 = otomatis (3× jalur terpendek + 20). |
| Dasar | Sisa langkah setelah ada yang finis (`sisa_finis`) | 30 | Begitu satu pemain keluar, yang lain hanya punya sekian langkah lagi. 0 = tidak dibatasi. |
| Informasi (kabut) | Pandangan (`pandang`) | ingat |  |
| Informasi (kabut) | Jarak pandang (petak) (`jarak_pandang`) | 2 | Dihitung menyusuri lorong (tembok menghalangi pandangan). |
| Informasi (kabut) | Posisi lawan (`lawan_terlihat`) | dekat |  |
| Informasi (kabut) | Pintu keluar terlihat dari awal (`kompas`) | True | Kalau mati, lokasi pintu keluar baru diketahui setelah terlihat. |
| Aturan | Jatah tanda / gambar (`tanda`) | 6 | Tanda (panah, silang, bintang, tanya, tengkorak) di petakmu. Terlihat oleh SEMUA pemain di seluruh peta, jadi bisa membantu... atau menyesatkan. |
| Aturan | Panjang tali (petak) (`tali`) | 40 | Tali menggambar jejak jalanmu selama dinyalakan. Terlihat oleh semua pemain. |
| Aturan | Jatah suar (`suar`) | 1 | Suar menambah jarak pandang +4 selama 6 langkah. |
| Aturan | Jalan pintas (%) (`pintas`) | 8 | Persentase tembok dalam yang dibuka, supaya ada lebih dari satu jalan. 0 = labirin sempurna (satu jalan). |
| Kejutan | Koin di labirin (`koin`) | 4 | Koin = +1 poin untuk yang pertama mengambil. |
| Kejutan | Jebakan tersembunyi (`jebakan`) | 0 | Menginjak jebakan: −5 jatah langkah dan tertahan 3 detik. Jebakan yang sudah terinjak terlihat oleh semua dan tidak aktif lagi. |
| Kejutan | Pasangan portal (`portal`) | 0 | Masuk satu portal langsung keluar di pasangannya. |

**Preset:** *Terang* (pandang=terang); *Hafalan* (pandang=kabut, jarak_pandang=1, kompas=False); *Kacau* (koin=10, jebakan=6, portal=3)

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

### Tangan Kanan

Menyusuri tembok kanan (selalu sampai di labirin sempurna). Langsung ke pintu keluar kalau jalannya sudah diketahui.

```python
def aksi():
    i = info()
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
```

### Penjelajah

Menuju petak perbatasan yang paling dekat ke pintu keluar; di kabut tanpa ingatan pakai tangan kiri.

```python
def aksi():
    i = info()
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    if i["pandang"] == "kabut":
        return tangan_kiri()
    batas = perbatasan()
    if not batas:
        return tangan_kiri()
    if k == None:
        p = batas[0]
    else:
        p = min(batas[:8], key=lambda x: abs(x[0] - k[0]) + abs(x[1] - k[1]))
    a = langkah_ke(p[0], p[1])
    return a if a != None else tangan_kiri()
```

### Penanda Buntu

Tangan kanan sambil memberi tanda ✖ di setiap jalan buntu (membantu semua pemain).

```python
def aksi():
    i = info()
    p = i["posisi"]
    if buntu() and tanda_di(p[0], p[1]) == None and i["tanda_sisa"] > 0 and p != [0, 0]:
        return {"tanda": "✖"}
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
```

### Pemburu Koin

Mengambil koin yang terlihat dulu, menyalakan tali, lalu mencari jalan keluar.

```python
def aksi():
    i = info()
    if i["tali_sisa"] > 0 and not i["tali_aktif"] and i["langkah"] == 0:
        return "tali_on"
    terbaik = None
    for c in i["koin"]:
        j = jalur_ke(c[0], c[1])
        if j != None and (terbaik == None or len(j) < len(terbaik)):
            terbaik = j
    if terbaik != None and len(terbaik) > 0 and len(terbaik) <= 12:
        return terbaik[0]
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
```

