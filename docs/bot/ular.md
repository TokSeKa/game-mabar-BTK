# Panduan Bot: Ular Mabar

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Snake real-time rame-rame: makan buah, jadi paling panjang, dan jangan menabrak ular lain (tidak boleh saling timpa).**

Pemain: 1–8. Fungsi wajib: `def aksi():`.

## Aturan

- Semua ular bergerak **bersamaan dan terus-menerus** (default 6 langkah per detik). Kamu hanya mengatur **belok**:
  panah / WASD di keyboard, atau geser di layar HP. Tidak bisa berbalik arah 180°.
- Makan **apel** (+1 poin, tumbuh 1) dan **buah emas** (+3 poin, tumbuh 2). Kalau diaktifkan, ada **buah busuk** (−2 poin, menyusut 2).
- **Tidak boleh saling timpa**: kepala yang masuk ke badan ular mana pun (termasuk badan sendiri), tembok, atau tepi arena
  membuat ularmu **tumbang**. Pemilik badan yang ditabrak mendapat **+2**. Dua kepala yang bertemu di petak yang sama
  sama-sama tumbang (atau, sesuai pengaturan, yang lebih panjang menang).
- Tumbang: **−3 poin** lalu bangkit lagi 2 detik kemudian dengan panjang 3 (atau, sesuai pengaturan, keluar dari ronde).
  Badan yang tumbang bisa berubah menjadi buah.
- Akhir ronde: ular yang masih hidup **+3**, ular terpanjang **+5**. Mode keluar-ronde: ronde berakhir kalau tinggal satu ular.
- Ronde dimulai dengan hitung mundur 3 detik.

## Aksi yang dikembalikan

`"atas"`, `"bawah"`, `"kiri"`, `"kanan"` (arah baru), atau `None` = tetap lurus. Berbalik 180° diabaikan.

## Isi `info()`

```
{ "ukuran": 24, "ronde": 1, "ronde_total": 2, "detak": 120, "sisa_detak": 420, "kecepatan": 6, "mulai_dalam": 0,
  "tembus_tepi": False, "dinding": [[x, y], ...], "buah": [[x, y, "apel"], ...],
  "ular": {"Budi": {"badan": [[x, y], ...] (kepala dulu), "arah": "kanan", "hidup": True, "bangkit_dalam": 0,
                    "panjang": 5, "skor": 4}, ...} }
```
Koordinat: `x` ke kanan, `y` ke bawah, mulai dari 0.

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `kepala()` | [x, y] kepala ularmu (None kalau sedang tumbang). |
| `arah_sekarang()` | Arah gerak ularmu sekarang. |
| `aman(arah)` | True kalau petak berikutnya ke arah itu kosong (bukan tembok/badan/tepi). Tidak menebak gerakan kepala lawan. |
| `ruang(arah)` | Berapa petak kosong yang bisa dijangkau setelah melangkah ke arah itu (0 = buntu). Bagus untuk menghindari jebakan. |
| `jalur_ke(x, y)` | Arah pertama jalur terpendek menuju petak (x, y), atau None kalau tidak terjangkau. |
| `jarak_ke(x, y)` | Panjang jalur terpendek dari kepalamu ke (x, y), atau None. |
| `buah_terdekat()` | [x, y, jenis] buah bagus (bukan busuk) dengan jalur terpendek, atau None. |
| `dekat_kepala_lawan(arah)` | True kalau petak tujuan bersebelahan dengan kepala ular lain (rawan adu kepala). |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Kecepatan (langkah per detik) (`kecepatan`) | 6 |  |
| Dasar | Lama satu ronde (detik) (`durasi`) | 90 |  |
| Dasar | Jumlah ronde (`ronde`) | 2 |  |
| Dasar | Ukuran arena (`ukuran`) | 0 | 0 = otomatis menurut jumlah pemain (16 untuk sendiri, sampai 34 untuk 8 pemain). |
| Aturan | Kalau menabrak (`tabrakan`) | bangkit |  |
| Aturan | Adu kepala (`adu_kepala`) | keduanya |  |
| Aturan | Jumlah buah di arena (`buah`) | 0 | 0 = otomatis (jumlah pemain + 2). |
| Aturan | Tepi arena tembus (`tembus_tepi`) | False | Keluar di tepi kanan muncul di tepi kiri (dan sebaliknya), jadi tepi tidak mematikan. |
| Kejutan | Rintangan (`rintangan`) | sedikit |  |
| Kejutan | Buah emas (+3, tumbuh 2) (`buah_emas`) | True |  |
| Kejutan | Buah busuk (−2, menyusut 2) (`buah_busuk`) | False | Warnanya mirip apel tapi lebih gelap. Hati-hati! |
| Kejutan | Badan ular yang tumbang jadi buah (`bangkai_jadi_buah`) | True |  |

**Preset:** *Gladiator* (tabrakan=habis, adu_kepala=panjang, rintangan=banyak); *Santai* (tembus_tepi=True, rintangan=kosong); *Jebakan* (buah_busuk=True, rintangan=banyak)

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

### Si Rakus

Mengejar buah terdekat lewat jalur terpendek; kalau tidak ada, cari arah yang aman.

```python
def aksi():
    if kepala() == None:
        return None
    b = buah_terdekat()
    if b != None:
        a = jalur_ke(b[0], b[1])
        if a != None and ruang(a) > 3:
            return a
    for a in ["atas", "kanan", "bawah", "kiri"]:
        if aman(a) and ruang(a) > 3:
            return a
    return None
```

### Penjaga Ruang

Selalu memilih arah dengan ruang terluas; buah dikejar kalau ruangnya cukup dan tidak dekat kepala lawan.

```python
def aksi():
    if kepala() == None:
        return None
    panjang = info()["ular"][nama_saya()]["panjang"]
    b = buah_terdekat()
    if b != None:
        a = jalur_ke(b[0], b[1])
        if a != None and ruang(a) >= panjang * 2 and not dekat_kepala_lawan(a):
            return a
    terbaik = None
    nilai = -1
    for a in ["atas", "kanan", "bawah", "kiri"]:
        if not aman(a):
            continue
        r = ruang(a)
        if dekat_kepala_lawan(a):
            r = r // 3
        if r > nilai:
            terbaik = a
            nilai = r
    return terbaik
```

### Pemburu

Agresif: kalau lebih panjang dari lawan terdekat, mengincar petak di depan kepalanya; selain itu makan buah.

```python
def aksi():
    if kepala() == None:
        return None
    u = info()["ular"]
    saya_p = u[nama_saya()]["panjang"]
    k = kepala()
    target = None
    jarak = 999
    for nama in u:
        if nama == nama_saya() or not u[nama]["hidup"]:
            continue
        if u[nama]["panjang"] < saya_p:
            h = u[nama]["badan"][0]
            d = abs(h[0] - k[0]) + abs(h[1] - k[1])
            if d < jarak:
                jarak = d
                target = h
    if target != None and jarak < 8:
        a = jalur_ke(target[0], target[1])
        if a != None and ruang(a) > saya_p:
            return a
    b = buah_terdekat()
    if b != None:
        a = jalur_ke(b[0], b[1])
        if a != None and ruang(a) > saya_p:
            return a
    for a in ["kanan", "bawah", "kiri", "atas"]:
        if aman(a) and ruang(a) > 3:
            return a
    return None
```

