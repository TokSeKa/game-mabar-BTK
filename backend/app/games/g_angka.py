"""Tiga game tebak-tebakan simultan: Angka Dua Pertiga, Pasar Malam Sepi, dan Dilema Kas Desa."""

from __future__ import annotations

import math
from typing import Any

from .base import ActionError, Game, Setting, as_int


class DuaPertiga(Game):
    id = "duapertiga"
    nama = "Angka Dua Pertiga"
    ringkas = "Semua menebak angka 0–100. Yang paling dekat dengan ⅔ rata-rata tebakan menang ronde itu."
    hint_aksi = "angka bulat 0 sampai batas"
    timer = 20
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 10, 1, 50),
        Setting("faktor", "Faktor target", "float", 0.667, 0.1, 1.0, ket="Target = faktor × rata-rata tebakan."),
        Setting("batas", "Angka maksimal", "int", 100, 10, 1000),
    ]
    aturan = """
- Setiap ronde semua pemain menebak satu angka bulat dari 0 sampai *batas* (default 100), bersamaan.
- **Target = faktor × rata-rata semua tebakan** (default ⅔).
- Pemain yang tebakannya paling dekat dengan target mendapat **1 poin** (kalau seri, semua yang seri dapat 1).
- Semua tebakan dibuka setelah ronde. Poin terbanyak setelah semua ronde menang.
- Intinya: menebak apa yang ditebak orang lain, yang juga sedang menebak tebakanmu.
"""
    format_aksi = "Satu angka bulat, misalnya `33`."
    format_info = """```
{ "ronde": 2, "ronde_total": 10, "faktor": 0.667, "batas": 100, "skor": {"Budi": 1, ...},
  "riwayat": [ {"ronde": 1, "tebakan": {"Budi": 33, "Ani": 50}, "rata": 41.5, "target": 27.7, "pemenang": ["Budi"]} ] }
```"""
    templates = [
        {"id": "sepertiga", "nama": "Sepertiga", "ket": "Selalu 33 (anggap lawan menebak acak di sekitar 50).", "kode": "def aksi():\n    return 33\n"},
        {"id": "level2", "nama": "Berpikir Dua Lapis", "ket": "Menganggap lawan menebak 33, jadi menebak ⅔ dari 33.",
         "kode": 'def aksi():\n    i = info()\n    return int(i["faktor"] * i["faktor"] * i["batas"] / 2)\n'},
        {"id": "ikut_target", "nama": "Pengejar Target", "ket": "Menebak ⅔ dari target ronde lalu (lawan cenderung makin kecil).", "kode": '''def aksi():
    i = info()
    if not i["riwayat"]:
        return 30
    return int(i["riwayat"][-1]["target"] * i["faktor"])
'''},
    ]

    def init(self, cfg, names, seed):
        return {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * len(names), "riwayat": []}

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s):
        c = s["cfg"]
        return {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "faktor": c["faktor"], "batas": c["batas"],
                "skor": dict(zip(s["names"], s["skor"])), "riwayat": s["riwayat"]}

    def validate(self, s, p, a):
        x = as_int(a, "tebakan")
        if not 0 <= x <= s["cfg"]["batas"]:
            raise ActionError(f"tebakan harus 0 sampai {s['cfg']['batas']}")
        return x

    def default(self, s, p):
        return s["cfg"]["batas"] // 3

    def apply(self, s, actions):
        n = s["names"]
        rata = sum(actions.values()) / len(actions)
        target = rata * s["cfg"]["faktor"]
        best = min(abs(v - target) for v in actions.values())
        win = [i for i, v in actions.items() if abs(abs(v - target) - best) < 1e-9]
        for i in win:
            s["skor"][i] += 1
        entry = {"ronde": s["ronde"], "tebakan": {n[i]: v for i, v in actions.items()}, "rata": round(rata, 3),
                 "target": round(target, 3), "pemenang": [n[i] for i in win]}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]


