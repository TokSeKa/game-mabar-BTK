# Panduan Bot: Domino (Gaple & Draw)

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Domino gaya Indonesia: tempel kartu di ujung meja, habiskan kartumu dulu. Aturan Gaple atau Draw, bisa tim 2 lawan 2, plus mode tantangan.**

Pemain: 2–6. Fungsi wajib: `def aksi():`.

## Aturan

- Setiap pemain mendapat kartu domino. Di giliranmu, **tempel satu kartu** di ujung **kiri** atau **kanan** meja: salah satu
  angka kartumu harus sama dengan angka di ujung itu. Kartu pertama ronde boleh apa saja (atau wajib balak tertinggi di
  ronde pertama, tergantung pengaturan).
- **Gaple**: kalau tidak punya kartu yang cocok, kamu **lewat**. **Draw**: kamu harus **ambil** kartu dari tumpukan sampai
  dapat yang cocok (kalau tumpukan habis, baru boleh lewat).
- Ronde selesai saat ada yang **menghabiskan kartu**, atau meja **buntu** (semua pemain lewat berturut-turut). Kalau buntu,
  pemenangnya yang **jumlah mata kartu sisanya paling sedikit** (seri: yang lebih dulu duduk setelah penempel terakhir).
- Skor: pemenang ronde mendapat jumlah mata sisa kartu semua lawan (atau, sesuai pengaturan, semua pemain kena minus
  sebanyak mata kartunya sendiri). Pemenang membuka ronde berikutnya.
- **Tim** (4 pemain): kursi 1 & 3 melawan 2 & 4; kemenangan satu orang adalah kemenangan tim.
- **Tantangan**: kartu terbuka, bonus tutup balak (×2), denda tiap lewat, kartu 0-0 jadi bom, set balak 9.

## Aksi yang dikembalikan

- `{"kartu": 2, "sisi": "kiri"}`: tempel kartu nomor 2 di tanganmu (mulai dari 0) di ujung kiri. `sisi` boleh dihilangkan
  kalau kartu itu cuma cocok di satu sisi (atau langsung kirim angka `2`).
- `"ambil"`: ambil satu kartu dari tumpukan (aturan Draw, hanya kalau tidak ada kartu yang cocok). Giliranmu berlanjut.
- `"lewat"`: lewat (hanya kalau memang tidak bisa menempel dan tidak bisa mengambil).

## Isi `info()`

