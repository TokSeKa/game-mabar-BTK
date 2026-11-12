# Panduan Bot: Satu! (gaya UNO)

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Habiskan kartu warna & angka lebih dulu. Ada kartu lewati, balik, +2, +4, dan kartu power kustom buatanmu sendiri.**

Pemain: 2–8. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap pemain mendapat 7 kartu. Kartu: angka 0–9 empat warna (🟥 merah, 🟨 kuning, 🟩 hijau, 🟦 biru), **⊘ lewati**, **⇄ balik**,
  **+2**, dan kartu liar **🌈 ganti warna** dan **+4**.
- Giliran berjalan memutar. Mainkan satu kartu yang **sewarna** atau **sama angka/simbolnya** dengan kartu teratas, atau kartu liar
  (pilih warnanya). Tidak bisa / tidak mau main: **ambil** 1 kartu; kalau kartu itu bisa dimainkan boleh langsung dimainkan,
  kalau tidak giliran lewat.
- ⊘ = pemain berikutnya dilewati. ⇄ = arah berbalik (berdua: sama dengan lewati). +2 / +4 = pemain berikutnya menarik 2 / 4 kartu
  dan dilewati.
- Saat memainkan kartu **kedua terakhir**, tekan **SATU!**. Lupa = tarik 2 kartu.
- Yang pertama menghabiskan kartu memenangkan ronde dan mendapat poin dari **sisa kartu lawan**: angka = nilainya, aksi = 20,
  liar = 50 (kartu kustom sesuai pengaturannya). Poin terbanyak setelah semua ronde menang.
- Opsi host: **tumpuk +2/+4**, **ambil sampai dapat**, **aturan 7-0**, jumlah kartu lawan rahasia, dan **kartu power kustom**: kartu
  buatan sendiri yang efeknya ditulis dengan kode (lihat bagian *Membuat kartu power kustom*).

## Aksi yang dikembalikan

- Main kartu: `{"main": nomor, "warna": "merah", "satu": True, "target": "Budi"}`. `nomor` = indeks kartu di `info()["tangan"]`
  (mulai 0). `warna` wajib untuk kartu liar (kalau kosong dipilih warna terbanyak di tanganmu). `satu` = teriak SATU! (wajib saat
  kartumu tinggal 2). `target` untuk kartu kustom bertarget dan kartu 7 di aturan 7-0 (kalau kosong: lawan dengan kartu paling sedikit).
- `"ambil"`: ambil kartu (atau tarik semua tumpukan +2/+4 yang mengarah ke kamu).
- `"lewat"`: hanya setelah mengambil, kalau tidak mau memainkan kartu barunya.

## Isi `info()`

```
{ "ronde": 1, "ronde_total": 3, "giliran": "Budi", "arah": 1, "urutan": ["Ani", "Budi", "Citra"],
  "tangan": [{"id": 12, "warna": "merah", "jenis": "angka", "angka": 5, "kustom": None, "teks": "5", "nilai": 5}, ...],
  "atas": {"warna": "biru", "jenis": "lewati", ...}, "warna": "biru",     # warna yang berlaku sekarang
  "fase": "main",                     # atau "setelah_ambil" (hanya kartu_baru yang boleh dimainkan, atau "lewat")
  "kartu_baru": 6,                    # indeks kartu yang baru diambil (fase setelah_ambil), selain itu None
  "tumpukan_tarik": 0,                # tumpukan +2/+4 yang mengarah ke pemain giliran (opsi tumpuk)
  "jumlah_kartu": {"Ani": 5, "Budi": 7, ...},   # None kalau dirahasiakan
  "teriak": ["Ani"],                  # pemain yang sudah teriak SATU! dan kartunya tinggal 1
  "kustom": [{"nama": "Tukar Tangan", "simbol": "🔄", "warna": "liar", "target": True, "ket": "...", "nilai": 50}],
  "sisa_dek": 60, "skor": {"Ani": 0, ...}, "terakhir": [ {"pemain": "Ani", "kartu": {...}} ],
  "riwayat": [ {"ronde": 1, "pemenang": "Ani", "poin": 45, "sisa": {"Budi": 3, ...}} ] }
```
`jenis`: angka, lewati, balik, tambah2, ganti, tambah4, kustom. Kartu liar punya `warna` "liar".

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `bisa_main()` | Daftar indeks kartu di tanganmu yang boleh dimainkan sekarang. |
| `cocok(nomor)` | True kalau kartu nomor itu boleh dimainkan sekarang. |
| `warna_terbanyak()` | Warna yang paling banyak di tanganmu (selain kartu liar). |
| `berikutnya()` | Nama pemain yang mendapat giliran setelahmu (kalau tidak ada efek). |
| `jumlah_kartu(nama)` | Jumlah kartu pemain itu (None kalau dirahasiakan). |
| `nilai_kartu(nomor)` | Nilai poin kartu nomor itu di tanganmu (angka = nilainya, aksi 20, liar 50). |
| `lawan_tersedikit()` | Nama lawan dengan kartu paling sedikit yang terlihat. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Jumlah ronde (`ronde`) | 3 |  |
| Dasar | Kartu awal per pemain (`kartu_awal`) | 7 |  |
| Informasi (kabut) | Jumlah kartu lawan (`kartu_lawan`) | terlihat |  |
| Aturan | Wajib teriak SATU! (`teriak_satu`) | True | Saat memainkan kartu kedua terakhir kamu harus menekan SATU!. Lupa = tarik 2 kartu. |
| Aturan | Tumpuk +2 / +4 (`tumpuk`) | False | Kartu +2/+4 boleh dibalas +2/+4 lagi; yang akhirnya tidak bisa membalas menarik semuanya. |
| Aturan | Ambil sampai dapat (`ambil_sampai`) | False | Kalau mengambil, terus ambil sampai dapat kartu yang bisa dimainkan (maksimal 10). |
| Kejutan | Aturan 7-0 (`aturan_70`) | False | Memainkan 7 = tukar kartu dengan pemain pilihanmu. Memainkan 0 = semua tangan berpindah ke pemain berikutnya. |
| Kejutan | Kartu power kustom (`kartu_kustom`) | [] | Kartu buatanmu sendiri: efeknya ditulis dengan kode (def efek():). Tambahkan dari contoh, atau minta AI menuliskannya dengan panduan di tab Panduan bot. |

