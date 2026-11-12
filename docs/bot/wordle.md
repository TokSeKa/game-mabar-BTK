# Panduan Bot: Wordle Mabar

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Tebak kata 5 huruf bahasa Indonesia bareng-bareng: balapan siapa paling cepat, serentak, atau bergiliran di satu papan.**

Pemain: 1–8. Fungsi wajib: `def aksi():`.

## Aturan

- Tebak kata rahasia **5 huruf bahasa Indonesia**. Setiap tebakan diberi warna:
  🟩 **hijau** = huruf benar di posisi benar, 🟨 **kuning** = huruf ada di kata tapi posisinya lain, ⬜ **abu-abu** = huruf tidak ada
  (huruf kembar dihitung seperti Wordle asli).
- Tebakan harus kata yang ada di kamus (kecuali host mengatur lain). Satu match berisi beberapa kata (default 3).
- **Mode Balapan** (default): semua menebak kata yang sama di papan masing-masing, **real-time**. Menebak benar di tebakan ke-*k*
  memberi **(maksimal tebakan + 1 − k)** poin, ditambah **bonus tercepat** +3 / +2 / +1 untuk tiga orang pertama.
  Asal menebak cepat-cepat itu rugi: setiap baris yang terpakai mengurangi poin, kalau baris habis poinnya 0, dan setelah
  tebakan salah kamu **harus menunggu 3 detik** (hukuman anti spam, bisa diatur host) sebelum boleh menebak lagi.
- **Mode Serentak**: sama, tapi di setiap langkah semua pemain mengirim satu tebakan bersamaan (tanpa bonus tercepat).
- **Mode Bergiliran**: satu papan bersama, pemain menebak bergantian. Yang menebak benar dapat **+5**, dan tebakan yang
  membuka huruf hijau baru dapat **+1** (tapi hati-hati: petunjukmu juga membantu pemain berikutnya!).
- Waktu habis: di mode balapan/serentak baris itu hangus (kecuali kata yang sudah kamu ketik lengkap dikirim otomatis),
  di mode bergiliran giliranmu dilewati.
- Opsi host: **papan lawan** (warna saja / huruf & warna / tidak terlihat), **mode sulit**, **kata di luar kamus** (ditolak /
  memakan satu baris / bebas), **hukuman tebakan salah**, **kata licik** (jawaban terus menghindar), jumlah kata, dan maksimal
  tebakan.
- Setelah satu kata selesai (semua menebak benar atau barisnya habis), jawabannya dan semua papan dibuka.

## Aksi yang dikembalikan

Teks kata 5 huruf, misalnya `"rumah"` (huruf besar/kecil sama saja). `None` atau `"lewati"` = lewati
(di mode bergiliran giliran dilewati, di mode lain memakan satu baris).

## Isi `info()`

```
{ "mode": "balapan", "ronde": 1, "ronde_total": 3, "maks_tebakan": 6, "panjang": 5,
  "mode_sulit": False, "kata_asal": "tolak", "licik": False, "info_lawan": "warna", "hukuman_detik": 3,
  "skor": {"Budi": 7, ...}, "tebakan_total": {"Budi": 9, ...},
  "papan": {"Budi": {"baris": [{"kata": "tanah", "warna": "AHAKA"}, ...], "selesai": False, "menang": False}, ...},
  "bersama": [ {"pemain": "Budi", "kata": "tanah", "warna": "AHAKA"} ],    # mode bergiliran
  "giliran": "Budi",                                                      # mode bergiliran
  "urut_selesai": ["Ani"],                                                # yang sudah menebak benar (urut)
  "riwayat": [ {"ronde": 1, "jawaban": "rumah", "hasil": {"Budi": {"tebakan": 4, "menang": True, "poin": 5}}, ...} ] }
```
- `warna`: `H` hijau, `K` kuning, `A` abu-abu. Baris yang hangus/dilewati: `"kata": None`, `"warna": None`, `"lewat": True`.
  Baris kata asal (opsi *memakan baris*): `"warna": "?????"`.
- Papan lawan: tergantung *papan lawan*, `kata` lawan berisi `None` (warna saja) atau `warna` juga `None` (tidak terlihat).
  Papanmu sendiri selalu lengkap.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `kandidat()` | Semua kata jawaban (urut abjad) yang masih cocok dengan petunjuk di papanmu (mode bergiliran: papan bersama). |
