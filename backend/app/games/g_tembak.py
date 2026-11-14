"""Tembak Jitu: adu ketepatan dan kecepatan mouse/jari. Khusus pemain manusia.

Semua pemain mendapat urutan target yang sama (dari seed). Waktu reaksi dihitung di browser masing-masing sejak
target muncul di layarnya, jadi kecepatan jaringan tidak berpengaruh. Browser mengirim posisi tembakan relatif ke
pusat target dan waktu reaksinya; skor dihitung server. Server hanya mengirim target yang sedang aktif, jadi posisi
target berikutnya tidak bisa diintip.
"""

from __future__ import annotations

import math
from typing import Any

from .base import ActionError, Game, Setting, rng

RASIO = 0.625            # tinggi arena / lebar arena (16:10); koordinat dalam satuan lebar arena
UKURAN = {"besar": 0.085, "sedang": 0.06, "kecil": 0.042}
LAJU = {"diam": 0.0, "pelan": 0.12, "cepat": 0.26}      # lebar arena per detik
MS_MIN = 90              # reaksi lebih cepat dari ini dianggap tebakan (bukan reaksi manusia)


def jari_jari(r0: float, ms: float, waktu: float, menyusut: bool) -> float:
    if not menyusut:
        return r0
    return r0 * max(0.45, 1 - 0.55 * min(1.0, ms / waktu))


def nilai_tembakan(dx: float, dy: float, r: float, ms: float, waktu: float) -> tuple[int, float, int]:
    """(cincin 0–10, faktor waktu, poin). Cincin 10 = tepat di tengah. Faktor waktu turun proporsional dari 1.0 (instan)
    sampai 0.3 (di batas waktu target)."""
    d = math.hypot(dx, dy)
    if d > r:
        return 0, 0.0, 0
    cincin = max(1, min(10, math.ceil((1 - d / r) * 10)))
    faktor = max(0.3, 1 - 0.7 * min(1.0, max(0.0, ms) / waktu))
    return cincin, round(faktor, 3), int(round(cincin * 10 * faktor))


