"""Evolusi Hex: spesies makhluk berebut makanan, beranak, berevolusi, dan saling memangsa di peta heksagonal.

Terinspirasi simulasi evolusi: biaya energi tiap langkah = ukuran³ × kelincahan (dinormalkan), pandangan membayar sesuai
nilainya tiap giliran, makhluk yang cukup lebih besar (≥ 1,2×) memangsa yang lebih kecil, dan makhluk berenergi cukup bisa
beranak (anak mewarisi desain spesies, kadang bermutasi). Semua bergerak bersamaan tiap giliran. Peta, makanan, jebakan,
dan mutasi diacak dari seed match; bot tidak punya keacakan dan tidak punya memori (perintah yang tersimpan di makhluk terlihat
di info)."""

from __future__ import annotations

from collections import deque
from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

MAKS_ASAL_JALUR = 100   # batas BFS berbeda per aksi bot (menjaga server tidak tersendat)

ARAH = {"timur": (1, 0), "timur_laut": (1, -1), "barat_laut": (0, -1), "barat": (-1, 0), "barat_daya": (-1, 1), "tenggara": (0, 1)}
URUT_ARAH = list(ARAH)
MAKANAN = {"rumput": (12, 1), "buah": (25, 2), "daging": (45, 3)}   # energi, poin
SIFAT = ("pandangan", "kelincahan", "ukuran")
MODE = ("naluri", "tujuan", "manual", "diam")
BIAYA_DASAR = 0.5
BIAYA_PANDANG = 0.25
POIN_MANGSA, POIN_LAHIR, POIN_HIDUP = 5, 3, 5
RUSAK_JEBAKAN, RUSAK_DURI = 8, 10


def key(c) -> str:
    return f"{c[0]},{c[1]}"


def unkey(k: str) -> list[int]:
    q, r = k.split(",")
    return [int(q), int(r)]


def hex_dist(a, b) -> int:
    dq, dr = a[0] - b[0], a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def tambah(c, d):
    return [c[0] + d[0], c[1] + d[1]]


def biaya_langkah(ukuran: int, kelincahan: int) -> float:
    """Energi per langkah: (ukuran/5)³ × (kelincahan/5), minimal 0,05."""
    return max(0.05, round((ukuran / 5) ** 3 * (kelincahan / 5), 3))


def energi_maks(ukuran: int) -> int:
    return 40 + 12 * ukuran


def hp_maks(ukuran: int) -> int:
    return 10 + 5 * ukuran


def biaya_lahir(ukuran: int) -> int:
    return 25 + 5 * ukuran


