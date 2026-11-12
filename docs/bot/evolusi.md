# Panduan Bot: Evolusi Hex

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Kembangkan spesiesmu di peta heksagonal: cari makanan, beranak, bermutasi, dan mangsa spesies lain. Ukuran, kecepatan, dan pandangan punya harga energi.**

Pemain: 1–6. Fungsi wajib: `def aksi():`.

## Aturan

- Peta **heksagonal**. Setiap pemain mengendalikan satu **spesies**, mulai dengan 2 makhluk di sarangnya (pojok peta).
- Giliran 0 = **desain spesies**: bagi **15 poin** ke tiga sifat (masing-masing 1–9):
  - 👁️ **Pandangan**: melihat lurus ke 6 arah sejauh nilainya (tembok & semak menghalangi). Biaya **0.25 × pandangan** energi per giliran.
  - 🐾 **Kelincahan**: langkah maksimal per giliran. Biaya **per langkah = (ukuran/5)³ × (kelincahan/5)**: makhluk besar dan cepat
    sangat boros!
  - 🦣 **Ukuran**: HP = 10 + 5×ukuran, energi maksimal = 40 + 12×ukuran. Makhluk yang ukurannya **≥ 1,2×** ukuran lawan
    **memangsa** lawan itu (masuk ke petaknya, atau lawan masuk ke mulutnya). Ukuran juga menentukan biaya beranak.
- Semua makhluk bergerak **bersamaan** tiap giliran, satu langkah demi satu langkah (urutan bergiliran adil). Setiap makhluk juga
  membayar **0.5** energi per giliran untuk hidup. Energi habis = HP −2 per giliran (kelaparan). HP sembuh +1 per giliran
  kalau energi di atas separuh.
- Makanan: 🌱 rumput (+12 energi, 1 poin), 🍎 buah (+25, 2 poin), 🍖 daging (+45, 3 poin; muncul dari makhluk yang mati).
  Makanan tumbuh lagi dari waktu ke waktu.
- **Beranak** (toggle per makhluk): kalau energi ≥ biaya lahir (25 + 5×ukuran anak) + 30% energi maksimal, makhluk itu melahirkan
  satu anak di sebelahnya dengan **desain spesies saat ini** (bisa diubah kapan saja) dan kadang **bermutasi** ±1 di satu sifat.
- Perintah per makhluk: **naluri** (otomatis: kabur dari pemangsa, cari makanan/mangsa), **tujuan** (jalan sendiri ke petak yang
  dipilih), **manual** (pilih langkah satu per satu tiap giliran), atau **diam**. Makhluk diberi nomor otomatis dan boleh diberi nama.
- **Rintangan** (jatah 3): pasang 🪨 batu atau 🌵 duri tersembunyi di sebelah makhlukmu (10 energi).
- Poin: makanan 1/2/3, memangsa makhluk lawan **+5**, kelahiran **+3**, dan **+5** per makhluk yang masih hidup di
  akhir. Poin terbanyak setelah semua giliran menang.

## Aksi yang dikembalikan

Dict (semua kunci opsional; `{}` = semua makhluk melanjutkan perintahnya):
```
{ "desain": {"pandangan": 4, "kelincahan": 5, "ukuran": 6},     # desain spesies (giliran 0: makhluk awal; setelahnya: anak baru)
  "perintah": {"7": {"mode": "tujuan", "tujuan": [2, -1]},      # mode: naluri / tujuan / manual / diam
               "9": {"mode": "manual", "jalan": ["timur", "tenggara"]}},   # jalan: langkah giliran ini (≤ kelincahan)
  "beranak": {"7": True},
  "nama": {"7": "Si Gesit"},
  "pasang": {"makhluk": "7", "arah": "barat", "jenis": "duri"} }   # jenis: batu / duri
```
Arah: `timur`, `timur_laut`, `barat_laut`, `barat`, `barat_daya`, `tenggara`. Id makhluk boleh angka atau teks. Perintah untuk makhluk
yang sudah mati diabaikan.

## Isi `info()`

