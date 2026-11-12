"""Satu!: permainan kartu warna & angka bergaya UNO, plus kartu power KUSTOM yang ditulis dengan kode.

Kartu kustom: host menulis fungsi `def efek():` (subset Python yang sama dengan bot) yang dijalankan saat kartu itu dimainkan,
memakai fungsi seperti `tarik(nama, n)`, `lewati()`, `tukar_tangan(a, b)`. Kodenya dicek dulu saat disimpan, dijalankan di
interpreter aman yang sama dengan bot, dan hasilnya deterministik (keacakan, misalnya kartu mana yang dibuang, berasal dari
seed match). Panduan untuk AI ada di panduan game ini.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..bot.errors import BotError
from ..bot.interpreter import Interpreter, LibFunction, Limits
from ..bot.validator import CompiledBot, compile_bot
from .base import ActionError, Game, Setting, as_int, rng

WARNA = ["merah", "kuning", "hijau", "biru"]
SIMBOL_JENIS = {"lewati": "⊘", "balik": "⇄", "tambah2": "+2", "ganti": "🌈", "tambah4": "+4"}
MAKS_KUSTOM = 8
MAKS_GILIRAN = 600
NILAI_AKSI, NILAI_LIAR = 20, 50

CONTOH_KARTU: list[dict[str, Any]] = [
    {"nama": "Tukar Tangan", "simbol": "🔄", "warna": "liar", "jumlah": 2, "target": True, "nilai": 50,
     "ket": "Tukar semua kartumu dengan kartu pemain pilihanmu.",
     "kode": "def efek():\n    tukar_tangan(pemain_ini(), target())\n"},
    {"nama": "Hujan Kartu", "simbol": "🌧️", "warna": "semua", "jumlah": 1, "target": False, "nilai": 20,
     "ket": "Semua lawan menarik 1 kartu.",
     "kode": "def efek():\n    for nama in lawan():\n        tarik(nama, 1)\n"},
    {"nama": "Putar Tangan", "simbol": "🌀", "warna": "liar", "jumlah": 2, "target": False, "nilai": 50,
     "ket": "Semua pemain memberikan seluruh kartunya ke pemain berikutnya (searah permainan).",
     "kode": "def efek():\n    putar_tangan()\n"},
    {"nama": "Hadiah", "simbol": "🎁", "warna": "semua", "jumlah": 1, "target": True, "nilai": 20,
     "ket": "Berikan 2 kartu acak dari tanganmu ke pemain pilihanmu.",
     "kode": "def efek():\n    beri(pemain_ini(), target(), 2)\n"},
    {"nama": "Lompat Dua", "simbol": "⏭️", "warna": "semua", "jumlah": 1, "target": False, "nilai": 20,
     "ket": "Dua pemain berikutnya dilewati.",
     "kode": "def efek():\n    lewati(2)\n"},
    {"nama": "Sial Bersama", "simbol": "🎲", "warna": "liar", "jumlah": 1, "target": False, "nilai": 50,
     "ket": "Lawan dengan kartu paling sedikit menarik 2 kartu.",
     "kode": "def efek():\n    korban = min(lawan(), key=lambda n: jumlah_kartu(n))\n    tarik(korban, 2)\n"
             "    pesan(korban + \" kena sial!\")\n"},
    {"nama": "Main Lagi", "simbol": "🔁", "warna": "semua", "jumlah": 1, "target": False, "nilai": 20,
     "ket": "Kamu langsung mendapat giliran sekali lagi.",
     "kode": "def efek():\n    giliran_lagi()\n"},
    {"nama": "Balas Dendam", "simbol": "⚔️", "warna": "semua", "jumlah": 1, "target": False, "nilai": 20,
     "ket": "Pemain sebelum kamu menarik 3 kartu.",
     "kode": "def efek():\n    tarik(sebelumnya(), 3)\n"},
]


@lru_cache(maxsize=256)
def _compile_card(code: str) -> CompiledBot:
    return compile_bot(code, "efek", "None (efek dijalankan lewat fungsi seperti tarik() dan lewati())")


def bersihkan_kartu(v: Any) -> list[dict[str, Any]]:
    """Rapikan daftar kartu kustom dari host. Kartu yang kodenya tidak valid dibuang (editor sudah mengecek sebelumnya)."""
    out: list[dict[str, Any]] = []
    if not isinstance(v, list):
        return out
    for item in v[:MAKS_KUSTOM]:
        try:
            c = _clean_card(item)
            _compile_card(c["kode"])
        except (ActionError, BotError, TypeError, ValueError, KeyError, AttributeError):
            continue
        out.append(c)
    return out


def _clean_card(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ActionError("kartu harus berupa dict")
    nama = " ".join(str(item.get("nama", "")).split())[:24]
    if not nama:
        raise ActionError("nama kartu wajib diisi")
    warna = str(item.get("warna", "liar"))
    if warna not in WARNA + ["liar", "semua"]:
        raise ActionError("warna kartu harus merah, kuning, hijau, biru, liar, atau semua")
    kode = str(item.get("kode", ""))
    if len(kode) > 3000:
        raise ActionError("kode kartu maksimal 3000 karakter")
    jumlah = max(1, min(4, as_int(item.get("jumlah", 1), "jumlah")))
    nilai = max(0, min(100, as_int(item.get("nilai", NILAI_LIAR if warna == "liar" else NILAI_AKSI), "nilai")))
    simbol = str(item.get("simbol", "★")).strip()[:8] or "★"
    return {"nama": nama, "simbol": simbol, "warna": warna, "jumlah": jumlah, "target": bool(item.get("target", False)),
            "nilai": nilai, "ket": str(item.get("ket", ""))[:200], "kode": kode}


def card_value(c: dict[str, Any], kustom: list[dict[str, Any]]) -> int:
    if c["jenis"] == "angka":
        return c["angka"]
    if c["jenis"] == "kustom":
        return kustom[c["kustom"]]["nilai"]
    return NILAI_LIAR if c["warna"] == "liar" else NILAI_AKSI


def card_text(c: dict[str, Any], kustom: list[dict[str, Any]]) -> str:
    if c["jenis"] == "angka":
        return str(c["angka"])
    if c["jenis"] == "kustom":
        return kustom[c["kustom"]]["simbol"]
    return SIMBOL_JENIS[c["jenis"]]


class Satu(Game):
    id = "satu"
    nama = "Satu! (gaya UNO)"
    ringkas = "Habiskan kartu warna & angka lebih dulu. Ada kartu lewati, balik, +2, +4, dan kartu power kustom buatanmu sendiri."
    kategori = "giliran"
    min_pemain, max_pemain = 2, 8
    hint_aksi = "{'main': nomor_kartu, 'warna': 'merah', 'satu': True}, 'ambil', atau 'lewat'"
    timer = 20
    jeda_pada, jeda_hasil = ("menang_ronde",), 6
    label_skor = "Poin"
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 3, 1, 10),
        Setting("kartu_awal", "Kartu awal per pemain", "int", 7, 3, 12),
        Setting("kartu_lawan", "Jumlah kartu lawan", "pilihan", "terlihat", grup="informasi",
                pilihan=[["terlihat", "Terlihat"], ["rahasia", "Rahasia (kecuali yang sudah teriak SATU)"]]),
        Setting("teriak_satu", "Wajib teriak SATU!", "bool", True, grup="aturan",
                ket="Saat memainkan kartu kedua terakhir kamu harus menekan SATU!. Lupa = tarik 2 kartu."),
        Setting("tumpuk", "Tumpuk +2 / +4", "bool", False, grup="aturan",
                ket="Kartu +2/+4 boleh dibalas +2/+4 lagi; yang akhirnya tidak bisa membalas menarik semuanya."),
        Setting("ambil_sampai", "Ambil sampai dapat", "bool", False, grup="aturan",
                ket="Kalau mengambil, terus ambil sampai dapat kartu yang bisa dimainkan (maksimal 10)."),
        Setting("aturan_70", "Aturan 7-0", "bool", False, grup="kejutan",
                ket="Memainkan 7 = tukar kartu dengan pemain pilihanmu. Memainkan 0 = semua tangan berpindah ke pemain berikutnya."),
        Setting("kartu_kustom", "Kartu power kustom", "kartu", [], grup="kejutan", cleaner=bersihkan_kartu,
                ket="Kartu buatanmu sendiri: efeknya ditulis dengan kode (def efek():). Tambahkan dari contoh, atau minta AI "
                    "menuliskannya dengan panduan di tab Panduan bot."),
    ]
    presets = [
        {"id": "pesta", "nama": "Pesta", "ket": "Tumpuk +2/+4, aturan 7-0, dan dua kartu kustom (Hujan Kartu & Tukar Tangan).",
         "nilai": {"tumpuk": True, "aturan_70": True, "kartu_kustom": [CONTOH_KARTU[1], CONTOH_KARTU[0]]}},
        {"id": "kabut", "nama": "Kabut", "ket": "Jumlah kartu lawan dirahasiakan.", "nilai": {"kartu_lawan": "rahasia"}},
    ]
    aturan = """
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
"""
    format_aksi = """- Main kartu: `{"main": nomor, "warna": "merah", "satu": True, "target": "Budi"}`. `nomor` = indeks kartu di `info()["tangan"]`
  (mulai 0). `warna` wajib untuk kartu liar (kalau kosong dipilih warna terbanyak di tanganmu). `satu` = teriak SATU! (wajib saat
  kartumu tinggal 2). `target` untuk kartu kustom bertarget dan kartu 7 di aturan 7-0 (kalau kosong: lawan dengan kartu paling sedikit).