class TembakJitu(Game):
    id = "tembak"
    nama = "Tembak Jitu"
    ringkas = "Adu ketepatan & kecepatan: tembak lingkaran sasaran secepat dan setepat mungkin. Makin dekat ke tengah dan makin cepat, makin besar poinnya."
    kategori = "mandiri"
    min_pemain = 1
    max_pemain = 12
    mandiri = True
    bot = False
    hint_aksi = '{"target": nomor, "dx": .., "dy": .., "ms": ..} atau {"target": nomor, "lewat": True}'
    timer = 20
    jeda_pada, jeda_hasil = ("ronde_selesai",), 6
    label_skor = "Poin"
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 3, 1, 8),
        Setting("target", "Target per ronde", "int", 10, 3, 40),
        Setting("waktu_target", "Waktu tiap target (milidetik)", "int", 1600, 500, 5000,
                ket="Target hilang setelah sekian milidetik. Poin dikali faktor waktu: 1.0 kalau instan, turun proporsional sampai 0.3 di batas waktu."),
        Setting("ukuran", "Ukuran target", "pilihan", "sedang",
                pilihan=[["besar", "Besar"], ["sedang", "Sedang"], ["kecil", "Kecil (untuk jago)"]]),
        Setting("gerak", "Target bergerak", "pilihan", "diam", grup="kejutan",
                pilihan=[["diam", "Diam"], ["pelan", "Bergerak pelan"], ["cepat", "Bergerak cepat"]]),
        Setting("menyusut", "Target menyusut", "bool", False, grup="kejutan",
                ket="Target mengecil selama terlihat (sampai 45%). Menembak cepat = sasaran lebih besar."),
        Setting("sandera", "Ada sasaran sandera", "bool", False, grup="kejutan",
                ket="Sesekali muncul sasaran biru bergambar orang: JANGAN ditembak (−30). Menahan diri sampai hilang = +10."),
        Setting("ganda", "Target ganda", "bool", False, grup="kejutan",
                ket="Sesekali muncul dua target sekaligus; dua-duanya harus ditembak (satu peluru per target)."),
    ]
    presets = [
        {"id": "jago", "nama": "Penembak Jitu", "ket": "Target kecil, bergerak pelan, dan menyusut.",
         "nilai": {"ukuran": "kecil", "gerak": "pelan", "menyusut": True}},
        {"id": "refleks", "nama": "Refleks", "ket": "Target besar tapi waktunya singkat, ada sandera.",
         "nilai": {"waktu_target": 900, "sandera": True}},
        {"id": "kacau", "nama": "Kacau", "ket": "Bergerak cepat, target ganda, sandera.",
         "nilai": {"gerak": "cepat", "ganda": True, "sandera": True}},
    ]
    aturan = """
- Lingkaran sasaran (seperti papan tembak) muncul satu per satu di arena. **Klik / ketuk sasarannya**: makin dekat ke
  **titik tengah** makin tinggi cincinnya (10 di tengah, 1 di pinggir), dan makin **cepat** kamu menembak makin besar
  pengalinya.
- Poin satu tembakan = **cincin × 10 × faktor waktu**. Faktor waktu 1,0 kalau instan dan turun **proporsional** sampai
  0,3 di batas waktu target. Tembakan meleset (di luar lingkaran) atau terlambat = 0. **Satu peluru per target.**
- Semua pemain mendapat urutan sasaran yang sama, dan waktu reaksi dihitung **di browser masing-masing** sejak sasaran
  muncul di layarmu, jadi koneksi lambat tidak merugikan. Setiap ronde dimulai serentak dengan hitung mundur 3-2-1.
- Kejutan (opsi host): sasaran **bergerak**, **menyusut**, **sandera** biru (jangan ditembak: −30; tahan diri: +10), dan
  **target ganda**.
- Pemain dengan total poin tertinggi menang. Main di **layar penuh** (tombol ⛶) supaya arenanya besar.
"""
    format_aksi = """`{"target": k, "dx": 0.004, "dy": -0.01, "ms": 412}`: tembakan untuk target ke-k, posisi relatif ke pusat sasaran
(satuan lebar arena) dan waktu reaksi (milidetik). `{"target": k, "lewat": True}`: tidak menembak (waktu habis / sandera)."""

    # ------------------------------------------------------------ util
    def _targets(self, s, ronde):
        """Daftar sasaran satu ronde (sama untuk semua pemain)."""
        c = s["cfg"]
        r = rng(s, "sasaran", ronde)
        r0 = UKURAN[c["ukuran"]]
        out = []
        k = 0
        while len(out) < c["target"]:
            ganda = c["ganda"] and k > 0 and r.random() < 0.2 and len(out) + 2 <= c["target"]
            grup = []
            for j in range(2 if ganda else 1):
                sandera = c["sandera"] and not ganda and k > 1 and r.random() < 0.15
                x = r.uniform(r0 + 0.04, 1 - r0 - 0.04)
                y = r.uniform(r0 + 0.04, RASIO - r0 - 0.04)
                if ganda and j == 1 and grup:
                    # target kedua cukup jauh dari yang pertama
                    for _ in range(20):
                        if math.hypot(x - grup[0]["x"], y - grup[0]["y"]) > 4 * r0:
                            break
                        x = r.uniform(r0 + 0.04, 1 - r0 - 0.04)
                        y = r.uniform(r0 + 0.04, RASIO - r0 - 0.04)
                laju = LAJU[c["gerak"]]
                ang = r.uniform(0, 2 * math.pi)
                grup.append({"x": round(x, 4), "y": round(y, 4), "r": r0,
                             "vx": round(laju * math.cos(ang), 4), "vy": round(laju * math.sin(ang), 4),
                             "jeda": int(r.uniform(450, 1300)), "sandera": sandera})
            for j, t in enumerate(grup):
                t["grup"] = k
                t["kembar"] = len(grup) == 2
                t["jeda"] = grup[0]["jeda"] if j == 0 else 0
                out.append(t)
            k += 1
        return out

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * n, "riwayat": [],
             "kena_total": [0] * n, "cincin_total": [0] * n}
        self._new_round(s)
        return s

    def _new_round(self, s):
        n = len(s["names"])
        s["sasaran"] = self._targets(s, s["ronde"])
        s["ke"] = [0] * n
        s["hasil"] = [[] for _ in range(n)]
        s["poin_ronde"] = [0] * n

    def pending(self, s):
        if self.over(s):
            return []
        total = len(s["sasaran"])
        return [i for i in range(len(s["names"])) if s["ke"][i] < total]

    # ------------------------------------------------------------ tampilan
    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        total = len(s["sasaran"])
        v = {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "jumlah_target": total,
             "waktu_target": c["waktu_target"], "rasio": RASIO, "menyusut": c["menyusut"], "gerak": c["gerak"],
             "skor": dict(zip(n, s["skor"])), "poin_ronde": dict(zip(n, s["poin_ronde"])),
             "progres": {n[i]: s["ke"][i] for i in range(len(n))},
             "hasil": {n[i]: [dict(h) for h in s["hasil"][i]] for i in range(len(n))},
             "riwayat": [dict(e) for e in s["riwayat"]]}
        if viewer == "semua":
            v["sasaran"] = [dict(t) for t in s["sasaran"]]
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        v = self._view(s, p)
        k = s["ke"][p]
        # hanya sasaran yang sedang aktif (dan pasangannya kalau target ganda) yang dikirim
        aktif = []
        if k < len(s["sasaran"]):
            g = s["sasaran"][k]["grup"]
            for j in range(k, len(s["sasaran"])):
                if s["sasaran"][j]["grup"] != g:
                    break
                aktif.append({**s["sasaran"][j], "nomor": j})
        v["aktif"] = aktif
        v["ke"] = k
        return {**v, "saya": p, "nama_saya": s["names"][p]}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if not isinstance(a, dict):
            raise ActionError('kirim {"target": nomor, "dx": .., "dy": .., "ms": ..} atau {"target": nomor, "lewat": True}')
        try:
            k = int(a.get("target"))
        except (TypeError, ValueError):
            raise ActionError("nomor target tidak valid") from None
        if k != s["ke"][p]:
            raise ActionError("target itu sudah lewat")
        if a.get("lewat"):
            return {"target": k, "lewat": True}
        try:
            dx, dy, ms = float(a.get("dx")), float(a.get("dy")), float(a.get("ms"))
        except (TypeError, ValueError):
            raise ActionError("dx, dy, dan ms harus angka") from None
        if not all(math.isfinite(x) for x in (dx, dy, ms)):
            raise ActionError("dx, dy, dan ms harus angka")
        return {"target": k, "dx": max(-1.0, min(1.0, dx)), "dy": max(-1.0, min(1.0, dy)), "ms": max(0.0, min(60000.0, ms))}

    def default(self, s, p):
        return {"target": s["ke"][p], "lewat": True}

    def apply(self, s, actions):
        c, n = s["cfg"], s["names"]
        events: list[dict[str, Any]] = []
        for p, a in sorted(actions.items()):
            k = s["ke"][p]
            if k >= len(s["sasaran"]) or a["target"] != k:
                continue
            t = s["sasaran"][k]
            T = c["waktu_target"]
            if t["sandera"]:
                if a.get("lewat"):
                    h = {"nomor": k, "sandera": True, "tahan": True, "poin": 10}
                else:
                    h = {"nomor": k, "sandera": True, "tahan": False, "poin": -30}
            elif a.get("lewat"):
                h = {"nomor": k, "cincin": 0, "poin": 0, "ms": None, "meleset": False}
            else:
                ms = a["ms"]
                if ms < MS_MIN or ms > T + 150:
                    h = {"nomor": k, "cincin": 0, "poin": 0, "ms": int(ms), "meleset": True,
                         "catatan": "terlalu cepat (tebakan)" if ms < MS_MIN else "terlambat"}
                else:
                    r = jari_jari(t["r"], ms, T, c["menyusut"])
                    cincin, faktor, poin = nilai_tembakan(a["dx"], a["dy"], r, ms, T)
                    h = {"nomor": k, "cincin": cincin, "faktor": faktor, "poin": poin, "ms": int(ms), "meleset": cincin == 0,
                         "dx": round(a["dx"] / r, 3), "dy": round(a["dy"] / r, 3)}
                    if cincin:
                        s["kena_total"][p] += 1
                        s["cincin_total"][p] += cincin
            s["hasil"][p].append(h)
            s["skor"][p] += h["poin"]
            s["poin_ronde"][p] += h["poin"]
            s["ke"][p] += 1
            events.append({"jenis": "tembak", "pemain": n[p], **h})
        if all(x >= len(s["sasaran"]) for x in s["ke"]):
            events += self._end_round(s)
        return events

    def _end_round(self, s):
        n = s["names"]
        entry = {"ronde": s["ronde"], "poin": dict(zip(n, s["poin_ronde"])),
                 "rata_ms": {n[i]: (round(sum(h["ms"] for h in s["hasil"][i] if h.get("ms") and h.get("cincin")) /
                                          max(1, sum(1 for h in s["hasil"][i] if h.get("ms") and h.get("cincin")))))
                             for i in range(len(n))},
                 "kena": {n[i]: sum(1 for h in s["hasil"][i] if h.get("cincin")) for i in range(len(n))},
                 "sasaran": [dict(t) for t in s["sasaran"]],
                 "hasil": {n[i]: [dict(h) for h in s["hasil"][i]] for i in range(len(n))}}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "ronde_selesai", **{k: v for k, v in entry.items() if k not in ("sasaran", "hasil")}}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [float(x) for x in s["cincin_total"]]

    def reveal(self, s):
        return {"ronde": [{"ronde": e["ronde"], "poin": e["poin"]} for e in s["riwayat"]]}
