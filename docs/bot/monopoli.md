# Panduan Bot: Juragan Nusantara (gaya Monopoli)

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Kelilingi papan kota-kota Indonesia: beli, bangun rumah & hotel, tagih sewa, lelang, dan tukar properti dengan pemain lain.**

Pemain: 2–6. Fungsi wajib: `def aksi():`.

## Aturan

- Semua pemain mulai di **Mulai** dengan **1.500 jt**. Di giliranmu **lempar dua dadu** lalu maju. Lewat Mulai = gaji **200**.
  Dadu kembar = lempar lagi (tiga kali kembar berturut-turut = masuk penjara).
- Berhenti di **kota / transportasi / utilitas** tanpa pemilik: **beli** atau **tolak** (yang ditolak dilelang tertutup ke semua pemain;
  tawaran tertinggi menang, seri dimenangkan pemain yang lebih dekat urutannya).
- Berhenti di petak milik orang lain: bayar **sewa**. Kota: sewa dasar = 8% harga (×2 kalau pemiliknya memiliki **satu kelompok
  warna lengkap** tanpa rumah), lalu naik besar dengan **rumah** (1–4) dan **hotel**. Transportasi: 25 / 50 / 100 / 200 tergantung
  jumlah yang dimiliki. Utilitas: 4× dadu (10× kalau punya keduanya). Petak yang digadai tidak menarik sewa.
- **Bangun** rumah kalau punya satu kelompok warna lengkap (tanpa gadai), merata (selisih rumah antar petak maksimal 1). Rumah ke-5 = hotel.
  **Gadai** properti = dapat 50% harga; **tebus** = bayar 55%.
- **Kesempatan / Dana Umum**: kartu kejutan (maju, bayar, terima, masuk penjara, kartu bebas penjara, ...).
- **Penjara**: keluar dengan bayar 50, kartu bebas, atau dadu kembar (maksimal 3 giliran, lalu wajib bayar).
- **Tukar-menukar**: di gilirannya pemain boleh menawarkan properti/uang ke pemain lain; pemain itu menerima atau menolak.
- Tidak bisa bayar: rumah dijual (setengah harga) dan properti digadai otomatis; kalau masih kurang = **bangkrut** (semua harta ke
  penagih). Pemain terakhir yang bertahan menang, atau kekayaan bersih terbesar setelah batas putaran (default 25).

## Aksi yang dikembalikan

- `"lempar"` (fase awal), `"beli"` / `"tolak"` (fase beli), `"selesai"` (akhiri giliran, fase akhir).
- Kapan saja di gilirannya (fase awal/akhir): `{"bangun": petak}`, `{"jual_rumah": petak}`, `{"gadai": petak}`, `{"tebus": petak}`,
  `"bayar_penjara"`, `"kartu_bebas"`, dan tawaran tukar:
  `{"tawar": {"ke": "Budi", "beri": {"uang": 100, "properti": [6]}, "minta": {"uang": 0, "properti": [8]}}}`.
- Fase lelang (semua pemain): `{"lelang": harga}` (0 = tidak ikut). Fase tawaran (pemain yang ditawari): `"terima"` atau `"tolak"`.

## Isi `info()`

```
{ "putaran": 3, "batas_putaran": 25, "giliran": "Budi", "fase": "awal",   # awal / beli / akhir / lelang / tawaran
  "dadu": [3, 4], "kembar": 0,
  "papan": [ {"id": 1, "nama": "Pacitan", "jenis": "kota", "harga": 60, "kelompok": "coklat", "pemilik": "Ani",
              "rumah": 0, "gadai": False, "sewa": 10, "harga_rumah": 50}, ... ],     # 40 petak
  "pemain": {"Ani": {"uang": 1340, "posisi": 6, "penjara": False, "giliran_penjara": 0, "kartu_bebas": 0,
                     "bangkrut": False, "kekayaan": 1560}, ...},      # uang None kalau dirahasiakan
  "lelang": {"petak": 8, "harga": 100} | None, "tawaran": {"dari": "Ani", "ke": "Budi", "beri": {...}, "minta": {...}} | None,
  "jackpot": 0, "kartu_terakhir": "Dividen saham: terima 50.", "riwayat": [...],
  "bisa_bangun": [16, 18], "boleh_tawar": True }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `petak(id)` | Info satu petak (sama dengan info()['papan'][id]). |
| `milik(nama=None)` | Daftar id properti milik pemain itu (default: kamu). |
| `kelompok(warna)` | Daftar id petak dalam kelompok itu (coklat, biru_muda, ..., transport, utilitas). |
| `lengkap(warna, nama=None)` | True kalau pemain itu memiliki semua petak di kelompok itu. |
| `bisa_bangun()` | Daftar petak yang boleh kamu bangun rumah sekarang (aturan merata, uang cukup). |
| `kekayaan(nama=None)` | Kekayaan bersih pemain itu (uang + properti + rumah; None kalau uangnya rahasia). |
| `uang(nama=None)` | Uang tunai pemain itu (None kalau dirahasiakan). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Uang awal (jt) (`uang_awal`) | 1500 |  |
| Dasar | Batas putaran (`batas_putaran`) | 25 | Kalau belum ada pemenang setelah sekian putaran, pemain dengan kekayaan bersih terbesar menang. |
| Dasar | Gaji lewat Mulai (jt) (`gaji`) | 200 |  |
| Aturan | Lelang kalau tidak dibeli (`lelang_properti`) | True | Petak yang tidak dibeli dilelang tertutup ke semua pemain (penawaran rahasia, tertinggi menang). |
| Aturan | Boleh tukar-menukar (`tukar`) | True | Di gilirannya, pemain boleh menawarkan tukar properti/uang ke pemain lain (maks 3 tawaran per giliran). |
| Aturan | Jackpot Parkir Bebas (`parkir_jackpot`) | False | Semua pajak & denda dikumpulkan di Parkir Bebas dan diambil pemain yang berhenti di sana. |
| Informasi (kabut) | Uang lawan rahasia (`uang_rahasia`) | False | Uang tunai pemain lain tidak terlihat (properti tetap terlihat). |

**Preset:** *Cepat* (parkir_jackpot=True); *Dompet Rahasia* (uang_rahasia=True)

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

### Pembeli Rajin

Membeli hampir semua properti, membangun kalau ada sisa 250, menawar lelang sampai 80% harga.

```python
def aksi():
    i = info()
    saya = nama_saya()
    me = i["pemain"][saya]
    f = i["fase"]
    if f == "tawaran":
        t = i["tawaran"]
        nilai_dapat = t["beri"]["uang"] + sum(petak(p)["harga"] for p in t["beri"]["properti"])
        nilai_beri = t["minta"]["uang"] + sum(petak(p)["harga"] for p in t["minta"]["properti"])
        return "terima" if nilai_dapat >= nilai_beri * 1.2 else "tolak"
    if f == "lelang":
        h = petak(i["lelang"]["petak"])["harga"]
        return {"lelang": min(me["uang"] - 50, int(h * 0.8))} if me["uang"] > 150 else {"lelang": 0}
    if f == "beli":
        p = petak(me["posisi"])
        return "beli" if me["uang"] - p["harga"] >= 80 else "tolak"
    b = bisa_bangun()
    if b and me["uang"] > 250:
        return {"bangun": b[0]}
    if me["penjara"] and me["uang"] > 300 and f == "awal":
        return "bayar_penjara"
    return "lempar" if f == "awal" else "selesai"