```
{ "giliran": 5, "giliran_total": 60, "fase": "main",          # fase "desain" di giliran 0
  "radius": 6, "peta": {"0,0": ".", "1,-1": "s", "2,0": "#", ...},   # "." tanah, "s" semak, "#" batu (koordinat aksial "q,r")
  "makhluk_saya": [ {"id": "7", "nama": "#3", "posisi": [1, -2], "pandangan": 4, "kelincahan": 5, "ukuran": 6,
                     "hp": 40, "hp_maks": 40, "energi": 63.5, "energi_maks": 112, "mode": "naluri", "tujuan": None,
                     "beranak": True, "biaya_langkah": 1.728, "biaya_lahir": 55, "umur": 3}, ... ],
  "makhluk_lain": [ {"id": "12", "pemilik": "Budi", "posisi": [3, 0], "ukuran": 8, "hp": 50}, ... ],   # yang terlihat saja
  "makanan": [[2, 1, "buah"], ...], "jebakan": [[0, 3, "duri", True], ...],  # yang diketahui; True = milikmu (tidak melukaimu)
  "terlihat": ["1,-2", "2,-2", ...],                        # petak yang terlihat sekarang (None tanpa kabut)
  "desain": {"pandangan": 4, "kelincahan": 5, "ukuran": 6}, "poin_sifat": 15, "rintangan_sisa": 3,
  "sarang": [5, -5], "populasi": {"Ani": 4, "Budi": 2}, "skor": {"Ani": 12, ...},
  "rasio_mangsa": 1.2, "maks_populasi": 12 }
```
Koordinat aksial: arah timur = (+1, 0), timur_laut = (+1, −1), barat_laut = (0, −1), barat = (−1, 0), barat_daya = (−1, +1),
tenggara = (0, +1). Jarak = (|dq| + |dr| + |dq+dr|) / 2.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `makhluk_saya()` | Daftar makhlukmu yang hidup (sama dengan info()['makhluk_saya']). |
| `jarak(a, b)` | Jarak heksagon antara dua petak [q, r]. |
| `jalur(dari, ke)` | Daftar petak jalur terpendek (tanpa petak awal) yang menghindari batu & jebakan yang diketahui, atau None. Maksimal 100 petak awal berbeda per giliran (petak awal yang sama boleh dipakai berulang kali). |
| `tetangga(petak)` | Petak sebelah [q, r] yang bisa diinjak (bukan batu, di dalam peta). |
| `arah_ke(dari, ke)` | Nama arah dari petak ke petak sebelahnya, atau None. |
| `makanan_terdekat(id)` | [q, r, jenis] makanan terlihat dengan jalur terpendek dari makhluk itu, atau None. |
| `mangsa_terdekat(id)` | Makhluk lawan terlihat terdekat yang bisa dimangsa makhluk itu, atau None. |
| `ancaman_terdekat(id)` | Makhluk lawan terlihat terdekat yang bisa memangsa makhluk itu, atau None. |
| `bisa_beranak(id)` | True kalau energi makhluk itu cukup untuk beranak sekarang (dengan desain sekarang). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Jumlah giliran (`giliran`) | 60 |  |
| Dasar | Ukuran peta (radius heksagon) (`radius`) | 6 |  |
| Dasar | Makhluk awal per pemain (`populasi_awal`) | 2 |  |
| Dasar | Poin sifat (pandangan + kelincahan + ukuran) (`poin_sifat`) | 15 | Jatah poin untuk desain spesies; tiap sifat 1–9. |
| Dasar | Populasi maksimal per pemain (`maks_populasi`) | 12 |  |
| Dasar | Kelimpahan makanan (`makanan`) | 3 |  |
| Informasi (kabut) | Kabut (hanya yang terlihat makhlukmu) (`kabut`) | True | Makhluk, makanan, dan jebakan hanya terlihat dalam pandangan makhlukmu. Medan selalu terlihat. |
| Aturan | Syarat memangsa (× ukuran lawan) (`rasio_mangsa`) | 1.2 | Makhluk memangsa lawan kalau ukurannya minimal sekian kali ukuran lawan. |
| Aturan | Jatah rintangan per pemain (`rintangan`) | 3 | 🪨 batu (menghalangi semua) atau 🌵 duri (tersembunyi, −10 HP untuk makhluk lawan). Dipasang di samping makhluk, biaya 10 energi. |
| Aturan | Bangkit setelah punah (giliran) (`bangkit`) | 10 | Spesies yang punah mendapat satu makhluk baru di sarangnya setelah sekian giliran. 0 = punah selamanya. |
| Kejutan | Semak (%) (`semak`) | 15 | Semak bisa dilewati tapi isinya (makanan, makhluk, jebakan) hanya terlihat dari dalam atau dari sebelahnya. |
| Kejutan | Batu (%) (`batu`) | 8 |  |
| Kejutan | Jebakan tersembunyi di semak (`jebakan`) | 3 | Menginjak jebakan: −8 HP. |
| Kejutan | Peluang mutasi anak (%) (`mutasi`) | 30 | Anak bisa lahir dengan satu sifat +1 atau −1 dari desain spesiesnya. |