class PasarMalamSepi(Game):
    id = "farol"
    nama = "Pasar Malam Sepi"
    ringkas = "Datang ke pasar malam atau di rumah? Asyik kalau sepi, sumpek kalau terlalu ramai. Kalau semua berpikir sama, semua rugi."
    hint_aksi = "'datang' atau 'rumah'"
    timer = 12
    max_pemain = 12
    settings = [
        Setting("malam", "Jumlah malam", "int", 20, 1, 100),
        Setting("kapasitas", "Kapasitas nyaman (%)", "int", 60, 10, 90, ket="Persentase pemain yang boleh datang supaya tetap nyaman."),
    ]
    aturan = """
- Setiap malam semua pemain memilih **datang** ke pasar malam atau **rumah**, bersamaan.
- Kalau yang datang **tidak lebih dari kapasitas** (default 60% pemain, dibulatkan ke bawah, minimal 1), semua yang datang dapat **+1** (asyik).
- Kalau yang datang **melebihi kapasitas**, semua yang datang dapat **−1** (sumpek). Yang di rumah selalu 0.
- Semua pilihan dibuka setelah malam selesai. Skor tertinggi setelah semua malam menang.
"""
    format_aksi = "Teks `\"datang\"` atau `\"rumah\"` (atau `True`/`False`)."
    format_info = """```
{ "malam": 4, "malam_total": 20, "kapasitas": 3, "skor": {"Budi": 2, ...},
  "riwayat": [ {"malam": 1, "datang": ["Budi", "Ani"], "jumlah": 2, "ramai": false} ] }
```"""
    templates = [
        {"id": "kebalikan", "nama": "Kebalikan Kemarin", "ket": "Kalau kemarin ramai, di rumah. Kalau sepi, datang.", "kode": '''def aksi():
    i = info()
    if not i["riwayat"]:
        return "datang"
    return "rumah" if i["riwayat"][-1]["ramai"] else "datang"
'''},
        {"id": "rata3", "nama": "Peramal 3 Malam", "ket": "Memperkirakan pengunjung dari rata-rata 3 malam terakhir.", "kode": '''def aksi():
    i = info()
    r = i["riwayat"][-3:]
    if not r:
        return "datang"
    perkiraan = sum(x["jumlah"] for x in r) / len(r)
    return "datang" if perkiraan < i["kapasitas"] else "rumah"
'''},
        {"id": "selang", "nama": "Selang-seling", "ket": "Datang di malam ganjil, di rumah di malam genap.",
         "kode": 'def aksi():\n    return "datang" if info()["malam"] % 2 == 1 else "rumah"\n'},
        {"id": "bergiliran", "nama": "Bergiliran Kursi", "ket": "Memakai nomor kursi supaya tiap malam yang datang pas kapasitas (kalau semua memakai cara ini).", "kode": '''def aksi():
    i = info()
    return "datang" if (i["malam"] + saya()) % jumlah_pemain() < i["kapasitas"] else "rumah"
'''},
    ]

    def init(self, cfg, names, seed):
        cap = max(1, math.floor(len(names) * cfg["kapasitas"] / 100))
        return {"seed": seed, "names": names, "cfg": cfg, "cap": cap, "malam": 1, "skor": [0] * len(names), "riwayat": []}

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s):
        return {"malam": min(s["malam"], s["cfg"]["malam"]), "malam_total": s["cfg"]["malam"], "kapasitas": s["cap"],
                "skor": dict(zip(s["names"], s["skor"])), "riwayat": s["riwayat"]}

    def validate(self, s, p, a):
        if a is True or (isinstance(a, str) and a.strip().lower() in ("datang", "ya", "pergi")):
            return "datang"
        if a is False or (isinstance(a, str) and a.strip().lower() in ("rumah", "tidak", "diam")):
            return "rumah"
        raise ActionError("pilih 'datang' atau 'rumah'")

    def default(self, s, p):
        return "rumah"

    def apply(self, s, actions):
        n = s["names"]
        come = [i for i, v in actions.items() if v == "datang"]
        ramai = len(come) > s["cap"]
        for i in come:
            s["skor"][i] += -1 if ramai else 1
        entry = {"malam": s["malam"], "datang": [n[i] for i in come], "jumlah": len(come), "ramai": ramai}
        s["riwayat"].append(entry)
        s["malam"] += 1
        return [{"jenis": "malam", **entry}]

    def over(self, s):
        return s["malam"] > s["cfg"]["malam"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]


