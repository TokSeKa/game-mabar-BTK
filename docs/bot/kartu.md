# Panduan Bot: Petualangan Kartu Nusantara

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Deck-builder: lawan makhluk Nusantara di 10 lantai dengan kartu jurus. Semua pemain memakai seed yang sama, adu siapa paling jauh dan sehat.**

Pemain: 1–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap pemain menempuh **10 lantai** sendiri-sendiri, dengan **musuh dan pilihan hadiah yang sama** untuk semua (seed sama). Tidak saling menunggu.
- Lantai 4 dan 7 adalah **tempat istirahat**: pulihkan 35% HP maksimal, atau buang satu kartu dari dek. Lantai 6 dan 9 dijaga makhluk **elit**
  (mengalahkannya menambah HP maksimal +6). Lantai 10: bos **Raksasa Batu**.
- **Pertarungan:** tiap giliran kamu dapat 3 energi dan mengambil 5 kartu. Mainkan kartu (biaya energi tertulis), lalu akhiri giliran.
  Sisa kartu di tangan dibuang, lalu musuh bertindak sesuai **niat** yang sudah terlihat (serang, blok, dll.).
- **Blok** menahan serangan dan hilang di awal giliranmu berikutnya. **Racun**: kehilangan HP sebesar racun di awal giliran, lalu racun −1.
  **Lemah**: serangan 25% lebih kecil. **Kuat**: setiap serangan bertambah sebesar nilai kuat.
- Tumpukan ambil habis → tumpukan buang dikocok ulang (kocokan juga dari seed). Kartu "hilang setelah dipakai" kembali lagi di pertarungan berikutnya.
- Menang pertarungan → pilih 1 dari 3 kartu hadiah (atau lewati) untuk ditambahkan ke dek.
- Pertarungan yang terlalu lama (lebih dari 20 giliran) membuat musuh mengamuk: kuat +2 setiap giliran.
- **Skor** = lantai yang diselesaikan × 100 + sisa HP (kalau masih hidup) + 500 kalau bos kalah. Seri: yang memakai giliran lebih sedikit menang.

## Aksi yang dikembalikan

Tergantung `info()["fase"]`:
- `"tarung"`: `{"main": i, "target": j}` memainkan kartu ke-`i` di tangan (mulai 0) ke musuh ke-`j` (target boleh dihilangkan → musuh hidup pertama), atau `"akhiri"` untuk mengakhiri giliran.
- `"hadiah"`: `{"pilih": i}` mengambil kartu `info()["pilihan"][i]`, atau `"lewati"`.
- `"istirahat"`: `"pulihkan"` atau `{"buang": i}` membuang kartu `info()["dek"][i]` dari dek.

## Isi `info()`

```
{ "fase": "tarung" | "hadiah" | "istirahat" | "selesai", "lantai": 3, "lantai_total": 10,
  "hp": 52, "hp_maks": 70, "energi": 2, "blok": 5, "kuat": 0, "racun": 0, "lemah": 0, "giliran": 2,
  "tangan": ["tebas", "silat", "tangkis"],     # id kartu; detail lewat kartu(id)
  "tarik": 4, "tarik_isi": [...], "buang": [...], "dek": [...],
  "musuh": [ {"nama": "Babi Hutan", "hp": 20, "hp_maks": 34, "blok": 0, "kuat": 2, "racun": 0, "lemah": 0, "hidup": True,
              "niat": {"serang": 7, "kali": 1}, "niat_teks": "serang 7"} ],
  "pilihan": ["amukan", "keris", "semedi"],   # fase hadiah
  "skor": 240, "pemain": {"Budi": {"lantai": 3, "hp": 52, "fase": "tarung", "skor": 240}, ...},
  "katalog": {"tebas": {"id": "tebas", "nama": "Tebas", "biaya": 1, "serang": 6, "ket": "Serang 6."}, ...} }
```
`niat.serang` sudah termasuk kuat & lemah musuh (belum dikurangi blokmu).

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `kartu(id)` | Detail kartu: {'nama', 'biaya', 'serang', 'blok', 'racun', ...}. |
| `bisa_main(i)` | True kalau kartu ke-i di tangan bisa dimainkan (energi cukup). |
| `musuh_hidup()` | Indeks musuh yang masih hidup. |
| `musuh_terlemah()` | Indeks musuh hidup dengan HP + blok paling kecil (atau -1). |
| `perkiraan_serangan()` | Total kerusakan yang akan dilakukan musuh giliran ini (sebelum dikurangi blokmu). |
| `daftar_kartu()` | Semua kartu di game ini (dict id → detail). |