```
{ "aturan": "gaple", "ronde": 1, "ronde_total": 3, "set": 6,
  "meja": [[6, 6], [6, 3], ...],            # urut dari kiri ke kanan, angka sudah diputar sesuai sambungan
  "ujung": [6, 3],                          # angka ujung kiri & kanan (None kalau meja kosong)
  "tangan": [[1, 4], [3, 3], ...],          # kartumu
  "jumlah_kartu": {"Budi": 6, ...}, "tangan_semua": {...} (kalau kartu terbuka),
  "tumpukan": 0, "giliran": "Budi", "skor": {"Budi": 12, ...},
  "lewat_pada": {"Budi": [5, 2], ...},      # angka ujung saat pemain itu terpaksa lewat/ambil (petunjuk!)
  "tim": None atau [["Budi", "Cici"], ["Ani", "Dodi"]],
  "wajib": [6, 6] atau None,                # kartu yang wajib dimainkan pertama
  "riwayat": [ {"ronde": 1, "pemenang": "Budi", "cara": "habis", "poin": {...}, "sisa": {...}} ] }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `saya()` | Nomor kursimu (0, 1, 2, ...). |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `tangan()` | Kartu di tanganmu: [[a, b], ...]. |
| `ujung()` | [kiri, kanan] angka ujung meja, atau None kalau meja kosong. |
| `langkah_sah()` | Semua aksi tempel yang sah: [{'kartu': i, 'sisi': 'kiri'}, ...]. Kosong = harus ambil/lewat. |
| `mata(kartu)` | Jumlah mata sebuah kartu, misalnya mata([6, 3]) = 9. |
| `balak(kartu)` | True kalau kartu itu balak (dua angkanya sama). |
| `sudah_keluar(angka)` | Berapa kartu berisi `angka` yang sudah ada di meja. |
| `lawan_tidak_punya(nama)` | Angka-angka yang (kemungkinan besar) tidak dimiliki pemain itu: angka ujung saat ia terpaksa lewat/ambil. |
| `berikutnya()` | Nama pemain yang jalan setelahmu. |
| `kawan()` | Nama kawan setimmu (mode tim), atau None. |
| `ujung_setelah(aksi)` | [kiri, kanan] meja kalau aksi tempel itu dimainkan. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Aturan (`aturan`) | gaple |  |
| Dasar | Jumlah ronde (`ronde`) | 3 |  |
| Dasar | Set kartu (`set`) | 6 | Dengan 5–6 pemain set balak 6 hanya cukup 4 kartu per orang; balak 9 lebih seru untuk ramai-ramai. |
| Dasar | Kartu per pemain (`kartu_awal`) | 0 | 0 = otomatis (7 kartu; aturan Draw dengan 3+ pemain 5 kartu; dikurangi kalau kartunya tidak cukup). |
| Aturan | Cara menghitung skor (`skor`) | sisa_lawan |  |
| Aturan | Selesai lebih cepat kalau poin mencapai (`target`) | 0 | 0 = main sampai semua ronde selesai. |
| Aturan | Main tim (2 lawan 2) (`tim`) | False | Hanya untuk 4 pemain: kursi 1 & 3 melawan kursi 2 & 4, duduk berselang. Poin tim dijumlah dan dibagi berdua. |
| Aturan | Ronde pertama dibuka oleh (`mulai`) | balak_tertinggi | Ronde berikutnya dibuka pemenang ronde sebelumnya. |
| Informasi (kabut) | Kartu lawan terlihat (`kartu_terbuka`) | False | Tantangan strategi: semua kartu di tangan terbuka, menang murni dari perhitungan. |
| Kejutan | Bonus tutup balak (`bonus_balak`) | False | Menghabiskan kartu dengan kartu balak: poin ronde ×2. |
| Kejutan | Denda tiap lewat (`denda_lewat`) | 0 | Setiap kali terpaksa lewat, poinmu berkurang sekian. Bikin pemain menyimpan angka yang aman. |
| Kejutan | Kartu 0-0 = bom (`bom_kosong`) | False | Menempel kartu 0-0 membuat pemain berikutnya wajib ambil 2 kartu (Draw) atau kena denda 10 poin (Gaple). |

**Preset:** *Catur Domino* (kartu_terbuka=True); *Pedas* (bonus_balak=True, denda_lewat=5, bom_kosong=True); *Tim 2 lawan 2* (tim=True)

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

### Buang Besar

Selalu menempel kartu dengan mata terbesar (mengurangi risiko kalau meja buntu).

```python
def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    terbaik = sah[0]
    for a in sah:
        if mata(t[a["kartu"]]) > mata(t[terbaik["kartu"]]):
            terbaik = a
    return terbaik
```

### Balak Dulu

Balak susah ditempel, jadi dibuang secepatnya; selain itu buang yang besar.

```python
def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    def nilai(a):
        k = t[a["kartu"]]
        return (100 if balak(k) else 0) + mata(k)
    terbaik = sah[0]
    for a in sah:
        if nilai(a) > nilai(terbaik):
            terbaik = a
    return terbaik
```

### Pengunci

Membaca lawan: memilih langkah yang membuat ujung meja berisi angka yang tidak dimiliki pemain berikutnya, sambil menjaga variasi angka di tangan sendiri.

```python
def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    lawan = berikutnya()
    kosong = lawan_tidak_punya(lawan) if lawan != kawan() else []
    def nilai(a):
        u = ujung_setelah(a)
        v = mata(t[a["kartu"]])
        for x in u:
            if x in kosong:
                v += 15
            # simpan kartu yang bisa menyambung ujung baru
            for i in range(len(t)):
                if i != a["kartu"] and x in t[i]:
                    v += 3
                    break
            v += sudah_keluar(x)
        if balak(t[a["kartu"]]):
            v += 6
        return v
    terbaik = sah[0]
    for a in sah:
        if nilai(a) > nilai(terbaik):
            terbaik = a
    return terbaik
```