| `cocok(kata)` | True kalau kata itu masih mungkin jadi jawaban menurut petunjuk di papanmu. |
| `warna(tebakan, jawaban)` | Pola warna kalau `tebakan` ditebak dan jawabannya `jawaban`, misalnya "HKAAA". |
| `di_kamus(kata)` | True kalau kata itu ada di kamus tebakan. |
| `nilai_info(kata)` | Berapa banyak pola warna berbeda yang dihasilkan `kata` terhadap kandidat sekarang (makin besar makin informatif). Mahal: pakai kalau kandidat sudah sedikit (≤ 150). |
| `baris_saya()` | Daftar tebakanmu untuk kata ini (mode bergiliran: papan bersama): [{'kata', 'warna'}, ...]. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Mode (`mode`) | balapan |  |
| Dasar | Jumlah kata (`ronde`) | 3 |  |
| Dasar | Maksimal tebakan per kata (`maks_tebakan`) | 6 | Di mode bergiliran ini jumlah baris papan bersama (boleh lebih banyak kalau pemainnya banyak). |
| Dasar | Waktu berpikir bot di mode balapan (detik) (`bot_detik`) | 12 | Bot menebak paling cepat sekali tiap sekian detik, supaya balapan melawan manusia tetap seru. |
| Informasi (kabut) | Papan lawan (`info_lawan`) | warna | Setelah satu kata selesai, semua papan dibuka. |
| Aturan | Mode sulit (`mode_sulit`) | False | Huruf hijau harus tetap di tempatnya dan huruf kuning wajib dipakai lagi di tebakan berikutnya. |
| Aturan | Kata di luar kamus (`kata_asal`) | tolak |  |
| Aturan | Bonus tercepat (`bonus_cepat`) | True | Yang pertama, kedua, dan ketiga menebak benar dapat +3, +2, +1. |
| Aturan | Hukuman tebakan salah (detik) (`hukuman_detik`) | 3 | Anti spam: setelah tebakan yang salah kamu harus menunggu sekian detik sebelum boleh menebak lagi. Kata yang ditolak kamus tidak kena hukuman (dan tidak memakan baris). 0 = tanpa hukuman. |
| Kejutan | Kata licik (`licik`) | False | Jawaban belum ditentukan: setiap tebakan dijawab dengan petunjuk yang menyisakan kata paling banyak (gaya Absurdle). Kata baru 'terkunci' kalau tinggal satu kemungkinan. Paling sulit! |

**Preset:** *Santai* (info_lawan=semua); *Kabut* (info_lawan=tidak, kata_asal=hangus); *Neraka* (mode_sulit=True, licik=True, kata_asal=hangus)

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

### Kandidat Pertama

Selalu menebak kandidat pertama menurut abjad (setelah pembuka 'teras').

```python
def aksi():
    if not baris_saya():
        return "teras"
    k = kandidat()
    if not k:
        return "rumah"
    return k[0]
```

### Pemburu Info

Dua pembuka tetap untuk menyapu huruf umum, lalu memilih kandidat yang paling memecah kemungkinan.

```python
def aksi():
    b = [x for x in baris_saya() if x["kata"] != None]
    k = kandidat()
    if len(k) == 1:
        return k[0]
    if len(b) == 0:
        return "kartu"
    if len(b) == 1 and len(k) > 40 and not info()["mode_sulit"]:
        return "selip"
    if not k:
        return "nasib"
    if len(k) > 150:
        return k[len(k) // 2]
    terbaik = k[0]
    nilai = -1
    for kata in k:
        v = nilai_info(kata)
        if v > nilai:
            terbaik = kata
            nilai = v
    return terbaik
```

### Kandidat Tengah

Menebak kandidat di tengah daftar (beda dari bot lain, jadi di mode bergiliran tidak saling meniru).

```python
def aksi():
    if not baris_saya():
        return "kapal"
    k = kandidat()
    if not k:
        return "tanah"
    return k[(len(k) + saya()) // 2 % len(k)]
```

### Huruf Umum

Memilih kandidat yang hurufnya paling sering muncul di kandidat lain (heuristik Wordle klasik).

```python
def aksi():
    k = kandidat()
    if not k:
        return "sinar"
    if not baris_saya():
        return "sinar"
    if len(k) > 250:
        return k[0]
    hit = {}
    for kata in k:
        for h in kata:
            hit[h] = hit.get(h, 0) + 1
    terbaik = k[0]
    nilai = -1
    for kata in k:
        unik = []
        for h in kata:
            if h not in unik:
                unik.append(h)
        v = sum(hit[h] for h in unik)
        if v > nilai:
            terbaik = kata
            nilai = v
    return terbaik
```

