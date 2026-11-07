"""Tenggelamkan Kapal: susun armada rahasia, lalu bergantian menembak petak lawan."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

ARMADA = {"standar": [5, 4, 3, 3, 2], "kecil": [4, 3, 2, 2], "besar": [5, 4, 4, 3, 3, 2]}
KAPAL = {5: "Kapal Induk", 4: "Kapal Perang", 3: "Kapal Selam", 2: "Kapal Patroli"}


def cells(r: int, c: int, o: str, size: int) -> list[tuple[int, int]]:
    return [(r + (k if o == "V" else 0), c + (k if o == "H" else 0)) for k in range(size)]


class TenggelamkanKapal(Game):
    id = "kapal"
    nama = "Tenggelamkan Kapal"
    ringkas = "1 lawan 1. Susun armada di papan rahasia, lalu bergantian menembak. Tenggelamkan semua kapal lawan lebih dulu."
    kategori = "giliran"
    min_pemain, max_pemain = 2, 2
    hint_aksi = "susunan kapal atau koordinat tembakan"
    timer = 30
    settings = [
        Setting("ukuran", "Ukuran papan", "int", 10, 6, 12),
        Setting("armada", "Armada", "pilihan", "standar",
                pilihan=[["standar", "Standar (5,4,3,3,2)"], ["kecil", "Kecil (4,3,2,2)"], ["besar", "Besar (5,4,4,3,3,2)"]]),
        Setting("tembak_lagi", "Kena = tembak lagi", "bool", False, grup="aturan", ket="Kalau aktif, tembakan yang kena memberi tembakan tambahan."),
        Setting("info_tenggelam", "Kabar kapal tenggelam", "pilihan", "ukuran", grup="informasi",
                pilihan=[["ukuran", "Tenggelam + ukuran kapal diumumkan"], ["tenggelam", "Hanya 'tenggelam' (tanpa ukuran)"],
                         ["tidak", "Tidak diumumkan (hanya kena/meleset)"]],
                ket="Makin sedikit kabar, makin susah tahu kapan berhenti memburu satu kapal."),
        Setting("salvo", "Salvo", "bool", False, grup="aturan",
                ket="Setiap giliran kamu menembak sebanyak kapalmu yang masih mengapung. Kehilangan kapal = tembakan berkurang."),
        Setting("sonar", "Sonar per pemain", "int", 0, 0, 3, grup="aturan",
                ket="Sonar memakai satu tembakan untuk menghitung petak kapal lawan (yang belum kena) di area 3×3."),
        Setting("ranjau", "Ranjau per papan", "int", 0, 0, 6, grup="kejutan",
                ket="Ranjau disebar acak di air setiap papan. Menembak ranjau lawan = sisa tembakanmu hangus dan giliranmu berikutnya dilewati."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut", "ket": "Kapal tenggelam tidak diumumkan, hanya kena/meleset.", "nilai": {"info_tenggelam": "tidak"}},
        {"id": "kacau", "nama": "Kacau", "ket": "Salvo, 2 sonar, dan 3 ranjau per papan.", "nilai": {"salvo": True, "sonar": 2, "ranjau": 3}},
    ]
    aturan = """
- **Fase susun:** kedua pemain menyusun armadanya secara rahasia di papan (default 10×10). Kapal lurus (mendatar atau menurun), tidak boleh keluar papan atau bertumpuk. Boleh bersentuhan.
- **Fase tembak:** pemain bergantian menembak satu petak papan lawan. Hasilnya: *meleset*, *kena*, atau *tenggelam* (kalau semua petak kapal itu sudah kena). Ukuran kapal yang tenggelam diumumkan.
- Yang pertama menenggelamkan seluruh armada lawan menang. Siapa yang menembak duluan ditentukan undian di awal.
- Kalau waktu habis: susunan diacak otomatis / tembakan diarahkan ke petak acak yang belum ditembak.
- Opsi host: **kabar tenggelam** (ukuran diumumkan / hanya "tenggelam" / tidak diumumkan), **salvo** (tembakan per giliran = kapalmu yang
  masih mengapung), **sonar** (hitung petak kapal lawan di area 3×3, memakai satu tembakan), **ranjau** (menembak ranjau lawan = sisa
  tembakan hangus dan giliran berikutnya dilewati), **kena = tembak lagi**.
