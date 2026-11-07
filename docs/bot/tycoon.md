# Panduan Bot: Pasar Malam Tycoon

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Semua pedagang berjualan di pasar malam yang sama. Pilih dagangan, jumlah, harga, dan iklan; pembeli terbagi ke penjual yang paling menarik.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap malam setiap pemain memilih **satu dagangan** (Sate, Es Teh, Bakso, Mainan) atau tutup. Tentukan **jumlah** yang dibeli (bayar modal di muka),
  **harga jual**, dan **iklan** (Rp). Total modal + iklan tidak boleh melebihi uangmu.
- **Pembeli dibagi bersama.** Tiap penjual punya daya tarik = (2 − harga/harga_wajar)² × (1 + iklan/(iklan + 30.000)).
  Penjual seharga wajar tanpa iklan = 1; seharga 2× wajar = 0 (tidak laku). Pangsa pembeli = daya_tarik / (1 + jumlah daya tarik semua penjual produk itu),
  dari pasar sebesar 2 × permintaan. Jadi makin banyak penjual, pasar sedikit membesar tapi tiap penjual kebagian lebih sedikit.
- Barang yang tidak laku **basi** (hangus). Kalau daganganmu habis, separuh pembeli yang kecewa pindah ke penjual lain yang masih punya stok.
- **Permintaan dipengaruhi hari:** cuaca (diumumkan pagi hari), akhir pekan (×1,3; mainan ×1,8), dan acara khusus (×1,6). Ada juga
  gejolak acak ±15% yang baru ketahuan malamnya. Ramalan cuaca besok tersedia, benar sekitar 75%.
- Permintaan dasar membesar sesuai jumlah pemain supaya pasar tidak terlalu sempit.
- Uang terbanyak di akhir menang.
- Opsi host: **dagangan pesaing rahasia**, **ketepatan ramalan** (0 = tanpa ramalan), **stok tahan sehari** (sisa barang bisa dijual
  lagi besok untuk produk yang sama, dijual lebih dulu dari barang baru), dan **kejadian pasar** (razia, viral, bahan naik, subsidi).

## Aksi yang dikembalikan

- `"tutup"` (libur, uang aman), atau
- `{"produk": "sate", "jumlah": 30, "harga": 14000, "iklan": 5000}`. Produk: `sate`, `es_teh`, `bakso`, `mainan`. Harga 1 sampai 3× harga wajar.

## Isi `info()`

```
{ "hari": 4, "hari_total": 15, "nama_hari": "Kamis", "akhir_pekan": False, "cuaca": "hujan", "acara": None,
  "ramalan_besok": "mendung",
  "produk": {"sate": {"nama": "Sate", "modal": 6000, "wajar": 15000, "permintaan": 120, "pengaruh": 0.7}, ...},
  "uang": {"Budi": 254000, ...},
  "riwayat": [ {"hari": 1, "cuaca": "cerah", "acara": None, "pembeli": {"sate": 160, ...},
                "jual": {"Budi": {"produk": "sate", "jumlah": 30, "harga": 14000, "iklan": 0, "terjual": 30, "untung": 240000}, "Ani": "tutup"}} ] }
```
`pengaruh` = pengali permintaan hari ini (cuaca × akhir pekan × acara × kejadian), belum termasuk gejolak acak dan jumlah pemain.
`produk[k]["modal"]` adalah modal HARI INI (bisa berubah karena kejadian pasar) dan `dilarang` True kalau produk itu dirazia.
`kejadian` = kejadian pasar hari ini atau None. `stok_saya` = sisa barang kemarin yang masih bisa dijual hari ini (atau None).
Kalau dagangan pesaing rahasia, entri `jual` pedagang lain berisi `{"rahasia": True}` dan setiap hari punya `penjual` (jumlah penjual per produk).

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `uang_saya()` | Uangmu sekarang (Rp). |
| `maks_beli(produk, iklan=0)` | Jumlah barang terbanyak yang bisa kamu beli dengan uangmu. |
| `perkiraan_pembeli(produk, harga, iklan=0)` | Perkiraan pembeli untukmu kalau pesaing memakai harga & iklan seperti kemarin (tanpa gejolak acak). |
| `pesaing_kemarin(produk)` | List penjual produk itu kemarin: {'nama', 'harga', 'iklan', 'jumlah', 'terjual'}. Kosong kalau dagangan pesaing rahasia. |
| `jumlah_penjual_kemarin(produk)` | Banyaknya pedagang lain yang menjual produk itu kemarin (selalu terlihat). |
| `untung_per_barang(produk, harga)` | harga − modal per barang. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Jumlah hari (`hari`) | 15 |  |
| Dasar | Modal awal (Rp) (`modal`) | 200000 |  |
| Informasi (kabut) | Dagangan pesaing rahasia (`pesaing_rahasia`) | False | Produk, harga, iklan, dan hasil jualan pedagang lain tidak dibuka (total uang tetap terlihat); yang terlihat hanya jumlah penjual & pembeli tiap produk. |
| Informasi (kabut) | Ketepatan ramalan cuaca (%) (`ramalan`) | 75 | 0 = tidak ada ramalan sama sekali. |
| Aturan | Stok tahan sehari (`stok_awet`) | False | Barang yang tidak laku tidak langsung basi: bisa dijual lagi besok (produk yang sama, tanpa modal), setelah itu basi. |
| Kejutan | Kejadian pasar (%) (`event_pasar`) | 0 | Peluang tiap hari ada kejadian (diumumkan pagi): razia (satu produk dilarang), viral (permintaan ×2,5), bahan naik (modal ×1,5), atau subsidi (modal separuh). |

**Preset:** *Kabut* (pesaing_rahasia=True, ramalan=50); *Kacau* (event_pasar=40, stok_awet=True)

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

### Pedagang Sate Setia

Selalu jualan sate dengan harga wajar, jumlah menyesuaikan perkiraan pembeli.

```python
def aksi():
    harga = 15000
    q = min(maks_beli("sate"), perkiraan_pembeli("sate", harga))
    if q <= 0:
        return "tutup"
    return {"produk": "sate", "jumlah": q, "harga": harga, "iklan": 0}
```

### Pembaca Cuaca

Memilih dagangan dengan perkiraan untung terbesar hari ini.

```python
def aksi():
    i = info()
    terbaik = None
    for k in i["produk"]:
        p = i["produk"][k]
        harga = p["wajar"] * 95 // 100
        q = min(maks_beli(k, 5000), perkiraan_pembeli(k, harga, 5000))
        untung = q * untung_per_barang(k, harga) - 5000
        if terbaik == None or untung > terbaik[0]:
            terbaik = [untung, k, q, harga]
    if terbaik == None or terbaik[0] <= 0:
        return "tutup"
    return {"produk": terbaik[1], "jumlah": terbaik[2], "harga": terbaik[3], "iklan": 5000}
```

### Banting Harga

Cari produk yang paling sepi pesaing, jual 20% di bawah harga wajar.

```python
def aksi():
    i = info()
    pilihan = sorted(i["produk"].keys(), key=lambda k: len(pesaing_kemarin(k)))
    k = pilihan[0]
    harga = i["produk"][k]["wajar"] * 80 // 100
    q = min(maks_beli(k), perkiraan_pembeli(k, harga) * 11 // 10)
    if q <= 0:
        return "tutup"
    return {"produk": k, "jumlah": q, "harga": harga, "iklan": 0}
```