class EvolusiHex(Game):
    id = "evolusi"
    nama = "Evolusi Hex"
    ringkas = "Kembangkan spesiesmu di peta heksagonal: cari makanan, beranak, bermutasi, dan mangsa spesies lain. Ukuran, kecepatan, dan pandangan punya harga energi."
    kategori = "tick"
    min_pemain, max_pemain = 1, 6
    hint_aksi = "dict perintah, misalnya {'perintah': {'3': {'mode': 'tujuan', 'tujuan': [2, -1]}}, 'beranak': {'3': True}}"
    timer = 10
    label_skor = "Poin"
    max_frames = 400
    settings = [
        Setting("giliran", "Jumlah giliran", "int", 60, 15, 200),
        Setting("radius", "Ukuran peta (radius heksagon)", "int", 6, 4, 9),
        Setting("populasi_awal", "Makhluk awal per pemain", "int", 2, 1, 4),
        Setting("poin_sifat", "Poin sifat (pandangan + kelincahan + ukuran)", "int", 15, 6, 24,
                ket="Jatah poin untuk desain spesies; tiap sifat 1–9."),
        Setting("maks_populasi", "Populasi maksimal per pemain", "int", 12, 3, 20),
        Setting("makanan", "Kelimpahan makanan", "int", 3, 1, 5),
        Setting("kabut", "Kabut (hanya yang terlihat makhlukmu)", "bool", True, grup="informasi",
                ket="Makhluk, makanan, dan jebakan hanya terlihat dalam pandangan makhlukmu. Medan selalu terlihat."),
        Setting("rasio_mangsa", "Syarat memangsa (× ukuran lawan)", "float", 1.2, 1.05, 2.0, grup="aturan",
                ket="Makhluk memangsa lawan kalau ukurannya minimal sekian kali ukuran lawan."),
        Setting("rintangan", "Jatah rintangan per pemain", "int", 3, 0, 10, grup="aturan",
                ket="🪨 batu (menghalangi semua) atau 🌵 duri (tersembunyi, −10 HP untuk makhluk lawan). Dipasang di samping makhluk, biaya 10 energi."),
        Setting("bangkit", "Bangkit setelah punah (giliran)", "int", 10, 0, 60, grup="aturan",
                ket="Spesies yang punah mendapat satu makhluk baru di sarangnya setelah sekian giliran. 0 = punah selamanya."),
        Setting("semak", "Semak (%)", "int", 15, 0, 40, grup="kejutan",
                ket="Semak bisa dilewati tapi isinya (makanan, makhluk, jebakan) hanya terlihat dari dalam atau dari sebelahnya."),
        Setting("batu", "Batu (%)", "int", 8, 0, 25, grup="kejutan"),
        Setting("jebakan", "Jebakan tersembunyi di semak", "int", 3, 0, 15, grup="kejutan", ket=f"Menginjak jebakan: −{RUSAK_JEBAKAN} HP."),
        Setting("mutasi", "Peluang mutasi anak (%)", "int", 30, 0, 100, grup="kejutan",
                ket="Anak bisa lahir dengan satu sifat +1 atau −1 dari desain spesiesnya."),
    ]
    presets = [
        {"id": "terang", "nama": "Terang", "ket": "Tanpa kabut: semua makhluk dan makanan terlihat.", "nilai": {"kabut": False}},
        {"id": "rimba", "nama": "Rimba", "ket": "Semak lebat dan banyak jebakan.", "nilai": {"semak": 35, "jebakan": 8}},
        {"id": "kejam", "nama": "Seleksi Kejam", "ket": "Makanan langka, mutasi tinggi, tanpa bangkit.", "nilai": {"mutasi": 70, "bangkit": 0}},
    ]
    aturan = f"""
- Peta **heksagonal**. Setiap pemain mengendalikan satu **spesies**, mulai dengan 2 makhluk di sarangnya (pojok peta).
- Giliran 0 = **desain spesies**: bagi **15 poin** ke tiga sifat (masing-masing 1–9):
  - 👁️ **Pandangan**: melihat lurus ke 6 arah sejauh nilainya (tembok & semak menghalangi). Biaya **{BIAYA_PANDANG} × pandangan** energi per giliran.
  - 🐾 **Kelincahan**: langkah maksimal per giliran. Biaya **per langkah = (ukuran/5)³ × (kelincahan/5)**: makhluk besar dan cepat
    sangat boros!
  - 🦣 **Ukuran**: HP = 10 + 5×ukuran, energi maksimal = 40 + 12×ukuran. Makhluk yang ukurannya **≥ 1,2×** ukuran lawan
    **memangsa** lawan itu (masuk ke petaknya, atau lawan masuk ke mulutnya). Ukuran juga menentukan biaya beranak.
- Semua makhluk bergerak **bersamaan** tiap giliran, satu langkah demi satu langkah (urutan bergiliran adil). Setiap makhluk juga
  membayar **{BIAYA_DASAR}** energi per giliran untuk hidup. Energi habis = HP −2 per giliran (kelaparan). HP sembuh +1 per giliran
  kalau energi di atas separuh.
- Makanan: 🌱 rumput (+12 energi, 1 poin), 🍎 buah (+25, 2 poin), 🍖 daging (+45, 3 poin; muncul dari makhluk yang mati).
  Makanan tumbuh lagi dari waktu ke waktu.
- **Beranak** (toggle per makhluk): kalau energi ≥ biaya lahir (25 + 5×ukuran anak) + 30% energi maksimal, makhluk itu melahirkan
  satu anak di sebelahnya dengan **desain spesies saat ini** (bisa diubah kapan saja) dan kadang **bermutasi** ±1 di satu sifat.
- Perintah per makhluk: **naluri** (otomatis: kabur dari pemangsa, cari makanan/mangsa), **tujuan** (jalan sendiri ke petak yang
  dipilih), **manual** (pilih langkah satu per satu tiap giliran), atau **diam**. Makhluk diberi nomor otomatis dan boleh diberi nama.
- **Rintangan** (jatah 3): pasang 🪨 batu atau 🌵 duri tersembunyi di sebelah makhlukmu (10 energi).
- Poin: makanan 1/2/3, memangsa makhluk lawan **+{POIN_MANGSA}**, kelahiran **+{POIN_LAHIR}**, dan **+{POIN_HIDUP}** per makhluk yang masih hidup di
  akhir. Poin terbanyak setelah semua giliran menang.
"""
    format_aksi = """Dict (semua kunci opsional; `{}` = semua makhluk melanjutkan perintahnya):
```
{ "desain": {"pandangan": 4, "kelincahan": 5, "ukuran": 6},     # desain spesies (giliran 0: makhluk awal; setelahnya: anak baru)
  "perintah": {"7": {"mode": "tujuan", "tujuan": [2, -1]},      # mode: naluri / tujuan / manual / diam
               "9": {"mode": "manual", "jalan": ["timur", "tenggara"]}},   # jalan: langkah giliran ini (≤ kelincahan)
  "beranak": {"7": True},
  "nama": {"7": "Si Gesit"},
  "pasang": {"makhluk": "7", "arah": "barat", "jenis": "duri"} }   # jenis: batu / duri
```
Arah: `timur`, `timur_laut`, `barat_laut`, `barat`, `barat_daya`, `tenggara`. Id makhluk boleh angka atau teks. Perintah untuk makhluk
yang sudah mati diabaikan."""
    format_info = """```
{ "giliran": 5, "giliran_total": 60, "fase": "main",          # fase "desain" di giliran 0
  "radius": 6, "peta": {"0,0": ".", "1,-1": "s", "2,0": "#", ...},   # "." tanah, "s" semak, "#" batu (koordinat aksial "q,r")
  "makhluk_saya": [ {"id": "7", "nama": "#3", "posisi": [1, -2], "pandangan": 4, "kelincahan": 5, "ukuran": 6,
                     "hp": 40, "hp_maks": 40, "energi": 63.5, "energi_maks": 112, "mode": "naluri", "tujuan": None,
                     "beranak": True, "biaya_langkah": 1.728, "biaya_lahir": 55, "umur": 3}, ... ],
  "makhluk_lain": [ {"id": "12", "pemilik": "Budi", "posisi": [3, 0], "ukuran": 8, "hp": 50}, ... ],   # yang terlihat saja
  "makanan": [[2, 1, "buah"], ...], "jebakan": [[0, 3, "duri", True], ...],  # yang diketahui; True = milikmu (tidak melukaimu)
  "terlihat": ["1,-2", "2,-2", ...],                        # petak yang terlihat sekarang (None tanpa kabut)
  "desain": {"pandangan": 4, "kelincahan": 5, "ukuran": 6}, "poin_sifat": 15, "rintangan_sisa": 3,
  "sarang": [5, -5], "populasi": {"Ani": 4, "Budi": 2}, "skor": {"Ani": 12, ...},
  "rasio_mangsa": 1.2, "maks_populasi": 12 }
```
Koordinat aksial: arah timur = (+1, 0), timur_laut = (+1, −1), barat_laut = (0, −1), barat = (−1, 0), barat_daya = (−1, +1),
tenggara = (0, +1). Jarak = (|dq| + |dr| + |dq+dr|) / 2."""
    lib_docs = [
        {"nama": "makhluk_saya", "jenis": "fungsi", "tanda": "makhluk_saya()", "ket": "Daftar makhlukmu yang hidup (sama dengan info()['makhluk_saya'])."},
        {"nama": "jarak", "jenis": "fungsi", "tanda": "jarak(a, b)", "ket": "Jarak heksagon antara dua petak [q, r]."},
        {"nama": "jalur", "jenis": "fungsi", "tanda": "jalur(dari, ke)", "ket": "Daftar petak jalur terpendek (tanpa petak awal) yang menghindari batu & jebakan yang diketahui, atau None. Maksimal 100 petak awal berbeda per giliran (petak awal yang sama boleh dipakai berulang kali)."},
        {"nama": "tetangga", "jenis": "fungsi", "tanda": "tetangga(petak)", "ket": "Petak sebelah [q, r] yang bisa diinjak (bukan batu, di dalam peta)."},
        {"nama": "arah_ke", "jenis": "fungsi", "tanda": "arah_ke(dari, ke)", "ket": "Nama arah dari petak ke petak sebelahnya, atau None."},
        {"nama": "makanan_terdekat", "jenis": "fungsi", "tanda": "makanan_terdekat(id)", "ket": "[q, r, jenis] makanan terlihat dengan jalur terpendek dari makhluk itu, atau None."},
        {"nama": "mangsa_terdekat", "jenis": "fungsi", "tanda": "mangsa_terdekat(id)", "ket": "Makhluk lawan terlihat terdekat yang bisa dimangsa makhluk itu, atau None."},
        {"nama": "ancaman_terdekat", "jenis": "fungsi", "tanda": "ancaman_terdekat(id)", "ket": "Makhluk lawan terlihat terdekat yang bisa memangsa makhluk itu, atau None."},
        {"nama": "bisa_beranak", "jenis": "fungsi", "tanda": "bisa_beranak(id)", "ket": "True kalau energi makhluk itu cukup untuk beranak sekarang (dengan desain sekarang)."},
    ]
    templates = [
        {"id": "naluri", "nama": "Naluri Saja", "ket": "Desain seimbang, semua makhluk memakai naluri, beranak kalau energi cukup.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "desain":
        return {"desain": {"pandangan": 5, "kelincahan": 5, "ukuran": 5}}
    return {"beranak": {m["id"]: True for m in i["makhluk_saya"]}}
'''},
        {"id": "pemangsa", "nama": "Pemangsa Besar", "ket": "Spesies besar dan lambat yang mengejar mangsa terdekat, kalau tidak ada mencari makanan.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "desain":
        b = i["poin_sifat"]
        return {"desain": {"pandangan": 3, "kelincahan": 3, "ukuran": min(9, b - 6)}}
    perintah = {}
    lahir = {}
    for m in i["makhluk_saya"]:
        lahir[m["id"]] = len(i["makhluk_saya"]) < 6
        target = mangsa_terdekat(m["id"])
        if target != None:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": target["posisi"]}
        else:
            perintah[m["id"]] = {"mode": "naluri"}
    return {"perintah": perintah, "beranak": lahir}
'''},
        {"id": "pengumpul", "nama": "Pengumpul Hemat", "ket": "Kecil, hemat energi, pandangan jauh. Kabur dari pemangsa, banyak beranak.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "desain":
        b = i["poin_sifat"]
        u = 2
        k = 4
        return {"desain": {"pandangan": min(9, b - u - k), "kelincahan": k, "ukuran": u}}
    perintah = {}
    for m in i["makhluk_saya"]:
        bahaya = ancaman_terdekat(m["id"])
        if bahaya != None and jarak(bahaya["posisi"], m["posisi"]) <= 3:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": i["sarang"]}
            continue
        f = makanan_terdekat(m["id"])
        if f != None:
            perintah[m["id"]] = {"mode": "tujuan", "tujuan": [f[0], f[1]]}
        else:
            perintah[m["id"]] = {"mode": "naluri"}
    return {"perintah": perintah, "beranak": {m["id"]: True for m in i["makhluk_saya"]}}
'''},
        {"id": "penjaga_duri", "nama": "Penjaga Duri", "ket": "Desain menengah, menanam duri di sekitar sarang di awal, lalu memakai naluri.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "desain":
        return {"desain": {"pandangan": 4, "kelincahan": 4, "ukuran": 7}}
    out = {"beranak": {m["id"]: m["energi"] > m["energi_maks"] * 0.6 for m in i["makhluk_saya"]}}
    if i["rintangan_sisa"] > 0 and i["makhluk_saya"]:
        m = i["makhluk_saya"][0]
        for a in ["timur", "barat", "tenggara", "barat_laut", "timur_laut", "barat_daya"]:
            p = [m["posisi"][0], m["posisi"][1]]
            d = {"timur": [1, 0], "timur_laut": [1, -1], "barat_laut": [0, -1], "barat": [-1, 0], "barat_daya": [-1, 1], "tenggara": [0, 1]}[a]
            t = [p[0] + d[0], p[1] + d[1]]
            k = str(t[0]) + "," + str(t[1])
            if i["peta"].get(k) == "s" and m["energi"] > 30:
                out["pasang"] = {"makhluk": m["id"], "arah": a, "jenis": "duri"}
                break
    return out
'''},
    ]

    # ------------------------------------------------------------ peta
    def _cells(self, R):
        return [[q, r] for q in range(-R, R + 1) for r in range(-R, R + 1) if hex_dist([q, r], [0, 0]) <= R]

    def _corners(self, R, n):
        dirs = [ARAH[a] for a in ("timur", "tenggara", "barat_daya", "barat", "barat_laut", "timur_laut")]
        corners = [[d[0] * (R - 1), d[1] * (R - 1)] for d in dirs]
        order = {1: [3], 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 3, 4], 6: [0, 1, 2, 3, 4, 5]}[n]
        return [corners[k] for k in order]

    def init(self, cfg, names, seed):
        n = len(names)
        R = cfg["radius"]
        s = {"seed": seed, "names": names, "cfg": cfg, "giliran": 0, "fase": "desain", "makhluk": {}, "id_next": 1,
             "nomor": [0] * n, "poin": [0] * n, "stat": [{"makan": 0, "mangsa": 0, "lahir": 0, "mati": 0} for _ in range(n)],
             "desain": [self._balanced(cfg) for _ in range(n)], "rintangan_sisa": [cfg["rintangan"]] * n,
             "punah": [None] * n, "kejadian": []}
        g = rng(s, "peta")
        cells = self._cells(R)
        sarang = self._corners(R, n)
        s["sarang"] = sarang
        aman = {key(x) for h in sarang for x in [h] + [tambah(h, d) for d in ARAH.values()]}
        peta = {key(c): "." for c in cells}
        bebas = [c for c in cells if key(c) not in aman]
        g.shuffle(bebas)
        nb = len(bebas) * cfg["batu"] // 100
        ns = len(bebas) * cfg["semak"] // 100
        for c in bebas[:nb]:
            peta[key(c)] = "#"
        for c in bebas[nb:nb + ns]:
            peta[key(c)] = "s"
        # batu tidak boleh memutus peta: buka lagi kalau ada petak yang tidak terjangkau dari pusat
        self._connect(peta, R)
        s["peta"] = peta
        semak = sorted((c for c in cells if peta[key(c)] == "s"), key=lambda c: (c[0], c[1]))
        g.shuffle(semak)
        s["jebakan"] = {key(c): {"jenis": "jebakan", "oleh": None, "terbuka": False} for c in semak[: cfg["jebakan"]]}
        s["makanan"] = {}
        k = cfg["makanan"]
        empty = [c for c in cells if peta[key(c)] != "#" and key(c) not in aman]
        g.shuffle(empty)
        nr, nf = len(cells) * 5 * k // 300, len(cells) * 5 * k // 600
        for c in empty[:nr]:
            s["makanan"][key(c)] = "rumput"
        for c in empty[nr:nr + nf]:
            s["makanan"][key(c)] = "buah"
        return s

    def _connect(self, peta, R):
        start = "0,0"
        if peta[start] == "#":
            peta[start] = "."
        while True:
            seen = {start}
            q = deque([start])
            while q:
                c = unkey(q.popleft())
                for d in ARAH.values():
                    k = key(tambah(c, d))
                    if k in peta and peta[k] != "#" and k not in seen:
                        seen.add(k)
                        q.append(k)
            lost = sorted(k for k, t in peta.items() if t != "#" and k not in seen)
            if not lost:
                return
            # buka satu batu yang bersebelahan dengan bagian yang terputus
            for k in lost:
                c = unkey(k)
                walls = [key(tambah(c, d)) for d in ARAH.values() if peta.get(key(tambah(c, d))) == "#"]
                if walls:
                    peta[walls[0]] = "."
                    break
            else:
                return

    def _balanced(self, cfg):
        b = cfg["poin_sifat"]
        base = b // 3
        out = {"pandangan": base, "kelincahan": base, "ukuran": base}
        for k in SIFAT[: b - 3 * base]:
            out[k] += 1
        return {k: max(1, min(9, v)) for k, v in out.items()}

    # ------------------------------------------------------------ makhluk
    def _spawn(self, s, p, pos, traits, energy_frac=0.7, parent=None, beranak=False):
        cid = str(s["id_next"])
        s["id_next"] += 1
        s["nomor"][p] += 1
        u = traits["ukuran"]
        m = {"id": cid, "pemilik": p, "nama": f"#{s['nomor'][p]}", "posisi": list(pos), **{k: traits[k] for k in SIFAT},
             "hp": hp_maks(u), "energi": round(energi_maks(u) * energy_frac, 2), "mode": "naluri", "tujuan": None,
             "beranak": beranak, "lahir": s["giliran"], "induk": parent}
        s["makhluk"][cid] = m
        return m

    def _occupant(self, s, pos):
        for m in s["makhluk"].values():
            if m["posisi"] == pos:
                return m
        return None

    def _passable(self, s, pos):
        t = s["peta"].get(key(pos))
        return t is not None and t != "#"

    def _pop(self, s, p):
        return sum(1 for m in s["makhluk"].values() if m["pemilik"] == p)

    # ------------------------------------------------------------ pandangan
    def _sees(self, s, m) -> set[str]:
        out = {key(m["posisi"])}
        for d in ARAH.values():
            c = tambah(m["posisi"], d)
            if key(c) in s["peta"]:
                out.add(key(c))
            c = list(m["posisi"])
            for _ in range(m["pandangan"]):
                c = tambah(c, d)
                k = key(c)
                if k not in s["peta"]:
                    break
                out.add(k)
                if s["peta"][k] in ("#", "s"):
                    break
        return out

    def _vision(self, s, p) -> tuple[set[str], set[str]]:
        """(petak terlihat, petak yang isinya terlihat) untuk pemain p."""
        vis: set[str] = set()
        close: set[str] = set()
        for m in s["makhluk"].values():
            if m["pemilik"] != p:
                continue
            vis |= self._sees(s, m)
            close.add(key(m["posisi"]))
            for d in ARAH.values():
                close.add(key(tambah(m["posisi"], d)))
        content = {k for k in vis if s["peta"][k] != "s" or k in close}
        return vis, content

    def _creature_view(self, s, m, full):
        u = m["ukuran"]
        base = {"id": m["id"], "pemilik": s["names"][m["pemilik"]], "posisi": list(m["posisi"]), "ukuran": u, "hp": m["hp"],
                "hp_maks": hp_maks(u)}
        if not full:
            return base
        return {**base, "nama": m["nama"], "pandangan": m["pandangan"], "kelincahan": m["kelincahan"],
                "energi": round(m["energi"], 1), "energi_maks": energi_maks(u), "mode": m["mode"],
                "tujuan": list(m["tujuan"]) if m["tujuan"] else None, "beranak": m["beranak"],
                "biaya_langkah": biaya_langkah(u, m["kelincahan"]),
                "biaya_lahir": biaya_lahir(s["desain"][m["pemilik"]]["ukuran"]), "umur": s["giliran"] - m["lahir"]}

    def _view(self, s, viewer):
        c, names = s["cfg"], s["names"]
        fog = c["kabut"] and viewer != "semua"
        if fog and isinstance(viewer, int):
            vis, content = self._vision(s, viewer)
        elif fog:
            vis, content = set(), set()
        else:
            vis = content = set(s["peta"])
        mine = [m for m in s["makhluk"].values() if isinstance(viewer, int) and m["pemilik"] == viewer]
        others = [m for m in s["makhluk"].values() if not (isinstance(viewer, int) and m["pemilik"] == viewer)
                  and (not fog or key(m["posisi"]) in content)]
        traps = []
        for k, t in sorted(s["jebakan"].items()):
            own = isinstance(viewer, int) and t["oleh"] == viewer
            if viewer == "semua" or own or (t["terbuka"] and (not fog or k in vis)):
                traps.append(unkey(k) + [t["jenis"], own])
        v = {"giliran": s["giliran"], "giliran_total": c["giliran"], "fase": s["fase"], "radius": c["radius"],
             "peta": dict(s["peta"]),
             "makhluk_lain": [self._creature_view(s, m, viewer == "semua") for m in sorted(others, key=lambda m: int(m["id"]))],
             "makanan": [unkey(k) + [f] for k, f in sorted(s["makanan"].items()) if not fog or k in content],
             "jebakan": traps, "terlihat": sorted(vis) if fog and isinstance(viewer, int) else None,
             "populasi": {nm: self._pop(s, i) for i, nm in enumerate(names)}, "skor": dict(zip(names, s["poin"])),
             "statistik": {nm: dict(s["stat"][i]) for i, nm in enumerate(names)},
             "sarang_semua": {nm: list(s["sarang"][i]) for i, nm in enumerate(names)},
             "rasio_mangsa": c["rasio_mangsa"], "maks_populasi": c["maks_populasi"], "poin_sifat": c["poin_sifat"],
             "kejadian": [dict(e) for e in s["kejadian"]] if not fog else []}
        if isinstance(viewer, int):
            v.update({"makhluk_saya": [self._creature_view(s, m, True) for m in sorted(mine, key=lambda m: int(m["id"]))],
                      "desain": dict(s["desain"][viewer]), "rintangan_sisa": s["rintangan_sisa"][viewer],
                      "sarang": list(s["sarang"][viewer])})
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def event_for(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"]["kabut"]:
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        if e.get("jenis") in ("punah", "bangkit", "akhir"):
            return e
        if me is not None and me in (e.get("pemilik"), e.get("korban_pemilik")):
            return e
        return None

    # ------------------------------------------------------------ aksi
    def pending(self, s):
        if self.over(s):
            return []
        return list(range(len(s["names"])))

    def _clean_design(self, s, d):
        if not isinstance(d, dict):
            raise ActionError("desain harus dict {'pandangan', 'kelincahan', 'ukuran'}")
        out = {}
        for k in SIFAT:
            v = as_int(d.get(k, 1), k)
            if not 1 <= v <= 9:
                raise ActionError(f"{k} harus 1 sampai 9")
            out[k] = v
        if sum(out.values()) > s["cfg"]["poin_sifat"]:
            raise ActionError(f"total sifat {sum(out.values())} melebihi poin sifat {s['cfg']['poin_sifat']}")
        return out

    def validate(self, s, p, a):
        if a is None:
            return {}
        if not isinstance(a, dict):
            raise ActionError("aksi harus dict (boleh kosong {})")
        out: dict[str, Any] = {}
        if "desain" in a and a["desain"] is not None:
            out["desain"] = self._clean_design(s, a["desain"])
        mine = {m["id"]: m for m in s["makhluk"].values() if m["pemilik"] == p}
        if isinstance(a.get("perintah"), dict):
            cmds = {}
            for cid, cmd in a["perintah"].items():
                cid = str(cid)
                if cid not in mine or not isinstance(cmd, dict):
                    continue
                mode = cmd.get("mode", "manual" if "jalan" in cmd else "tujuan" if "tujuan" in cmd else None)
                if mode not in MODE:
                    raise ActionError("mode harus naluri, tujuan, manual, atau diam")
                c: dict[str, Any] = {"mode": mode}
                if mode == "tujuan":
                    t = cmd.get("tujuan")
                    if not isinstance(t, (list, tuple)) or len(t) != 2:
                        raise ActionError("tujuan harus [q, r]")
                    t = [as_int(t[0], "q"), as_int(t[1], "r")]
                    if key(t) not in s["peta"]:
                        raise ActionError("tujuan di luar peta")
                    c["tujuan"] = t
                if "jalan" in cmd:
                    j = cmd["jalan"]
                    if isinstance(j, str):
                        j = [j]
                    if not isinstance(j, (list, tuple)) or any(x not in ARAH for x in j):
                        raise ActionError("jalan harus daftar arah: " + ", ".join(ARAH))
                    c["jalan"] = list(j)[: mine[cid]["kelincahan"]]
                cmds[cid] = c
            out["perintah"] = cmds
        if isinstance(a.get("beranak"), dict):
            out["beranak"] = {str(k): bool(v) for k, v in a["beranak"].items() if str(k) in mine}
        if isinstance(a.get("nama"), dict):
            out["nama"] = {str(k): " ".join(str(v).split())[:16] for k, v in a["nama"].items() if str(k) in mine and str(v).strip()}
        if a.get("pasang"):
            ps = a["pasang"]
            if not isinstance(ps, dict):
                raise ActionError("pasang harus {'makhluk', 'arah', 'jenis'}")
            cid = str(ps.get("makhluk"))
            if cid in mine:
                if ps.get("arah") not in ARAH or ps.get("jenis") not in ("batu", "duri"):
                    raise ActionError("pasang: arah harus nama arah, jenis harus 'batu' atau 'duri'")
                if s["rintangan_sisa"][p] <= 0:
                    raise ActionError("jatah rintanganmu habis")
                out["pasang"] = {"makhluk": cid, "arah": ps["arah"], "jenis": ps["jenis"]}
        return out

    def default(self, s, p):
        return {}

    # ------------------------------------------------------------ langkah
    def _bfs_path(self, s, start, goal, avoid: set[str], limit=None):
        if start == goal:
            return []
        gk = key(goal)
        prev = {key(start): None}
        q = deque([key(start)])
        while q:
            k = q.popleft()
            if k == gk:
                break
            c = unkey(k)
            for d in ARAH.values():
                nk = key(tambah(c, d))
                if nk in prev or nk not in s["peta"] or s["peta"][nk] == "#" or (nk in avoid and nk != gk):
                    continue
                prev[nk] = k
                q.append(nk)
        if gk not in prev:
            return None
        path = []
        k = gk
        while prev[k] is not None:
            path.append(unkey(k))
            k = prev[k]
        path.reverse()
        return path[:limit] if limit else path

    def _known_traps(self, s, p):
        """Jebakan yang diketahui berbahaya bagi pemain p (duri milik sendiri tidak melukai pemiliknya)."""
        return {k for k, t in s["jebakan"].items() if t["terbuka"] and t["oleh"] != p}

    def _bfs_all(self, s, start, avoid, maxd=12):
        dist = {key(start): 0}
        prev: dict[str, str | None] = {key(start): None}
        q = deque([key(start)])
        while q:
            k = q.popleft()
            if dist[k] >= maxd:
                continue
            c = unkey(k)
            for d in ARAH.values():
                nk = key(tambah(c, d))
                if nk in dist or nk not in s["peta"] or s["peta"][nk] == "#" or nk in avoid:
                    continue
                dist[nk] = dist[k] + 1
                prev[nk] = k
                q.append(nk)
        return dist, prev

    @staticmethod
    def _trace(prev, k):
        out = []
        while prev.get(k) is not None:
            out.append(unkey(k))
            k = prev[k]
        return list(reversed(out))

    def _instinct(self, s, m, content, avoid):
        """Naluri: kabur dari pemangsa dekat, kejar makanan/mangsa terbaik, atau menjelajah pelan."""
        p = m["pemilik"]
        ratio = s["cfg"]["rasio_mangsa"]
        pos = m["posisi"]
        others = [o for o in s["makhluk"].values() if o["pemilik"] != p and key(o["posisi"]) in content]
        threats = [o for o in others if o["ukuran"] >= ratio * m["ukuran"] and hex_dist(o["posisi"], pos) <= 3]
        A = m["kelincahan"]
        if threats:
            path, cur = [], list(pos)
            for _ in range(A):
                best, bd = None, min(hex_dist(cur, t["posisi"]) for t in threats)
                for a in URUT_ARAH:
                    nxt = tambah(cur, ARAH[a])
                    if not self._passable(s, nxt) or key(nxt) in avoid:
                        continue
                    dd = min(hex_dist(nxt, t["posisi"]) for t in threats)
                    if dd > bd:
                        best, bd = nxt, dd
                if best is None:
                    break
                path.append(best)
                cur = best
            return path
        dist, prev = self._bfs_all(s, pos, avoid)
        step_cost = biaya_langkah(m["ukuran"], A)
        best_k, best_score = None, 0.0
        cands = [(MAKANAN[f][0], k) for k, f in s["makanan"].items() if k in content]
        cands += [(min(o["energi"], 30) + 5 * o["ukuran"], key(o["posisi"])) for o in others if m["ukuran"] >= ratio * o["ukuran"]]
        for val, k in sorted(cands, key=lambda x: x[1]):
            if k not in dist or dist[k] == 0:
                continue
            score = (val - dist[k] * step_cost) / (dist[k] + 1)
            if score > best_score:
                best_k, best_score = k, score
        if best_k is not None:
            return self._trace(prev, best_k)[:A]
        # jelajah: menuju pojok peta bergiliran, setengah kecepatan supaya hemat energi
        R = s["cfg"]["radius"]
        corners = self._corners(R, 6)
        tgt = corners[(int(m["id"]) + s["giliran"] // 8) % 6]
        path = self._bfs_path(s, pos, tgt, avoid)
        return (path or [])[: max(1, A // 2)]

    def _plan(self, s, m, cmd, content, avoid):
        mode = m["mode"]
        if cmd and "jalan" in cmd:
            path, cur = [], list(m["posisi"])
            for a in cmd["jalan"][: m["kelincahan"]]:
                cur = tambah(cur, ARAH[a])
                path.append(cur)
            return path
        if mode == "diam" or mode == "manual":
            return []
        if mode == "tujuan" and m["tujuan"]:
            if m["posisi"] == m["tujuan"]:
                m["mode"], m["tujuan"] = "naluri", None
                return self._instinct(s, m, content, avoid)
            path = self._bfs_path(s, m["posisi"], m["tujuan"], avoid)
            return (path or [])[: m["kelincahan"]]
        return self._instinct(s, m, content, avoid)

    def _kill(self, s, m, sebab, events, oleh=None):
        names = s["names"]
        s["makhluk"].pop(m["id"], None)
        s["stat"][m["pemilik"]]["mati"] += 1
        k = key(m["posisi"])
        if sebab != "dimangsa" and k not in s["makanan"] and s["peta"].get(k) != "#":
            s["makanan"][k] = "daging"
        e = {"jenis": "mati", "pemilik": names[m["pemilik"]], "id": m["id"], "nama": m["nama"], "sebab": sebab,
             "posisi": list(m["posisi"])}
        if oleh is not None:
            e["oleh"] = names[oleh["pemilik"]]
            e["oleh_nama"] = oleh["nama"]
        events.append(e)

    def _eat_creature(self, s, eater, prey, events):
        gain = min(prey["energi"], 30) + 5 * prey["ukuran"]
        eater["energi"] = min(energi_maks(eater["ukuran"]), eater["energi"] + gain)
        s["poin"][eater["pemilik"]] += POIN_MANGSA
        s["stat"][eater["pemilik"]]["mangsa"] += 1
        names = s["names"]
        events.append({"jenis": "mangsa", "pemilik": names[eater["pemilik"]], "nama": eater["nama"], "id": eater["id"],
                       "korban_pemilik": names[prey["pemilik"]], "korban": prey["nama"], "posisi": list(prey["posisi"])})
        self._kill(s, prey, "dimangsa", events, oleh=eater)

    def apply(self, s, actions):
        c, names = s["cfg"], s["names"]
        events: list[dict[str, Any]] = []
        if s["fase"] == "desain":
            for p in range(len(names)):
                a = actions.get(p) or {}
                if "desain" in a:
                    s["desain"][p] = a["desain"]
                home = s["sarang"][p]
                spots = [home] + [tambah(home, ARAH[x]) for x in URUT_ARAH]
                spots = [x for x in spots if self._passable(s, x)]
                for k in range(c["populasi_awal"]):
                    self._spawn(s, p, spots[k % len(spots)], s["desain"][p], beranak=False)
            s["fase"] = "main"
            s["giliran"] = 1
            events.append({"jenis": "mulai", "desain": {names[p]: dict(s["desain"][p]) for p in range(len(names))}})
            s["kejadian"] = events[-10:]
            return events
        # 1. perintah & pengaturan
        cmds_all: dict[str, dict[str, Any]] = {}
        for p, a in actions.items():
            a = a or {}
            if "desain" in a:
                s["desain"][p] = a["desain"]
            for cid, cmd in (a.get("perintah") or {}).items():
                m = s["makhluk"].get(cid)
                if m is None or m["pemilik"] != p:
                    continue
                m["mode"] = cmd["mode"]
                m["tujuan"] = cmd.get("tujuan") if cmd["mode"] == "tujuan" else None
                cmds_all[cid] = cmd
            for cid, on in (a.get("beranak") or {}).items():
                m = s["makhluk"].get(cid)
                if m is not None and m["pemilik"] == p:
                    m["beranak"] = on
            for cid, nm in (a.get("nama") or {}).items():
                m = s["makhluk"].get(cid)
                if m is not None and m["pemilik"] == p:
                    m["nama"] = nm
            ps = a.get("pasang")
            if ps:
                m = s["makhluk"].get(ps["makhluk"])
                if m is not None and m["pemilik"] == p and s["rintangan_sisa"][p] > 0 and m["energi"] >= 10:
                    tgt = tambah(m["posisi"], ARAH[ps["arah"]])
                    k = key(tgt)
                    if k in s["peta"] and s["peta"][k] != "#" and self._occupant(s, tgt) is None and k not in s["jebakan"]:
                        m["energi"] -= 10
                        s["rintangan_sisa"][p] -= 1
                        if ps["jenis"] == "batu":
                            s["peta"][k] = "#"
                            s["makanan"].pop(k, None)
                        else:
                            s["jebakan"][k] = {"jenis": "duri", "oleh": p, "terbuka": False}
                        events.append({"jenis": "pasang", "pemilik": names[p], "rintangan": ps["jenis"],
                                       "posisi": tgt if ps["jenis"] == "batu" else None})
        # 2. rencana jalan
        vision = {p: self._vision(s, p)[1] if c["kabut"] else set(s["peta"]) for p in range(len(names))}
        paths: dict[str, list[list[int]]] = {}
        for cid, m in sorted(s["makhluk"].items(), key=lambda x: int(x[0])):
            avoid = self._known_traps(s, m["pemilik"])
            paths[cid] = self._plan(s, m, cmds_all.get(cid), vision[m["pemilik"]], avoid)
        # 3. gerak langkah demi langkah, urutan pemain bergiliran tiap giliran
        n = len(names)
        order = sorted(paths, key=lambda cid: ((s["makhluk"][cid]["pemilik"] - s["giliran"]) % n, int(cid)))
        ratio = c["rasio_mangsa"]
        for step in range(9):
            for cid in order:
                m = s["makhluk"].get(cid)
                path = paths.get(cid) or []
                if m is None or step >= len(path):
                    continue
                nxt = path[step]
                if hex_dist(nxt, m["posisi"]) != 1 or not self._passable(s, nxt):
                    paths[cid] = []
                    continue
                cost = biaya_langkah(m["ukuran"], m["kelincahan"])
                if m["energi"] < cost:
                    paths[cid] = []
                    continue
                occ = self._occupant(s, nxt)
                if occ is not None:
                    if occ["pemilik"] == m["pemilik"]:
                        paths[cid] = []
                        continue
                    if m["ukuran"] >= ratio * occ["ukuran"]:
                        m["energi"] -= cost
                        self._eat_creature(s, m, occ, events)
                        m["posisi"] = list(nxt)
                    elif occ["ukuran"] >= ratio * m["ukuran"]:
                        self._eat_creature(s, occ, m, events)
                        continue
                    else:
                        paths[cid] = []
                        continue
                else:
                    m["energi"] -= cost
                    m["posisi"] = list(nxt)
                k = key(nxt)
                f = s["makanan"].pop(k, None)
                if f:
                    en, pt = MAKANAN[f]
                    m["energi"] = min(energi_maks(m["ukuran"]), m["energi"] + en)
                    s["poin"][m["pemilik"]] += pt
                    s["stat"][m["pemilik"]]["makan"] += 1
                trap = s["jebakan"].get(k)
                if trap and trap["oleh"] != m["pemilik"]:
                    dmg = RUSAK_DURI if trap["jenis"] == "duri" else RUSAK_JEBAKAN
                    m["hp"] -= dmg
                    del s["jebakan"][k]
                    events.append({"jenis": "jebakan", "pemilik": names[m["pemilik"]], "id": m["id"], "nama": m["nama"],
                                   "rusak": dmg, "duri_milik": names[trap["oleh"]] if trap["oleh"] is not None else None,
                                   "korban_pemilik": names[trap["oleh"]] if trap["oleh"] is not None else None})
                    paths[cid] = []
                    if m["hp"] <= 0:
                        self._kill(s, m, "jebakan", events)
                if m.get("tujuan") == m["posisi"]:
                    m["mode"], m["tujuan"] = "naluri", None
        # 4. biaya hidup, lapar, sembuh
        for cid in sorted(list(s["makhluk"]), key=int):
            m = s["makhluk"].get(cid)
            if m is None:
                continue
            m["energi"] -= BIAYA_DASAR + BIAYA_PANDANG * m["pandangan"]
            hpm = hp_maks(m["ukuran"])
            if m["energi"] <= 0:
                m["energi"] = 0.0
                m["hp"] -= 2
            elif m["hp"] < hpm and m["energi"] >= energi_maks(m["ukuran"]) / 2:
                m["hp"] = min(hpm, m["hp"] + 1)
                m["energi"] -= 1.5
            m["energi"] = round(m["energi"], 3)
            if m["hp"] <= 0:
                self._kill(s, m, "lapar", events)
        # 5. beranak
        for cid in sorted(list(s["makhluk"]), key=int):
            m = s["makhluk"].get(cid)
            if m is None or not m["beranak"]:
                continue
            p = m["pemilik"]
            design = dict(s["desain"][p])
            cost = biaya_lahir(design["ukuran"])
            if self._pop(s, p) >= c["maks_populasi"] or m["energi"] < cost + 0.3 * energi_maks(m["ukuran"]):
                continue
            rot = int(cid) % 6
            spot = None
            for a in URUT_ARAH[rot:] + URUT_ARAH[:rot]:
                x = tambah(m["posisi"], ARAH[a])
                if self._passable(s, x) and self._occupant(s, x) is None and key(x) not in s["jebakan"]:
                    spot = x
                    break
            if spot is None:
                continue
            g = rng(s, "mutasi", s["giliran"], cid)
            mut = None
            if g.random() * 100 < c["mutasi"]:
                trait = g.choice(SIFAT)
                delta = g.choice((-1, 1))
                if 1 <= design[trait] + delta <= 9:
                    design[trait] += delta
                    mut = {"sifat": trait, "ubah": delta}
            m["energi"] -= cost
            child = self._spawn(s, p, spot, design, energy_frac=min(1.0, 0.7 * cost / energi_maks(design["ukuran"])),
                                parent=cid, beranak=m["beranak"])
            s["poin"][p] += POIN_LAHIR
            s["stat"][p]["lahir"] += 1
            events.append({"jenis": "lahir", "pemilik": names[p], "id": child["id"], "nama": child["nama"], "induk": m["nama"],
                           "sifat": {k: child[k] for k in SIFAT}, "mutasi": mut})
        # 6. punah & bangkit
        for p in range(n):
            if self._pop(s, p) == 0:
                if s["punah"][p] is None:
                    s["punah"][p] = s["giliran"]
                    events.append({"jenis": "punah", "pemilik": names[p]})
                elif c["bangkit"] and s["giliran"] - s["punah"][p] >= c["bangkit"]:
                    home = s["sarang"][p]
                    spot = next((x for x in [home] + [tambah(home, ARAH[a]) for a in URUT_ARAH]
                                 if self._passable(s, x) and self._occupant(s, x) is None), None)
                    if spot is not None:
                        self._spawn(s, p, spot, s["desain"][p], beranak=False)
                        s["punah"][p] = None
                        events.append({"jenis": "bangkit", "pemilik": names[p]})
            else:
                s["punah"][p] = None
        # 7. makanan tumbuh
        self._grow(s)
        s["giliran"] += 1
        if self.over(s):
            for m in s["makhluk"].values():
                s["poin"][m["pemilik"]] += POIN_HIDUP
            events.append({"jenis": "akhir", "hidup": {nm: self._pop(s, i) for i, nm in enumerate(names)}})
        s["kejadian"] = events[-12:]
        return events

    def _grow(self, s):
        c = s["cfg"]
        g = rng(s, "tumbuh", s["giliran"])
        total = len(s["peta"])
        k = c["makanan"]
        occupied = {key(m["posisi"]) for m in s["makhluk"].values()}
        empty = sorted(x for x, t in s["peta"].items() if t != "#" and x not in s["makanan"] and x not in occupied)
        if not empty:
            return
        for jenis, rate in (("rumput", 0.004), ("buah", 0.0015)):
            base = total * rate * k
            cnt = int(base) + (1 if g.random() < base - int(base) else 0)
            for _ in range(cnt):
                if not empty:
                    return
                x = empty.pop(g.randrange(len(empty)))
                s["makanan"][x] = jenis

    def over(self, s):
        if s["fase"] == "desain":
            return False
        if s["giliran"] > s["cfg"]["giliran"]:
            return True
        n = len(s["names"])
        alive = sum(1 for p in range(n) if self._pop(s, p) > 0)
        return n > 1 and alive <= 1 and not s["cfg"]["bangkit"]

    def scores(self, s):
        return [float(x) for x in s["poin"]]

    def tiebreak(self, s):
        return [float(self._pop(s, p)) for p in range(len(s["names"]))]

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        peta = obs["peta"]
        mine = {m["id"]: m for m in obs.get("makhluk_saya", [])}
        others = obs.get("makhluk_lain", [])
        ratio = obs["rasio_mangsa"]
        avoid = {key(t[:2]) for t in obs.get("jebakan", []) if not t[3]}      # duri milik sendiri aman

        def _pos(x):
            if not isinstance(x, (list, tuple)) or len(x) < 2:
                raise ActionError("petak harus [q, r]")
            return [as_int(x[0], "q"), as_int(x[1], "r")]

        def jarak(a, b):
            return hex_dist(_pos(a), _pos(b))

        def tetangga(c):
            c = _pos(c)
            return [tambah(c, d) for d in ARAH.values() if peta.get(key(tambah(c, d)), "#") != "#"]

        def arah_ke(a, b):
            a, b = _pos(a), _pos(b)
            for nm, d in ARAH.items():
                if tambah(a, d) == b:
                    return nm
            return None

        bfs_cache: dict[str, dict[str, str | None]] = {}

        def _bfs_dari(ka):
            """BFS penuh dari satu petak, disimpan per aksi: memanggil jalur() berulang dari petak yang sama tidak
            menghitung ulang (bot yang memanggilnya ribuan kali tidak membuat server tersendat). Jebakan boleh menjadi
            tujuan tetapi tidak dilewati, jadi hasilnya sama persis dengan BFS per tujuan."""
            if ka not in bfs_cache:
                if len(bfs_cache) >= MAKS_ASAL_JALUR:
                    raise ActionError(f"jalur() dihitung dari lebih dari {MAKS_ASAL_JALUR} petak awal berbeda dalam satu giliran")
                prev: dict[str, str | None] = {ka: None}
                q = deque([ka])
                while q:
                    k = q.popleft()
                    if k != ka and k in avoid:
                        continue
                    cc = unkey(k)
                    for d in ARAH.values():
                        nk = key(tambah(cc, d))
                        if nk in prev or peta.get(nk, "#") == "#":
                            continue
                        prev[nk] = k
                        q.append(nk)
                bfs_cache[ka] = prev
            return bfs_cache[ka]

        def jalur(a, b):
            a, b = _pos(a), _pos(b)
            if a == b:
                return []
            prev, kb = _bfs_dari(key(a)), key(b)
            if kb not in prev:
                return None
            out, k = [], kb
            while prev[k] is not None:
                out.append(unkey(k))
                k = prev[k]
            return list(reversed(out))

        def _get(cid):
            m = mine.get(str(cid))
            if m is None:
                raise ActionError(f"makhluk {cid!r} bukan milikmu atau sudah mati")
            return m

        def makanan_terdekat(cid):
            m = _get(cid)
            best = None
            for f in obs.get("makanan", []):
                j = jalur(m["posisi"], f[:2])
                if j is not None and (best is None or len(j) < best[0]):
                    best = (len(j), f)
            return list(best[1]) if best else None

        def _nearest(cid, pred):
            m = _get(cid)
            cands = [o for o in others if pred(m, o)]
            cands.sort(key=lambda o: (hex_dist(o["posisi"], m["posisi"]), int(o["id"])))
            return dict(cands[0]) if cands else None

        def bisa_beranak(cid):
            m = _get(cid)
            return m["energi"] >= m["biaya_lahir"] + 0.3 * m["energi_maks"]

        return {"makhluk_saya": lambda: [dict(m) for m in mine.values()], "jarak": jarak, "tetangga": tetangga, "arah_ke": arah_ke,
                "jalur": jalur, "makanan_terdekat": makanan_terdekat,
                "mangsa_terdekat": lambda cid: _nearest(cid, lambda m, o: m["ukuran"] >= ratio * o["ukuran"]),
                "ancaman_terdekat": lambda cid: _nearest(cid, lambda m, o: o["ukuran"] >= ratio * m["ukuran"]),
                "bisa_beranak": bisa_beranak}
