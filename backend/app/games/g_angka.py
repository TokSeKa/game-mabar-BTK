"""Tiga game tebak-tebakan simultan: Angka Dua Pertiga, Pasar Malam Sepi, dan Dilema Kas Desa."""

from __future__ import annotations

import math
from typing import Any

from .base import ActionError, Game, Setting, as_int, rng


class DuaPertiga(Game):
    id = "duapertiga"
    nama = "Angka Dua Pertiga"
    ringkas = ("Semua menebak angka 0–100. Target = faktor × rata-rata tebakan; yang paling dekat menang. "
               "Faktornya rahasia tiap ronde dan tebakan kembar gugur, jadi ikut-ikutan orang lain tidak aman.")
    hint_aksi = "angka bulat 0 sampai batas"
    timer = 20
    jeda_pada, jeda_hasil = ("ronde",), 5
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 10, 1, 50),
        Setting("batas", "Angka maksimal", "int", 100, 10, 1000),
        Setting("mode_faktor", "Faktor tiap ronde", "pilihan", "acak", grup="aturan",
                pilihan=[["acak", "Acak & rahasia (dibuka setelah ronde)"], ["tetap", "Tetap (klasik)"]],
                ket="Acak: faktor ronde ini diambil di antara batas bawah dan atas, baru diumumkan setelah semua menebak."),
        Setting("faktor_min", "Faktor acak: batas bawah", "float", 0.5, 0.1, 2.0, grup="aturan", jika={"mode_faktor": "acak"}),
        Setting("faktor_max", "Faktor acak: batas atas", "float", 1.5, 0.1, 2.0, grup="aturan", jika={"mode_faktor": "acak"}),
        Setting("faktor", "Faktor tetap", "float", 0.667, 0.1, 2.0, grup="aturan", jika={"mode_faktor": "tetap"},
                ket="Klasik: ⅔."),
        Setting("kembar_gugur", "Tebakan kembar gugur", "bool", True, grup="aturan",
                ket="Angka yang ditebak lebih dari satu orang tidak bisa menang (tetap ikut dihitung di rata-rata)."),
        Setting("acuan", "Acuan target", "pilihan", "rata", grup="aturan",
                pilihan=[["rata", "Rata-rata tebakan"], ["median", "Median (nilai tengah) tebakan"]],
                ket="Median tidak terpengaruh satu-dua tebakan ekstrem."),
        Setting("poin_mode", "Pembagian poin", "pilihan", "satu", grup="aturan",
                pilihan=[["satu", "Terdekat dapat 1"], ["bertingkat", "Tiga terdekat dapat 3-2-1"]]),
        Setting("tebakan_rahasia", "Tebakan lawan rahasia", "bool", False, grup="informasi",
                ket="Setelah ronde hanya rata-rata/median, target, dan pemenang yang dibuka; tebakan orang lain tidak."),
        Setting("terlarang", "Angka terlarang tiap ronde", "int", 0, 0, 10, grup="kejutan",
                ket="Sekian angka acak diumumkan di awal ronde. Tebakan di angka itu gugur (tidak bisa menang)."),
    ]
    presets = [
        {"id": "klasik", "nama": "Klasik ⅔", "ket": "Versi asli: faktor tetap ⅔, tebakan kembar tidak gugur.",
         "nilai": {"mode_faktor": "tetap", "kembar_gugur": False}},
        {"id": "kabut", "nama": "Kabut", "ket": "Tebakan orang lain tidak pernah dibuka.", "nilai": {"tebakan_rahasia": True}},
        {"id": "kacau", "nama": "Kacau", "ket": "Acuan median, poin 3-2-1, dan 5 angka terlarang tiap ronde.",
         "nilai": {"acuan": "median", "poin_mode": "bertingkat", "terlarang": 5}},
    ]
    aturan = """
- Setiap ronde semua pemain menebak satu angka bulat dari 0 sampai *batas* (default 100), bersamaan.
- **Target = faktor × rata-rata semua tebakan.** Pemain yang tebakannya paling dekat dengan target mendapat **1 poin**
  (kalau dua tebakan berbeda sama dekatnya, keduanya dapat 1).
- **Faktor acak & rahasia** (default): setiap ronde faktor diambil di antara 0,5 dan 1,5 (bisa diatur) dan **baru diumumkan setelah semua
  menebak**. Kadang target di bawah rata-rata, kadang di atas. Host bisa memilih faktor tetap (klasik ⅔).
- **Tebakan kembar gugur** (default): angka yang dipilih dua orang atau lebih tidak bisa menang, walaupun paling dekat. Tetap ikut dihitung
  di rata-rata.
- Semua tebakan dan faktor dibuka setelah ronde (kecuali opsi *tebakan lawan rahasia*). Poin terbanyak setelah semua ronde menang.
- Opsi host: **acuan median** (target = faktor × median, bukan rata-rata), **poin 3-2-1** (tiga tebakan sah terdekat), **angka terlarang**
  (diumumkan di awal ronde; tebakan di angka itu gugur).

**Kenapa begini:** di versi klasik semua orang cepat sadar jawabannya selalu turun ke 0 (faktor < 1), naik ke batas (faktor > 1),
atau berkumpul di tengah (faktor 1), lalu semua menebak sama dan permainan jadi membosankan. Dengan faktor rahasia, kamu harus
menebak *ke mana* rata-rata akan jatuh tanpa tahu persis pengalinya; dengan aturan kembar gugur, berkumpul di angka yang "jelas"
malah membuat semua yang di sana kalah. Kamu harus dekat dengan target **dan** berbeda dari orang lain.
"""
    format_aksi = "Satu angka bulat, misalnya `33`."
    format_info = """```
{ "ronde": 2, "ronde_total": 10, "batas": 100,
  "mode_faktor": "acak", "faktor": None, "faktor_min": 0.5, "faktor_max": 1.5, "faktor_rata": 1.0,
  "kembar_gugur": True, "acuan": "rata", "poin_mode": "satu", "terlarang": [13, 40], "tebakan_rahasia": False,
  "skor": {"Budi": 1, ...},
  "riwayat": [ {"ronde": 1, "tebakan": {"Budi": 33, "Ani": 50, "Citra": 50}, "rata": 44.3, "faktor": 1.12,
                "target": 49.6, "gugur": ["Ani", "Citra"], "pemenang": ["Budi"]} ] }
```
- `faktor` = faktor ronde ini kalau sudah diketahui (mode tetap), `None` kalau masih rahasia (mode acak).
- `faktor_rata` = faktor rata-rata yang bisa diharapkan (tengah-tengah batas bawah & atas, atau faktor tetap).
- `gugur` = pemain yang tebakannya kembar dengan orang lain atau kena angka terlarang (tidak bisa menang).
- `terlarang` = angka terlarang ronde ini (diumumkan di awal ronde). Riwayat juga berisi `poin` per pemain ronde itu.
- Kalau tebakan lawan rahasia, `tebakan` & `gugur` di riwayat hanya berisi milikmu."""
    templates = [
        {"id": "sepertiga", "nama": "Sepertiga", "ket": "Selalu 33 (anggap orang lain menebak di sekitar 50).", "kode": "def aksi():\n    return 33\n"},
        {"id": "level2", "nama": "Berpikir Dua Lapis", "ket": "Menganggap lawan menebak tengah-tengah, lalu dikali faktor yang diharapkan dua kali.",
         "kode": '''def aksi():
    i = info()
    f = i["faktor_rata"]
    return min(i["batas"], int(f * f * i["batas"] / 2))
'''},
        {"id": "ikut_target", "nama": "Pengejar Target", "ket": "Menebak target ronde lalu dikali faktor yang diharapkan.", "kode": '''def aksi():
    i = info()
    if not i["riwayat"]:
        return 30
    return min(i["batas"], int(i["riwayat"][-1]["target"] * i["faktor_rata"]))
'''},
        {"id": "unik", "nama": "Si Beda Sendiri", "ket": "Menebak acuan ronde lalu × faktor yang diharapkan, digeser sesuai nomor kursi supaya tidak kembar, dan menghindari angka terlarang.",
         "kode": '''def aksi():
    i = info()
    dasar = i["batas"] // 2
    if i["riwayat"]:
        dasar = int(i["riwayat"][-1]["rata"] * i["faktor_rata"])
    geser = (saya() + 1) // 2
    if saya() % 2 == 1:
        geser = -geser
    x = max(0, min(i["batas"], dasar + geser * 3))
    while x in i["terlarang"] and x < i["batas"]:
        x = x + 1
    return x
'''},
    ]

    def _range(self, c):
        lo, hi = sorted((c["faktor_min"], c["faktor_max"]))
        return lo, hi

    def _factor(self, s, ronde):
        c = s["cfg"]
        if c["mode_faktor"] == "tetap":
            return c["faktor"]
        lo, hi = self._range(c)
        return round(rng(s, "faktor", ronde).uniform(lo, hi), 3)

    def init(self, cfg, names, seed):
        return {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * len(names), "riwayat": []}

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def _terlarang(self, s, r):
        k = s["cfg"].get("terlarang", 0)
        if k <= 0:
            return []
        return sorted(rng(s, "terlarang", r).sample(range(s["cfg"]["batas"] + 1), min(k, s["cfg"]["batas"])))

    def _fog(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"].get("tebakan_rahasia"):
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return {**e, "tebakan": {n: (v if n == me else None) for n, v in e["tebakan"].items()},
                "gugur": [n for n in e["gugur"] if n == me]}

    def _view(self, s, viewer):
        c = s["cfg"]
        lo, hi = self._range(c)
        tetap = c["mode_faktor"] == "tetap"
        return {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "batas": c["batas"],
                "mode_faktor": c["mode_faktor"], "faktor": c["faktor"] if tetap else None,
                "faktor_min": None if tetap else lo, "faktor_max": None if tetap else hi,
                "faktor_rata": c["faktor"] if tetap else round((lo + hi) / 2, 3), "kembar_gugur": c["kembar_gugur"],
                "acuan": c.get("acuan", "rata"), "poin_mode": c.get("poin_mode", "satu"),
                "tebakan_rahasia": bool(c.get("tebakan_rahasia")),
                "terlarang": [] if self.over(s) else self._terlarang(s, s["ronde"]),
                "skor": dict(zip(s["names"], s["skor"])), "riwayat": [self._fog(s, e, viewer) for e in s["riwayat"]]}

    def event_for(self, s, e, viewer):
        return self._fog(s, e, viewer) if e.get("jenis") == "ronde" else e

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def validate(self, s, p, a):
        x = as_int(a, "tebakan")
        if not 0 <= x <= s["cfg"]["batas"]:
            raise ActionError(f"tebakan harus 0 sampai {s['cfg']['batas']}")
        return x

    def default(self, s, p):
        return s["cfg"]["batas"] // 3

    def apply(self, s, actions):
        n, c = s["names"], s["cfg"]
        vals = sorted(actions.values())
        rata = sum(vals) / len(vals)
        mid = len(vals) // 2
        median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
        acuan = median if c.get("acuan") == "median" else rata
        faktor = self._factor(s, s["ronde"])
        target = acuan * faktor
        hitung: dict[int, int] = {}
        for v in actions.values():
            hitung[v] = hitung.get(v, 0) + 1
        larang = set(self._terlarang(s, s["ronde"]))
        gugur = [i for i, v in actions.items() if (c["kembar_gugur"] and hitung[v] > 1) or v in larang]
        calon = {i: v for i, v in actions.items() if i not in gugur}
        dapat: dict[int, int] = {}
        if calon:
            jarak = sorted({round(abs(v - target), 9) for v in calon.values()})
            tingkat = [3, 2, 1] if c.get("poin_mode") == "bertingkat" else [1]
            for t, d in zip(tingkat, jarak):
                for i, v in calon.items():
                    if abs(round(abs(v - target), 9) - d) < 1e-9:
                        dapat[i] = t
        win = [i for i, t in dapat.items() if t == max(dapat.values())] if dapat else []
        for i, t in dapat.items():
            s["skor"][i] += t
        entry = {"ronde": s["ronde"], "tebakan": {n[i]: v for i, v in actions.items()}, "rata": round(rata, 3),
                 "median": median, "acuan": c.get("acuan", "rata"), "faktor": faktor, "target": round(target, 3),
                 "terlarang": sorted(larang), "gugur": [n[i] for i in gugur], "pemenang": [n[i] for i in sorted(win)],
                 "poin": {n[i]: t for i, t in dapat.items()}}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]


