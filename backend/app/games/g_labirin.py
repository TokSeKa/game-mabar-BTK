"""Labirin Mabar: balapan keluar dari labirin yang sama, real-time (setiap pemain bergerak sendiri-sendiri).

Opsi pandangan: terang (seluruh labirin terlihat), kabut yang diingat (jalur yang pernah terlihat tetap terbuka di petamu),
dan kabut tanpa ingatan (hanya sekitar dirimu yang terlihat, jadi harus menghafal jalan). Kemampuan terbatas yang bisa
dilihat SEMUA pemain: tanda/gambar di petak (panah, silang, bintang, ...), tali (jejak jalanmu), dan suar (pandangan jauh
sebentar). Labirin, koin, jebakan, dan portal diacak dari seed match; bot tidak punya keacakan dan tidak punya ingatan
(kecuali yang terlihat di peta, tanda, dan talinya sendiri)."""

from __future__ import annotations

from collections import deque
from typing import Any

from .base import ActionError, Game, Setting, rng

ARAH = {"atas": (-1, 0), "bawah": (1, 0), "kiri": (0, -1), "kanan": (0, 1)}
BIT = {"atas": 1, "kanan": 2, "bawah": 4, "kiri": 8}
BALIK = {"atas": "bawah", "bawah": "atas", "kiri": "kanan", "kanan": "kiri"}
KANAN_DARI = {"atas": "kanan", "kanan": "bawah", "bawah": "kiri", "kiri": "atas"}
KIRI_DARI = {v: k for k, v in KANAN_DARI.items()}
SIMBOL = ["↑", "↓", "←", "→", "✖", "⭐", "❓", "💀"]
FINIS = [10, 7, 5, 4, 3, 2, 1, 1]
SUAR_LANGKAH = 6
SUAR_TAMBAH = 4