"""
    format_aksi = """- Fase `susun`: list posisi untuk setiap kapal sesuai urutan `armada`, masing-masing `[baris, kolom, arah]` dengan arah `"H"` (mendatar ke kanan) atau `"V"` (menurun ke bawah). Baris & kolom mulai dari 0.
  Contoh armada standar: `[[0,0,"H"], [2,0,"H"], [4,0,"H"], [6,0,"H"], [8,0,"H"]]`.
- Fase `tembak`: `[baris, kolom]`, misalnya `[3, 7]`. Kalau sonar diaktifkan: `{"sonar": [baris, kolom]}` (pusat area 3×3)."""
    format_info = """```
{ "fase": "susun" | "tembak", "ukuran": 10, "armada": [5,4,3,3,2], "giliran": "Budi",
  "papan_saya": ["K.....", ...],    # baris teks: K = kapalku, x = tembakan lawan meleset, o = kapalku kena, # = kapalku tenggelam
  "papan_tembak": ["..x.o#", ...],  # tembakanku ke lawan: . belum, x meleset, o kena, # tenggelam
  "kapal_lawan_sisa": [5,3,2],      # ukuran kapal lawan yang belum tenggelam (None kalau ukuran dirahasiakan)
  "jumlah_kapal_lawan_sisa": 3,     # None kalau kabar tenggelam tidak diumumkan
  "sisa_tembak": 1, "sonar_sisa": 0, "ranjau": 0, "lewati": False,
  "riwayat": [ {"penembak": "Budi", "baris": 3, "kolom": 7, "hasil": "kena" | "meleset" | "tenggelam" | "ranjau", "ukuran": 3},
               {"penembak": "Ani", "sonar": [4, 4], "jumlah": 2} ] }
```
Di `papan_tembak` ranjau lawan yang kena ditandai `*`. Di `papan_saya`: `m` = ranjaumu, `*` = ranjaumu yang sudah kena."""
    lib_docs = [
        {"nama": "belum_ditembak", "jenis": "fungsi", "tanda": "belum_ditembak()", "ket": "List [baris, kolom] petak lawan yang belum pernah kamu tembak."},
        {"nama": "tetangga", "jenis": "fungsi", "tanda": "tetangga(baris, kolom)", "ket": "Petak atas/bawah/kiri/kanan yang masih di dalam papan."},
        {"nama": "susunan_valid", "jenis": "fungsi", "tanda": "susunan_valid(susunan)", "ket": "True kalau susunan kapal itu sah."},
    ]
    templates = [
        {"id": "pemburu", "nama": "Pemburu Papan Catur", "ket": "Menembak pola papan catur; kalau ada yang kena, memburu petak di sekitarnya.", "kode": '''def aksi():
    i = info()
    n = i["ukuran"]
    if i["fase"] == "susun":
        hasil = []
        baris = 0
        for ukuran in i["armada"]:
            hasil.append([baris, (baris * 3) % (n - ukuran + 1), "H"])
            baris += 2
        return hasil
    p = i["papan_tembak"]
    # buru di sekitar petak yang kena tapi kapalnya belum tenggelam
    for r in range(n):
        for c in range(n):
            if p[r][c] == "o":
                for t in tetangga(r, c):
                    if p[t[0]][t[1]] == ".":
                        return t
    for t in belum_ditembak():
        if (t[0] + t[1]) % 2 == 0:
            return t
    return belum_ditembak()[0]
'''},
        {"id": "penyapu", "nama": "Penyapu Baris", "ket": "Menembak baris demi baris dari pojok kiri atas.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "susun":
        return [[k * 2, 0, "H"] for k in range(len(i["armada"]))]
    return belum_ditembak()[0]
'''},
    ]

    # ------------------------------------------------------------ dasar
    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "fase": "susun", "fleet": ARMADA[cfg["armada"]],
             "ships": [None, None], "shots": [[], []], "riwayat": [], "winner": None, "sisa_tembak": 1,
             "sonar": [cfg.get("sonar", 0)] * 2, "ranjau": [[], []], "lewati": [False, False]}
        s["giliran"] = rng(s, "mulai").randint(0, 1)
        return s

    def pending(self, s):
        if s["winner"] is not None:
            return []
        if s["fase"] == "susun":
            return [i for i in (0, 1) if s["ships"][i] is None]
        return [s["giliran"]]

    def _grid_mine(self, s, p):
        n = s["cfg"]["ukuran"]
        g = [["."] * n for _ in range(n)]
        ships = s["ships"][p] or []
        enemy_shots = {(r, c) for r, c in s["shots"][1 - p]}
        for sh in ships:
            sunk = all(cell in enemy_shots for cell in map(tuple, sh["cells"]))
            for r, c in sh["cells"]:
                g[r][c] = "#" if sunk else ("o" if (r, c) in enemy_shots else "K")
        for r, c in s.get("ranjau", [[], []])[p]:
            g[r][c] = "*" if (r, c) in enemy_shots else "m"
        for r, c in enemy_shots:
            if g[r][c] == ".":
                g[r][c] = "x"
        return ["".join(row) for row in g]

    def _grid_shots(self, s, p, fog=True):
        """Tembakan p ke papan lawan. ``fog``: sembunyikan kapal tenggelam kalau kabar tenggelam tidak diumumkan."""
        n = s["cfg"]["ukuran"]
        g = [["."] * n for _ in range(n)]
        enemy = s["ships"][1 - p] or []
        mine = {(r, c) for r, c in s["shots"][p]}
        hide = fog and s["cfg"].get("info_tenggelam", "ukuran") == "tidak"
        for r, c in mine:
            g[r][c] = "x"
        for r, c in s.get("ranjau", [[], []])[1 - p]:
            if (r, c) in mine:
                g[r][c] = "*"
        for sh in enemy:
            cs = [tuple(x) for x in sh["cells"]]
            sunk = all(x in mine for x in cs)
            for x in cs:
                if x in mine:
                    g[x[0]][x[1]] = "#" if sunk and not hide else "o"
        return ["".join(row) for row in g]

    def _sisa_info(self, s, owner, fog):
        """Info kapal ``owner`` yang belum tenggelam menurut lawannya: (ukuran list | None, jumlah | None)."""
        left = self._left(s, owner) if s["ships"][owner] else list(s["fleet"])
        mode = s["cfg"].get("info_tenggelam", "ukuran") if fog else "ukuran"
        if mode == "ukuran":
            return left, len(left)
        if mode == "tenggelam":
            return None, len(left)
        return None, None

    def _fog_entry(self, s, e, fog):
        mode = s["cfg"].get("info_tenggelam", "ukuran")
        if not fog or mode == "ukuran" or "hasil" not in e:
            return e
        if mode == "tenggelam":
            return {**e, "ukuran": None}
        return {**e, "ukuran": None, "hasil": "kena" if e["hasil"] == "tenggelam" else e["hasil"]}

    def _left(self, s, p):
        ships = s["ships"][p] or []
        shots = {(r, c) for r, c in s["shots"][1 - p]}
        return [sh["size"] for sh in ships if not all(tuple(x) in shots for x in sh["cells"])]

    def _view(self, s, fog):
        n = s["names"]
        c = s["cfg"]
        return {"fase": s["fase"] if s["winner"] is None else "selesai", "ukuran": c["ukuran"], "armada": s["fleet"],
                "giliran": n[s["giliran"]] if s["fase"] == "tembak" else None,
                "tembakan": {n[p]: self._grid_shots(s, p, fog) for p in (0, 1)},
                "sisa": {n[p]: self._sisa_info(s, p, fog)[0] for p in (0, 1)},
                "jumlah_sisa": {n[p]: self._sisa_info(s, p, fog)[1] for p in (0, 1)},
                "sudah_susun": {n[p]: s["ships"][p] is not None for p in (0, 1)},
                "info_tenggelam": c.get("info_tenggelam", "ukuran"), "salvo": bool(c.get("salvo")), "ranjau": c.get("ranjau", 0),
                "sisa_tembak": s.get("sisa_tembak", 1), "sonar_sisa": {n[p]: s.get("sonar", [0, 0])[p] for p in (0, 1)},
                "lewati": {n[p]: s.get("lewati", [False, False])[p] for p in (0, 1)},
                "riwayat": [self._fog_entry(s, e, fog) for e in s["riwayat"][-40:]],
                "pemenang": n[s["winner"]] if s["winner"] is not None else None}

    def event_for(self, s, e, viewer):
        return self._fog_entry(s, e, viewer != "semua") if e.get("jenis") == "tembak" else e

    def public(self, s):
        return self._view(s, True)

    def full_view(self, s):
        return {**self._view(s, False), "papan": {s["names"][p]: self._grid_mine(s, p) for p in (0, 1)}}

    def observe(self, s, p):
        o = self._view(s, True)
        ukuran, jumlah = self._sisa_info(s, 1 - p, True)
        o.update({"saya": p, "nama_saya": s["names"][p], "lawan": s["names"][1 - p], "papan_saya": self._grid_mine(s, p),
                  "papan_tembak": self._grid_shots(s, p), "kapal_lawan_sisa": ukuran, "jumlah_kapal_lawan_sisa": jumlah})
        return o

    # ------------------------------------------------------------ aksi
    def _check_layout(self, s, layout) -> list[dict[str, Any]]:
        n = s["cfg"]["ukuran"]
        fleet = s["fleet"]
        if not isinstance(layout, (list, tuple)) or len(layout) != len(fleet):
            raise ActionError(f"susunan harus berisi {len(fleet)} kapal: {fleet}")
        used, out = set(), []
        for size, item in zip(fleet, layout):
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                raise ActionError("setiap kapal ditulis [baris, kolom, 'H'/'V']")
            r, c = as_int(item[0], "baris"), as_int(item[1], "kolom")
            o = str(item[2]).upper()
            if o not in ("H", "V"):
                raise ActionError("arah kapal harus 'H' atau 'V'")
            cs = cells(r, c, o, size)
            if any(not (0 <= x < n and 0 <= y < n) for x, y in cs):
                raise ActionError(f"kapal ukuran {size} di {r},{c} keluar papan")
            if any(x in used for x in cs):
                raise ActionError("ada kapal yang bertumpuk")
            used.update(cs)
            out.append({"size": size, "cells": [list(x) for x in cs], "r": r, "c": c, "o": o})
        return out

    def validate(self, s, p, a):
        if s["fase"] == "susun":
            return {"susun": self._check_layout(s, a)}
        if isinstance(a, dict) and "sonar" in a:
            if s.get("sonar", [0, 0])[p] <= 0:
                raise ActionError("sonar habis (atau tidak diaktifkan)")
            pt = a["sonar"]
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ActionError("sonar ditulis {'sonar': [baris, kolom]}")
            r, c = as_int(pt[0], "baris"), as_int(pt[1], "kolom")
            n = s["cfg"]["ukuran"]
            if not (0 <= r < n and 0 <= c < n):
                raise ActionError("koordinat sonar di luar papan")
            return {"sonar": [r, c]}
        if not isinstance(a, (list, tuple)) or len(a) != 2:
            raise ActionError("tembakan ditulis [baris, kolom]")
        r, c = as_int(a[0], "baris"), as_int(a[1], "kolom")
        n = s["cfg"]["ukuran"]
        if not (0 <= r < n and 0 <= c < n):
            raise ActionError("koordinat di luar papan")
        if [r, c] in s["shots"][p]:
            raise ActionError("petak itu sudah pernah kamu tembak")
        return {"tembak": [r, c]}

    def random_layout(self, s, p, attempt=0):
        n = s["cfg"]["ukuran"]
        g = rng(s, "susun", p, attempt)
        for _ in range(500):
            used, res = set(), []
            ok = True
            for size in s["fleet"]:
                for _ in range(200):
                    o = g.choice("HV")
                    r = g.randint(0, n - (size if o == "V" else 1))
                    c = g.randint(0, n - (size if o == "H" else 1))
                    cs = cells(r, c, o, size)
                    if not any(x in used for x in cs):
                        used.update(cs)
                        res.append([r, c, o])
                        break
                else:
                    ok = False
                    break
            if ok:
                return res
        raise RuntimeError("gagal menyusun")

    def default(self, s, p):
        if s["fase"] == "susun":
            return {"susun": self._check_layout(s, self.random_layout(s, p))}
        n = s["cfg"]["ukuran"]
        free = [[r, c] for r in range(n) for c in range(n) if [r, c] not in s["shots"][p]]
        g = rng(s, "tembak", p, len(s["shots"][p]))
        return {"tembak": g.choice(free)}

    def _shots_for(self, s, p):
        return max(1, len(self._left(s, p))) if s["cfg"].get("salvo") else 1

    def _place_mines(self, s):
        k = s["cfg"].get("ranjau", 0)
        n = s["cfg"]["ukuran"]
        for p in (0, 1):
            ships = {tuple(x) for sh in s["ships"][p] for x in sh["cells"]}
            free = [[r, c] for r in range(n) for c in range(n) if (r, c) not in ships]
            s["ranjau"][p] = sorted(rng(s, "ranjau", p).sample(free, min(k, len(free)))) if k > 0 else []

    def apply(self, s, actions):
        n = s["names"]
        if s["fase"] == "susun":
            for p, a in actions.items():
                s["ships"][p] = a["susun"]
            ev = [{"jenis": "susun", "pemain": [n[p] for p in actions]}]
            if all(x is not None for x in s["ships"]):
                s["fase"] = "tembak"
                self._place_mines(s)
                s["sisa_tembak"] = self._shots_for(s, s["giliran"])
                ev.append({"jenis": "mulai_tembak", "pertama": n[s["giliran"]]})
            return ev
        p = s["giliran"]
        a = actions[p]
        ev: list[dict[str, Any]] = []
        if "sonar" in a:
            r, c = a["sonar"]
            s["sonar"][p] -= 1
            shots = {tuple(x) for x in s["shots"][p]}
            cnt = sum(1 for sh in s["ships"][1 - p] for x in sh["cells"]
                      if abs(x[0] - r) <= 1 and abs(x[1] - c) <= 1 and tuple(x) not in shots)
            entry = {"penembak": n[p], "sonar": [r, c], "jumlah": cnt}
            s["riwayat"].append(entry)
            ev.append({"jenis": "sonar", **entry})
            s["sisa_tembak"] -= 1
        else:
            r, c = a["tembak"]
            s["shots"][p].append([r, c])
            hit = None
            for sh in s["ships"][1 - p]:
                if [r, c] in sh["cells"]:
                    hit = sh
            shots = {tuple(x) for x in s["shots"][p]}
            if hit is None and [r, c] in s["ranjau"][1 - p]:
                hasil, size = "ranjau", None
            elif hit is None:
                hasil, size = "meleset", None
            elif all(tuple(x) in shots for x in hit["cells"]):
                hasil, size = "tenggelam", hit["size"]
            else:
                hasil, size = "kena", None
            entry = {"penembak": n[p], "baris": r, "kolom": c, "hasil": hasil, "ukuran": size}
            s["riwayat"].append(entry)
            ev.append({"jenis": "tembak", **entry})
            if hasil == "ranjau":
                s["sisa_tembak"] = 0
                s["lewati"][p] = True
            elif not (s["cfg"]["tembak_lagi"] and hit is not None):
                s["sisa_tembak"] -= 1
        if not self._left(s, 1 - p):
            s["winner"] = p
        elif s["sisa_tembak"] <= 0:
            nxt = 1 - p
            if s["lewati"][nxt]:
                s["lewati"][nxt] = False
                ev.append({"jenis": "lewati", "pemain": n[nxt]})
                nxt = p
            s["giliran"] = nxt
            s["sisa_tembak"] = self._shots_for(s, nxt)
        return ev

    def over(self, s):
        return s["winner"] is not None

    def scores(self, s):
        sunk = [len(s["fleet"]) - len(self._left(s, 1 - p)) for p in (0, 1)]
        return [float((100 if s["winner"] == p else 0) + sunk[p]) for p in (0, 1)]

    def reveal(self, s):
        return {"papan": {s["names"][p]: self._grid_mine(s, p) for p in (0, 1)}}

    def bot_library(self, s, p, obs):
        n = s["cfg"]["ukuran"]

        def belum_ditembak():
            shot = {tuple(x) for x in s["shots"][p]}
            return [[r, c] for r in range(n) for c in range(n) if (r, c) not in shot]

        def tetangga(r, c):
            r, c = as_int(r), as_int(c)
            return [[x, y] for x, y in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if 0 <= x < n and 0 <= y < n]

        def susunan_valid(layout):
            try:
                self._check_layout(s, layout)
                return True
            except ActionError:
                return False

        return {"belum_ditembak": belum_ditembak, "tetangga": tetangga, "susunan_valid": susunan_valid}