TEMPAT = [("pasar", "🎡 Pasar Malam", 1.0, 1), ("konser", "🎤 Konser", 0.5, 2), ("bazar", "🍢 Bazar Kuliner", 0.3, 3)]
SPESIAL = {"festival": "🎉 Festival: kapasitas ×1,5 dan hadiah ×2", "hujan": "🌧️ Hujan: kapasitas separuh"}


class PasarMalamSepi(Game):
    id = "farol"
    nama = "Pasar Malam Sepi"
    ringkas = "Datang ke pasar malam atau di rumah? Asyik kalau sepi, sumpek kalau terlalu ramai. Kalau semua berpikir sama, semua rugi."
    hint_aksi = "'datang' atau 'rumah' (atau nama tempat: 'pasar', 'konser', 'bazar')"
    timer = 12
    jeda_pada, jeda_hasil = ("malam",), 4
    max_pemain = 12
    settings = [
        Setting("malam", "Jumlah malam", "int", 20, 1, 100),
        Setting("kapasitas", "Kapasitas nyaman (%)", "int", 60, 10, 90, ket="Persentase pemain yang boleh datang supaya tetap nyaman."),
        Setting("jumlah_rahasia", "Jumlah pengunjung rahasia", "bool", False, grup="informasi",
                ket="Setelah malam, hanya diumumkan nyaman atau sumpek; jumlah dan siapa yang datang tidak dibuka."),
        Setting("kapasitas_mode", "Kapasitas tiap malam", "pilihan", "tetap", grup="aturan",
                pilihan=[["tetap", "Tetap"], ["berubah", "Berubah tiap malam (diumumkan sore hari)"],
                         ["rahasia", "Berubah & rahasia (dibuka setelah malam)"]],
                ket="Berubah: kapasitas acak 70%–130% dari biasanya."),
        Setting("tempat", "Jumlah tempat hiburan", "int", 1, 1, 3, grup="aturan",
                ket="2–3 tempat: 🎡 Pasar Malam (kapasitas besar, +1), 🎤 Konser (separuhnya, +2), 🍢 Bazar Kuliner (kecil, +3)."),
        Setting("hadiah", "Hadiah nyaman", "int", 1, 1, 5, grup="aturan", ket="Poin untuk yang datang ke tempat yang nyaman (dikali pengali tempat)."),
        Setting("hukuman", "Hukuman sumpek", "int", 1, 0, 5, grup="aturan", ket="Poin yang hilang kalau tempatnya terlalu ramai."),
        Setting("malam_spesial", "Malam spesial (%)", "int", 0, 0, 100, grup="kejutan",
                ket="Peluang tiap malam jadi 🎉 Festival (kapasitas ×1,5, hadiah ×2) atau 🌧️ Hujan (kapasitas separuh). Diumumkan sore hari."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut", "ket": "Jumlah pengunjung tidak dibuka dan kapasitas berubah diam-diam.",
         "nilai": {"jumlah_rahasia": True, "kapasitas_mode": "rahasia"}},
        {"id": "kacau", "nama": "Kacau", "ket": "Tiga tempat hiburan, kapasitas berubah, dan malam spesial.",
         "nilai": {"tempat": 3, "kapasitas_mode": "berubah", "malam_spesial": 30}},
    ]
    aturan = """
- Setiap malam semua pemain memilih **datang** ke pasar malam atau **rumah**, bersamaan.
- Kalau yang datang **tidak lebih dari kapasitas** (default 60% pemain, dibulatkan ke bawah, minimal 1), semua yang datang dapat **+1** (asyik).
- Kalau yang datang **melebihi kapasitas**, semua yang datang dapat **−1** (sumpek). Yang di rumah selalu 0.
- Semua pilihan dibuka setelah malam selesai. Skor tertinggi setelah semua malam menang.
- Opsi host: **beberapa tempat** (🎡 Pasar Malam +1, 🎤 Konser +2 dengan kapasitas separuhnya, 🍢 Bazar Kuliner +3 dengan kapasitas
  kecil), **kapasitas berubah** tiap malam (diumumkan atau rahasia), **hadiah/hukuman**, **malam spesial** (Festival / Hujan), dan
  **jumlah pengunjung rahasia**.
"""
    format_aksi = "Teks `\"datang\"` atau `\"rumah\"` (atau `True`/`False`). Kalau ada beberapa tempat: `\"pasar\"`, `\"konser\"`, atau `\"bazar\"`."
    format_info = """```
{ "malam": 4, "malam_total": 20, "kapasitas": 3, "skor": {"Budi": 2, ...},
  "tempat": [{"id": "pasar", "nama": "🎡 Pasar Malam", "kapasitas": 3, "hadiah": 1}, ...],
  "spesial": None, "hukuman": 1,
  "riwayat": [ {"malam": 1, "datang": ["Budi", "Ani"], "jumlah": 2, "ramai": false,
                "tempat": [{"id": "pasar", "kapasitas": 3, "jumlah": 2, "ramai": False, "datang": [...]}]} ] }
```
- `kapasitas`, `jumlah`, `ramai` di tingkat atas adalah milik tempat pertama (Pasar Malam), supaya bot lama tetap jalan.
- `kapasitas` None kalau kapasitas dirahasiakan. Kalau jumlah pengunjung rahasia, `jumlah` & `datang` di riwayat None (kecuali dirimu)."""
    templates = [
        {"id": "kebalikan", "nama": "Kebalikan Kemarin", "ket": "Kalau kemarin ramai, di rumah. Kalau sepi, datang.", "kode": '''def aksi():
    i = info()
    if not i["riwayat"]:
        return "datang"
    return "rumah" if i["riwayat"][-1]["ramai"] else "datang"
'''},
        {"id": "rata3", "nama": "Peramal 3 Malam", "ket": "Memperkirakan pengunjung dari rata-rata 3 malam terakhir (kalau jumlahnya terlihat).", "kode": '''def aksi():
    i = info()
    r = [x for x in i["riwayat"][-3:] if x["jumlah"] != None]
    if not r or i["kapasitas"] == None:
        return "datang" if i["malam"] % 2 == 1 else "rumah"
    perkiraan = sum(x["jumlah"] for x in r) / len(r)
    return "datang" if perkiraan < i["kapasitas"] else "rumah"
'''},
        {"id": "selang", "nama": "Selang-seling", "ket": "Datang di malam ganjil, di rumah di malam genap.",
         "kode": 'def aksi():\n    return "datang" if info()["malam"] % 2 == 1 else "rumah"\n'},
        {"id": "bergiliran", "nama": "Bergiliran Kursi", "ket": "Memakai nomor kursi supaya tiap malam yang datang pas kapasitas (kalau semua memakai cara ini).", "kode": '''def aksi():
    i = info()
    kap = i["kapasitas"]
    if kap == None:
        kap = jumlah_pemain() // 2
    return "datang" if (i["malam"] + saya()) % jumlah_pemain() < kap else "rumah"
'''},
        {"id": "pemburu_hadiah", "nama": "Pemburu Hadiah", "ket": "Kalau ada beberapa tempat, bergiliran ke tempat berhadiah besar sesuai nomor kursi.", "kode": '''def aksi():
    i = info()
    t = i["tempat"]
    k = (i["malam"] + saya()) % (len(t) + 1)
    if k == len(t):
        return "rumah"
    return t[len(t) - 1 - k]["id"]
'''},
    ]

    def _caps(self, s, night):
        """Kapasitas & hadiah tiap tempat untuk malam ``night``: list (id, nama, kapasitas, hadiah)."""
        c = s["cfg"]
        n = len(s["names"])
        m = 1.0
        if c.get("kapasitas_mode", "tetap") != "tetap":
            m = rng(s, "kapasitas", night).uniform(0.7, 1.3)
        sp = self._spesial(s, night)
        reward_mult = 1
        if sp == "festival":
            m *= 1.5
            reward_mult = 2
        elif sp == "hujan":
            m *= 0.5
        out = []
        for tid, nama, share, mult in TEMPAT[: c.get("tempat", 1)]:
            cap = max(1, math.floor(n * c["kapasitas"] / 100 * share * m))
            out.append((tid, nama, cap, c.get("hadiah", 1) * mult * reward_mult))
        return out

    def _spesial(self, s, night):
        pct = s["cfg"].get("malam_spesial", 0)
        if pct <= 0:
            return None
        g = rng(s, "spesial", night)
        return g.choice(sorted(SPESIAL)) if g.random() * 100 < pct else None

    def init(self, cfg, names, seed):
        cap = max(1, math.floor(len(names) * cfg["kapasitas"] / 100))
        return {"seed": seed, "names": names, "cfg": cfg, "cap": cap, "malam": 1, "skor": [0] * len(names), "riwayat": []}

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def _fog(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"].get("jumlah_rahasia"):
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        mine = [me] if me in e["datang"] else []
        return {**e, "datang": mine, "jumlah": None,
                "tempat": [{**t, "jumlah": None, "datang": [x for x in t["datang"] if x == me]} for t in e.get("tempat", [])]}

    def event_for(self, s, e, viewer):
        return self._fog(s, e, viewer) if e.get("jenis") == "malam" else e

    def _view(self, s, viewer):
        c = s["cfg"]
        night = min(s["malam"], c["malam"])
        hide_cap = c.get("kapasitas_mode") == "rahasia" and viewer != "semua"
        caps = self._caps(s, night)
        tempat = [{"id": t, "nama": nm, "kapasitas": None if hide_cap else cap, "hadiah": r} for t, nm, cap, r in caps]
        sp = self._spesial(s, night)
        return {"malam": night, "malam_total": c["malam"], "kapasitas": tempat[0]["kapasitas"], "tempat": tempat,
                "spesial": {"jenis": sp, "teks": SPESIAL[sp]} if sp else None, "hukuman": c.get("hukuman", 1),
                "jumlah_rahasia": bool(c.get("jumlah_rahasia")), "kapasitas_mode": c.get("kapasitas_mode", "tetap"),
                "skor": dict(zip(s["names"], s["skor"])), "riwayat": [self._fog(s, e, viewer) for e in s["riwayat"]]}

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def validate(self, s, p, a):
        ids = [t[0] for t in TEMPAT[: s["cfg"].get("tempat", 1)]]
        if a is True or (isinstance(a, str) and a.strip().lower() in ("datang", "ya", "pergi")):
            return "pasar"
        if a is False or (isinstance(a, str) and a.strip().lower() in ("rumah", "tidak", "diam")):
            return "rumah"
        if isinstance(a, str) and a.strip().lower() in ids:
            return a.strip().lower()
        raise ActionError("pilih 'datang' atau 'rumah'" + (f" (atau tempat: {', '.join(ids)})" if len(ids) > 1 else ""))

    def default(self, s, p):
        return "rumah"

    def apply(self, s, actions):
        n = s["names"]
        night = s["malam"]
        caps = self._caps(s, night)
        hukuman = s["cfg"].get("hukuman", 1)
        # aksi lama ("datang"/True/False) tetap diterima kalau apply dipanggil langsung
        actions = {i: ("pasar" if v in ("datang", True) else "rumah" if v in (False, None) else v) for i, v in actions.items()}
        tempat = []
        for tid, nama, cap, reward in caps:
            come = [i for i, v in actions.items() if v == tid]
            ramai = len(come) > cap
            for i in come:
                s["skor"][i] += -hukuman if ramai else reward
            tempat.append({"id": tid, "nama": nama, "kapasitas": cap, "hadiah": reward, "jumlah": len(come), "ramai": ramai,
                           "datang": [n[i] for i in come]})
        semua = [n[i] for i, v in actions.items() if v != "rumah"]
        sp = self._spesial(s, night)
        entry = {"malam": night, "datang": tempat[0]["datang"] if len(tempat) == 1 else semua, "jumlah": tempat[0]["jumlah"],
                 "ramai": tempat[0]["ramai"], "kapasitas": tempat[0]["kapasitas"], "spesial": sp, "tempat": tempat}
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
    ringkas = ("Tiap ronde dapat 10 koin. Sumbang ke kas desa atau simpan sendiri. Kalau kas mencapai target, semua dapat bonus; "
               "kalau kurang, sumbangan terasa sia-sia. Siapa yang mau menutup kekurangannya?")
    hint_aksi = "jumlah koin yang disumbang (atau sanksi di fase sanksi)"
    timer = 20
    jeda_pada, jeda_hasil = ("ronde",), 6
    settings = [
        Setting("ronde", "Jumlah ronde", "int", 12, 1, 50),
        Setting("pendapatan", "Koin per ronde", "int", 10, 1, 100),
        Setting("pengali", "Pengali kas", "float", 1.6, 1.0, 5.0, ket="Kas dikali angka ini sebelum dibagi rata."),
        Setting("target", "Target kas (%)", "int", 50, 0, 100, grup="aturan",
                ket="Persen dari total pendapatan semua pemain. Kalau kas ronde itu mencapai target, semua dapat bonus. 0 = tanpa target (versi klasik)."),
        Setting("bonus", "Bonus target (koin/orang)", "int", 10, 0, 200, grup="aturan", ket="Diterima SEMUA pemain kalau target tercapai."),
        Setting("akhir_rahasia", "Ronde terakhir dirahasiakan", "bool", True, grup="informasi",
                ket="Jumlah ronde sebenarnya acak di sekitar angka di atas (±25%), jadi tidak ada yang tahu kapan aman berkhianat."),
        Setting("terbuka", "Sumbangan tiap orang terlihat", "bool", True, grup="informasi", ket="Kalau mati, hanya total kas yang terlihat."),
        Setting("pengali_rahasia", "Pengali kas rahasia", "bool", False, grup="informasi",
                ket="Pengali tiap ronde acak (½× sampai 1½× pengali) dan baru dibuka setelah ronde."),
        Setting("denda", "Denda (koin hilang per koin)", "int", 0, 0, 5, grup="aturan",
                ket="Menambah fase SANKSI setelah sumbangan dibuka: setiap koin yang kamu bayar menghapus sekian koin tabungan orang yang kamu pilih. "
                    "Maksimal bayar = pendapatan per ronde. 0 = mati."),
        Setting("usir", "Voting usir", "bool", False, grup="aturan",
                ket="Di fase sanksi tiap pemain boleh memilih satu orang. Yang dipilih lebih dari separuh pemain lain diusir di ronde berikutnya: "
                    "tidak bisa menyumbang dan tidak dapat bagian kas maupun bonus."),
        Setting("bencana", "Bencana (% tabungan)", "int", 0, 0, 100, grup="kejutan",
                ket="Kalau target kas gagal 2 ronde berturut-turut, banjir datang: semua kehilangan sekian persen tabungan. Perlu target > 0."),
    ]
    presets = [
        {"id": "klasik", "nama": "Klasik", "ket": "Versi asli: tanpa target, jumlah ronde diketahui (menyumbang 0 selalu paling untung).",
         "nilai": {"target": 0, "akhir_rahasia": False}},
        {"id": "kabut", "nama": "Kabut", "ket": "Sumbangan tiap orang dan pengali kas dirahasiakan.", "nilai": {"terbuka": False, "pengali_rahasia": True}},
        {"id": "sanksi", "nama": "Desa Tegas", "ket": "Ada denda dan voting usir untuk penumpang gelap, plus bencana kalau target sering gagal.",
         "nilai": {"denda": 3, "usir": True, "bencana": 30}},
    ]
    aturan = """
- Setiap ronde setiap pemain mendapat *pendapatan* (default 10 koin) dan memilih berapa yang **disumbang** ke kas desa (0 sampai 10).
- Total kas **dikali pengali** (default 1,6) lalu **dibagi rata** ke semua pemain, termasuk yang tidak menyumbang.
- **Target gotong royong:** tiap ronde desa punya target kas (default 50% dari total pendapatan semua pemain, misalnya 4 pemain → 20 koin).
  Kalau kas ronde itu **mencapai target**, **semua** pemain mendapat **bonus** (default +10 koin). Kalau kurang sedikit saja, bonusnya hilang.
- Koin yang tidak disumbang langsung masuk tabunganmu. Tabungan terbanyak setelah semua ronde menang.
- **Ronde terakhir dirahasiakan** (default): jumlah ronde sebenarnya ±25% dari angka di pengaturan, jadi strategi "khianat di ronde terakhir" berisiko.
- **Fase sanksi** (kalau host mengaktifkan denda atau voting usir): setelah sumbangan dibuka, semua bersamaan memilih **denda** (bayar koin
  untuk menghapus tabungan orang lain, misalnya bayar 1 → orang itu −3) dan/atau **usir** (satu nama). Yang dipilih lebih dari separuh pemain
  lain diusir di ronde berikutnya: tidak bisa menyumbang dan tidak dapat bagian kas maupun bonus.
- **Bencana** (opsi): target gagal 2 ronde berturut-turut → semua kehilangan sebagian tabungan.

**Kenapa menyumbang bisa masuk akal:** tanpa target, setiap koin yang kamu sumbang hanya kembali 1,6/jumlah pemain (selalu rugi untukmu).
Dengan target, kalau kas kurang sedikit dari target, menutup kekurangannya justru menguntungkanmu karena bonus untukmu sendiri lebih besar
daripada koin yang kamu keluarkan. Tapi kalau orang lain sudah menutup target, menyumbang lebih banyak lagi kembali rugi. Jadi pertanyaannya:
**siapa yang menutup target, dan apakah kamu percaya mereka?** Denda dan voting usir membuat penumpang gelap bisa dihukum.
"""
    format_aksi = """- Fase `sumbang`: satu angka bulat 0 sampai pendapatan, misalnya `10`.
- Fase `sanksi`: `{"denda": {"Budi": 2}, "usir": "Budi"}` (keduanya boleh kosong / `None`). Mengembalikan angka atau `None` di fase ini
  dianggap tanpa sanksi, jadi bot lama tetap jalan."""
    format_info = """```
{ "fase": "sumbang", "ronde": 3, "ronde_total": 12, "akhir_pasti": False, "pendapatan": 10, "pengali": 1.6, "terbuka": True,
  "target": 20, "bonus": 10, "pemain": 4, "denda": 0, "usir_aktif": False, "dikucilkan": [],
  "skor": {"Budi": 31.2, ...},
  "riwayat": [ {"ronde": 1, "sumbangan": {"Budi": 10, "Ani": 0}, "total": 22, "bagian": 8.8, "pengali": 1.6,
                "target": 20, "tercapai": True, "bonus": 10, "dikucilkan": [],
                "sanksi": {"denda": {"Budi": {"Ani": 2}}, "usir": {"Budi": "Ani"}, "diusir": ["Ani"]}} ] }
```
- `pengali` None kalau pengali rahasia (dibuka di riwayat setelah ronde); `pengali_kisaran` = [terkecil, terbesar] yang mungkin.
  `dikucilkan` = pemain yang diusir di ronde ini.
- Kalau `terbuka` mati, `sumbangan` berisi `None`."""
    templates = [
        {"id": "dermawan", "nama": "Dermawan", "ket": "Selalu menyumbang penuh, tidak pernah menghukum.", "kode": 'def aksi():\n    if info()["fase"] == "sanksi":\n        return None\n    return info()["pendapatan"]\n'},
        {"id": "penutup", "nama": "Penutup Target", "ket": "Menyumbang bagian adilnya dari target; kalau ronde lalu gagal, menambah sedikit.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    bagian = (i["target"] + jumlah_pemain() - 1) // jumlah_pemain()
    if i["riwayat"] and not i["riwayat"][-1]["tercapai"]:
        bagian = bagian + 2
    return min(i["pendapatan"], bagian)
'''},
        {"id": "hitung", "nama": "Si Penghitung", "ket": "Menganggap orang lain menyumbang seperti ronde lalu, lalu hanya menutup kekurangan target (kalau ada).", "kode": '''def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    if not i["riwayat"]:
        return i["pendapatan"] // 2
    r = i["riwayat"][-1]
    saya_lalu = r["sumbangan"][nama_saya()]
    if saya_lalu == None:
        saya_lalu = r["total"] // jumlah_pemain()
    lain = r["total"] - saya_lalu
    kurang = i["target"] - lain
    if kurang <= 0:
        return 0
    return min(i["pendapatan"], kurang)
'''},
        {"id": "penegak", "nama": "Penegak Aturan", "ket": "Menyumbang adil; di fase sanksi mendenda dan memilih usir penyumbang paling pelit.", "kode": '''def aksi():
    i = info()
    adil = (max(i["target"], 1) + jumlah_pemain() - 1) // jumlah_pemain()
    if i["fase"] != "sanksi":
        return min(i["pendapatan"], adil)
    r = i["riwayat"][-1]
    pelit = None
    for nama in r["sumbangan"]:
        v = r["sumbangan"][nama]
        if nama != nama_saya() and v != None and v < adil:
            if pelit == None or v < r["sumbangan"][pelit]:
                pelit = nama
    if pelit == None:
        return None
    hasil = {"denda": {}, "usir": None}
    if i["denda"] > 0:
        hasil["denda"][pelit] = 2
    if i["usir_aktif"] and r["sumbangan"][pelit] == 0:
        hasil["usir"] = pelit
    return hasil
'''},
        {"id": "akhir_pelit", "nama": "Akhir Pelit", "ket": "Kerja sama penuh, kecuali 2 ronde terakhir (menurut jumlah ronde di pengaturan).", "kode": '''def aksi():
    i = info()
    if i["fase"] == "sanksi":
        return None
    if i["ronde"] > i["ronde_total"] - 2:
        return 0
    return i["pendapatan"]
'''},
    ]

    def _target(self, s):
        c = s["cfg"]
        return math.ceil(c["target"] * c["pendapatan"] * len(s["names"]) / 100)

    def _sanksi_on(self, s):
        return s["cfg"].get("denda", 0) > 0 or bool(s["cfg"].get("usir"))

    def _pengali(self, s, r):
        c = s["cfg"]
        if not c.get("pengali_rahasia"):
            return c["pengali"]
        return round(c["pengali"] * rng(s, "pengali", r).uniform(0.5, 1.5), 2)

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0.0] * len(names), "riwayat": [],
             "fase": "sumbang", "kucil": [], "gagal": 0}
        akhir = cfg["ronde"]
        if cfg["akhir_rahasia"] and akhir > 1:
            d = max(1, akhir // 4)
            akhir = max(1, rng(s, "akhir").randint(akhir - d, akhir + d))
        s["akhir"] = akhir
        return s

    def pending(self, s):
        if self.over(s):
            return []
        if s.get("fase") == "sanksi":
            return list(range(len(s["names"])))
        return [i for i in range(len(s["names"])) if i not in s.get("kucil", [])]

    def _view(self, s, viewer):
        c = s["cfg"]
        selesai = self.over(s)
        total = s["akhir"] if (selesai or not c["akhir_rahasia"] or viewer == "semua") else c["ronde"]
        n = s["names"]
        hist = s["riwayat"]
        if viewer != "semua" and not c["terbuka"]:
            hist = [{**e, "sumbangan": {k: (v if isinstance(viewer, int) and k == n[viewer] else None)
                                        for k, v in e.get("sumbangan_asli", e["sumbangan"]).items()}} for e in hist]
        hist = [{k: v for k, v in e.items() if k != "sumbangan_asli"} for e in hist]
        return {"fase": s.get("fase", "sumbang"), "ronde": min(s["ronde"], s["akhir"]), "ronde_total": total,
                "akhir_pasti": selesai or not c["akhir_rahasia"] or viewer == "semua",
                "pendapatan": c["pendapatan"],
                "pengali": self._pengali(s, min(s["ronde"], s["akhir"])) if not c.get("pengali_rahasia") or viewer == "semua" else None,
                "pengali_kisaran": [round(c["pengali"] * 0.5, 2), round(c["pengali"] * 1.5, 2)] if c.get("pengali_rahasia") else None,
                "pengali_rahasia": bool(c.get("pengali_rahasia")), "terbuka": c["terbuka"],
                "target": self._target(s), "bonus": c["bonus"] if c["target"] > 0 else 0, "pemain": len(n),
                "denda": c.get("denda", 0), "usir_aktif": bool(c.get("usir")), "bencana": c.get("bencana", 0),
                "dikucilkan": [n[i] for i in s.get("kucil", [])],
                "skor": {nm: round(x, 2) for nm, x in zip(n, s["skor"])}, "riwayat": hist}

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def validate(self, s, p, a):
        c = s["cfg"]
        if s.get("fase") == "sanksi":
            if a is None or isinstance(a, (int, float, str)) and not isinstance(a, dict):
                return {"denda": {}, "usir": None}          # bot lama / "lewati" = tanpa sanksi
            if not isinstance(a, dict):
                raise ActionError("fase sanksi: {'denda': {nama: koin}, 'usir': nama atau None}")
            names = s["names"]
            denda: dict[str, int] = {}
            raw = a.get("denda") or {}
            if not isinstance(raw, dict):
                raise ActionError("denda ditulis {nama: koin}")
            if raw and c.get("denda", 0) <= 0:
                raise ActionError("denda tidak diaktifkan di room ini")
            for nm, x in raw.items():
                if nm not in names or nm == names[p]:
                    raise ActionError(f"tidak bisa mendenda {nm!r}")
                v = as_int(x, "koin denda")
                if v < 0:
                    raise ActionError("koin denda tidak boleh negatif")
                if v:
                    denda[nm] = v
            if sum(denda.values()) > c["pendapatan"]:
                raise ActionError(f"total denda yang kamu bayar maksimal {c['pendapatan']} koin")
            usir = a.get("usir")
            if usir in ("", None):
                usir = None
            elif not c.get("usir"):
                raise ActionError("voting usir tidak diaktifkan di room ini")
            elif usir not in names or usir == names[p]:
                raise ActionError(f"tidak bisa memilih {usir!r} untuk diusir")
            return {"denda": denda, "usir": usir}
        x = as_int(a, "sumbangan")
        if not 0 <= x <= c["pendapatan"]:
            raise ActionError(f"sumbangan harus 0 sampai {c['pendapatan']}")
        return x

    def default(self, s, p):
        return {"denda": {}, "usir": None} if s.get("fase") == "sanksi" else 0

    def apply(self, s, actions):
        if s.get("fase") == "sanksi":
            return self._apply_sanksi(s, actions)
        n, c = s["names"], s["cfg"]
        kucil = set(s.get("kucil", []))
        total = sum(actions.values())
        pengali = self._pengali(s, s["ronde"])
        penerima = [i for i in range(len(n)) if i not in kucil]
        bagian = total * pengali / max(1, len(penerima))
        target = self._target(s)
        tercapai = target > 0 and total >= target
        bonus = c["bonus"] if tercapai else 0
        for i in range(len(n)):
            v = actions.get(i, 0)
            s["skor"][i] += c["pendapatan"] - v + (bagian + bonus if i in penerima else 0)
        asli = {n[i]: actions.get(i, 0) for i in range(len(n))}
        entry = {"ronde": s["ronde"], "sumbangan": dict(asli), "sumbangan_asli": dict(asli),
                 "total": total, "bagian": round(bagian, 3), "pengali": pengali, "target": target, "tercapai": tercapai,
                 "bonus": bonus, "dikucilkan": [n[i] for i in sorted(kucil)]}
        s["riwayat"].append(entry)
        ev = [{"jenis": "ronde", **{k: v for k, v in entry.items() if k != "sumbangan_asli"},
               "sumbangan": {k: (v if c["terbuka"] else None) for k, v in asli.items()}}]
        if target > 0:
            s["gagal"] = 0 if tercapai else s.get("gagal", 0) + 1
            if c.get("bencana", 0) > 0 and s["gagal"] >= 2:
                hilang = {}
                for i in range(len(n)):
                    rugi = max(0.0, s["skor"][i]) * c["bencana"] / 100
                    s["skor"][i] -= rugi
                    hilang[n[i]] = round(rugi, 2)
                s["gagal"] = 0
                entry["bencana"] = hilang
                ev.append({"jenis": "bencana", "ronde": s["ronde"], "hilang": hilang})
        if self._sanksi_on(s):
            s["fase"] = "sanksi"
        else:
            s["kucil"] = []
            s["ronde"] += 1
        return ev

    def _apply_sanksi(self, s, actions):
        n, c = s["names"], s["cfg"]
        ratio = c.get("denda", 0)
        denda_log: dict[str, dict[str, int]] = {}
        for i, a in actions.items():
            for nm, v in a["denda"].items():
                t = n.index(nm)
                s["skor"][i] -= v
                s["skor"][t] -= v * ratio
                denda_log.setdefault(n[i], {})[nm] = v
        votes = {n[i]: a["usir"] for i, a in actions.items() if a.get("usir")}
        hitung: dict[str, int] = {}
        for t in votes.values():
            hitung[t] = hitung.get(t, 0) + 1
        diusir = sorted((nm for nm, k in hitung.items() if k > (len(n) - 1) / 2), key=n.index)
        info = {"denda": denda_log, "usir": votes, "diusir": diusir}
        s["riwayat"][-1]["sanksi"] = info
        s["kucil"] = [n.index(nm) for nm in diusir]
        s["fase"] = "sumbang"
        s["ronde"] += 1
        return [{"jenis": "sanksi", "ronde": s["riwayat"][-1]["ronde"], **info}]

    def over(self, s):
        return s["ronde"] > s["akhir"]

    def scores(self, s):
        return [round(x, 2) for x in s["skor"]]
