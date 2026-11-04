"""Arena Robot Grid: robot bergerak di peta petak, berebut kristal dan saling tembak (semua bergerak bersamaan)."""

from __future__ import annotations

from collections import deque
from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

ARAH = {"atas": (-1, 0), "bawah": (1, 0), "kiri": (0, -1), "kanan": (0, 1)}
AKSI = ["diam"] + list(ARAH) + [f"tembak_{a}" for a in ARAH]
COOLDOWN = 3


class RobotGrid(Game):
    id = "robot"
    nama = "Arena Robot Grid"
    ringkas = "Robot bergerak bersamaan di peta petak: ambil kristal, tembak lawan, hindari tembakan. Poin terbanyak menang."
    kategori = "tick"
    min_pemain, max_pemain = 2, 8
    hint_aksi = "'atas', 'bawah', 'kiri', 'kanan', 'diam', atau 'tembak_atas' dst."
    timer = 8
    settings = [
        Setting("ukuran", "Ukuran peta", "int", 15, 9, 25),
        Setting("tick", "Jumlah giliran", "int", 120, 20, 500),
        Setting("hp", "Nyawa robot", "int", 3, 1, 10),
        Setting("kristal", "Kristal di peta", "int", 8, 1, 30),
        Setting("tembok", "Kepadatan tembok (%)", "int", 12, 0, 30),
        Setting("bangkit", "Bangkit lagi setelah (giliran)", "int", 8, 0, 50,
                ket="Robot hancur muncul lagi di posisi awal dengan nyawa penuh setelah sekian giliran. 0 = hancur permanen."),
    ]
    aturan = """
- Peta berupa petak (default 15×15) dengan tembok. Semua robot bertindak **bersamaan** setiap giliran (default 120 giliran).
- Aksi: bergerak 1 petak (`atas/bawah/kiri/kanan`), `diam`, atau **menembak** lurus ke satu arah (`tembak_atas`, dst.).
- Tembakan langsung mengenai robot pertama di garis itu (terhalang tembok). Setelah menembak, senjata perlu **3 giliran** untuk siap lagi.
- Kena tembak: nyawa −1, penembak +1 poin. Menghancurkan robot: +3 poin tambahan. Robot hancur **bangkit lagi** di posisi awalnya
  dengan nyawa penuh setelah 8 giliran (bisa diatur; 0 = hancur permanen dan permainan berhenti kalau tinggal satu robot).
- **Kristal** (◆): masuk petaknya = +2 poin, lalu kristal baru muncul di tempat lain (posisi ditentukan seed, sama untuk semua).
- Dua robot yang menuju petak yang sama, atau bertukar tempat, sama-sama batal bergerak. Bergerak ke tembok atau robot yang diam = tetap di tempat.
- Urutan dalam satu giliran: semua tembakan dihitung dulu (dari posisi awal), lalu gerakan, lalu kristal.
- Peta simetris supaya posisi awal adil. Poin terbanyak menang; seri dipecah jumlah hancur paling sedikit, lalu sisa nyawa.
"""
    format_aksi = "Teks: `\"atas\"`, `\"bawah\"`, `\"kiri\"`, `\"kanan\"`, `\"diam\"`, `\"tembak_atas\"`, `\"tembak_bawah\"`, `\"tembak_kiri\"`, `\"tembak_kanan\"`."
    format_info = """```
{ "giliran": 12, "giliran_total": 120, "ukuran": 15,
  "peta": ["...#....", ...],          # baris teks: '#' tembok, '.' kosong (robot & kristal tidak digambar di sini)
  "robot": {"Budi": {"baris": 3, "kolom": 4, "nyawa": 3, "poin": 5, "siap_tembak": 0, "hidup": True,
                     "hancur": 1, "bangkit_dalam": None}, ...},   # bangkit_dalam: giliran sampai bangkit (kalau sedang hancur)
  "kristal": [[7, 7], [2, 12], ...],  # [baris, kolom]
  "kejadian": [ ... ]                 # tembakan & kristal di giliran sebelumnya
}
```
`siap_tembak` = berapa giliran lagi sampai bisa menembak (0 = siap). Baris 0 di atas, kolom 0 di kiri."""
    lib_docs = [
        {"nama": "posisi", "jenis": "fungsi", "tanda": "posisi(nama=None)", "ket": "[baris, kolom] robotmu (atau robot bernama itu)."},
        {"nama": "langkah_ke", "jenis": "fungsi", "tanda": "langkah_ke(baris, kolom)", "ket": "Arah langkah pertama jalur terpendek ke petak itu (menghindari tembok & robot), atau 'diam' kalau tidak ada jalan."},
        {"nama": "jarak", "jenis": "fungsi", "tanda": "jarak(baris, kolom)", "ket": "Panjang jalur terpendek dari robotmu ke petak itu (-1 kalau tidak terjangkau)."},
        {"nama": "kristal_terdekat", "jenis": "fungsi", "tanda": "kristal_terdekat()", "ket": "[baris, kolom] kristal dengan jalur terpendek, atau None."},
        {"nama": "musuh_terdekat", "jenis": "fungsi", "tanda": "musuh_terdekat()", "ket": "Nama robot musuh hidup yang paling dekat (jalur), atau None."},
        {"nama": "bisa_kena", "jenis": "fungsi", "tanda": "bisa_kena()", "ket": "Arah tembakan yang sekarang akan mengenai musuh, misalnya 'kanan', atau None."},
        {"nama": "terancam", "jenis": "fungsi", "tanda": "terancam()", "ket": "True kalau ada musuh segaris tanpa halangan yang senjatanya siap sekarang atau giliran depan. Tembakan dihitung sebelum gerakan, jadi menghindar menyelamatkanmu untuk giliran berikutnya."},
        {"nama": "bisa_jalan", "jenis": "fungsi", "tanda": "bisa_jalan(arah)", "ket": "True kalau petak di arah itu bukan tembok/robot/luar peta."},
    ]
    templates = [
        {"id": "pemungut", "nama": "Pemungut Kristal", "ket": "Fokus mengambil kristal terdekat, menembak kalau ada musuh segaris.", "kode": '''def aksi():
    arah = bisa_kena()
    if arah != None and info()["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
'''},
        {"id": "pemburu", "nama": "Pemburu", "ket": "Mengejar robot terdekat dan menembak begitu segaris.", "kode": '''def aksi():
    i = info()
    saya = i["robot"][nama_saya()]
    arah = bisa_kena()
    if arah != None and saya["siap_tembak"] == 0:
        return "tembak_" + arah
    m = musuh_terdekat()
    if m == None:
        k = kristal_terdekat()
        return "diam" if k == None else langkah_ke(k[0], k[1])
    r = i["robot"][m]
    return langkah_ke(r["baris"], r["kolom"])
'''},
        {"id": "penghindar", "nama": "Penghindar", "ket": "Menghindar dari garis tembak musuh, mengambil kristal kalau aman.", "kode": '''def aksi():
    arah = bisa_kena()
    if arah != None and info()["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    if terancam():
        for a in ["atas", "kiri", "bawah", "kanan"]:
            if bisa_jalan(a):
                return a
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
'''},
    ]

    # ------------------------------------------------------------ peta
    def _make_map(self, s):
        c = s["cfg"]
        n = c["ukuran"]
        g = rng(s, "peta")
        walls = set()
        # dibuat di seperempat peta lalu dicerminkan ke 4 arah supaya adil untuk semua posisi awal
        quarter = [(r, k) for r in range((n + 1) // 2) for k in range((n + 1) // 2)]
        for r, k in quarter:
            if g.random() * 100 < c["tembok"]:
                for x, y in {(r, k), (n - 1 - r, k), (r, n - 1 - k), (n - 1 - r, n - 1 - k)}:
                    walls.add((x, y))
        return walls

    def _starts(self, n, count):
        m = n // 2
        pts = [(1, 1), (n - 2, n - 2), (1, n - 2), (n - 2, 1), (1, m), (n - 2, m), (m, 1), (m, n - 2)]
        return pts[:count]

    def _connected(self, n, walls, pts):
        start = pts[0]
        seen = {start}
        q = deque([start])
        while q:
            r, k = q.popleft()
            for dr, dk in ARAH.values():
                x, y = r + dr, k + dk
                if 0 <= x < n and 0 <= y < n and (x, y) not in walls and (x, y) not in seen:
                    seen.add((x, y))
                    q.append((x, y))
        free = n * n - len(walls)
        return all(p in seen for p in pts) and len(seen) >= free * 0.95, seen

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "t": 1, "events": [], "spawn_no": 0}
        n = cfg["ukuran"]
        starts = self._starts(n, len(names))
        walls: set = set()
        for attempt in range(40):
            walls = self._make_map({**s, "seed": f"{seed}:{attempt}"})
            for p in self._starts(n, 8):
                walls.discard(p)
            ok, _ = self._connected(n, walls, starts)
            if ok:
                break
        else:
            walls = set()
        s["walls"] = sorted([list(w) for w in walls])
        s["bots"] = [{"r": r, "c": k, "hp": cfg["hp"], "poin": 0, "cd": 0, "hidup": True, "hancur_di": 0, "bangkit_di": 0,
                      "awal": [r, k], "hancur": 0} for (r, k) in starts]
        s["crystals"] = []
        for _ in range(cfg["kristal"]):
            self._spawn(s)
        return s

    def _wallset(self, s):
        return {(r, k) for r, k in s["walls"]}

    def _spawn(self, s):
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        occupied = {(b["r"], b["c"]) for b in s["bots"] if b["hidup"]} | {tuple(x) for x in s["crystals"]}
        g = rng(s, "kristal", s["spawn_no"])
        s["spawn_no"] += 1
        for _ in range(400):
            r, k = g.randrange(n), g.randrange(n)
            if (r, k) not in walls and (r, k) not in occupied:
                s["crystals"].append([r, k])
                return

    # ------------------------------------------------------------ kontrak
    def pending(self, s):
        return [] if self.over(s) else [i for i, b in enumerate(s["bots"]) if b["hidup"]]

    def _grid(self, s):
        n = s["cfg"]["ukuran"]
        rows = [["."] * n for _ in range(n)]
        for r, k in s["walls"]:
            rows[r][k] = "#"
        return ["".join(x) for x in rows]

    def public(self, s):
        names = s["names"]
        return {"giliran": min(s["t"], s["cfg"]["tick"]), "giliran_total": s["cfg"]["tick"], "ukuran": s["cfg"]["ukuran"],
                "peta": self._grid(s),
                "robot": {names[i]: {"baris": b["r"], "kolom": b["c"], "nyawa": b["hp"], "poin": b["poin"],
                                     "siap_tembak": b["cd"], "hidup": b["hidup"], "hancur": b["hancur"],
                                     "bangkit_dalam": max(0, b["bangkit_di"] - s["t"]) if not b["hidup"] and b["bangkit_di"] else None}
                          for i, b in enumerate(s["bots"])},
                "kristal": [list(x) for x in s["crystals"]], "kejadian": s["events"]}

    def validate(self, s, p, a):
        if not isinstance(a, str) or a.strip().lower() not in AKSI:
            raise ActionError("aksi robot: " + ", ".join(AKSI))
        a = a.strip().lower()
        if a.startswith("tembak_") and s["bots"][p]["cd"] > 0:
            raise ActionError(f"senjata belum siap ({s['bots'][p]['cd']} giliran lagi)")
        return a

    def default(self, s, p):
        return "diam"

    def _ray(self, s, p, arah):
        """Robot pertama yang kena tembakan p ke arah itu (indeks) dan titik akhir sinar."""
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        b = s["bots"][p]
        dr, dk = ARAH[arah]
        pos = {(x["r"], x["c"]): i for i, x in enumerate(s["bots"]) if x["hidup"] and i != p}
        r, k = b["r"], b["c"]
        while True:
            r, k = r + dr, k + dk
            if not (0 <= r < n and 0 <= k < n) or (r, k) in walls:
                return None, [r - dr, k - dk]
            if (r, k) in pos:
                return pos[(r, k)], [r, k]

    def apply(self, s, actions):
        names = s["names"]
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        ev: list[dict[str, Any]] = []
        bots = s["bots"]
        for b in bots:
            if b["cd"] > 0:
                b["cd"] -= 1
        # 1) tembakan dari posisi awal (bersamaan)
        dmg: dict[int, list[int]] = {}
        for p, a in actions.items():
            if a.startswith("tembak_") and bots[p]["hidup"]:
                arah = a.split("_", 1)[1]
                hit, end = self._ray(s, p, arah)
                bots[p]["cd"] = COOLDOWN
                ev.append({"jenis": "tembak", "pemain": names[p], "arah": arah, "dari": [bots[p]["r"], bots[p]["c"]],
                           "sampai": end, "kena": names[hit] if hit is not None else None})
                if hit is not None:
                    dmg.setdefault(hit, []).append(p)
        for victim, shooters in dmg.items():
            v = bots[victim]
            for sh in shooters:
                bots[sh]["poin"] += 1
            v["hp"] -= len(shooters)
            if v["hp"] <= 0 and v["hidup"]:
                v["hp"], v["hidup"], v["hancur_di"] = 0, False, s["t"]
                v["hancur"] += 1
                v["bangkit_di"] = s["t"] + s["cfg"]["bangkit"] if s["cfg"]["bangkit"] > 0 else 0
                for sh in set(shooters):
                    bots[sh]["poin"] += 3
                ev.append({"jenis": "hancur", "pemain": names[victim], "oleh": [names[x] for x in sorted(set(shooters))]})
        # 2) gerakan (bersamaan, konflik = batal)
        want: dict[int, tuple[int, int]] = {}
        for p, a in actions.items():
            b = bots[p]
            if not b["hidup"]:
                continue
            if a in ARAH:
                dr, dk = ARAH[a]
                t = (b["r"] + dr, b["c"] + dk)
                if 0 <= t[0] < n and 0 <= t[1] < n and t not in walls:
                    want[p] = t
        changed = True
        cur = {i: (b["r"], b["c"]) for i, b in enumerate(bots) if b["hidup"]}
        moving = dict(want)
        while changed:
            changed = False
            targets: dict[tuple[int, int], list[int]] = {}
            for p, t in moving.items():
                targets.setdefault(t, []).append(p)
            for t, ps in targets.items():
                if len(ps) > 1:
                    for p in ps:
                        moving.pop(p, None)
                    changed = True
            for p, t in list(moving.items()):
                if p not in moving:
                    continue
                occ = next((i for i, c in cur.items() if c == t and i != p), None)
                if occ is not None:
                    if occ not in moving:
                        moving.pop(p, None)
                        changed = True
                    elif moving[occ] == cur[p]:  # bertukar tempat
                        moving.pop(p, None)
                        moving.pop(occ, None)
                        changed = True
        for p, t in moving.items():
            bots[p]["r"], bots[p]["c"] = t
        # 3) kristal
        for p, b in enumerate(bots):
            if not b["hidup"]:
                continue
            for cr in list(s["crystals"]):
                if cr[0] == b["r"] and cr[1] == b["c"]:
                    s["crystals"].remove(cr)
                    b["poin"] += 2
                    ev.append({"jenis": "kristal", "pemain": names[p], "di": cr})
                    self._spawn(s)
        s["t"] += 1
        ev += self._respawn(s)
        # kalau semua robot sedang hancur, waktu terus berjalan sampai ada yang bangkit
        while s["cfg"]["bangkit"] > 0 and not any(b["hidup"] for b in bots) and s["t"] <= s["cfg"]["tick"]:
            s["t"] += 1
            ev += self._respawn(s)
        s["events"] = ev
        return ev or [{"jenis": "giliran"}]

    def _respawn(self, s):
        ev = []
        if s["cfg"]["bangkit"] <= 0:
            return ev
        taken = {(b["r"], b["c"]) for b in s["bots"] if b["hidup"]}
        for i, b in enumerate(s["bots"]):
            if not b["hidup"] and b["bangkit_di"] and s["t"] >= b["bangkit_di"] and tuple(b["awal"]) not in taken:
                b["r"], b["c"] = b["awal"]
                b["hp"], b["hidup"], b["cd"], b["bangkit_di"] = s["cfg"]["hp"], True, 0, 0
                taken.add((b["r"], b["c"]))
                ev.append({"jenis": "bangkit", "pemain": s["names"][i], "di": list(b["awal"])})
        return ev

    def over(self, s):
        if s["t"] > s["cfg"]["tick"]:
            return True
        return s["cfg"]["bangkit"] <= 0 and sum(1 for b in s["bots"] if b["hidup"]) <= 1

    def scores(self, s):
        return [float(b["poin"]) for b in s["bots"]]

    def tiebreak(self, s):
        return [-b["hancur"] * 10**6 + b["hp"] * 1000 + (s["t"] if b["hidup"] else b["hancur_di"]) for b in s["bots"]]

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        names = s["names"]
        me = s["bots"][p]
        others = {(b["r"], b["c"]) for i, b in enumerate(s["bots"]) if b["hidup"] and i != p}
        cache: dict[str, Any] = {}

        def bfs():
            if "dist" in cache:
                return cache["dist"], cache["first"]
            start = (me["r"], me["c"])
            dist = {start: 0}
            first: dict[tuple[int, int], str] = {}
            q = deque([start])
            while q:
                cur = q.popleft()
                for a in ("atas", "bawah", "kiri", "kanan"):
                    dr, dk = ARAH[a]
                    nx = (cur[0] + dr, cur[1] + dk)
                    if not (0 <= nx[0] < n and 0 <= nx[1] < n) or nx in walls or nx in dist:
                        continue
                    dist[nx] = dist[cur] + 1
                    first[nx] = first.get(cur, a)
                    if nx in others:   # boleh dituju (untuk mengejar) tapi tidak dilewati
                        continue
                    q.append(nx)
            cache["dist"], cache["first"] = dist, first
            return dist, first

        def _pt(r, k):
            return (as_int(r, "baris"), as_int(k, "kolom"))

        def posisi(nama=None):
            if nama is None:
                return [me["r"], me["c"]]
            if nama not in names:
                raise ActionError(f"tidak ada robot bernama {nama!r}")
            b = s["bots"][names.index(nama)]
            return [b["r"], b["c"]]

        def jarak(r, k):
            d, _ = bfs()
            return d.get(_pt(r, k), -1)

        def langkah_ke(r, k):
            t = _pt(r, k)
            d, f = bfs()
            if t == (me["r"], me["c"]) or t not in f:
                return "diam"
            step = f[t]
            dr, dk = ARAH[step]
            if (me["r"] + dr, me["c"] + dk) in others:
                return "diam"
            return step

        def kristal_terdekat():
            d, _ = bfs()
            best = None
            for cr in s["crystals"]:
                v = d.get((cr[0], cr[1]))
                if v is not None and (best is None or v < best[0]):
                    best = (v, list(cr))
            return best[1] if best else None

        def musuh_terdekat():
            d, _ = bfs()
            best = None
            for i, b in enumerate(s["bots"]):
                if i == p or not b["hidup"]:
                    continue
                v = d.get((b["r"], b["c"]), 10**6)
                if best is None or v < best[0]:
                    best = (v, names[i])
            return best[1] if best else None

        def bisa_kena():
            for a in ("atas", "bawah", "kiri", "kanan"):
                hit, _ = self._ray(s, p, a)
                if hit is not None:
                    return a
            return None

        def terancam():
            for i, b in enumerate(s["bots"]):
                if i == p or not b["hidup"] or b["cd"] > 1:
                    continue
                for a in ARAH:
                    hit, _ = self._ray(s, i, a)
                    if hit == p:
                        return True
            return False

        def bisa_jalan(arah):
            arah = str(arah).lower()
            if arah not in ARAH:
                raise ActionError("arah harus 'atas', 'bawah', 'kiri', atau 'kanan'")
            dr, dk = ARAH[arah]
            t = (me["r"] + dr, me["c"] + dk)
            return 0 <= t[0] < n and 0 <= t[1] < n and t not in walls and t not in others

        return {"posisi": posisi, "jarak": jarak, "langkah_ke": langkah_ke, "kristal_terdekat": kristal_terdekat,
                "musuh_terdekat": musuh_terdekat, "bisa_kena": bisa_kena, "terancam": terancam, "bisa_jalan": bisa_jalan}