**Preset:** *Pesta* (tumpuk=True, aturan_70=True, kartu_kustom=[{'nama': 'Hujan Kartu', 'simbol': '🌧️', 'warna': 'semua', 'jumlah': 1, 'target': False, 'nilai': 20, 'ket': 'Semua lawan menarik 1 kartu.', 'kode': 'def efek():\n    for nama in lawan():\n        tarik(nama, 1)\n'}, {'nama': 'Tukar Tangan', 'simbol': '🔄', 'warna': 'liar', 'jumlah': 2, 'target': True, 'nilai': 50, 'ket': 'Tukar semua kartumu dengan kartu pemain pilihanmu.', 'kode': 'def efek():\n    tukar_tangan(pemain_ini(), target())\n'}]); *Kabut* (kartu_lawan=rahasia)

## Membuat kartu power kustom (untuk AI)

> **Untuk AI:** pemain ingin kartu baru untuk *Satu!*. Tulis **definisi kartu** dalam format di bawah, dengan `kode` berisi
> `def efek():` yang hanya memakai fungsi kartu di tabel. Subset Python sama dengan bot (tanpa `import`, `random`, `class`,
> `try`). Jelaskan efeknya singkat dalam bahasa Indonesia, lalu tulis isian kartunya.

Isian satu kartu (ditambahkan host di pengaturan room → *Kartu power kustom*):

| Isian | Keterangan |
|---|---|
| `nama` | Nama kartu (maks 24 huruf). |
| `simbol` | Emoji/teks pendek yang tampil di kartu, misalnya 🔄. |
| `warna` | `liar` (bisa dimainkan kapan saja, pemain memilih warna), `semua` (satu kartu untuk tiap warna), atau `merah`/`kuning`/`hijau`/`biru`. |
| `jumlah` | Berapa lembar per warna (1–4). |
| `target` | `True` kalau pemain harus memilih lawan saat memainkannya (dibaca dengan `target()`). |
| `nilai` | Nilai poin kalau kartu ini tersisa di tangan saat ronde selesai (0–100). |
| `ket` | Penjelasan singkat untuk pemain. |
| `kode` | Teks Python berisi `def efek():`. |

Kartu kustom bisa dimainkan kalau warnanya sama dengan warna yang berlaku, kalau kartu teratas adalah kartu kustom yang sama,
atau kapan saja kalau warnanya `liar`. Efek dijalankan **setelah** kartu diletakkan (warna yang berlaku sudah berganti).
Kalau kode error, kartu tetap dianggap dimainkan tanpa efek, dan pesan errornya muncul di log.

### Fungsi untuk `efek()`

