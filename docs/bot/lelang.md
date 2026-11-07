# Panduan Bot: Lelang Rahasia

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Setiap ronde satu barang dilelang. Semua menawar diam-diam dengan modal terbatas. Penawar tertinggi membayar dan mendapat poin barang.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Ada sejumlah **barang** (default 12) yang dilelang satu per satu. Default: **nilai poin semua barang sudah diumumkan dari awal** (1–10).
  Host bisa menyembunyikan jadwal (hanya *N* barang ke depan yang terlihat, atau rahasia penuh) dan nilai barang (taksiran pribadi atau rahasia).
- Setiap ronde semua pemain menawar secara **tertutup**, maksimal sebanyak koin yang dimiliki (modal awal default 100 koin).
- **Penawar tertinggi** mendapat poin barang itu dan membayar tawarannya (atau tawaran tertinggi kedua / semua penawar bayar, sesuai *jenis lelang*).
- Kalau tawaran tertinggi **seri**, barang **hangus**: tidak ada yang dapat. Kalau *koin seri ikut hangus* > 0%, para penawar seri itu kehilangan
  sekian persen tawarannya.
- **Barang minus** (kalau diaktifkan): barang kutukan bernilai −1 sampai −8. Tidak ada yang membayar, tapi poin minusnya kena ke penawar
  **tertinggi** dan **terendah** (semua yang seri di ujung ikut kena), plus penawar **tengah** kalau jumlah pemain ganjil dan lebih dari 3.
  Kalau semua menawar sama, semua kena. Jadi tawaran barang minus adalah soal posisi: jangan di ujung, jangan di tengah.
- **Bonus set** (kalau diaktifkan): setiap 3 barang dari kategori yang sama (Pusaka, Seni, Kriya, Harta) memberi bonus poin.
- Skor akhir = poin barang + bonus set + koin sisa × *poin per koin sisa* (default 0,1).

## Aksi yang dikembalikan

Satu angka bulat 0 sampai koinmu, misalnya `25`.

## Isi `info()`