## Pengaturan room (diatur host)

| Pengaturan | Default | Keterangan |
|---|---|---|
| HP awal | 70 |  |
| Energi per giliran | 3 |  |

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

### Pendekar Seimbang

Blok secukupnya kalau musuh mau menyerang, sisanya menyerang musuh terlemah.

```python
def aksi():
    i = info()
    f = i["fase"]
    if f == "hadiah":
        suka = ["amukan", "tombak_ganda", "silat", "angin_puyuh", "pukulan_tenaga", "perisai_rotan", "keris"]
        for k in suka:
            if k in i["pilihan"]:
                return {"pilih": i["pilihan"].index(k)}
        return "lewati"
    if f == "istirahat":
        if i["hp"] < i["hp_maks"] * 7 // 10 or "tangkis" not in i["dek"]:
            return "pulihkan"
        return {"buang": i["dek"].index("tangkis")}
    tangan = i["tangan"]
    target = musuh_terlemah()
    if perkiraan_serangan() > i["blok"]:
        for k in range(len(tangan)):
            if bisa_main(k) and kartu(tangan[k]).get("blok", 0) > 0:
                return {"main": k, "target": target}
    for k in range(len(tangan)):
        if bisa_main(k) and kartu(tangan[k]).get("blok", 0) == 0:
            return {"main": k, "target": target}
    for k in range(len(tangan)):
        if bisa_main(k):
            return {"main": k, "target": target}
    return "akhiri"
```

### Si Nekat

Serang terus, kartu termahal dulu. Hadiah selalu kartu serangan.

```python
def aksi():
    i = info()
    if i["fase"] == "hadiah":
        for k in range(len(i["pilihan"])):
            d = kartu(i["pilihan"][k])
            if d.get("serang", 0) > 0 or d.get("serang_semua", 0) > 0:
                return {"pilih": k}
        return "lewati"
    if i["fase"] == "istirahat":
        return "pulihkan"
    tangan = i["tangan"]
    urut = sorted(range(len(tangan)), key=lambda k: -kartu(tangan[k])["biaya"])
    for k in urut:
        if bisa_main(k):
            return {"main": k, "target": musuh_terlemah()}
    return "akhiri"
```

### Dukun Racun

Mengumpulkan kartu racun dan bertahan sambil racun bekerja.

```python
def aksi():
    i = info()
    if i["fase"] == "hadiah":
        for suka in ["racun_upas", "keris", "perisai_rotan", "kuda_kuda", "teriakan"]:
            if suka in i["pilihan"]:
                return {"pilih": i["pilihan"].index(suka)}
        return "lewati"
    if i["fase"] == "istirahat":
        return "pulihkan"
    tangan = i["tangan"]
    hidup = musuh_hidup()
    # racuni musuh yang racunnya paling sedikit
    sasaran = hidup[0]
    for m in hidup:
        if i["musuh"][m]["racun"] < i["musuh"][sasaran]["racun"]:
            sasaran = m
    for k in range(len(tangan)):
        if bisa_main(k) and kartu(tangan[k]).get("racun", 0) > 0:
            return {"main": k, "target": sasaran}
    if perkiraan_serangan() > i["blok"]:
        for k in range(len(tangan)):
            if bisa_main(k) and kartu(tangan[k]).get("blok", 0) > 0:
                return {"main": k, "target": sasaran}
    for k in range(len(tangan)):
        if bisa_main(k):
            return {"main": k, "target": musuh_terlemah()}
    return "akhiri"
```