| Fungsi | Keterangan |
|---|---|
| `info()` | Keadaan meja: `pemain` (urut kursi), `jumlah_kartu` {nama: n}, `arah` (1 / -1), `warna`, `atas` (kartu teratas), `skor`, `tangan_saya` (kartu pemain yang memainkan), `sisa_dek`. |
| `pemain_ini()` | Nama pemain yang memainkan kartu ini. |
| `target()` | Nama lawan yang dipilih pemain (kartu bertarget), atau None. |
| `warna_dipilih()` | Warna yang dipilih saat memainkan kartu liar, atau None. |
| `berikutnya(n=1)` | Nama pemain ke-n berikutnya searah permainan. |
| `sebelumnya()` | Nama pemain sebelum pemain ini (searah permainan). |
| `lawan()` | Daftar nama semua pemain lain. |
| `jumlah_kartu(nama)` | Jumlah kartu pemain itu. |
| `tarik(nama, n=1)` | Pemain itu menarik n kartu (1–10). |
| `lewati(n=1)` | Lewati n pemain berikutnya. |
| `balik()` | Balik arah permainan. |
| `ganti_warna(warna)` | Ganti warna yang berlaku (merah/kuning/hijau/biru). |
| `tukar_tangan(a, b)` | Tukar semua kartu dua pemain. |
| `buang(nama, n=1)` | Pemain itu membuang n kartu acak (acak dari seed match). |
| `beri(dari, ke, n=1)` | Pindahkan n kartu acak dari tangan `dari` ke `ke`. |
| `putar_tangan()` | Semua pemain memberikan seluruh kartunya ke pemain berikutnya (searah permainan). |
| `giliran_lagi()` | Pemain ini langsung mendapat giliran lagi. |
| `tambah_tumpukan(n)` | Tambah tumpukan tarik untuk pemain berikutnya (seperti +2; bisa dibalas kalau opsi tumpuk menyala, kalau tidak langsung ditarik). |
| `poin(nama, n)` | Tambah/kurangi skor pemain itu (−50 sampai 50). |
| `pesan(teks)` | Tulis pesan ke log permainan. |

Batas: 5.000 langkah dan 30 operasi efek per kartu, total tarik per efek maksimal 30 kartu.

### Format salin-tempel (JSON)

Di editor kartu ada tombol **Tempel JSON**. Tulis kartunya sebagai satu objek JSON (atau daftar objek) seperti ini, lalu pemain
cukup menyalin-tempel:

```json
{"nama": "Sial Bersama", "simbol": "🎲", "warna": "liar", "jumlah": 1, "target": false, "nilai": 50,
 "ket": "Lawan dengan kartu paling sedikit menarik 2 kartu.",
 "kode": "def efek():\n    korban = min(lawan(), key=lambda n: jumlah_kartu(n))\n    tarik(korban, 2)\n"}
```

### Contoh

```python
# Kartu "Sial Bersama" (warna liar): lawan dengan kartu paling sedikit menarik 2
def efek():
    korban = min(lawan(), key=lambda n: jumlah_kartu(n))
    tarik(korban, 2)
    pesan(korban + " kena sial!")
```

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

### Asal Cocok

Mainkan kartu angka bernilai besar dulu, kartu liar paling akhir. Tidak lupa teriak SATU.

```python
def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    pilih = sorted(pilih, key=lambda k: (t[k]["warna"] == "liar", -nilai_kartu(k)))
    return {"main": pilih[0], "warna": warna_terbanyak(), "satu": len(t) == 2}
```

### Penyerang

Kalau pemain berikutnya hampir habis, serang dengan +4 / +2 / lewati. Selain itu simpan kartu serangan.

```python
def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    n = jumlah_kartu(berikutnya())
    darurat = n != None and n <= 3
    def skor(k):
        j = t[k]["jenis"]
        serang = j in ["tambah4", "tambah2", "lewati", "kustom"]
        if darurat:
            return (0 if serang else 1, -nilai_kartu(k))
        return (1 if serang else 0, t[k]["warna"] == "liar", -nilai_kartu(k))
    k = sorted(pilih, key=skor)[0]
    return {"main": k, "warna": warna_terbanyak(), "satu": len(t) == 2, "target": lawan_tersedikit()}
```

### Pengumpul Warna

Utamakan kartu dengan warna terbanyak di tangan supaya warna itu terus berlaku.

```python
def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    w = warna_terbanyak()
    k = sorted(pilih, key=lambda k: (t[k]["warna"] != w, t[k]["warna"] == "liar", -nilai_kartu(k)))[0]
    return {"main": k, "warna": w, "satu": len(t) == 2}
```

### Ahli Kustom

Senang memakai kartu power kustom ke lawan dengan kartu paling sedikit.

```python
def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    k = sorted(pilih, key=lambda k: (t[k]["jenis"] != "kustom", t[k]["warna"] == "liar", -nilai_kartu(k)))[0]
    return {"main": k, "warna": warna_terbanyak(), "satu": len(t) == 2, "target": lawan_tersedikit()}
```