- `"ambil"`: ambil kartu (atau tarik semua tumpukan +2/+4 yang mengarah ke kamu).
- `"lewat"`: hanya setelah mengambil, kalau tidak mau memainkan kartu barunya."""
    format_info = """```
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
`jenis`: angka, lewati, balik, tambah2, ganti, tambah4, kustom. Kartu liar punya `warna` "liar"."""
    lib_docs = [
        {"nama": "bisa_main", "jenis": "fungsi", "tanda": "bisa_main()", "ket": "Daftar indeks kartu di tanganmu yang boleh dimainkan sekarang."},
        {"nama": "cocok", "jenis": "fungsi", "tanda": "cocok(nomor)", "ket": "True kalau kartu nomor itu boleh dimainkan sekarang."},
        {"nama": "warna_terbanyak", "jenis": "fungsi", "tanda": "warna_terbanyak()", "ket": "Warna yang paling banyak di tanganmu (selain kartu liar)."},
        {"nama": "berikutnya", "jenis": "fungsi", "tanda": "berikutnya()", "ket": "Nama pemain yang mendapat giliran setelahmu (kalau tidak ada efek)."},
        {"nama": "jumlah_kartu", "jenis": "fungsi", "tanda": "jumlah_kartu(nama)", "ket": "Jumlah kartu pemain itu (None kalau dirahasiakan)."},
        {"nama": "nilai_kartu", "jenis": "fungsi", "tanda": "nilai_kartu(nomor)", "ket": "Nilai poin kartu nomor itu di tanganmu (angka = nilainya, aksi 20, liar 50)."},
        {"nama": "lawan_tersedikit", "jenis": "fungsi", "tanda": "lawan_tersedikit()", "ket": "Nama lawan dengan kartu paling sedikit yang terlihat."},
    ]
    panduan_tambahan = r"""## Membuat kartu power kustom (untuk AI)

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
"""
    templates = [
        {"id": "asal_cocok", "nama": "Asal Cocok", "ket": "Mainkan kartu angka bernilai besar dulu, kartu liar paling akhir. Tidak lupa teriak SATU.", "kode": '''def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    pilih = sorted(pilih, key=lambda k: (t[k]["warna"] == "liar", -nilai_kartu(k)))
    return {"main": pilih[0], "warna": warna_terbanyak(), "satu": len(t) == 2}
'''},
        {"id": "penyerang", "nama": "Penyerang", "ket": "Kalau pemain berikutnya hampir habis, serang dengan +4 / +2 / lewati. Selain itu simpan kartu serangan.", "kode": '''def aksi():
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
'''},
        {"id": "pengumpul_warna", "nama": "Pengumpul Warna", "ket": "Utamakan kartu dengan warna terbanyak di tangan supaya warna itu terus berlaku.", "kode": '''def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    w = warna_terbanyak()
    k = sorted(pilih, key=lambda k: (t[k]["warna"] != w, t[k]["warna"] == "liar", -nilai_kartu(k)))[0]
    return {"main": k, "warna": w, "satu": len(t) == 2}
'''},
        {"id": "ahli_kustom", "nama": "Ahli Kustom", "ket": "Senang memakai kartu power kustom ke lawan dengan kartu paling sedikit.", "kode": '''def aksi():
    i = info()
    pilih = bisa_main()
    if not pilih:
        return "lewat" if i["fase"] == "setelah_ambil" else "ambil"
    t = i["tangan"]
    k = sorted(pilih, key=lambda k: (t[k]["jenis"] != "kustom", t[k]["warna"] == "liar", -nilai_kartu(k)))[0]
    return {"main": k, "warna": warna_terbanyak(), "satu": len(t) == 2, "target": lawan_tersedikit()}
'''},
    ]

    def meta(self):
        return {**super().meta(), "contoh_kustom": CONTOH_KARTU}

    # ------------------------------------------------------------ dek & ronde
    def _deck(self, s):
        kustom = s["cfg"]["kartu_kustom"]
        cards: list[dict[str, Any]] = []

        def add(warna, jenis, angka=None, kid=None):
            cards.append({"id": len(cards), "warna": warna, "jenis": jenis, "angka": angka, "kustom": kid})

        for w in WARNA:
            add(w, "angka", 0)
            for a in range(1, 10):
                add(w, "angka", a)
                add(w, "angka", a)
            for j in ("lewati", "balik", "tambah2"):
                add(w, j)
                add(w, j)
        for _ in range(4):
            add("liar", "ganti")
            add("liar", "tambah4")
        for kid, d in enumerate(kustom):
            for w in (WARNA if d["warna"] == "semua" else [d["warna"]]):
                for _ in range(d["jumlah"]):
                    add(w, "kustom", None, kid)
        return cards

    def _new_round(self, s):
        n = len(s["names"])
        deck = self._deck(s)
        g = rng(s, "dek", s["ronde"])
        g.shuffle(deck)
        s["tangan"] = [[deck.pop() for _ in range(s["cfg"]["kartu_awal"])] for _ in range(n)]
        while deck[-1]["jenis"] != "angka":           # kartu pertama selalu angka
            deck.insert(0, deck.pop())
        top = deck.pop()
        s["dek"] = deck
        s["buang"] = [top]
        s["warna"] = top["warna"]
        s["arah"] = 1
        s["giliran"] = (s["dealer"] + 1) % n
        s["fase"] = "main"
        s["baru"] = None
        s["tumpukan"] = 0
        s["teriak"] = [False] * n
        s["giliran_ke"] = 0
        s["kocok"] = 0
        s["efek_no"] = 0
        s["terakhir"] = []

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * len(names), "riwayat": [], "dealer": 0}
        self._new_round(s)
        return s

    def _draw(self, s, p, k):
        """Pemain p menarik k kartu (kalau dek habis, tumpukan buang dikocok ulang; kartu teratas tetap)."""
        got = []
        for _ in range(k):
            if not s["dek"]:
                if len(s["buang"]) <= 1:
                    break
                s["kocok"] += 1
                pile = s["buang"][:-1]
                s["buang"] = s["buang"][-1:]
                rng(s, "kocok", s["ronde"], s["kocok"]).shuffle(pile)
                s["dek"] = pile
            c = s["dek"].pop()
            s["tangan"][p].append(c)
            got.append(c)
        if len(s["tangan"][p]) != 1:
            s["teriak"][p] = False
        return got

    def _step_from(self, s, p, k=1):
        n = len(s["names"])
        return (p + s["arah"] * k) % n

    def _playable(self, s, p, c) -> bool:
        top = s["buang"][-1]
        if s["tumpukan"] > 0:
            return c["jenis"] in ("tambah2", "tambah4")
        if c["warna"] == "liar" or c["warna"] == s["warna"]:
            return True
        if c["jenis"] == "kustom":
            return top["jenis"] == "kustom" and top["kustom"] == c["kustom"]
        if c["jenis"] == "angka":
            return top["jenis"] == "angka" and top["angka"] == c["angka"]
        return c["jenis"] == top["jenis"]

    def _playable_idx(self, s, p) -> list[int]:
        hand = s["tangan"][p]
        if s["fase"] == "setelah_ambil":
            k = next((i for i, c in enumerate(hand) if c["id"] == s["baru"]), None)
            return [k] if k is not None and self._playable(s, p, hand[k]) else []
        return [i for i, c in enumerate(hand) if self._playable(s, p, c)]

    # ------------------------------------------------------------ tampilan
    def _card_view(self, s, c):
        kustom = s["cfg"]["kartu_kustom"]
        return {**c, "teks": card_text(c, kustom), "nilai": card_value(c, kustom)}

    def _view(self, s, viewer):
        c, names = s["cfg"], s["names"]
        rahasia = c["kartu_lawan"] == "rahasia" and viewer != "semua"
        counts = {}
        for i, nm in enumerate(names):
            k = len(s["tangan"][i])
            counts[nm] = k if (not rahasia or viewer == i or (k == 1 and s["teriak"][i])) else None
        v = {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "giliran": names[s["giliran"]] if not self.over(s) else None,
             "arah": s["arah"], "urutan": list(names), "atas": self._card_view(s, s["buang"][-1]), "warna": s["warna"],
             "fase": s["fase"], "tumpukan_tarik": s["tumpukan"], "jumlah_kartu": counts,
             "teriak": [names[i] for i in range(len(names)) if s["teriak"][i] and len(s["tangan"][i]) == 1],
             "kustom": [{k: d[k] for k in ("nama", "simbol", "warna", "target", "ket", "nilai", "jumlah")} for d in c["kartu_kustom"]],
             "aturan": {"tumpuk": c["tumpuk"], "teriak_satu": c["teriak_satu"], "ambil_sampai": c["ambil_sampai"], "aturan_70": c["aturan_70"]},
             "sisa_dek": len(s["dek"]), "skor": dict(zip(names, s["skor"])),
             "terakhir": [dict(x) for x in s["terakhir"]], "riwayat": [dict(e) for e in s["riwayat"]]}
        if viewer == "semua":
            v["semua_tangan"] = {nm: [self._card_view(s, x) for x in s["tangan"][i]] for i, nm in enumerate(names)}
        if isinstance(viewer, int):
            hand = s["tangan"][viewer]
            v["tangan"] = [self._card_view(s, x) for x in hand]
            v["kartu_baru"] = next((i for i, x in enumerate(hand) if x["id"] == s["baru"]), None) \
                if s["fase"] == "setelah_ambil" and s["giliran"] == viewer else None
            v["bisa_main"] = self._playable_idx(s, viewer) if s["giliran"] == viewer and not self.over(s) else []
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def event_for(self, s, e, viewer):
        if viewer == "semua" or s["cfg"]["kartu_lawan"] != "rahasia":
            return e
        if e.get("jenis") in ("ambil", "efek_tarik") and not (isinstance(viewer, int) and s["names"][viewer] == e.get("pemain")):
            return {k: v for k, v in e.items() if k != "jumlah"}
        return e

    # ------------------------------------------------------------ aksi
    def pending(self, s):
        return [] if self.over(s) else [s["giliran"]]

    def _auto_color(self, hand, skip=None):
        cnt = {w: 0 for w in WARNA}
        for i, c in enumerate(hand):
            if i != skip and c["warna"] in cnt:
                cnt[c["warna"]] += 1
        return max(WARNA, key=lambda w: (cnt[w], -WARNA.index(w)))

    def _auto_target(self, s, p):
        others = [i for i in range(len(s["names"])) if i != p]
        return s["names"][min(others, key=lambda i: (len(s["tangan"][i]), (i - p) % len(s["names"])))]

    def validate(self, s, p, a):
        if isinstance(a, str):
            a = a.strip().lower()
            if a in ("ambil", "tarik", "draw"):
                if s["fase"] == "setelah_ambil":
                    raise ActionError("kamu sudah mengambil: mainkan kartu baru itu atau 'lewat'")
                return "ambil"
            if a in ("lewat", "pass"):
                if s["fase"] != "setelah_ambil":
                    raise ActionError("'lewat' hanya boleh setelah mengambil kartu")
                return "lewat"
            raise ActionError("aksi harus {'main': nomor}, 'ambil', atau 'lewat'")
        if a is None:
            return "lewat" if s["fase"] == "setelah_ambil" else "ambil"
        if not isinstance(a, dict) or "main" not in a:
            raise ActionError("aksi harus {'main': nomor}, 'ambil', atau 'lewat'")
        hand = s["tangan"][p]
        i = as_int(a["main"], "nomor kartu")
        if not 0 <= i < len(hand):
            raise ActionError(f"nomor kartu harus 0 sampai {len(hand) - 1}")
        if i not in self._playable_idx(s, p):
            if s["fase"] == "setelah_ambil":
                raise ActionError("setelah mengambil, hanya kartu baru itu yang boleh dimainkan (atau 'lewat')")
            if s["tumpukan"] > 0:
                raise ActionError(f"ada tumpukan +{s['tumpukan']}: balas dengan +2/+4 atau 'ambil'")
            raise ActionError("kartu itu tidak cocok dengan warna atau angka/simbol kartu teratas")
        c = hand[i]
        w = a.get("warna")
        if c["warna"] == "liar":
            w = str(w).lower() if w else self._auto_color(hand, i)
            if w not in WARNA:
                raise ActionError("warna harus merah, kuning, hijau, atau biru")
        else:
            w = None
        need_target = (c["jenis"] == "kustom" and s["cfg"]["kartu_kustom"][c["kustom"]]["target"]) or \
                      (c["jenis"] == "angka" and c["angka"] == 7 and s["cfg"]["aturan_70"])
        t = None
        if need_target:
            t = a.get("target")
            if t is None:
                t = self._auto_target(s, p)
            if t not in s["names"] or t == s["names"][p]:
                raise ActionError("target harus nama pemain lain")
        return {"main": i, "warna": w, "satu": bool(a.get("satu")), "target": t}

    def default(self, s, p):
        return "lewat" if s["fase"] == "setelah_ambil" else "ambil"

    def _advance(self, s, skip=0):
        s["giliran"] = self._step_from(s, s["giliran"], 1 + skip)
        s["fase"] = "main"
        s["baru"] = None

    def apply(self, s, actions):
        (p, a), = actions.items()
        names = s["names"]
        c = s["cfg"]
        events: list[dict[str, Any]] = []
        s["giliran_ke"] += 1
        if a == "ambil":
            if s["tumpukan"] > 0:
                k = s["tumpukan"]
                s["tumpukan"] = 0
                got = self._draw(s, p, k)
                events.append({"jenis": "ambil", "pemain": names[p], "jumlah": len(got), "tumpukan": True})
                self._advance(s)
            else:
                got = self._draw(s, p, 1)
                while c["ambil_sampai"] and got and not self._playable(s, p, got[-1]) and len(got) < 10:
                    got += self._draw(s, p, 1)
                events.append({"jenis": "ambil", "pemain": names[p], "jumlah": len(got)})
                if got and self._playable(s, p, got[-1]):
                    s["fase"] = "setelah_ambil"
                    s["baru"] = got[-1]["id"]
                else:
                    self._advance(s)
        elif a == "lewat":
            events.append({"jenis": "lewat", "pemain": names[p]})
            self._advance(s)
        else:
            events += self._play(s, p, a)
        if s["giliran_ke"] >= MAKS_GILIRAN and not any(len(h) == 0 for h in s["tangan"]):
            # batas aman: ronde yang terlalu panjang dimenangkan pemain dengan kartu paling sedikit
            w = min(range(len(names)), key=lambda i: (len(s["tangan"][i]), i))
            events += self._end_round(s, w, batas=True)
        return events

    def _play(self, s, p, a):
        names, c = s["names"], s["cfg"]
        kustom = c["kartu_kustom"]
        hand = s["tangan"][p]
        card = hand.pop(a["main"])
        s["buang"].append(card)
        s["warna"] = a["warna"] if card["warna"] == "liar" else card["warna"]
        s["fase"], s["baru"] = "main", None
        cv = self._card_view(s, card)
        events: list[dict[str, Any]] = [{"jenis": "main", "pemain": names[p], "kartu": cv, "warna": s["warna"],
                                         "target": a.get("target"), "sisa": len(hand)}]
        s["terakhir"] = (s["terakhir"] + [{"pemain": names[p], "kartu": cv, "warna": s["warna"]}])[-6:]
        if len(hand) == 1:
            if a["satu"]:
                s["teriak"][p] = True
                events.append({"jenis": "teriak", "pemain": names[p]})
            elif c["teriak_satu"]:
                got = self._draw(s, p, 2)
                events.append({"jenis": "lupa_satu", "pemain": names[p], "jumlah": len(got)})
        skip = 0
        again = False
        nxt = self._step_from(s, p)
        j = card["jenis"]
        if j == "lewati":
            skip = 1
            events.append({"jenis": "dilewati", "pemain": names[nxt]})
        elif j == "balik":
            s["arah"] *= -1
            if len(names) == 2:
                skip = 1
            events.append({"jenis": "balik", "arah": s["arah"]})
        elif j in ("tambah2", "tambah4"):
            k = 2 if j == "tambah2" else 4
            if c["tumpuk"]:
                s["tumpukan"] += k
            else:
                got = self._draw(s, nxt, k)
                skip = 1
                events.append({"jenis": "ambil", "pemain": names[nxt], "jumlah": len(got), "kena": card_text(card, kustom)})
        elif j == "angka" and c["aturan_70"] and card["angka"] in (0, 7):
            if card["angka"] == 7:
                q = names.index(a["target"])
                s["tangan"][p], s["tangan"][q] = s["tangan"][q], s["tangan"][p]
                events.append({"jenis": "tukar", "pemain": names[p], "dengan": names[q]})
            else:
                self._rotate_hands(s)
                events.append({"jenis": "putar", "arah": s["arah"]})
            for i in range(len(names)):
                s["teriak"][i] = s["teriak"][i] and len(s["tangan"][i]) == 1
        elif j == "kustom":
            res = self._run_custom(s, p, card, a)
            events += res["events"]
            skip += res["lewati"]
            again = res["lagi"]
        if not s["tangan"][p]:
            # efek kartu terakhir tetap berlaku (misalnya +2) supaya poin lawan dihitung setelahnya
            return events + self._end_round(s, p)
        winner = next((i for i in range(len(names)) if not s["tangan"][i]), None)
        if winner is not None:                 # misalnya efek tukar tangan membuat orang lain habis kartu
            return events + self._end_round(s, winner)
        if again:
            s["giliran"] = p
            s["fase"], s["baru"] = "main", None
        else:
            s["giliran"] = p
            self._advance(s, skip)
        return events

    def _rotate_hands(self, s):
        n = len(s["names"])
        old = s["tangan"]
        s["tangan"] = [old[(i - s["arah"]) % n] for i in range(n)]

    # ------------------------------------------------------------ kartu kustom
    def _run_custom(self, s, p, card, a):
        names = s["names"]
        d = s["cfg"]["kartu_kustom"][card["kustom"]]
        s["efek_no"] += 1
        g = rng(s, "efek", s["ronde"], s["efek_no"])
        events: list[dict[str, Any]] = []
        st = {"ops": 0, "tarik": 0, "lewati": 0, "lagi": False}

        def op():
            st["ops"] += 1
            if st["ops"] > 30:
                raise ActionError("efek kartu terlalu banyak operasi (maksimal 30)")

        def idx(nama):
            if nama not in names:
                raise ActionError(f"tidak ada pemain bernama {nama!r}")
            return names.index(nama)

        def jumlah(n, lo=1, hi=10):
            return max(lo, min(hi, as_int(n, "jumlah")))

        def tarik(nama, n=1):
            op()
            i, k = idx(nama), jumlah(n)
            k = min(k, 30 - st["tarik"])
            if k <= 0:
                raise ActionError("total tarik per efek maksimal 30 kartu")
            st["tarik"] += k
            got = self._draw(s, i, k)
            events.append({"jenis": "efek_tarik", "pemain": names[i], "jumlah": len(got), "kartu": d["nama"]})

        def lewati(n=1):
            op()
            k = jumlah(n, 1, len(names) - 1)
            st["lewati"] += k
            events.append({"jenis": "efek_lewati", "pemain": names[p], "jumlah": k, "kartu": d["nama"]})

        def balik():
            op()
            s["arah"] *= -1
            events.append({"jenis": "balik", "arah": s["arah"]})

        def ganti_warna(w):
            op()
            w = str(w).lower()
            if w not in WARNA:
                raise ActionError("warna harus merah, kuning, hijau, atau biru")
            s["warna"] = w
            events.append({"jenis": "efek_warna", "warna": w, "kartu": d["nama"]})

        def tukar_tangan(x, y):
            op()
            i, j = idx(x), idx(y)
            s["tangan"][i], s["tangan"][j] = s["tangan"][j], s["tangan"][i]
            s["teriak"][i] = s["teriak"][j] = False
            events.append({"jenis": "tukar", "pemain": names[i], "dengan": names[j], "kartu": d["nama"]})

        def buang(nama, n=1):
            op()
            i, k = idx(nama), jumlah(n)
            hand = s["tangan"][i]
            k = min(k, len(hand))
            for _ in range(k):
                c = hand.pop(g.randrange(len(hand)))
                s["buang"].insert(0, c)         # masuk ke bawah tumpukan buang (kartu teratas tidak berubah)
            events.append({"jenis": "efek_buang", "pemain": names[i], "jumlah": k, "kartu": d["nama"]})

        def beri(x, y, n=1):
            op()
            i, j, k = idx(x), idx(y), jumlah(n)
            k = min(k, len(s["tangan"][i]))
            for _ in range(k):
                hand = s["tangan"][i]
                s["tangan"][j].append(hand.pop(g.randrange(len(hand))))
            events.append({"jenis": "efek_beri", "dari": names[i], "ke": names[j], "jumlah": k, "kartu": d["nama"]})

        def putar_tangan():
            op()
            self._rotate_hands(s)
            events.append({"jenis": "putar", "arah": s["arah"], "kartu": d["nama"]})

        def giliran_lagi():
            op()
            st["lagi"] = True
            events.append({"jenis": "efek_lagi", "pemain": names[p], "kartu": d["nama"]})

        def tambah_tumpukan(n):
            op()
            k = jumlah(n, 1, 10)
            nxt = self._step_from(s, p, 1 + st["lewati"])
            if s["cfg"]["tumpuk"]:
                s["tumpukan"] += k
            else:
                tarik(names[nxt], k)
                st["lewati"] += 1

        def poin(nama, n):
            op()
            i = idx(nama)
            k = max(-50, min(50, as_int(n, "poin")))
            s["skor"][i] += k
            events.append({"jenis": "efek_poin", "pemain": names[i], "poin": k, "kartu": d["nama"]})

        def pesan(teks):
            op()
            events.append({"jenis": "efek_pesan", "pemain": names[p], "teks": str(teks)[:120], "kartu": d["nama"]})

        def info():
            kustom = s["cfg"]["kartu_kustom"]
            return {"pemain": list(names), "jumlah_kartu": {nm: len(s["tangan"][i]) for i, nm in enumerate(names)},
                    "arah": s["arah"], "warna": s["warna"], "atas": self._card_view(s, s["buang"][-1]),
                    "skor": dict(zip(names, s["skor"])), "tangan_saya": [self._card_view(s, x) for x in s["tangan"][p]],
                    "sisa_dek": len(s["dek"]), "kustom": [x["nama"] for x in kustom]}

        lib = {
            "info": LibFunction("info", info, 5),
            "pemain_ini": LibFunction("pemain_ini", lambda: names[p], 1),
            "target": LibFunction("target", lambda: a.get("target"), 1),
            "warna_dipilih": LibFunction("warna_dipilih", lambda: a.get("warna"), 1),
            "berikutnya": LibFunction("berikutnya", lambda n=1: names[self._step_from(s, p, jumlah(n, 1, 20))], 1),
            "sebelumnya": LibFunction("sebelumnya", lambda: names[self._step_from(s, p, -1)], 1),
            "lawan": LibFunction("lawan", lambda: [nm for i, nm in enumerate(names) if i != p], 2),
            "jumlah_kartu": LibFunction("jumlah_kartu", lambda nama: len(s["tangan"][idx(nama)]), 1),
        }
        for f in (tarik, lewati, balik, ganti_warna, tukar_tangan, buang, beri, putar_tangan, giliran_lagi, tambah_tumpukan,
                  poin, pesan):
            lib[f.__name__] = LibFunction(f.__name__, f, 3)
        try:
            it = Interpreter(_compile_card(d["kode"]), lib, Limits(max_steps=5000, max_prints=0))
            it.run_module()
            it.call_function("efek")
        except (BotError, ActionError, RecursionError, MemoryError) as e:
            msg = e.pesan if isinstance(e, BotError) else str(e)
            events.append({"jenis": "efek_gagal", "pemain": names[p], "kartu": d["nama"], "pesan": str(msg)[:200]})
        return {"events": events, "lewati": st["lewati"], "lagi": st["lagi"]}

    def cek_kustom(self, item):
        """Cek kartu kustom dari editor: rapikan isian, kompilasi kode, lalu coba mainkan di meja contoh."""
        try:
            card = _clean_card(item)
            _compile_card(card["kode"])
        except BotError as e:
            return {"ok": False, "error": e.to_dict(), "kartu": None}
        except (ActionError, TypeError, ValueError) as e:
            return {"ok": False, "error": {"baris": None, "pesan": str(e)}, "kartu": None}
        cfg = self.clean_settings({"kartu_kustom": [card], "kartu_awal": 5})
        s = self.init(cfg, ["Kamu", "Lawan1", "Lawan2"], 7)
        hand = s["tangan"][0]
        warna = WARNA[0] if card["warna"] in ("liar", "semua") else card["warna"]
        hand.append({"id": 9999, "warna": "liar" if card["warna"] == "liar" else warna, "jenis": "kustom", "angka": None, "kustom": 0})
        s["warna"] = warna
        s["giliran"] = 0
        act = {"main": len(hand) - 1, "warna": warna if card["warna"] == "liar" else None, "satu": False,
               "target": "Lawan1" if card["target"] else None}
        events = self._play(s, 0, act)
        gagal = next((e for e in events if e["jenis"] == "efek_gagal"), None)
        if gagal:
            return {"ok": False, "error": {"baris": None, "pesan": "Saat dicoba: " + gagal["pesan"]}, "kartu": card}
        return {"ok": True, "error": None, "kartu": card,
                "contoh": [e for e in events if e["jenis"] != "main"],
                "sesudah": {nm: len(s["tangan"][i]) for i, nm in enumerate(s["names"])},
                "giliran_berikut": s["names"][s["giliran"]], "warna": s["warna"]}

    def _end_round(self, s, w, batas=False):
        names = s["names"]
        kustom = s["cfg"]["kartu_kustom"]
        pts = sum(card_value(c, kustom) for i, h in enumerate(s["tangan"]) if i != w for c in h)
        s["skor"][w] += pts
        entry = {"ronde": s["ronde"], "pemenang": names[w], "poin": pts, "batas": batas,
                 "sisa": {names[i]: len(h) for i, h in enumerate(s["tangan"])},
                 "tangan": {names[i]: [card_text(c, kustom) for c in h] for i, h in enumerate(s["tangan"])}}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        s["dealer"] = (s["dealer"] + 1) % len(names)
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "menang_ronde", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        hand = obs.get("tangan", [])
        kustom = s["cfg"]["kartu_kustom"]
        playable = list(obs.get("bisa_main", []))

        def cocok(nomor):
            return as_int(nomor, "nomor") in playable

        def nilai_kartu(nomor):
            k = as_int(nomor, "nomor")
            if not 0 <= k < len(hand):
                raise ActionError("nomor kartu di luar tangan")
            return card_value(hand[k], kustom)

        def jumlah_kartu(nama):
            return obs["jumlah_kartu"].get(nama)

        def lawan_tersedikit():
            others = [(v if v is not None else 99, k) for k, v in obs["jumlah_kartu"].items() if k != s["names"][p]]
            return min(others)[1] if others else None

        return {"bisa_main": lambda: list(playable), "cocok": cocok, "nilai_kartu": nilai_kartu,
                "warna_terbanyak": lambda: self._auto_color(s["tangan"][p]),
                "berikutnya": lambda: s["names"][self._step_from(s, p)], "jumlah_kartu": jumlah_kartu,
                "lawan_tersedikit": lawan_tersedikit}
