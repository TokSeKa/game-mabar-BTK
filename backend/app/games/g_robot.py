"""Arena Robot Grid: robot bergerak di peta petak, berebut kristal dan saling tembak (semua bergerak bersamaan).

Urutan satu giliran: gerakan → tembakan → kristal. Tembakan dihitung ke posisi lawan setelah bergerak, jadi menembak
berarti memprediksi gerakan lawan, dan lawan yang segaris masih bisa menghindar."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

ARAH = {"atas": (-1, 0), "bawah": (1, 0), "kiri": (0, -1), "kanan": (0, 1)}
POWERUP = {"senjata": "⚡ senjata langsung siap", "perisai": "🛡️ perisai (menahan 1 tembakan)", "nyawa": "❤️ nyawa +1"}
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
        Setting("pandang", "Jarak pandang (petak)", "int", 0, 0, 15, grup="informasi",
                ket="Kabut perang: robot, kristal, dan power-up di luar jarak ini dari robotmu tidak terlihat (tembok selalu terlihat). 0 = terlihat semua."),
        Setting("powerup", "Power-up di peta", "int", 0, 0, 6, grup="kejutan",
                ket="⚡ senjata langsung siap, 🛡️ perisai menahan 1 tembakan, ❤️ nyawa +1. Muncul lagi di tempat lain setelah diambil."),
        Setting("zona", "Zona menyempit mulai (% giliran)", "int", 0, 0, 90, grup="kejutan",
                ket="Setelah sekian persen giliran, pinggir peta berubah jadi badai dan zona aman menyempit bertahap. "
                    "Robot di luar zona kehilangan 1 nyawa tiap giliran. 0 = mati."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut Perang", "ket": "Robot hanya melihat 4 petak di sekitarnya.", "nilai": {"pandang": 4}},
        {"id": "kacau", "nama": "Kacau", "ket": "4 power-up dan zona menyempit mulai di tengah permainan.", "nilai": {"powerup": 4, "zona": 50}},
    ]
    aturan = """
- Peta berupa petak (default 15×15) dengan tembok. Semua robot bertindak **bersamaan** setiap giliran (default 120 giliran).
- Aksi: bergerak 1 petak (`atas/bawah/kiri/kanan`), `diam`, atau **menembak** lurus ke satu arah (`tembak_atas`, dst.).
- Tembakan mengenai robot pertama di garis itu (terhalang tembok) **setelah semua robot bergerak**. Setelah menembak, senjata perlu
  **3 giliran** untuk siap lagi.
- Kena tembak: nyawa −1, penembak +1 poin. Menghancurkan robot: +3 poin tambahan. Robot hancur **bangkit lagi** di posisi awalnya
  dengan nyawa penuh setelah 8 giliran (bisa diatur; 0 = hancur permanen dan permainan berhenti kalau tinggal satu robot).
- **Kristal** (◆): masuk petaknya = +2 poin, lalu kristal baru muncul di tempat lain (posisi ditentukan seed, sama untuk semua).
- Dua robot yang menuju petak yang sama, atau bertukar tempat, sama-sama batal bergerak. Bergerak ke tembok atau robot yang diam = tetap di tempat.
- **Urutan dalam satu giliran: gerakan dulu, baru tembakan, lalu kristal.** Robot yang menembak diam di tempat; sinarnya dihitung ke
  posisi lawan **setelah** lawan bergerak. Jadi lawan yang sudah segaris masih bisa kabur, dan penembak yang jeli **menembak ke arah
  petak tujuan lawan** (memprediksi gerakannya), bukan ke tempat lawan sekarang.
