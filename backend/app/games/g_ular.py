"""Ular Mabar: snake multiplayer real-time. Semua ular bergerak bersamaan setiap detak; tidak boleh saling timpa.

Server melangkah sendiri setiap detak (``detak()``); pemain manusia mengirim arah kapan saja, bot berpikir tiap detak.
Buah, rintangan, dan titik bangkit diacak dari seed match, jadi match tetap bisa diulang persis dari seed + aksi.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from .base import ActionError, Game, Setting, rng

ARAH = {"atas": (0, -1), "bawah": (0, 1), "kiri": (-1, 0), "kanan": (1, 0)}
BALIK = {"atas": "bawah", "bawah": "atas", "kiri": "kanan", "kanan": "kiri"}
ALIAS = {"u": "atas", "up": "atas", "w": "atas", "d": "bawah", "down": "bawah", "s": "bawah",
         "l": "kiri", "left": "kiri", "a": "kiri", "r": "kanan", "right": "kanan"}
BUAH = {"apel": {"poin": 1, "tumbuh": 1}, "emas": {"poin": 3, "tumbuh": 2}, "busuk": {"poin": -2, "tumbuh": -2}}
HITUNG_MUNDUR = 3          # detik diam sebelum ronde mulai
PANJANG_AWAL = 3


class UlarMabar(Game):
    id = "ular"
    nama = "Ular Mabar"
    ringkas = "Snake real-time rame-rame: makan buah, jadi paling panjang, dan jangan menabrak ular lain (tidak boleh saling timpa)."
    kategori = "tick"
    min_pemain = 1
    max_pemain = 8
    hint_aksi = '"atas", "bawah", "kiri", "kanan", atau None (tetap lurus)'
    timer = 30
    jeda_pada, jeda_hasil = ("ronde_selesai",), 6
    label_skor = "Poin"
    max_frames = 900
    bot_langkah = 4000
    settings = [
        Setting("kecepatan", "Kecepatan (langkah per detik)", "int", 6, 3, 12),
        Setting("durasi", "Lama satu ronde (detik)", "int", 90, 20, 300),
        Setting("ronde", "Jumlah ronde", "int", 2, 1, 6),
        Setting("ukuran", "Ukuran arena", "int", 0, 0, 40,
                ket="0 = otomatis menurut jumlah pemain (16 untuk sendiri, sampai 34 untuk 8 pemain)."),
        Setting("tabrakan", "Kalau menabrak", "pilihan", "bangkit", grup="aturan",
                pilihan=[["bangkit", "Bangkit lagi 2 detik kemudian dengan panjang 3 (−3 poin)"],
                         ["habis", "Keluar dari ronde (yang bertahan paling lama menang ronde)"]]),
        Setting("adu_kepala", "Adu kepala", "pilihan", "keduanya", grup="aturan",
                pilihan=[["keduanya", "Dua kepala bertemu: keduanya tumbang"],
                         ["panjang", "Ular yang lebih panjang menang (sama panjang: keduanya tumbang)"]]),
        Setting("buah", "Jumlah buah di arena", "int", 0, 0, 20, grup="aturan",
                ket="0 = otomatis (jumlah pemain + 2)."),
        Setting("tembus_tepi", "Tepi arena tembus", "bool", False, grup="aturan",
                ket="Keluar di tepi kanan muncul di tepi kiri (dan sebaliknya), jadi tepi tidak mematikan."),
        Setting("rintangan", "Rintangan", "pilihan", "sedikit", grup="kejutan",
                pilihan=[["kosong", "Tanpa rintangan"], ["sedikit", "Beberapa tembok pendek"], ["banyak", "Banyak tembok (arena sempit)"]]),
        Setting("buah_emas", "Buah emas (+3, tumbuh 2)", "bool", True, grup="kejutan"),
        Setting("buah_busuk", "Buah busuk (−2, menyusut 2)", "bool", False, grup="kejutan",
                ket="Warnanya mirip apel tapi lebih gelap. Hati-hati!"),
        Setting("bangkai_jadi_buah", "Badan ular yang tumbang jadi buah", "bool", True, grup="kejutan"),
    ]
    presets = [
        {"id": "arena", "nama": "Gladiator", "ket": "Tabrakan = keluar ronde, adu kepala dimenangkan yang panjang, tembok banyak.",
         "nilai": {"tabrakan": "habis", "adu_kepala": "panjang", "rintangan": "banyak"}},
        {"id": "santai", "nama": "Santai", "ket": "Tepi tembus, tanpa rintangan, buah emas.",
         "nilai": {"tembus_tepi": True, "rintangan": "kosong"}},
        {"id": "jebakan", "nama": "Jebakan", "ket": "Ada buah busuk dan tembok banyak.",
         "nilai": {"buah_busuk": True, "rintangan": "banyak"}},
    ]
    aturan = """
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
"""
    format_aksi = '`"atas"`, `"bawah"`, `"kiri"`, `"kanan"` (arah baru), atau `None` = tetap lurus. Berbalik 180° diabaikan.'
    format_info = """```
{ "ukuran": 24, "ronde": 1, "ronde_total": 2, "detak": 120, "sisa_detak": 420, "kecepatan": 6, "mulai_dalam": 0,
  "tembus_tepi": False, "dinding": [[x, y], ...], "buah": [[x, y, "apel"], ...],
  "ular": {"Budi": {"badan": [[x, y], ...] (kepala dulu), "arah": "kanan", "hidup": True, "bangkit_dalam": 0,
                    "panjang": 5, "skor": 4}, ...} }
```
Koordinat: `x` ke kanan, `y` ke bawah, mulai dari 0."""
    lib_docs = [
        {"nama": "kepala", "jenis": "fungsi", "tanda": "kepala()", "ket": "[x, y] kepala ularmu (None kalau sedang tumbang)."},
        {"nama": "arah_sekarang", "jenis": "fungsi", "tanda": "arah_sekarang()", "ket": "Arah gerak ularmu sekarang."},
        {"nama": "aman", "jenis": "fungsi", "tanda": "aman(arah)", "ket": "True kalau petak berikutnya ke arah itu kosong (bukan tembok/badan/tepi). Tidak menebak gerakan kepala lawan."},
        {"nama": "ruang", "jenis": "fungsi", "tanda": "ruang(arah)", "ket": "Berapa petak kosong yang bisa dijangkau setelah melangkah ke arah itu (0 = buntu). Bagus untuk menghindari jebakan."},
        {"nama": "jalur_ke", "jenis": "fungsi", "tanda": "jalur_ke(x, y)", "ket": "Arah pertama jalur terpendek menuju petak (x, y), atau None kalau tidak terjangkau."},
        {"nama": "jarak_ke", "jenis": "fungsi", "tanda": "jarak_ke(x, y)", "ket": "Panjang jalur terpendek dari kepalamu ke (x, y), atau None."},
        {"nama": "buah_terdekat", "jenis": "fungsi", "tanda": "buah_terdekat()", "ket": "[x, y, jenis] buah bagus (bukan busuk) dengan jalur terpendek, atau None."},
        {"nama": "dekat_kepala_lawan", "jenis": "fungsi", "tanda": "dekat_kepala_lawan(arah)", "ket": "True kalau petak tujuan bersebelahan dengan kepala ular lain (rawan adu kepala)."},
    ]
    templates = [
        {"id": "rakus", "nama": "Si Rakus", "ket": "Mengejar buah terdekat lewat jalur terpendek; kalau tidak ada, cari arah yang aman.", "kode": '''def aksi():
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
'''},
        {"id": "penjaga_ruang", "nama": "Penjaga Ruang", "ket": "Selalu memilih arah dengan ruang terluas; buah dikejar kalau ruangnya cukup dan tidak dekat kepala lawan.", "kode": '''def aksi():
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
'''},
        {"id": "pemburu", "nama": "Pemburu", "ket": "Agresif: kalau lebih panjang dari lawan terdekat, mengincar petak di depan kepalanya; selain itu makan buah.", "kode": '''def aksi():
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
'''},
    ]

    # ------------------------------------------------------------ util
    def detak(self, cfg):
        return 1.0 / max(1, int(cfg.get("kecepatan", 6)))

    def _size(self, cfg, n):
        return int(cfg["ukuran"]) if cfg["ukuran"] >= 10 else min(34, 14 + 3 * n - (1 if n == 1 else 0) + 2)

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * n, "riwayat": [],
             "makan_total": [0] * n, "tumbang_total": [0] * n, "ukuran": self._size(cfg, n), "t_total": 0}
        self._new_round(s)
        return s

    def _ticks(self, s, detik):
        return int(round(detik * s["cfg"]["kecepatan"]))

    def _new_round(self, s):
        c, n, N = s["cfg"], len(s["names"]), s["ukuran"]
        s["t"] = 0
        s["mulai"] = self._ticks(s, HITUNG_MUNDUR)
        s["akhir"] = s["mulai"] + self._ticks(s, c["durasi"])
        s["dinding"] = self._walls(s)
        walls = {tuple(w) for w in s["dinding"]}
        s["ular"], s["buah"] = [], []
        for i in range(n):
            body, arah = self._spawn_spot(s, i, n, walls)
            s["ular"].append({"badan": body, "arah": arah, "hidup": True, "bangkit": 0, "tumbuh": 0, "keluar": False,
                              "mati_t": None})
        self._fill_fruit(s)

    def _walls(self, s):
        c, N = s["cfg"], s["ukuran"]
        mode = c["rintangan"]
        if mode == "kosong":
            return []
        r = rng(s, "tembok", s["ronde"])
        count = (N // 6) if mode == "sedikit" else (N // 3)
        cells: set[tuple[int, int]] = set()
        cx = cy = N / 2
        for _ in range(count):
            for _try in range(20):
                ln = r.randint(3, max(3, N // 4))
                horiz = r.random() < 0.5
                x, y = r.randint(2, N - 3), r.randint(2, N - 3)
                seg = [(x + k, y) if horiz else (x, y + k) for k in range(ln)]
                if any(not (1 < a < N - 2 and 1 < b < N - 2) for a, b in seg):
                    continue
                # jauhkan dari titik lahir (lingkaran di sekitar tengah) supaya awal ronde adil
                if any(abs(((a - cx) ** 2 + (b - cy) ** 2) ** 0.5 - N * 0.36) < 2.5 for a, b in seg):
                    continue
                cells |= set(seg)
                break
        return [list(p) for p in sorted(cells)]

    def _spawn_spot(self, s, i, n, walls):
        """Titik lahir awal ronde: melingkar di sekitar tengah arena, menghadap searah jarum jam (adil untuk semua)."""
        import math
        N = s["ukuran"]
        ang = 2 * math.pi * i / max(1, n) + (rng(s, "putar", s["ronde"]).random() * 2 * math.pi)
        rad = N * 0.36
        cx, cy = (N - 1) / 2, (N - 1) / 2
        hx, hy = int(round(cx + rad * math.cos(ang))), int(round(cy + rad * math.sin(ang)))
        # arah tegak lurus jari-jari (searah jarum jam)
        dx, dy = -math.sin(ang), math.cos(ang)
        arah = ("kanan" if dx > 0 else "kiri") if abs(dx) >= abs(dy) else ("bawah" if dy > 0 else "atas")
        ddx, ddy = ARAH[arah]
        body = [[hx - ddx * k, hy - ddy * k] for k in range(PANJANG_AWAL)]
        if all(0 <= x < N and 0 <= y < N and (x, y) not in walls for x, y in body):
            return body, arah
        return self._free_spot(s, ("lahir", i), {tuple(w) for w in walls})

    def _occupied(self, s):
        occ: dict[tuple[int, int], int] = {}
        for i, u in enumerate(s["ular"]):
            if u["hidup"]:
                for x, y in u["badan"]:
                    occ[(x, y)] = i
        return occ

    def _free_spot(self, s, key, walls=None):
        """Petak acak (dari seed) dengan ruang lurus 3 petak untuk bangkit."""
        N = s["ukuran"]
        walls = walls if walls is not None else {tuple(w) for w in s["dinding"]}
        occ = self._occupied(s) if "ular" in s else {}
        fruit = {(b[0], b[1]) for b in s.get("buah", [])}
        r = rng(s, "bangkit", s["ronde"], s["t"], *key) if isinstance(key, tuple) else rng(s, "bangkit", s["ronde"], s["t"], key)
        heads = [tuple(u["badan"][0]) for u in s.get("ular", []) if u["hidup"] and u["badan"]]
        for _ in range(400):
            x, y = r.randint(2, N - 3), r.randint(2, N - 3)
            arah = r.choice(["atas", "bawah", "kiri", "kanan"])
            dx, dy = ARAH[arah]
            body = [[x - dx * k, y - dy * k] for k in range(PANJANG_AWAL)]
            ahead = [(x + dx * k, y + dy * k) for k in range(1, 4)]
            cells = [tuple(b) for b in body] + ahead
            if any(not (0 <= a < N and 0 <= b < N) or (a, b) in walls or (a, b) in occ or (a, b) in fruit for a, b in cells):
                continue
            if any(abs(a - hx) + abs(b - hy) < 4 for hx, hy in heads for a, b in cells):
                continue
            return body, arah
        return [[N // 2, N // 2], [N // 2 - 1, N // 2], [N // 2 - 2, N // 2]], "kanan"

    def _fruit_target(self, s):
        c = s["cfg"]
        return c["buah"] if c["buah"] > 0 else len(s["names"]) + 2

    def _fill_fruit(self, s):
        c, N = s["cfg"], s["ukuran"]
        walls = {tuple(w) for w in s["dinding"]}
        occ = self._occupied(s)
        have = {(b[0], b[1]) for b in s["buah"]}
        r = rng(s, "buah", s["ronde"], s["t"])
        k = 0
        while sum(1 for b in s["buah"] if b[2] != "busuk") < self._fruit_target(s) and k < 500:
            k += 1
            x, y = r.randrange(N), r.randrange(N)
            if (x, y) in walls or (x, y) in occ or (x, y) in have:
                continue
            roll = r.random()
            jenis = "emas" if c["buah_emas"] and roll < 0.12 else "apel"
            s["buah"].append([x, y, jenis])
            have.add((x, y))
            if c["buah_busuk"] and r.random() < 0.35:
                for _t in range(20):
                    bx, by = r.randrange(N), r.randrange(N)
                    if (bx, by) not in walls and (bx, by) not in occ and (bx, by) not in have:
                        s["buah"].append([bx, by, "busuk"])
                        have.add((bx, by))
                        break
        busuk = [b for b in s["buah"] if b[2] == "busuk"]
        if len(busuk) > self._fruit_target(s):          # buah busuk tidak menumpuk tanpa batas
            drop = busuk[0]
            s["buah"].remove(drop)

    def pending(self, s):
        if self.over(s):
            return []
        return [i for i, u in enumerate(s["ular"]) if not u["keluar"]]

    # ------------------------------------------------------------ tampilan
    def _view(self, s):
        c, n = s["cfg"], s["names"]
        mulai = max(0, s["mulai"] - s["t"])
        return {"ukuran": s["ukuran"], "ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "detak": s["t"],
                "sisa_detak": max(0, s["akhir"] - s["t"]), "kecepatan": c["kecepatan"], "mulai_dalam": mulai,
                "tembus_tepi": c["tembus_tepi"], "tabrakan": c["tabrakan"], "adu_kepala": c["adu_kepala"],
                "dinding": [list(w) for w in s["dinding"]], "buah": [list(b) for b in s["buah"]],
                "ular": {n[i]: {"badan": [list(p) for p in u["badan"]] if u["hidup"] else [], "arah": u["arah"],
                                "hidup": u["hidup"], "keluar": u["keluar"],
                                "bangkit_dalam": max(0, u["bangkit"] - s["t"]) if not u["hidup"] and not u["keluar"] else 0,
                                "panjang": len(u["badan"]) if u["hidup"] else 0, "skor": s["skor"][i]}
                         for i, u in enumerate(s["ular"])},
                "skor": dict(zip(n, s["skor"])), "riwayat": [dict(e) for e in s["riwayat"]]}

    def public(self, s):
        return self._view(s)

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if a is None:
            return None
        if not isinstance(a, str):
            raise ActionError('arah harus "atas", "bawah", "kiri", atau "kanan"')
        w = a.strip().lower()
        w = ALIAS.get(w, w)
        if w in ("", "lurus", "tetap"):
            return None
        if w not in ARAH:
            raise ActionError('arah harus "atas", "bawah", "kiri", atau "kanan"')
        return w

    def default(self, s, p):
        return None

    def _step_cell(self, s, x, y, arah):
        N = s["ukuran"]
        dx, dy = ARAH[arah]
        nx, ny = x + dx, y + dy
        if s["cfg"]["tembus_tepi"]:
            nx, ny = nx % N, ny % N
        return nx, ny

    def apply(self, s, actions):
        c, n, N = s["cfg"], s["names"], s["ukuran"]
        events: list[dict[str, Any]] = []
        s["t"] += 1
        s["t_total"] += 1
        # belok (selama hitung mundur juga boleh mengatur arah awal)
        for p, a in actions.items():
            u = s["ular"][p]
            if a and u["hidup"] and a != BALIK.get(u["arah"]) and a != u["arah"]:
                # cegah belok ke leher sendiri (dua perintah cepat di detak yang sama ditangani antrean server)
                hx, hy = u["badan"][0]
                if len(u["badan"]) < 2 or list(self._step_cell(s, hx, hy, a)) != u["badan"][1]:
                    u["arah"] = a
        if s["t"] <= s["mulai"]:
            return events
        # bangkit
        for i, u in enumerate(s["ular"]):
            if not u["hidup"] and not u["keluar"] and s["t"] >= u["bangkit"]:
                body, arah = self._free_spot(s, ("bangkit", i))
                u.update(badan=body, arah=arah, hidup=True, tumbuh=0)
                events.append({"jenis": "bangkit", "pemain": n[i]})
        walls = {tuple(w) for w in s["dinding"]}
        alive = [i for i, u in enumerate(s["ular"]) if u["hidup"]]
        new_head: dict[int, tuple[int, int]] = {}
        grow = {i: s["ular"][i]["tumbuh"] > 0 for i in alive}
        for i in alive:
            u = s["ular"][i]
            hx, hy = u["badan"][0]
            new_head[i] = self._step_cell(s, hx, hy, u["arah"])
        # petak terisi setelah gerak: semua badan kecuali ekor ular yang tidak tumbuh (ekornya pindah)
        occ: dict[tuple[int, int], int] = {}
        for i in alive:
            body = s["ular"][i]["badan"]
            keep = body if grow[i] else body[:-1]
            for x, y in keep:
                occ[(x, y)] = i
        dead: dict[int, str] = {}
        killer: dict[int, int] = {}
        heads_at: dict[tuple[int, int], list[int]] = {}
        for i, h in new_head.items():
            heads_at.setdefault(h, []).append(i)
        for i, (x, y) in new_head.items():
            if not (0 <= x < N and 0 <= y < N):
                dead[i] = "tepi"
            elif (x, y) in walls:
                dead[i] = "tembok"
            elif (x, y) in occ:
                dead[i] = "badan"
                if occ[(x, y)] != i:
                    killer[i] = occ[(x, y)]
        for cell, who in heads_at.items():
            if len(who) < 2:
                continue
            if c["adu_kepala"] == "panjang":
                lens = {i: len(s["ular"][i]["badan"]) for i in who}
                top = max(lens.values())
                winners = [i for i in who if lens[i] == top]
                for i in who:
                    if len(winners) > 1 or i not in winners:
                        dead.setdefault(i, "adu_kepala")
                        if len(winners) == 1:
                            killer.setdefault(i, winners[0])
            else:
                for i in who:
                    dead.setdefault(i, "adu_kepala")
        fruit_at = {(b[0], b[1]): b for b in s["buah"]}
        for i in alive:
            u = s["ular"][i]
            if i in dead:
                continue
            u["badan"].insert(0, list(new_head[i]))
            if grow[i]:
                u["tumbuh"] -= 1
            else:
                u["badan"].pop()
            b = fruit_at.pop(new_head[i], None)
            if b is not None:
                s["buah"].remove(b)
                info = BUAH[b[2]]
                s["skor"][i] += info["poin"]
                s["makan_total"][i] += 1
                if info["tumbuh"] > 0:
                    u["tumbuh"] += info["tumbuh"]
                else:
                    for _ in range(-info["tumbuh"]):
                        if len(u["badan"]) > 2:
                            u["badan"].pop()
                events.append({"jenis": "makan", "pemain": n[i], "buah": b[2], "poin": info["poin"]})
        for i, sebab in sorted(dead.items()):
            u = s["ular"][i]
            body = u["badan"]
            u["hidup"] = False
            u["mati_t"] = s["t"]
            s["tumbang_total"][i] += 1
            if c["tabrakan"] == "habis":
                u["keluar"] = True
            else:
                s["skor"][i] -= 3
                u["bangkit"] = s["t"] + self._ticks(s, 2)
            k = killer.get(i)
            if k is not None and k != i:
                s["skor"][k] += 2
            if c["bangkai_jadi_buah"]:
                have = {(b[0], b[1]) for b in s["buah"]}
                live_occ = self._occupied(s)
                for x, y in body[1::2][:8]:
                    if (x, y) not in have and (x, y) not in live_occ and (x, y) not in walls:
                        s["buah"].append([x, y, "apel"])
                        have.add((x, y))
            u["badan"] = []
            events.append({"jenis": "tumbang", "pemain": n[i], "sebab": sebab, "oleh": n[k] if k is not None and k != i else None,
                           "panjang": len(body), "keluar": u["keluar"]})
        self._fill_fruit(s)
        hidup = [i for i, u in enumerate(s["ular"]) if u["hidup"]]
        selesai = s["t"] >= s["akhir"]
        if c["tabrakan"] == "habis":
            if len(n) > 1 and len(hidup) <= 1:
                selesai = True
            if len(n) == 1 and not hidup:
                selesai = True
        if selesai:
            events += self._end_round(s)
        return events

    def _end_round(self, s):
        n = s["names"]
        bonus = [0] * len(n)
        hidup = [i for i, u in enumerate(s["ular"]) if u["hidup"]]
        for i in hidup:
            bonus[i] += 3
        lens = [len(u["badan"]) if u["hidup"] else 0 for u in s["ular"]]
        top = max(lens) if lens else 0
        terpanjang = [i for i in range(len(n)) if lens[i] == top and top > 0]
        if len(terpanjang) == 1:
            bonus[terpanjang[0]] += 5
        for i in range(len(n)):
            s["skor"][i] += bonus[i]
        entry = {"ronde": s["ronde"], "bonus": dict(zip(n, bonus)), "panjang": dict(zip(n, lens)),
                 "terpanjang": n[terpanjang[0]] if len(terpanjang) == 1 else None,
                 "hidup": [n[i] for i in hidup], "skor": dict(zip(n, s["skor"]))}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "ronde_selesai", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [float(m) - t for m, t in zip(s["makan_total"], s["tumbang_total"])]

    def reveal(self, s):
        return {"ronde": [dict(e) for e in s["riwayat"]]}

    # ------------------------------------------------------------ bot
    def bot_library(self, s, p, obs):
        N = s["ukuran"]
        me = s["ular"][p]
        wrap = s["cfg"]["tembus_tepi"]
        cache: dict[str, Any] = {}
        DIRS = (("atas", 0, -1), ("kanan", 1, 0), ("bawah", 0, 1), ("kiri", -1, 0))

        def blocked() -> bytearray:
            """Peta terisi (indeks y*N+x): tembok + badan semua ular (ekor yang akan pindah dianggap kosong)."""
            if "occ" not in cache:
                occ = bytearray(N * N)
                for x, y in s["dinding"]:
                    occ[y * N + x] = 1
                for u in s["ular"]:
                    if u["hidup"]:
                        body = u["badan"] if u["tumbuh"] > 0 else u["badan"][:-1]
                        for x, y in body:
                            occ[y * N + x] = 1
                cache["occ"] = occ
            return cache["occ"]

        def nxt(x, y, dx, dy):
            nx, ny = x + dx, y + dy
            if wrap:
                return nx % N, ny % N
            return nx, ny

        def free(x, y):
            return 0 <= x < N and 0 <= y < N and not blocked()[y * N + x]

        def _arah(a):
            w = ALIAS.get(str(a).strip().lower(), str(a).strip().lower())
            if w not in ARAH:
                raise ActionError('arah harus "atas", "bawah", "kiri", atau "kanan"')
            return w

        def kepala():
            return list(me["badan"][0]) if me["hidup"] else None

        def arah_sekarang():
            return me["arah"]

        def aman(a):
            a = _arah(a)
            if not me["hidup"] or a == BALIK[me["arah"]]:
                return False
            return free(*nxt(*me["badan"][0], *ARAH[a]))

        def bfs():
            """Jarak & arah pertama ke setiap petak dari kepala (sekali per aksi bot)."""
            if "bfs" not in cache:
                occ = blocked()
                dist = [-1] * (N * N)
                first = [""] * (N * N)
                if me["hidup"]:
                    hx, hy = me["badan"][0]
                    q: deque = deque()
                    back = BALIK[me["arah"]]
                    for a, dx, dy in DIRS:
                        if a == back:
                            continue
                        nx, ny = nxt(hx, hy, dx, dy)
                        if 0 <= nx < N and 0 <= ny < N:
                            k = ny * N + nx
                            if not occ[k] and dist[k] < 0:
                                dist[k], first[k] = 1, a
                                q.append(k)
                    while q:
                        k = q.popleft()
                        d, f = dist[k] + 1, first[k]
                        y, x = divmod(k, N)
                        for _a, dx, dy in DIRS:
                            nx, ny = x + dx, y + dy
                            if wrap:
                                nx, ny = nx % N, ny % N
                            elif not (0 <= nx < N and 0 <= ny < N):
                                continue
                            k2 = ny * N + nx
                            if dist[k2] < 0 and not occ[k2]:
                                dist[k2], first[k2] = d, f
                                q.append(k2)
                cache["bfs"] = (dist, first)
            return cache["bfs"]

        def _cell(x, y):
            x, y = int(x), int(y)
            if not (0 <= x < N and 0 <= y < N):
                return None
            return y * N + x

        def ruang(a):
            a = _arah(a)
            if not aman(a):
                return 0
            key = "ruang_" + a
            if key not in cache:
                occ = blocked()
                sx, sy = nxt(*me["badan"][0], *ARAH[a])
                hk = me["badan"][0][1] * N + me["badan"][0][0]
                seen = bytearray(N * N)
                k0 = sy * N + sx
                seen[k0] = 1
                seen[hk] = 1
                q = deque([k0])
                count = 1
                while q and count < 300:
                    k = q.popleft()
                    y, x = divmod(k, N)
                    for _a, dx, dy in DIRS:
                        nx, ny = x + dx, y + dy
                        if wrap:
                            nx, ny = nx % N, ny % N
                        elif not (0 <= nx < N and 0 <= ny < N):
                            continue
                        k2 = ny * N + nx
                        if not seen[k2] and not occ[k2]:
                            seen[k2] = 1
                            count += 1
                            q.append(k2)
                cache[key] = count
            return cache[key]

        def jalur_ke(x, y):
            k = _cell(x, y)
            if k is None:
                return None
            dist, first = bfs()
            return first[k] if dist[k] > 0 else None

        def jarak_ke(x, y):
            k = _cell(x, y)
            if k is None:
                return None
            dist, _f = bfs()
            return dist[k] if dist[k] > 0 else None

        def buah_terdekat():
            dist, _f = bfs()
            best = None
            for b in s["buah"]:
                if b[2] == "busuk":
                    continue
                d = dist[b[1] * N + b[0]]
                if d > 0 and (best is None or d < best[0]):
                    best = (d, b)
            return list(best[1]) if best else None

        def dekat_kepala_lawan(a):
            a = _arah(a)
            if not me["hidup"]:
                return False
            tx, ty = nxt(*me["badan"][0], *ARAH[a])
            for i, u in enumerate(s["ular"]):
                if i != p and u["hidup"]:
                    hx, hy = u["badan"][0]
                    if abs(hx - tx) + abs(hy - ty) <= 1:
                        return True
            return False

        return {"kepala": kepala, "arah_sekarang": arah_sekarang, "aman": aman, "ruang": ruang, "jalur_ke": jalur_ke,
                "jarak_ke": jarak_ke, "buah_terdekat": buah_terdekat, "dekat_kepala_lawan": dekat_kepala_lawan}