def buat_labirin(g, n: int, pintas: int) -> list[list[int]]:
    """Labirin sempurna (recursive backtracker) lalu sebagian tembok dalam dibuka (``pintas`` %) untuk jalan pintas.
    Nilai tiap petak = bit tembok yang MASIH ada: atas 1, kanan 2, bawah 4, kiri 8."""
    walls = [[15] * n for _ in range(n)]
    seen = [[False] * n for _ in range(n)]
    seen[0][0] = True
    stack = [(0, 0)]
    while stack:
        r, c = stack[-1]
        opts = [(a, r + dr, c + dc) for a, (dr, dc) in ARAH.items()
                if 0 <= r + dr < n and 0 <= c + dc < n and not seen[r + dr][c + dc]]
        if not opts:
            stack.pop()
            continue
        a, nr, nc = opts[g.randrange(len(opts))]
        walls[r][c] &= ~BIT[a]
        walls[nr][nc] &= ~BIT[BALIK[a]]
        seen[nr][nc] = True
        stack.append((nr, nc))
    inner = [(r, c, a) for r in range(n) for c in range(n) for a in ("kanan", "bawah")
             if ((a == "kanan" and c + 1 < n) or (a == "bawah" and r + 1 < n)) and walls[r][c] & BIT[a]]
    for r, c, a in g.sample(inner, len(inner) * pintas // 100):
        dr, dc = ARAH[a]
        walls[r][c] &= ~BIT[a]
        walls[r + dr][c + dc] &= ~BIT[BALIK[a]]
    return walls


def terbuka(walls, r, c, a) -> bool:
    return not walls[r][c] & BIT[a]


def jarak_dari(walls, start) -> dict[tuple[int, int], int]:
    n = len(walls)
    dist = {tuple(start): 0}
    q = deque([tuple(start)])
    while q:
        r, c = q.popleft()
        for a, (dr, dc) in ARAH.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and terbuka(walls, r, c, a) and (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                q.append((nr, nc))
    return dist


class Labirin(Game):
    id = "labirin"
    nama = "Labirin Mabar"
    ringkas = "Balapan keluar dari labirin yang sama secara real-time. Ada kabut, tanda, tali, suar, koin, jebakan, dan portal."
    kategori = "mandiri"
    mandiri = True
    min_pemain, max_pemain = 1, 8
    hint_aksi = "'atas', 'bawah', 'kiri', 'kanan', 'lari_kanan', 'diam', {'tanda': '✖'}, 'tali_on', 'tali_off', atau 'suar'"
    timer = 15
    jeda_pada, jeda_hasil = ("labirin",), 8
    label_skor = "Poin"
    settings = [
        Setting("ukuran", "Ukuran labirin", "int", 10, 6, 20, ket="Jumlah petak per sisi."),
        Setting("ronde", "Jumlah labirin", "int", 2, 1, 5),
        Setting("bot_kecepatan", "Kecepatan bot (langkah per detik)", "int", 3, 1, 10,
                ket="Bot bergerak paling cepat sekian langkah per detik, supaya balapan melawan manusia tetap adil."),
        Setting("batas_langkah", "Batas langkah per labirin", "int", 0, 0, 3000,
                ket="Tiap pemain punya jatah langkah per labirin. 0 = otomatis (3× jalur terpendek + 20)."),
        Setting("sisa_finis", "Sisa langkah setelah ada yang finis", "int", 30, 0, 500,
                ket="Begitu satu pemain keluar, yang lain hanya punya sekian langkah lagi. 0 = tidak dibatasi."),
        Setting("pandang", "Pandangan", "pilihan", "ingat", grup="informasi",
                pilihan=[["terang", "Terang: seluruh labirin terlihat"],
                         ["ingat", "Kabut, jalan yang pernah terlihat tetap terbuka di petamu"],
                         ["kabut", "Kabut tanpa ingatan: hanya sekitarmu yang terlihat (harus hafal jalan)"]]),
        Setting("jarak_pandang", "Jarak pandang (petak)", "int", 2, 1, 6, grup="informasi", jika={"pandang": ["ingat", "kabut"]},
                ket="Dihitung menyusuri lorong (tembok menghalangi pandangan)."),
        Setting("lawan_terlihat", "Posisi lawan", "pilihan", "dekat", grup="informasi", jika={"pandang": ["ingat", "kabut"]},
                pilihan=[["dekat", "Hanya kalau dalam jarak pandang"], ["semua", "Selalu terlihat"]]),
        Setting("kompas", "Pintu keluar terlihat dari awal", "bool", True, grup="informasi", jika={"pandang": ["ingat", "kabut"]},
                ket="Kalau mati, lokasi pintu keluar baru diketahui setelah terlihat."),
        Setting("tanda", "Jatah tanda / gambar", "int", 6, 0, 20, grup="aturan",
                ket="Tanda (panah, silang, bintang, tanya, tengkorak) di petakmu. Terlihat oleh SEMUA pemain di seluruh peta, "
                    "jadi bisa membantu... atau menyesatkan."),
        Setting("tali", "Panjang tali (petak)", "int", 40, 0, 300, grup="aturan",
                ket="Tali menggambar jejak jalanmu selama dinyalakan. Terlihat oleh semua pemain."),
        Setting("suar", "Jatah suar", "int", 1, 0, 5, grup="aturan",
                ket=f"Suar menambah jarak pandang +{SUAR_TAMBAH} selama {SUAR_LANGKAH} langkah."),
        Setting("pintas", "Jalan pintas (%)", "int", 8, 0, 40, grup="aturan",
                ket="Persentase tembok dalam yang dibuka, supaya ada lebih dari satu jalan. 0 = labirin sempurna (satu jalan)."),
        Setting("koin", "Koin di labirin", "int", 4, 0, 30, grup="kejutan", ket="Koin = +1 poin untuk yang pertama mengambil."),
        Setting("jebakan", "Jebakan tersembunyi", "int", 0, 0, 15, grup="kejutan",
                ket="Menginjak jebakan: −5 jatah langkah dan tertahan 3 detik. Jebakan yang sudah terinjak terlihat oleh semua dan tidak aktif lagi."),
        Setting("portal", "Pasangan portal", "int", 0, 0, 4, grup="kejutan",
                ket="Masuk satu portal langsung keluar di pasangannya."),
    ]
    presets = [
        {"id": "terang", "nama": "Terang", "ket": "Seluruh labirin terlihat: murni adu cepat membaca jalan.", "nilai": {"pandang": "terang"}},
        {"id": "hafalan", "nama": "Hafalan", "ket": "Kabut tanpa ingatan, pandangan 1 petak, lawan tidak terlihat, tanpa kompas.",
         "nilai": {"pandang": "kabut", "jarak_pandang": 1, "kompas": False}},
        {"id": "kacau", "nama": "Kacau", "ket": "Koin, jebakan, dan portal di mana-mana.", "nilai": {"koin": 10, "jebakan": 6, "portal": 3}},
    ]
    aturan = f"""
- Semua pemain mulai dari **pojok kiri atas** labirin yang sama dan berlomba ke **pintu keluar** 🚪 (petak terjauh dari awal).
- **Real-time:** setiap pemain bergerak sendiri-sendiri secepat mungkin, tidak menunggu yang lain.
  `atas/bawah/kiri/kanan` = 1 langkah, **lari** (`lari_kanan`, dst.) = terus menyusuri lorong sampai persimpangan, jalan buntu,
  atau benda. Menabrak tembok tidak diizinkan.
- Finis ke-1 sampai ke-8 mendapat **{' / '.join(map(str, FINIS))}** poin. **Koin** 🪙 = +1 poin untuk yang pertama mengambil.
- Setiap pemain punya **jatah langkah** per labirin (default 3× jalur terpendek + 20). Begitu ada yang finis, yang lain tinggal punya
  **30 langkah** lagi (bisa diatur host). Jatah habis = tidak finis di labirin itu.
- **Pandangan** (diatur host): *terang* (seluruh labirin terlihat), *kabut yang diingat* (jalan yang pernah terlihat tetap terbuka
  di petamu), atau *kabut tanpa ingatan* (hanya sekitarmu yang terlihat: hafalkan jalannya!). Pandangan menyusuri lorong, tembok
  menghalangi.
- Kemampuan terbatas, terlihat oleh **semua pemain**:
  - 📍 **Tanda / gambar** (↑ ↓ ← → ✖ ⭐ ❓ 💀) di petakmu, misalnya menandai jalan buntu. Pemain lain bisa memanfaatkannya… atau
    tertipu.
  - 🧵 **Tali**: selama menyala, jejak jalanmu tergambar (panjang terbatas). Berguna di kabut tanpa ingatan.
  - 🔦 **Suar**: jarak pandang +{SUAR_TAMBAH} selama {SUAR_LANGKAH} langkah.
- Opsi kejutan: koin, **jebakan** tersembunyi (−5 jatah langkah dan tertahan 3 detik), dan **portal** berpasangan.
- Satu match berisi beberapa labirin (default 2). Setelah setiap labirin, seluruh petanya dibuka. Poin terbanyak menang
  (seri: total langkah paling sedikit).
"""
    format_aksi = """Teks: `"atas"`, `"bawah"`, `"kiri"`, `"kanan"` (1 langkah), `"lari_atas"` dst. (menyusuri lorong),
`"diam"`, `"tali_on"`, `"tali_off"`, `"suar"`, atau dict `{"tanda": "✖"}` (simbol: """ + " ".join(SIMBOL) + ")."
    format_info = """```
{ "ronde": 1, "ronde_total": 2, "ukuran": 10, "pandang": "ingat", "jarak_pandang": 2,
  "peta": [[9, 5, None, ...], ...],      # peta[baris][kolom]: bit tembok (atas 1, kanan 2, bawah 4, kiri 8), None = belum terlihat
  "terlihat": [[0, 0], [0, 1], ...],    # petak yang terlihat SEKARANG (None kalau terang)
  "posisi": [0, 0], "arah_terakhir": "kanan", "keluar": [7, 9],   # keluar None kalau belum diketahui
  "langkah": 12, "sisa_langkah": 58, "selesai": False,
  "pemain": {"Budi": {"posisi": [3, 4], "selesai": False, "urutan": None, "langkah": 15, "sisa": 55, "tali_aktif": True}, ...},
  "tanda": [{"posisi": [2, 3], "simbol": "✖", "oleh": "Budi"}, ...],     # tanda semua pemain (selalu terlihat)
  "tali": {"Budi": [[0, 0], [0, 1], ...], ...},                       # jejak tali semua pemain (selalu terlihat)
  "koin": [[4, 4], ...], "jebakan": [[6, 2]], "portal": [[[1, 8], [8, 1]]],
  "tanda_sisa": 6, "tali_sisa": 40, "tali_aktif": False, "suar_sisa": 1, "suar_aktif": 0,
  "skor": {"Budi": 10, ...}, "riwayat": [ {"ronde": 1, "urutan": ["Ani", "Budi"], "poin": {...}, ...} ] }
```
- Baris 0 di atas, kolom 0 di kiri. Di kabut, posisi lawan `None` kalau tidak terlihat; koin dan portal hanya yang terlihat;
  jebakan hanya yang sudah terinjak."""
    lib_docs = [
        {"nama": "bisa_jalan", "jenis": "fungsi", "tanda": "bisa_jalan(arah)", "ket": "True kalau tidak ada tembok di arah itu dari posisimu."},
        {"nama": "jalan_terbuka", "jenis": "fungsi", "tanda": "jalan_terbuka()", "ket": "Daftar arah tanpa tembok dari posisimu."},
        {"nama": "jalur_ke", "jenis": "fungsi", "tanda": "jalur_ke(baris, kolom)", "ket": "Daftar arah jalur terpendek ke petak itu lewat petak yang sudah kamu ketahui, atau None."},
        {"nama": "langkah_ke", "jenis": "fungsi", "tanda": "langkah_ke(baris, kolom)", "ket": "Arah pertama jalur_ke(baris, kolom), atau None."},
        {"nama": "perbatasan", "jenis": "fungsi", "tanda": "perbatasan()", "ket": "Petak [baris, kolom] yang sudah diketahui dan tersambung ke petak yang belum terlihat, urut dari yang terdekat (jalur)."},
        {"nama": "tangan_kanan", "jenis": "fungsi", "tanda": "tangan_kanan()", "ket": "Arah menurut aturan tangan kanan (berdasarkan arah_terakhir): kanan, lurus, kiri, lalu balik."},
        {"nama": "tangan_kiri", "jenis": "fungsi", "tanda": "tangan_kiri()", "ket": "Seperti tangan_kanan() tapi menyusuri tembok kiri."},
        {"nama": "tanda_di", "jenis": "fungsi", "tanda": "tanda_di(baris, kolom)", "ket": "Simbol tanda di petak itu (tanda terbaru), atau None."},
        {"nama": "buntu", "jenis": "fungsi", "tanda": "buntu()", "ket": "True kalau posisimu jalan buntu (hanya satu arah terbuka)."},
    ]
    templates = [
        {"id": "tangan_kanan", "nama": "Tangan Kanan", "ket": "Menyusuri tembok kanan (selalu sampai di labirin sempurna). Langsung ke pintu keluar kalau jalannya sudah diketahui.", "kode": '''def aksi():
    i = info()
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
'''},
        {"id": "penjelajah", "nama": "Penjelajah", "ket": "Menuju petak perbatasan yang paling dekat ke pintu keluar; di kabut tanpa ingatan pakai tangan kiri.", "kode": '''def aksi():
    i = info()
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    if i["pandang"] == "kabut":
        return tangan_kiri()
    batas = perbatasan()
    if not batas:
        return tangan_kiri()
    if k == None:
        p = batas[0]
    else:
        p = min(batas[:8], key=lambda x: abs(x[0] - k[0]) + abs(x[1] - k[1]))
    a = langkah_ke(p[0], p[1])
    return a if a != None else tangan_kiri()
'''},
        {"id": "penanda_buntu", "nama": "Penanda Buntu", "ket": "Tangan kanan sambil memberi tanda ✖ di setiap jalan buntu (membantu semua pemain).", "kode": '''def aksi():
    i = info()
    p = i["posisi"]
    if buntu() and tanda_di(p[0], p[1]) == None and i["tanda_sisa"] > 0 and p != [0, 0]:
        return {"tanda": "✖"}
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
'''},
        {"id": "pemburu_koin", "nama": "Pemburu Koin", "ket": "Mengambil koin yang terlihat dulu, menyalakan tali, lalu mencari jalan keluar.", "kode": '''def aksi():
    i = info()
    if i["tali_sisa"] > 0 and not i["tali_aktif"] and i["langkah"] == 0:
        return "tali_on"
    terbaik = None
    for c in i["koin"]:
        j = jalur_ke(c[0], c[1])
        if j != None and (terbaik == None or len(j) < len(terbaik)):
            terbaik = j
    if terbaik != None and len(terbaik) > 0 and len(terbaik) <= 12:
        return terbaik[0]
    k = i["keluar"]
    if k != None:
        a = langkah_ke(k[0], k[1])
        if a != None:
            return a
    return tangan_kanan()
'''},
    ]

    # ------------------------------------------------------------ labirin baru
    def _new_round(self, s):
        c = s["cfg"]
        n = c["ukuran"]
        g = rng(s, "labirin", s["ronde"])
        walls = buat_labirin(g, n, c["pintas"])
        dist = jarak_dari(walls, (0, 0))
        far = max(dist.values())
        keluar = min(rc for rc, d in dist.items() if d == far)
        bebas = [[r, cc] for r in range(n) for cc in range(n) if (r, cc) != (0, 0) and (r, cc) != keluar and dist[(r, cc)] >= 2]
        g.shuffle(bebas)
        koin = sorted(bebas[: c["koin"]])
        sisa = bebas[c["koin"]:]
        jebakan = sorted(sisa[: c["jebakan"]])
        sisa = sisa[c["jebakan"]:]
        portal = [[sisa[2 * k], sisa[2 * k + 1]] for k in range(min(c["portal"], len(sisa) // 2))]
        names = s["names"]
        batas = c["batas_langkah"] or 3 * far + 20
        s["lab"] = {"walls": walls, "n": n, "keluar": list(keluar), "jalur": far, "koin": koin, "jebakan": jebakan,
                    "jebakan_kena": [], "portal": portal}
        k = len(names)
        s["pos"] = [[0, 0] for _ in range(k)]
        s["arah"] = [None] * k
        s["langkah"] = [0] * k
        s["batas"] = [batas] * k
        s["selesai"] = [False] * k
        s["urut"] = []
        s["koin_dapat"] = [0] * k
        s["poin_ronde"] = [0] * k
        s["tali_aktif"] = [False] * k
        s["tali"] = [[] for _ in range(k)]
        s["tali_sisa"] = [c["tali"]] * k
        s["tanda"] = []
        s["tanda_sisa"] = [c["tanda"]] * k
        s["suar_sisa"] = [c["suar"]] * k
        s["suar_aktif"] = [0] * k
        s["dikenal"] = [[0] * (n * n) for _ in range(k)]
        for p in range(k):
            self._remember(s, p)

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * len(names),
             "langkah_total": [0] * len(names), "riwayat": []}
        self._new_round(s)
        return s

    # ------------------------------------------------------------ pandangan
    def _radius(self, s, p):
        return s["cfg"]["jarak_pandang"] + (SUAR_TAMBAH if s["suar_aktif"][p] > 0 else 0)

    def _visible(self, s, p) -> set[tuple[int, int]]:
        lab = s["lab"]
        n = lab["n"]
        if s["cfg"]["pandang"] == "terang":
            return {(r, c) for r in range(n) for c in range(n)}
        rad = self._radius(s, p)
        walls = lab["walls"]
        start = tuple(s["pos"][p])
        seen = {start: 0}
        q = deque([start])
        while q:
            r, c = q.popleft()
            if seen[(r, c)] >= rad:
                continue
            for a, (dr, dc) in ARAH.items():
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and terbuka(walls, r, c, a) and (nr, nc) not in seen:
                    seen[(nr, nc)] = seen[(r, c)] + 1
                    q.append((nr, nc))
        return set(seen)

    def _remember(self, s, p):
        n = s["lab"]["n"]
        mem = s["dikenal"][p]
        for r, c in self._visible(s, p):
            mem[r * n + c] = 1

    def _known(self, s, viewer) -> set[tuple[int, int]]:
        lab = s["lab"]
        n = lab["n"]
        mode = s["cfg"]["pandang"]
        if viewer == "semua" or mode == "terang":
            return {(r, c) for r in range(n) for c in range(n)}
        if not isinstance(viewer, int):
            return set()
        if mode == "ingat":
            mem = s["dikenal"][viewer]
            return {(i // n, i % n) for i, x in enumerate(mem) if x}
        return self._visible(s, viewer)

    def _view(self, s, viewer):
        c, lab, names = s["cfg"], s["lab"], s["names"]
        n = lab["n"]
        known = self._known(s, viewer)
        open_all = viewer == "semua" or c["pandang"] == "terang"
        now = known if open_all or not isinstance(viewer, int) else self._visible(s, viewer)
        peta = [[lab["walls"][r][cc] if (r, cc) in known else None for cc in range(n)] for r in range(n)]
        pemain = {}
        for i, nm in enumerate(names):
            see = open_all or viewer == i or c["lawan_terlihat"] == "semua" or tuple(s["pos"][i]) in now
            pemain[nm] = {"posisi": list(s["pos"][i]) if see else None, "selesai": s["selesai"][i],
                          "urutan": s["urut"].index(i) + 1 if i in s["urut"] else None, "langkah": s["langkah"][i],
                          "sisa": max(0, s["batas"][i] - s["langkah"][i]), "koin": s["koin_dapat"][i], "tali_aktif": s["tali_aktif"][i]}
        keluar = lab["keluar"] if open_all or c["kompas"] or tuple(lab["keluar"]) in known else None
        v = {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "ukuran": n, "pandang": c["pandang"],
             "jarak_pandang": c["jarak_pandang"], "peta": peta, "keluar": keluar, "jalur_terpendek": lab["jalur"] if open_all else None,
             "pemain": pemain,
             "tanda": [dict(t) for t in s["tanda"]],
             "tali": {nm: [list(x) for x in s["tali"][i]] for i, nm in enumerate(names)},
             "koin": [list(x) for x in lab["koin"] if tuple(x) in now],
             "jebakan": [list(x) for x in lab["jebakan_kena"]] + ([list(x) for x in lab["jebakan"]] if viewer == "semua" else []),
             "portal": [[list(a), list(b)] for a, b in lab["portal"] if open_all or tuple(a) in known or tuple(b) in known],
             "skor": dict(zip(names, s["skor"])), "riwayat": [dict(e) for e in s["riwayat"]],
             "maks_tanda": c["tanda"], "maks_tali": c["tali"], "simbol": list(SIMBOL)}
        if isinstance(viewer, int):
            p = viewer
            v.update({"terlihat": None if open_all else sorted([list(x) for x in now]),
                      "posisi": list(s["pos"][p]), "arah_terakhir": s["arah"][p], "langkah": s["langkah"][p],
                      "sisa_langkah": max(0, s["batas"][p] - s["langkah"][p]), "selesai": s["selesai"][p],
                      "tanda_sisa": s["tanda_sisa"][p], "tali_sisa": s["tali_sisa"][p], "tali_aktif": s["tali_aktif"][p],
                      "suar_sisa": s["suar_sisa"][p], "suar_aktif": s["suar_aktif"][p]})
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def event_for(self, s, e, viewer):
        if viewer == "semua" or s["cfg"]["pandang"] == "terang":
            return e
        j = e.get("jenis")
        mine = isinstance(viewer, int) and s["names"][viewer] == e.get("pemain")
        if j == "gerak":
            return e if mine else None
        if j in ("koin", "portal") and not mine:
            return {k: v for k, v in e.items() if k not in ("posisi", "dari", "ke")}
        return e

    # ------------------------------------------------------------ aksi
    def pending(self, s):
        if self.over(s):
            return []
        return [p for p in range(len(s["names"])) if not s["selesai"][p] and s["langkah"][p] < s["batas"][p]]

    def validate(self, s, p, a):
        walls = s["lab"]["walls"]
        r, c = s["pos"][p]
        if isinstance(a, dict):
            if "tanda" in a:
                sim = a["tanda"]
                if sim not in SIMBOL:
                    raise ActionError("simbol tanda harus salah satu dari " + " ".join(SIMBOL))
                if s["tanda_sisa"][p] <= 0:
                    raise ActionError("jatah tandamu sudah habis")
                return "tanda:" + sim
            if "lari" in a:
                a = "lari_" + str(a["lari"])
            elif "gerak" in a:
                a = str(a["gerak"])
            elif "tali" in a:
                a = "tali_on" if a["tali"] else "tali_off"
            else:
                raise ActionError("aksi tidak dikenal")
        if a is None:
            return "diam"
        if not isinstance(a, str):
            raise ActionError("aksi harus teks, misalnya 'kanan'")
        a = a.strip().lower()
        if a in ("diam", "tunggu", ""):
            return "diam"
        if a.startswith("tanda:") and a[6:] in SIMBOL:
            return self.validate(s, p, {"tanda": a[6:]})
        if a in ("tali", "tali_on", "tali_off"):
            on = (not s["tali_aktif"][p]) if a == "tali" else a == "tali_on"
            if on and s["tali_sisa"][p] <= 0:
                raise ActionError("talimu sudah habis")
            return "tali_on" if on else "tali_off"
        if a == "suar":
            if s["suar_sisa"][p] <= 0:
                raise ActionError("suarmu sudah habis")
            return "suar"
        lari = a.startswith("lari_") or a.startswith("lari ")
        arah = a[5:] if lari else a
        if arah not in ARAH:
            raise ActionError("arah harus atas, bawah, kiri, atau kanan")
        if not terbuka(walls, r, c, arah):
            raise ActionError(f"ada tembok di arah {arah}")
        return ("lari_" if lari else "") + arah

    def default(self, s, p):
        return "diam"

    def _step(self, s, p, arah, events):
        """Satu langkah ke ``arah`` (sudah pasti tidak menabrak tembok). True kalau ada kejadian (berhenti lari)."""
        lab, names, c = s["lab"], s["names"], s["cfg"]
        dr, dc = ARAH[arah]
        r, cc = s["pos"][p]
        s["pos"][p] = [r + dr, cc + dc]
        s["arah"][p] = arah
        s["langkah"][p] += 1
        s["langkah_total"][p] += 1
        if s["suar_aktif"][p] > 0:
            s["suar_aktif"][p] -= 1
        stop = False
        pos = s["pos"][p]
        if s["tali_aktif"][p] and s["tali_sisa"][p] > 0:
            if not s["tali"][p]:
                s["tali"][p].append([r, cc])
            s["tali"][p].append(list(pos))
            s["tali_sisa"][p] -= 1
            if s["tali_sisa"][p] <= 0:
                s["tali_aktif"][p] = False
                events.append({"jenis": "tali", "pemain": names[p], "aktif": False, "habis": True})
        if pos in lab["koin"]:
            lab["koin"].remove(pos)
            s["koin_dapat"][p] += 1
            s["skor"][p] += 1
            s["poin_ronde"][p] += 1
            events.append({"jenis": "koin", "pemain": names[p], "posisi": list(pos)})
            stop = True
        if pos in lab["jebakan"]:
            lab["jebakan"].remove(pos)
            lab["jebakan_kena"].append(list(pos))
            s["langkah"][p] += 5
            events.append({"jenis": "jebakan", "pemain": names[p], "posisi": list(pos), "hukuman": 5})
            stop = True
        for a_, b_ in lab["portal"]:
            if pos == a_ or pos == b_:
                dest = b_ if pos == a_ else a_
                events.append({"jenis": "portal", "pemain": names[p], "dari": list(pos), "ke": list(dest)})
                s["pos"][p] = list(dest)
                pos = s["pos"][p]
                if s["tali_aktif"][p] and s["tali_sisa"][p] > 0:
                    s["tali"][p].append(list(dest))
                stop = True
                break
        if pos == lab["keluar"]:
            k = len(s["urut"])
            pts = FINIS[min(k, len(FINIS) - 1)]
            s["urut"].append(p)
            s["selesai"][p] = True
            s["skor"][p] += pts
            s["poin_ronde"][p] += pts
            events.append({"jenis": "finis", "pemain": names[p], "urutan": k + 1, "poin": pts, "langkah": s["langkah"][p]})
            if k == 0 and c["sisa_finis"] > 0:
                for q in range(len(names)):
                    if not s["selesai"][q]:
                        s["batas"][q] = min(s["batas"][q], s["langkah"][q] + c["sisa_finis"])
            stop = True
        self._remember(s, p)
        return stop

    def _corridor_next(self, s, p, arah):
        """Arah lanjutan saat lari: hanya kalau petak sekarang lorong (tepat satu jalan selain arah datang)."""
        walls = s["lab"]["walls"]
        r, c = s["pos"][p]
        opts = [a for a in ARAH if a != BALIK[arah] and terbuka(walls, r, c, a)]
        return opts[0] if len(opts) == 1 else None

    def apply(self, s, actions):
        events: list[dict[str, Any]] = []
        names = s["names"]
        for p, a in actions.items():
            if self.over(s) or s["selesai"][p] or s["langkah"][p] >= s["batas"][p]:
                continue
            if a == "diam":
                s["langkah"][p] += 1
                s["langkah_total"][p] += 1
            elif a.startswith("tanda:"):
                sim = a[6:]
                pos = list(s["pos"][p])
                s["tanda"] = [t for t in s["tanda"] if not (t["posisi"] == pos and t["oleh"] == names[p])]
                s["tanda"].append({"posisi": pos, "simbol": sim, "oleh": names[p]})
                s["tanda_sisa"][p] -= 1
                events.append({"jenis": "tanda", "pemain": names[p], "posisi": pos, "simbol": sim})
            elif a in ("tali_on", "tali_off"):
                s["tali_aktif"][p] = a == "tali_on"
                events.append({"jenis": "tali", "pemain": names[p], "aktif": a == "tali_on"})
            elif a == "suar":
                s["suar_sisa"][p] -= 1
                s["suar_aktif"][p] = SUAR_LANGKAH
                self._remember(s, p)
                events.append({"jenis": "suar", "pemain": names[p]})
            else:
                lari = a.startswith("lari_")
                arah = a[5:] if lari else a
                start = list(s["pos"][p])
                n = 0
                while True:
                    if not terbuka(s["lab"]["walls"], s["pos"][p][0], s["pos"][p][1], arah):
                        break
                    stop = self._step(s, p, arah, events)
                    n += 1
                    if stop or not lari or s["langkah"][p] >= s["batas"][p]:
                        break
                    nxt = self._corridor_next(s, p, arah)
                    if nxt is None:
                        break
                    arah = nxt
                events.insert(0, {"jenis": "gerak", "pemain": names[p], "dari": start, "ke": list(s["pos"][p]), "langkah": n})
        if not self.over(s) and not self.pending(s):
            events += self._end_round(s)
        return events

    def cooldown(self, s, p, events):
        return 3.0 if any(e.get("jenis") == "jebakan" and e.get("pemain") == s["names"][p] for e in events) else 0.0

    def jeda_bot(self, cfg):
        return 1.0 / max(1, cfg.get("bot_kecepatan", 3))

    def _end_round(self, s):
        names, lab = s["names"], s["lab"]
        entry = {"ronde": s["ronde"], "urutan": [names[i] for i in s["urut"]],
                 "poin": {names[i]: s["poin_ronde"][i] for i in range(len(names))},
                 "langkah": {names[i]: s["langkah"][i] for i in range(len(names))},
                 "koin": {names[i]: s["koin_dapat"][i] for i in range(len(names))},
                 "jalur_terpendek": lab["jalur"], "ukuran": lab["n"], "peta": [list(row) for row in lab["walls"]],
                 "keluar": list(lab["keluar"]), "tali": {names[i]: [list(x) for x in s["tali"][i]] for i in range(len(names))},
                 "tanda": [dict(t) for t in s["tanda"]]}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "labirin", **{k: v for k, v in entry.items() if k not in ("peta", "tali", "tanda")}}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [-float(x) for x in s["langkah_total"]]

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        peta = obs["peta"]
        n = obs["ukuran"]
        me = tuple(obs["posisi"])

        def ok(r, c, a):
            w = peta[r][c]
            if w is None or w & BIT[a]:
                return False
            dr, dc = ARAH[a]
            nr, nc = r + dr, c + dc
            return 0 <= nr < n and 0 <= nc < n and peta[nr][nc] is not None

        def _bfs():
            prev = {me: None}
            q = deque([me])
            while q:
                r, c = q.popleft()
                for a, (dr, dc) in ARAH.items():
                    nxt = (r + dr, c + dc)
                    if nxt not in prev and ok(r, c, a):
                        prev[nxt] = (r, c, a)
                        q.append(nxt)
            return prev

        cache: dict[str, Any] = {}

        def prev_map():
            if "prev" not in cache:
                cache["prev"] = _bfs()
            return cache["prev"]

        def jalur_ke(baris, kolom):
            tgt = (int(baris), int(kolom))
            prev = prev_map()
            if tgt not in prev:
                return None
            out = []
            cur = tgt
            while prev[cur] is not None:
                r, c, a = prev[cur]
                out.append(a)
                cur = (r, c)
            return list(reversed(out))

        def langkah_ke(baris, kolom):
            j = jalur_ke(baris, kolom)
            return j[0] if j else None

        def bisa_jalan(arah):
            w = peta[me[0]][me[1]]
            return arah in ARAH and w is not None and not w & BIT[arah]

        def jalan_terbuka():
            return [a for a in ARAH if bisa_jalan(a)]

        def perbatasan():
            prev = prev_map()
            out = []
            for (r, c) in prev:
                w = peta[r][c]
                for a, (dr, dc) in ARAH.items():
                    nr, nc = r + dr, c + dc
                    if not w & BIT[a] and 0 <= nr < n and 0 <= nc < n and peta[nr][nc] is None:
                        out.append((len(jalur_ke(r, c)), r, c))
                        break
            return [[r, c] for _, r, c in sorted(out)]

        def _hand(turn):
            last = obs.get("arah_terakhir") or "kanan"
            for a in (turn[last], last, {v: k for k, v in turn.items()}[last], BALIK[last]):
                if bisa_jalan(a):
                    return a
            return "diam"

        def tanda_di(baris, kolom):
            hit = [t["simbol"] for t in obs["tanda"] if t["posisi"] == [int(baris), int(kolom)]]
            return hit[-1] if hit else None

        return {"jalur_ke": jalur_ke, "langkah_ke": langkah_ke, "bisa_jalan": bisa_jalan, "jalan_terbuka": jalan_terbuka,
                "perbatasan": perbatasan, "tangan_kanan": lambda: _hand(KANAN_DARI), "tangan_kiri": lambda: _hand(KIRI_DARI),
                "tanda_di": tanda_di, "buntu": lambda: len(jalan_terbuka()) == 1}
