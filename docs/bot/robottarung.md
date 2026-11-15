# Panduan Bot: Robot Tarung

> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** yang berisi `def aksi():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.

**Rakit robot tempurmu dari komponen (sasis, roda, baterai, armor, senjata) lalu adu di arena 3D. Kendalikan sendiri atau program botnya.**

Pemain: 2–4. Fungsi wajib: `def aksi():`.

## Aturan

- **Garasi**: rakit robotmu dalam batas berat (default 100 kg): sasis (kotak / baji / kubah), penggerak, baterai, armor
  per sisi (depan, kanan, belakang, kiri), senjata, dan pembalik badan. Semua ada tarik-ulurnya: armor tebal = berat,
  spinner besar = kuat tapi boros energi. Rakitan bisa disimpan di perangkatmu untuk dipakai lagi.
- **Kendali**: W/S atau ↑/↓ maju-mundur, A/D atau ←/→ belok, **Spasi** = senjata (spinner/gergaji: nyala-mati; flipper/palu:
  tekan untuk memukul), **E** = membalikkan badan. Di HP: joystick kiri + tombol di kanan. Atau pakai bot berkode.
- **Kerusakan per komponen**: pukulan mengenai armor di sisi yang terkena. Kalau armor sisi itu habis, yang rusak bagian
  dalamnya: depan → senjata, kanan/kiri → motor roda kanan/kiri (robot jadi berputar-putar), belakang → baterai. Rangka
  habis = hancur.
- **Senjata**: spinner horizontal (pukulan terkuat, perlu waktu memutar), drum vertikal (melontarkan lawan, kadang sampai
  terbalik), flipper (melempar dan membalikkan lawan), palu (menembus armor, 2× untuk lawan terbalik), gergaji (menggerus
  terus), atau tanpa senjata (baji pendorong). Sasis baji menyelip ke bawah lawan sehingga lawan mudah didorong.
- **Terbalik**: robot masih bisa jalan pelan, tapi senjatanya mati (kecuali drum vertikal, tetap 70%). Tekan E kalau punya
  pembalik badan atau flipper.
- **Jebakan**: lubang di pojok (terbuka setelah 45 detik; masuk = KO), gergaji lantai, palu arena, dinding berduri (opsi).
- **KO**: rangka hancur, masuk lubang, atau tidak bisa bergerak 10 detik (motor dua-duanya rusak / energi habis).
  Baterai rusak membuat robot pincang (tenaga tinggal 25%).
  Kalau waktu habis, **juri** menilai: kerusakan yang diberikan 50%, agresi 25%, kontrol (melempar, menyelip, mendorong ke
  jebakan) 25%.
- **Poin**: menang ronde +10, KO lawan +3, dan +1 untuk setiap 10 kerusakan yang diberikan.

## Aksi yang dikembalikan

Di garasi: `{"rakit": {"nama": "Drum Merah", "sasis": "kotak", "penggerak": "sedang", "baterai": "sedang",
"senjata": "spinner_v", "pembalik": False, "armor": {"depan": 4, "kanan": 2, "belakang": 2, "kiri": 2}}}`.
Saat tarung: `{"maju": 1.0, "belok": -0.5, "senjata": True, "balik": False}` (semua opsional; yang tidak dikirim tetap
seperti sebelumnya). `None` = kendali tidak berubah. `maju`/`belok` antara -1 dan 1 (belok positif = ke kanan).

## Isi `info()`

```
{ "fase": "garasi" | "hitung" | "tarung", "ronde": 1, "ronde_total": 1, "arena": 14.0, "sisa": 87.5 (detik),
  "berat_maks": 100, "siap": {"Budi": True, ...} (garasi), "desain_saya": {...} (garasi),
  "jebakan": [{"jenis": "lubang" | "gergaji" | "palu", "x": .., "y": .., "r": ..}, ...],
  "robot": {"Budi": {"x": 3.1, "y": 7.0, "a": 12.5 (derajat), "v": 2.1, "hidup": True, "ko": None,
                     "terbalik": False, "udara": 0.0, "energi": 140.2, "energi_maks": 170, "rpm": 0.8, "siap": True,
                     "rangka": 86, "armor": {"depan": 36, ...}, "motor": [40, 40], "senjata_hp": 50, "baterai_hp": 40,
                     "desain": {...}, ...}, ...} }