```

### Investor Hati-hati

Hanya membeli kalau tetap punya cadangan 300, fokus kelompok oranye & merah, membangun sampai 3 rumah.

```python
def aksi():
    i = info()
    me = i["pemain"][nama_saya()]
    f = i["fase"]
    if f == "tawaran":
        return "tolak"
    if f == "lelang":
        p = petak(i["lelang"]["petak"])
        suka = p["kelompok"] in ["oranye", "merah"]
        batas = int(p["harga"] * (0.9 if suka else 0.5))
        return {"lelang": max(0, min(batas, me["uang"] - 300))}
    if f == "beli":
        p = petak(me["posisi"])
        cadangan = 200 if p["kelompok"] in ["oranye", "merah"] else 300
        return "beli" if me["uang"] - p["harga"] >= cadangan else "tolak"
    for b in bisa_bangun():
        if petak(b)["rumah"] < 3 and me["uang"] - petak(b)["harga_rumah"] >= 300:
            return {"bangun": b}
    return "lempar" if f == "awal" else "selesai"
```

### Pedagang

Menawar properti terakhir yang melengkapi kelompoknya (1,5× harga), dan menerima tawaran yang lebih menguntungkan.

```python
def aksi():
    i = info()
    saya = nama_saya()
    me = i["pemain"][saya]
    f = i["fase"]
    if f == "tawaran":
        t = i["tawaran"]
        dapat = t["beri"]["uang"] + sum(petak(p)["harga"] * 1.3 for p in t["beri"]["properti"])
        beri = t["minta"]["uang"] + sum(petak(p)["harga"] * 1.3 for p in t["minta"]["properti"])
        for p in t["minta"]["properti"]:
            if lengkap(petak(p)["kelompok"], saya):
                return "tolak"
        return "terima" if dapat > beri else "tolak"
    if f == "lelang":
        h = petak(i["lelang"]["petak"])["harga"]
        return {"lelang": min(h, max(0, me["uang"] - 200))}
    if f == "beli":
        return "beli" if me["uang"] - petak(me["posisi"])["harga"] >= 50 else "tolak"
    if i["boleh_tawar"]:
        for w in ["coklat", "biru_muda", "merah_muda", "oranye", "merah", "kuning", "hijau", "biru_tua"]:
            ids = kelompok(w)
            mine = [x for x in ids if petak(x)["pemilik"] == saya]
            if len(mine) == len(ids) - 1:
                sisa = [x for x in ids if petak(x)["pemilik"] != saya][0]
                p = petak(sisa)
                if p["pemilik"] != None and p["rumah"] == 0 and me["uang"] > p["harga"] * 2:
                    return {"tawar": {"ke": p["pemilik"], "beri": {"uang": int(p["harga"] * 1.5), "properti": []},
                                      "minta": {"uang": 0, "properti": [sisa]}}}
    b = bisa_bangun()
    if b and me["uang"] > 200:
        return {"bangun": b[0]}
    return "lempar" if f == "awal" else "selesai"
```

### Raja Transportasi

Mengincar transportasi, utilitas, dan kota murah; menolak semua tawaran tukar.

```python
def aksi():
    i = info()
    me = i["pemain"][nama_saya()]
    f = i["fase"]
    if f == "tawaran":
        return "tolak"
    if f == "lelang":
        p = petak(i["lelang"]["petak"])
        suka = p["jenis"] in ["transport", "utilitas"]
        return {"lelang": max(0, min(p["harga"] if suka else p["harga"] // 3, me["uang"] - 100))}
    if f == "beli":
        p = petak(me["posisi"])
        if p["jenis"] in ["transport", "utilitas"] or p["harga"] <= 160:
            return "beli" if me["uang"] >= p["harga"] + 20 else "tolak"
        return "beli" if me["uang"] - p["harga"] >= 400 else "tolak"
    b = bisa_bangun()
    if b and me["uang"] > 350:
        return {"bangun": b[0]}
    return "lempar" if f == "awal" else "selesai"
```