**Preset:** *Terang* (kabut=False); *Rimba* (semak=35, jebakan=8); *Seleksi Kejam* (mutasi=70, bangkit=0)

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

### Naluri Saja

Desain seimbang, semua makhluk memakai naluri, beranak kalau energi cukup.

```python
def aksi():
    i = info()
    if i["fase"] == "desain":
        return {"desain": {"pandangan": 5, "kelincahan": 5, "ukuran": 5}}
    return {"beranak": {m["id"]: True for m in i["makhluk_saya"]}}
```

### Pemangsa Besar

Spesies besar dan lambat yang mengejar mangsa terdekat, kalau tidak ada mencari makanan.

```python
def aksi():
    i = info()
    if i["fase"] == "desain":
        b = i["poin_sifat"]
        return {"desain": {"pandangan": 3, "kelincahan": 3, "ukuran": min(9, b - 6)}}
    perintah = {}
    lahir = {}
    for m in i["makhluk_saya"]:
        lahir[m["id"]] = len(i["makhluk_saya"]) < 6
        target = mangsa_terdekat(m["id"])
        if target != None:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": target["posisi"]}
        else:
            perintah[m["id"]] = {"mode": "naluri"}
    return {"perintah": perintah, "beranak": lahir}
```

### Pengumpul Hemat

Kecil, hemat energi, pandangan jauh. Kabur dari pemangsa, banyak beranak.

```python
def aksi():
    i = info()
    if i["fase"] == "desain":
        b = i["poin_sifat"]
        u = 2
        k = 4
        return {"desain": {"pandangan": min(9, b - u - k), "kelincahan": k, "ukuran": u}}
    perintah = {}
    for m in i["makhluk_saya"]:
        bahaya = ancaman_terdekat(m["id"])
        if bahaya != None and jarak(bahaya["posisi"], m["posisi"]) <= 3:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": i["sarang"]}
            continue
        f = makanan_terdekat(m["id"])
        if f != None:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": [f[0], f[1]]}
        else:
            perintah[m["id"]] = {"mode": "naluri"}
    return {"perintah": perintah, "beranak": {m["id"]: True for m in i["makhluk_saya"]}}
```

### Penjaga Duri

Desain menengah, menanam duri di sekitar sarang di awal, lalu memakai naluri.

```python
def aksi():
    i = info()
    if i["fase"] == "desain":
        return {"desain": {"pandangan": 4, "kelincahan": 4, "ukuran": 7}}
    out = {"beranak": {m["id"]: m["energi"] > m["energi_maks"] * 0.6 for m in i["makhluk_saya"]}}
    if i["rintangan_sisa"] > 0 and i["makhluk_saya"]:
        m = i["makhluk_saya"][0]
        for a in ["timur", "barat", "tenggara", "barat_laut", "timur_laut", "barat_daya"]:
            p = [m["posisi"][0], m["posisi"][1]]
            d = {"timur": [1, 0], "timur_laut": [1, -1], "barat_laut": [0, -1], "barat": [-1, 0], "barat_daya": [-1, 1], "tenggara": [0, 1]}[a]
            t = [p[0] + d[0], p[1] + d[1]]
            k = str(t[0]) + "," + str(t[1])
            if i["peta"].get(k) == "s" and m["energi"] > 30:
                out["pasang"] = {"makhluk": m["id"], "arah": a, "jenis": "duri"}
                break
    return out
```