```

## Fungsi yang tersedia

| Fungsi | Keterangan |
|---|---|
| `info()` | Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game. |
| `nama_saya()` | Nama botmu. |
| `pemain()` | Daftar nama semua pemain, urut nomor kursi. |
| `jumlah_pemain()` | Banyaknya pemain di match ini. |
| `saya()` | Data robotmu (sama dengan info()['robot'][nama_saya()]) ditambah x, y, a (derajat). |
| `lawan()` | Daftar robot lawan yang masih hidup (dict, dengan kunci 'nama'). |
| `lawan_terdekat()` | Robot lawan terdekat yang masih hidup, atau None. |
| `sudut_ke(x, y)` | Sudut (derajat, -180..180) titik itu relatif ke arah hadapmu. Positif = di kanan. |
| `jarak_ke(x, y)` | Jarak (meter) dari pusat robotmu. |
| `kejar(x, y)` | Kendali {'maju', 'belok'} untuk menuju titik itu (belok dulu kalau sudutnya besar). |
| `kabur(x, y)` | Kendali untuk mundur menjauhi titik itu sambil tetap menghadapnya (berhenti mundur kalau di belakang ada dinding/jebakan). |
| `kena_senjata(nama)` | True kalau robot itu sedang dalam jangkauan senjatamu (jarak dan sudutnya pas). |
| `bahaya_di(x, y)` | True kalau titik itu di dalam/dekat lubang atau gergaji lantai, atau terlalu dekat dinding. |
| `jebakan()` | Daftar jebakan arena: [{'jenis', 'x', 'y', 'r'}]. |
| `contoh_rakitan(i)` | Rakitan contoh nomor i (0–5), sudah disesuaikan dengan batas berat room. Boleh dimodifikasi. |
| `pas_berat(rakitan)` | Kurangi armor/baterai/roda (senjata paling akhir) sampai rakitan muat di batas berat room. |
| `berat_rakitan(rakitan)` | Berat (kg) sebuah rakitan. |

## Pengaturan room (diatur host)

Pengaturan **Informasi** menyembunyikan sebagian `info()` (nilainya jadi `None` atau tidak ada) supaya bot dan manusia sama-sama bermain dengan kabut. Tulis bot yang tetap jalan kalau suatu nilai `None`.

| Grup | Pengaturan | Default | Keterangan |
|---|---|---|---|
| Dasar | Lama satu ronde (detik) (`durasi`) | 120 |  |
| Dasar | Jumlah ronde (`ronde`) | 1 |  |
| Aturan | Batas berat robot (kg) (`berat_maks`) | 100 | Kelas berat. Semua komponen + armor harus muat di batas ini. |
| Dasar | Waktu merakit di garasi (detik) (`waktu_garasi`) | 120 | Yang belum siap saat waktu habis memakai rakitan bawaan. |
| Aturan | Ukuran arena (`arena`) | otomatis |  |
| Kejutan | Lubang di pojok arena (`lubang`) | True | Terbuka setelah 45 detik. Robot yang masuk lubang langsung kalah (KO). |
| Kejutan | Gergaji lantai (`gergaji_lantai`) | True |  |
| Kejutan | Palu arena (`palu_arena`) | True | Menghantam setiap 5 detik di dekat dinding bawah. |
| Kejutan | Dinding berduri (`dinding_duri`) | False | Menabrak dinding 2,5× lebih sakit. |
| Aturan | Tingkat kerusakan (`kerusakan`) | normal |  |

**Preset:** *Brutal* (kerusakan=brutal, dinding_duri=True); *Arena Polos* (lubang=False, gergaji_lantai=False, palu_arena=False); *Kelas Ringan* (berat_maks=70, arena=kecil)

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

### Drum Pemburu

Drum vertikal: putar senjata, kejar lawan, hantam dari depan, mundur sebentar setelah memukul.

```python
def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(0)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0, "senjata": False}
    k = kejar(l["x"], l["y"])
    if s["rpm"] < 0.6 and jarak_ke(l["x"], l["y"]) < 2.5:
        k = kabur(l["x"], l["y"])
    k["senjata"] = True
    k["balik"] = s["terbalik"]
    return k
```

### Gasing Sabar

Spinner horizontal: putar sampai penuh dulu sambil menghindar, baru menyerang.

```python
def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(1)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0, "senjata": True}
    d = jarak_ke(l["x"], l["y"])
    if s["rpm"] >= 0.85:
        k = kejar(l["x"], l["y"])
    elif d < 3.5:
        k = kabur(l["x"], l["y"])
    else:
        k = {"maju": 0.2, "belok": 0.6}
    k["senjata"] = s["energi"] > 8
    return k
```

### Pelempar

Flipper + baji: menyelip ke depan lawan, lempar saat dalam jangkauan, lalu dorong ke lubang.

```python
def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(2)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    k = kejar(l["x"], l["y"])
    k["senjata"] = kena_senjata(l["nama"]) and s["siap"]
    k["balik"] = s["terbalik"]
    # lawan terbalik: dorong ke lubang kalau ada
    if l["terbalik"]:
        for j in jebakan():
            if j["jenis"] == "lubang" and jarak_ke(l["x"], l["y"]) < 1.5:
                k["maju"] = 1
    return k
```

### Godam

Palu: dekati lawan dengan armor tebal, pukul tiap kali siap, incar lawan yang terbalik.

```python
def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(3)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    k = kejar(l["x"], l["y"])
    if jarak_ke(l["x"], l["y"]) < 1.6 and abs(sudut_ke(l["x"], l["y"])) < 30:
        k["maju"] = 0.15
    k["senjata"] = kena_senjata(l["nama"]) and s["siap"]
    k["balik"] = s["terbalik"]
    return k
```

### Buldoser

Tanpa senjata: armor tebal + roda kuat, mendorong lawan ke dinding, gergaji, dan lubang.

```python
def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(4)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    tx = l["x"]
    ty = l["y"]
    # dekati dari sisi yang membuat lawan terdorong ke jebakan terdekat
    for j in jebakan():
        if j["jenis"] == "lubang":
            dx = l["x"] - j["x"]
            dy = l["y"] - j["y"]
            n = (dx * dx + dy * dy) ** 0.5
            if n > 0 and jarak_ke(l["x"], l["y"]) > 1.8:
                tx = l["x"] + dx / n * 0.8
                ty = l["y"] + dy / n * 0.8
    k = kejar(tx, ty)
    k["balik"] = s["terbalik"]
    return k
```