```
{ "ronde": 3, "ronde_total": 12,
  "barang": {"nama": "Keris Pusaka", "kategori": "Pusaka", "nilai": 8},   # nilai: pasti / taksiranmu / None kalau rahasia
  "jadwal": [5, 2, 8, None, ...],     # nilai semua barang urut ronde; None = belum terlihat (lihat_depan / nilai rahasia)
  "nama_barang": ["Batik Tulis", ...], "kategori": ["Kriya", ...],        # None untuk barang yang belum terlihat
  "koin": {"Budi": 70, "Ani": None, ...},   # None kalau koin lawan dirahasiakan (koinmu selalu terlihat)
  "poin": {"Budi": 5, ...}, "nilai_sisa": 0.1, "jenis": "pertama", "hangus_persen": 0, "koin_ronde": 0,
  "nilai_mode": "pasti", "lihat_depan": 30, "bonus_set": 0, "koleksi": {"Budi": {"Pusaka": 1}, ...},
  "riwayat": [ {"ronde": 1, "nama": "Batik Tulis", "nilai": 5, "minus": False, "tawaran": {"Budi": 30, "Ani": 20},
                "pemenang": "Budi", "harga": 30, "hangus": False, "kena_minus": []} ] }
```
- `tawaran` di riwayat bisa `None` (hanya pemenang yang dibuka) dan `harga` bisa `None` (hanya nama pemenang).
- Barang minus: `minus` True, `kena_minus` berisi pemain yang kena poin minus.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `koin_saya()` | Koinmu sekarang. |
| `nilai_sekarang()` | Nilai barang yang sedang dilelang menurut yang kamu lihat (pasti/taksiran), atau None kalau rahasia. |
| `nilai_tersisa(tebakan=5)` | Jumlah nilai barang positif dari ronde ini sampai akhir; barang yang belum terlihat dihitung sebesar `tebakan`. |
| `kemungkinan_minus()` | True kalau barang sekarang terlihat bernilai minus (barang kutukan). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Jumlah barang (`barang`) | 12 |  |
| Dasar | Modal koin (`modal`) | 100 |  |
| Dasar | Poin per koin sisa (`nilai_sisa`) | 0.1 | Koin yang tidak terpakai bernilai sekian poin di akhir. |
| Informasi (kabut) | Barang terlihat ke depan (`lihat_depan`) | 30 | Berapa barang SETELAH barang yang sedang dilelang yang sudah terlihat. 0 = rahasia penuh (hanya barang saat ini). 30 = jadwal terbuka semua. |
| Informasi (kabut) | Nilai barang (`nilai_mode`) | pasti | Taksiran: nilai yang kamu lihat bisa meleset; nilai asli dibuka setelah lelang. Pemenang sering kemahalan! |
| Informasi (kabut) | Taksiran meleset sampai (poin) (`taksiran_selisih`) | 3 |  |
| Informasi (kabut) | Koin lawan rahasia (`koin_rahasia`) | False | Hanya koinmu sendiri yang terlihat. |
| Informasi (kabut) | Yang dibuka setelah lelang (`buka_tawaran`) | semua |  |
| Aturan | Jenis lelang (`jenis`) | pertama | Semua bayar: semua penawar kehilangan tawarannya, tapi hanya yang tertinggi dapat barang. |
| Aturan | Koin seri ikut hangus (%) (`hangus_persen`) | 0 | Kalau tawaran tertinggi seri, barang hangus DAN para penawar seri itu kehilangan sekian persen tawarannya. |
| Aturan | Koin tambahan tiap ronde (`koin_ronde`) | 0 | Semua pemain dapat koin ini setelah setiap lelang. |
| Kejutan | Barang minus (`barang_minus`) | 0 | Jumlah barang kutukan (nilai −1 sampai −8) di jadwal. Tidak ada yang membayar barang minus; poin minusnya kena ke penawar TERTINGGI dan TERENDAH, plus yang di TENGAH kalau jumlah pemain ganjil dan lebih dari 3. |
| Kejutan | Bonus koleksi set (`bonus_set`) | 0 | Setiap 3 barang dari kategori yang sama (Pusaka, Seni, Kriya, Harta) memberi bonus poin ini. 0 = mati. |

**Preset:** *Jadwal Rahasia* (lihat_depan=0); *Lelang Gelap* (lihat_depan=0, nilai_mode=taksiran, koin_rahasia=True, buka_tawaran=pemenang); *Kacau* (lihat_depan=2, barang_minus=3, hangus_persen=50, bonus_set=8)

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

### Proporsional

Menawar sebanding nilai barang dibanding total nilai yang tersisa. Barang minus: menawar di posisi tengah-bawah.

```python
def aksi():
    i = info()
    koin = koin_saya()
    if kemungkinan_minus():
        return min(koin, 2 + saya())
    nilai = nilai_sekarang()
    if nilai == None:
        nilai = 5
    return int(koin * nilai / max(1, nilai_tersisa()))
```

### Pemburu Barang Mahal

Hanya serius menawar barang bernilai 7 ke atas.

```python
def aksi():
    koin = koin_saya()
    nilai = nilai_sekarang()
    if kemungkinan_minus():
        return min(koin, 3)
    if nilai != None and nilai >= 7:
        return min(koin, nilai * 5)
    return min(koin, 1)
```

### Pengintai Dompet

Menawar sedikit di atas dompet lawan terkaya untuk barang bagus (kalau dompet lawan terlihat).

```python
def aksi():
    i = info()
    saya = nama_saya()
    koin = koin_saya()
    nilai = nilai_sekarang()
    if nilai == None:
        nilai = 5
    if nilai < 0:
        return min(koin, 4)
    dompet = [v for k, v in i["koin"].items() if k != saya and v != None]
    if dompet and nilai >= 6:
        terkaya = max(dompet)
        if terkaya + 1 <= koin and terkaya + 1 <= nilai * 8:
            return terkaya + 1
    return min(koin, nilai * 3)
```