class KasDesa(Game):
    id = "kasdesa"
    nama = "Dilema Kas Desa"
    ringkas = "Tiap ronde dapat 10 koin. Sumbang ke kas desa (dilipatgandakan lalu dibagi rata) atau simpan sendiri. Kerja sama atau khianat?"
    hint_aksi = "jumlah koin yang disumbang"
    timer = 20
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 12, 1, 50),
        Setting("pendapatan", "Koin per ronde", "int", 10, 1, 100),
        Setting("pengali", "Pengali kas", "float", 1.6, 1.0, 5.0, ket="Kas dikali angka ini sebelum dibagi rata."),
        Setting("terbuka", "Sumbangan tiap orang terlihat", "bool", True, ket="Kalau mati, hanya total kas yang terlihat."),
    ]
    aturan = """
- Setiap ronde setiap pemain mendapat *pendapatan* (default 10 koin) dan memilih berapa yang **disumbang** ke kas desa (0 sampai 10).
- Total kas **dikali pengali** (default 1,6) lalu **dibagi rata** ke semua pemain, termasuk yang tidak menyumbang.
- Koin yang tidak disumbang langsung masuk tabunganmu. Tabungan terbanyak setelah semua ronde menang.
- Kalau semua menyumbang penuh, semua untung besar. Tapi yang tidak menyumbang selalu untung lebih banyak dari yang menyumbang di ronde itu.
"""
    format_aksi = "Satu angka bulat 0 sampai pendapatan, misalnya `10`."
    format_info = """```
{ "ronde": 3, "ronde_total": 12, "pendapatan": 10, "pengali": 1.6, "terbuka": true,
  "skor": {"Budi": 31.2, ...},
  "riwayat": [ {"ronde": 1, "sumbangan": {"Budi": 10, "Ani": 0}, "total": 10, "bagian": 8.0} ] }
```
Kalau `terbuka` mati, `sumbangan` berisi `None`."""
    templates = [
        {"id": "dermawan", "nama": "Dermawan", "ket": "Selalu menyumbang penuh.", "kode": 'def aksi():\n    return info()["pendapatan"]\n'},
        {"id": "balas", "nama": "Balas Setara", "ket": "Menyumbang sebesar rata-rata sumbangan ronde lalu.", "kode": '''def aksi():
    i = info()
    if not i["riwayat"]:
        return i["pendapatan"]
    r = i["riwayat"][-1]
    return int(r["total"] / jumlah_pemain())
'''},
        {"id": "akhir_pelit", "nama": "Akhir Pelit", "ket": "Kerja sama penuh, kecuali 2 ronde terakhir.", "kode": '''def aksi():
    i = info()
    if i["ronde"] > i["ronde_total"] - 2:
        return 0
    return i["pendapatan"]
'''},
    ]

    def init(self, cfg, names, seed):
        return {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0.0] * len(names), "riwayat": []}

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s):
        c = s["cfg"]
        return {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "pendapatan": c["pendapatan"],
                "pengali": c["pengali"], "terbuka": c["terbuka"],
                "skor": {n: round(x, 2) for n, x in zip(s["names"], s["skor"])}, "riwayat": s["riwayat"]}

    def validate(self, s, p, a):
        x = as_int(a, "sumbangan")
        if not 0 <= x <= s["cfg"]["pendapatan"]:
            raise ActionError(f"sumbangan harus 0 sampai {s['cfg']['pendapatan']}")
        return x

    def default(self, s, p):
        return 0

    def apply(self, s, actions):
        n, c = s["names"], s["cfg"]
        total = sum(actions.values())
        bagian = total * c["pengali"] / len(n)
        for i, v in actions.items():
            s["skor"][i] += c["pendapatan"] - v + bagian
        entry = {"ronde": s["ronde"], "sumbangan": {n[i]: (v if c["terbuka"] else None) for i, v in actions.items()},
                 "total": total, "bagian": round(bagian, 3)}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [round(x, 2) for x in s["skor"]]