- Peta simetris supaya posisi awal adil. Poin terbanyak menang; seri dipecah jumlah hancur paling sedikit, lalu sisa nyawa.
- **Kabut perang** (opsi jarak pandang): robot, kristal, dan power-up lawan hanya terlihat kalau dalam jarak tertentu dari robotmu.
- **Power-up** (opsi): ⚡ senjata langsung siap, 🛡️ perisai menahan satu tembakan (penembaknya tidak dapat poin), ❤️ nyawa +1.
- **Zona menyempit** (opsi): setelah sekian persen giliran, pinggir peta jadi badai dan zona aman mengecil bertahap; robot di luar zona
  kehilangan 1 nyawa tiap giliran (tidak ada yang dapat poin). Robot yang bangkit muncul di petak aman terdekat dari posisi awalnya.
"""
    format_aksi = "Teks: `\"atas\"`, `\"bawah\"`, `\"kiri\"`, `\"kanan\"`, `\"diam\"`, `\"tembak_atas\"`, `\"tembak_bawah\"`, `\"tembak_kiri\"`, `\"tembak_kanan\"`."
    format_info = """```
{ "giliran": 12, "giliran_total": 120, "ukuran": 15,
  "peta": ["...#....", ...],          # baris teks: '#' tembok, '.' kosong (robot & kristal tidak digambar di sini)
  "robot": {"Budi": {"baris": 3, "kolom": 4, "nyawa": 3, "poin": 5, "siap_tembak": 0, "hidup": True,
                     "hancur": 1, "bangkit_dalam": None}, ...},   # bangkit_dalam: giliran sampai bangkit (kalau sedang hancur)
  "kristal": [[7, 7], [2, 12], ...],  # [baris, kolom]
  "powerup": [{"baris": 3, "kolom": 9, "jenis": "perisai"}, ...],
  "skor": {"Budi": {"poin": 5, "hidup": True, "hancur": 1}, ...},   # semua pemain, selalu terlihat
  "zona": [2, 12],                    # zona aman: baris & kolom dari 2 sampai 12 (None kalau zona mati)
  "zona_berikut": 70,                 # giliran zona menyempit lagi (None kalau tidak lagi)
  "pandang": 0,                       # jarak pandang (0 = tanpa kabut)
  "kejadian": [ ... ]                 # tembakan & kristal di giliran sebelumnya
}
```
Dengan kabut perang, `robot`, `kristal`, `powerup`, dan `kejadian` hanya berisi yang terlihat dari robotmu.
`siap_tembak` = berapa giliran lagi sampai bisa menembak (0 = siap). Baris 0 di atas, kolom 0 di kiri."""
    lib_docs = [
        {"nama": "posisi", "jenis": "fungsi", "tanda": "posisi(nama=None)", "ket": "[baris, kolom] robotmu (atau robot bernama itu)."},
        {"nama": "langkah_ke", "jenis": "fungsi", "tanda": "langkah_ke(baris, kolom)", "ket": "Arah langkah pertama jalur terpendek ke petak itu (menghindari tembok & robot), atau 'diam' kalau tidak ada jalan."},
        {"nama": "jarak", "jenis": "fungsi", "tanda": "jarak(baris, kolom)", "ket": "Panjang jalur terpendek dari robotmu ke petak itu (-1 kalau tidak terjangkau)."},
        {"nama": "kristal_terdekat", "jenis": "fungsi", "tanda": "kristal_terdekat()", "ket": "[baris, kolom] kristal dengan jalur terpendek, atau None."},
        {"nama": "musuh_terdekat", "jenis": "fungsi", "tanda": "musuh_terdekat()", "ket": "Nama robot musuh hidup yang paling dekat (jalur), atau None."},
        {"nama": "bisa_kena", "jenis": "fungsi", "tanda": "bisa_kena()", "ket": "Arah tembakan yang mengenai musuh di posisinya SEKARANG, misalnya 'kanan', atau None. Ingat: lawan bergerak dulu sebelum tembakan dihitung."},
        {"nama": "arah_tembak_ke", "jenis": "fungsi", "tanda": "arah_tembak_ke(baris, kolom)", "ket": "Arah tembakan dari posisimu yang lurus & tanpa halangan tembok ke petak itu, atau None. Pakai untuk menembak ke petak tujuan lawan."},
        {"nama": "tebak_langkah", "jenis": "fungsi", "tanda": "tebak_langkah(nama)", "ket": "Tebakan petak [baris, kolom] robot itu setelah giliran ini, kalau ia berjalan ke kristal terdekatnya (atau diam kalau tidak ada)."},
        {"nama": "petak_mungkin", "jenis": "fungsi", "tanda": "petak_mungkin(nama)", "ket": "Semua petak [baris, kolom] yang bisa dicapai robot itu giliran ini (diam atau 1 langkah)."},
        {"nama": "terancam", "jenis": "fungsi", "tanda": "terancam()", "ket": "True kalau ada musuh segaris tanpa halangan yang senjatanya siap sekarang atau giliran depan. Gerakan dihitung sebelum tembakan, jadi keluar dari garis tembak menyelamatkanmu giliran ini juga (kecuali penembak menebak arah larimu)."},
        {"nama": "bisa_jalan", "jenis": "fungsi", "tanda": "bisa_jalan(arah)", "ket": "True kalau petak di arah itu bukan tembok/robot/luar peta."},
        {"nama": "powerup_terdekat", "jenis": "fungsi", "tanda": "powerup_terdekat()", "ket": "{'baris', 'kolom', 'jenis'} power-up terlihat yang paling dekat, atau None."},
        {"nama": "aman", "jenis": "fungsi", "tanda": "aman(baris, kolom)", "ket": "True kalau petak itu di dalam zona aman sekarang (selalu True kalau zona mati)."},
    ]
    templates = [
        {"id": "pemungut", "nama": "Pemungut Kristal", "ket": "Fokus mengambil kristal (atau power-up kalau lebih dekat), menembak kalau ada musuh segaris, menjauhi badai.", "kode": '''def aksi():
    i = info()
    arah = bisa_kena()
    if arah != None and i["robot"][nama_saya()]["siap_tembak"] == 0:
        return "tembak_" + arah
    saya = posisi()
    if not aman(saya[0], saya[1]):
        tengah = (i["zona"][0] + i["zona"][1]) // 2
        return langkah_ke(tengah, tengah)
    k = kristal_terdekat()
    pu = powerup_terdekat()
    if pu != None and (k == None or jarak(pu["baris"], pu["kolom"]) < jarak(k[0], k[1])):
        return langkah_ke(pu["baris"], pu["kolom"])
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
        {"id": "penembak_jitu", "nama": "Penembak Jitu", "ket": "Menebak ke mana lawan akan melangkah (ke kristal terdekatnya) lalu menembak ke petak itu.", "kode": '''def aksi():
    i = info()
    if i["robot"][nama_saya()]["siap_tembak"] == 0:
        for nama in i["robot"]:
            r = i["robot"][nama]
            if nama == nama_saya() or not r["hidup"]:
                continue
            t = tebak_langkah(nama)
            arah = arah_tembak_ke(t[0], t[1])
            if arah != None:
                return "tembak_" + arah
    k = kristal_terdekat()
    if k == None:
        return "diam"
    return langkah_ke(k[0], k[1])
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
                      "awal": [r, k], "hancur": 0, "perisai": False} for (r, k) in starts]
        s["crystals"] = []
        for _ in range(cfg["kristal"]):
            self._spawn(s)
        s["powerups"], s["pu_no"] = [], 0
        for _ in range(cfg.get("powerup", 0)):
            self._spawn_pu(s)
        s["zona"] = [0, n - 1] if cfg.get("zona", 0) > 0 else None
        return s

    def _zona_plan(self, s):
        """(giliran mulai, jarak antar penyempitan, maksimal cincin) zona menyempit."""
        c = s["cfg"]
        total = c["tick"]
        start = max(1, math.ceil(total * c["zona"] / 100))
        rings = max(1, (c["ukuran"] - 3) // 2)
        return start, max(2, (total - start) // rings), rings

    def _safe(self, s, r, k):
        z = s.get("zona")
        return z is None or (z[0] <= r <= z[1] and z[0] <= k <= z[1])

    def _spawn_pu(self, s):
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        occupied = ({(b["r"], b["c"]) for b in s["bots"] if b["hidup"]} | {tuple(x) for x in s["crystals"]}
                    | {(x["r"], x["c"]) for x in s["powerups"]})
        g = rng(s, "powerup", s["pu_no"])
        s["pu_no"] += 1
        jenis = g.choice(list(POWERUP))
        for _ in range(400):
            r, k = g.randrange(n), g.randrange(n)
            if (r, k) not in walls and (r, k) not in occupied and self._safe(s, r, k):
                s["powerups"].append({"r": r, "c": k, "jenis": jenis})
                return

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

    def _sees(self, s, viewer, r, k):
        rad = s["cfg"].get("pandang", 0)
        if viewer == "semua" or rad <= 0:
            return True
        if viewer is None:
            return False
        b = s["bots"][viewer]
        return max(abs(b["r"] - r), abs(b["c"] - k)) <= rad

    def _event_seen(self, s, viewer, e, me):
        if viewer == "semua" or s["cfg"].get("pandang", 0) <= 0:
            return True
        if me is not None and me in (e.get("pemain"), e.get("kena"), *e.get("oleh", [])):
            return True
        pts = [e[k] for k in ("dari", "sampai", "di") if k in e]
        return not pts or any(self._sees(s, viewer, p[0], p[1]) for p in pts)

    def _view(self, s, viewer):
        names = s["names"]
        c = s["cfg"]
        me = names[viewer] if isinstance(viewer, int) else None
        robot = {}
        for i, b in enumerate(s["bots"]):
            if i != viewer and not self._sees(s, viewer, b["r"], b["c"]):
                continue
            robot[names[i]] = {"baris": b["r"], "kolom": b["c"], "nyawa": b["hp"], "poin": b["poin"], "siap_tembak": b["cd"],
                               "hidup": b["hidup"], "hancur": b["hancur"], "perisai": b.get("perisai", False),
                               "bangkit_dalam": max(0, b["bangkit_di"] - s["t"]) if not b["hidup"] and b["bangkit_di"] else None}
        zona_next = None
        if s.get("zona") is not None:
            start, every, rings = self._zona_plan(s)
            shrunk = s["zona"][0]
            if shrunk < rings:
                zona_next = start if s["t"] < start else s["t"] + (every - (s["t"] - start) % every)
        return {"giliran": min(s["t"], c["tick"]), "giliran_total": c["tick"], "ukuran": c["ukuran"], "peta": self._grid(s),
                "robot": robot,
                "skor": {names[i]: {"poin": b["poin"], "hidup": b["hidup"], "hancur": b["hancur"]} for i, b in enumerate(s["bots"])},
                "kristal": [list(x) for x in s["crystals"] if self._sees(s, viewer, x[0], x[1])],
                "powerup": [{"baris": x["r"], "kolom": x["c"], "jenis": x["jenis"]} for x in s.get("powerups", [])
                            if self._sees(s, viewer, x["r"], x["c"])],
                "zona": list(s["zona"]) if s.get("zona") is not None else None, "zona_berikut": zona_next,
                "pandang": c.get("pandang", 0),
                "kejadian": [e for e in s["events"] if self._event_seen(s, viewer, e, me)]}

    def event_for(self, s, e, viewer):
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return e if self._event_seen(s, viewer, e, me) else None

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

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
        # 1) gerakan dulu (bersamaan, konflik = batal)
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
        # 2) tembakan SETELAH gerakan (bersamaan): penembak harus menebak ke mana lawan melangkah
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
            if v.get("perisai") and shooters:
                v["perisai"] = False
                ev.append({"jenis": "perisai", "pemain": names[victim], "oleh": [names[shooters[0]]]})
                shooters = shooters[1:]
                if not shooters:
                    continue
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
        # 4) power-up
        for p, b in enumerate(bots):
            if not b["hidup"]:
                continue
            for pu in list(s.get("powerups", [])):
                if pu["r"] == b["r"] and pu["c"] == b["c"]:
                    s["powerups"].remove(pu)
                    if pu["jenis"] == "senjata":
                        b["cd"] = 0
                    elif pu["jenis"] == "perisai":
                        b["perisai"] = True
                    else:
                        b["hp"] = min(s["cfg"]["hp"], b["hp"] + 1)
                    ev.append({"jenis": "powerup", "pemain": names[p], "powerup": pu["jenis"], "di": [pu["r"], pu["c"]]})
                    self._spawn_pu(s)
        # 5) badai di luar zona aman
        if s.get("zona") is not None:
            for p, b in enumerate(bots):
                if b["hidup"] and not self._safe(s, b["r"], b["c"]):
                    b["hp"] -= 1
                    if b["hp"] <= 0:
                        b["hp"], b["hidup"], b["hancur_di"] = 0, False, s["t"]
                        b["hancur"] += 1
                        b["bangkit_di"] = s["t"] + s["cfg"]["bangkit"] if s["cfg"]["bangkit"] > 0 else 0
                        ev.append({"jenis": "hancur", "pemain": names[p], "oleh": [], "badai": True})
                    else:
                        ev.append({"jenis": "badai", "pemain": names[p]})
            start, every, rings = self._zona_plan(s)
            if s["t"] >= start and (s["t"] - start) % every == 0 and s["zona"][0] < rings:
                s["zona"] = [s["zona"][0] + 1, s["zona"][1] - 1]
                ev.append({"jenis": "zona", "zona": list(s["zona"])})
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
            if not b["hidup"] and b["bangkit_di"] and s["t"] >= b["bangkit_di"]:
                spot = self._respawn_spot(s, b, taken)
                if spot is None:
                    continue
                b["r"], b["c"] = spot
                b["hp"], b["hidup"], b["cd"], b["bangkit_di"], b["perisai"] = s["cfg"]["hp"], True, 0, 0, False
                taken.add(spot)
                ev.append({"jenis": "bangkit", "pemain": s["names"][i], "di": list(spot)})
        return ev

    def _respawn_spot(self, s, b, taken):
        """Posisi awal, atau petak aman terdekat darinya kalau posisi awal sudah di luar zona."""
        home = tuple(b["awal"])
        if self._safe(s, *home):
            return None if home in taken else home
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        best = None
        for r in range(n):
            for k in range(n):
                if (r, k) in walls or (r, k) in taken or not self._safe(s, r, k):
                    continue
                d = abs(r - home[0]) + abs(k - home[1])
                if best is None or d < best[0]:
                    best = (d, (r, k))
        return best[1] if best else None

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
        """Fungsi bantu bot. Semua info lawan diambil dari ``obs`` (yang terlihat), jadi ikut kena kabut perang."""
        n = s["cfg"]["ukuran"]
        walls = self._wallset(s)
        names = s["names"]
        me = s["bots"][p]
        my_name = names[p]
        seen = {nm: r for nm, r in obs["robot"].items() if nm != my_name}
        others = {(r["baris"], r["kolom"]) for r in seen.values() if r["hidup"]}
        crystals = [list(x) for x in obs["kristal"]]
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

        def _ray_from(origin, arah, targets):
            dr, dk = ARAH[arah]
            r, k = origin
            while True:
                r, k = r + dr, k + dk
                if not (0 <= r < n and 0 <= k < n) or (r, k) in walls:
                    return None
                if (r, k) in targets:
                    return (r, k)

        def posisi(nama=None):
            if nama is None or nama == my_name:
                return [me["r"], me["c"]]
            if nama not in names:
                raise ActionError(f"tidak ada robot bernama {nama!r}")
            r = seen.get(nama)
            return [r["baris"], r["kolom"]] if r else None

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

        def _nearest(points):
            d, _ = bfs()
            best = None
            for pt in points:
                v = d.get((pt[0], pt[1]))
                if v is not None and (best is None or v < best[0]):
                    best = (v, pt)
            return best[1] if best else None

        def kristal_terdekat():
            x = _nearest(crystals)
            return list(x) if x else None

        def powerup_terdekat():
            pts = [(x["baris"], x["kolom"], x["jenis"]) for x in obs.get("powerup", [])]
            x = _nearest(pts)
            return {"baris": x[0], "kolom": x[1], "jenis": x[2]} if x else None

        def musuh_terdekat():
            d, _ = bfs()
            best = None
            for nm, r in seen.items():
                if not r["hidup"]:
                    continue
                v = d.get((r["baris"], r["kolom"]), 10**6)
                if best is None or v < best[0]:
                    best = (v, nm)
            return best[1] if best else None

        def bisa_kena():
            for a in ("atas", "bawah", "kiri", "kanan"):
                if _ray_from((me["r"], me["c"]), a, others):
                    return a
            return None

        def terancam():
            mine = {(me["r"], me["c"])}
            for r in seen.values():
                if not r["hidup"] or r["siap_tembak"] > 1:
                    continue
                blockers = (others - {(r["baris"], r["kolom"])}) | mine
                for a in ARAH:
                    if _ray_from((r["baris"], r["kolom"]), a, blockers) in mine:
                        return True
            return False

        def bisa_jalan(arah):
            arah = str(arah).lower()
            if arah not in ARAH:
                raise ActionError("arah harus 'atas', 'bawah', 'kiri', atau 'kanan'")
            dr, dk = ARAH[arah]
            t = (me["r"] + dr, me["c"] + dk)
            return 0 <= t[0] < n and 0 <= t[1] < n and t not in walls and t not in others

        def arah_tembak_ke(r, k):
            t = _pt(r, k)
            for a in ARAH:
                if _ray_from((me["r"], me["c"]), a, {t}) == t:
                    return a
            return None

        def petak_mungkin(nama):
            if nama not in names:
                raise ActionError(f"tidak ada robot bernama {nama!r}")
            r = seen.get(nama) if nama != my_name else {"baris": me["r"], "kolom": me["c"], "hidup": me["hidup"]}
            if not r or not r["hidup"]:
                return []
            out = [[r["baris"], r["kolom"]]]
            for dr, dk in ARAH.values():
                x, y = r["baris"] + dr, r["kolom"] + dk
                if 0 <= x < n and 0 <= y < n and (x, y) not in walls:
                    out.append([x, y])
            return out

        def tebak_langkah(nama):
            if nama not in names:
                raise ActionError(f"tidak ada robot bernama {nama!r}")
            r = seen.get(nama)
            if not r:
                return None
            start = (r["baris"], r["kolom"])
            if not r["hidup"] or not crystals:
                return [start[0], start[1]]
            block = (others - {start}) | {(me["r"], me["c"])}
            goals = {tuple(cr) for cr in crystals}
            prev = {start: None}
            q = deque([start])
            found = None
            while q:
                cur = q.popleft()
                if cur in goals:
                    found = cur
                    break
                for a in ("atas", "bawah", "kiri", "kanan"):
                    dr, dk = ARAH[a]
                    nx = (cur[0] + dr, cur[1] + dk)
                    if 0 <= nx[0] < n and 0 <= nx[1] < n and nx not in walls and nx not in block and nx not in prev:
                        prev[nx] = cur
                        q.append(nx)
            if found is None or found == start:
                return [start[0], start[1]]
            while prev[found] != start:
                found = prev[found]
            return [found[0], found[1]]

        def aman(r, k):
            return self._safe(s, *_pt(r, k))

        return {"posisi": posisi, "jarak": jarak, "langkah_ke": langkah_ke, "kristal_terdekat": kristal_terdekat,
                "musuh_terdekat": musuh_terdekat, "bisa_kena": bisa_kena, "terancam": terancam, "bisa_jalan": bisa_jalan,
                "arah_tembak_ke": arah_tembak_ke, "tebak_langkah": tebak_langkah, "petak_mungkin": petak_mungkin,
                "powerup_terdekat": powerup_terdekat, "aman": aman}
