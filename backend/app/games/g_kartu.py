"""Petualangan Kartu Nusantara: deck-builder roguelike. Semua pemain menempuh 10 lantai dengan seed yang sama
(musuh & pilihan hadiah sama), masing-masing jalan sendiri. Skor tertinggi menang."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

KARTU: dict[str, dict[str, Any]] = {
    "tebas": {"nama": "Tebas", "biaya": 1, "serang": 6, "ket": "Serang 6."},
    "tangkis": {"nama": "Tangkis", "biaya": 1, "blok": 5, "ket": "Blok 5."},
    "silat": {"nama": "Jurus Silat", "biaya": 1, "serang": 5, "blok": 4, "ket": "Serang 5, blok 4."},
    "keris": {"nama": "Keris Luk", "biaya": 1, "serang": 4, "racun": 3, "ket": "Serang 4, racun 3."},
    "tombak_ganda": {"nama": "Tombak Ganda", "biaya": 1, "serang": 4, "kali": 2, "ket": "Serang 4 dua kali."},
    "amukan": {"nama": "Amukan", "biaya": 2, "serang": 15, "ket": "Serang 15."},
    "perisai_rotan": {"nama": "Perisai Rotan", "biaya": 2, "blok": 12, "ket": "Blok 12."},
    "jamu": {"nama": "Jamu Kunyit", "biaya": 1, "pulih": 7, "habis": True, "ket": "Pulihkan 7 HP. Hilang setelah dipakai (di pertarungan ini)."},
    "semedi": {"nama": "Semedi", "biaya": 0, "tarik": 2, "habis": True, "ket": "Ambil 2 kartu. Hilang setelah dipakai."},
    "semangat": {"nama": "Semangat 45", "biaya": 1, "kuat": 2, "habis": True, "ket": "Kuat +2 (setiap serangan +2) sampai pertarungan selesai. Hilang setelah dipakai."},
    "racun_upas": {"nama": "Racun Upas", "biaya": 1, "racun": 5, "ket": "Racun 5."},
    "teriakan": {"nama": "Teriakan Perang", "biaya": 1, "lemah_semua": 2, "blok": 3, "ket": "Semua musuh lemah 2 giliran, blok 3."},
    "pukulan_tenaga": {"nama": "Pukulan Tenaga Dalam", "biaya": 2, "serang": 11, "lemah": 2, "ket": "Serang 11, musuh lemah 2 giliran."},
    "angin_puyuh": {"nama": "Angin Puyuh", "biaya": 1, "serang_semua": 5, "ket": "Serang 5 ke semua musuh."},
    "kuda_kuda": {"nama": "Kuda-kuda", "biaya": 1, "blok": 4, "tarik": 1, "ket": "Blok 4, ambil 1 kartu."},
}
DEK_AWAL = ["tebas"] * 5 + ["tangkis"] * 4 + ["silat"]
HADIAH = [k for k in KARTU if k not in ("tebas", "tangkis")]

MUSUH: dict[str, dict[str, Any]] = {
    "kera": {"nama": "Kera Hutan", "hp": 22, "pola": [{"serang": 6}, {"serang": 4, "blok": 4}, {"serang": 7}]},
    "ular": {"nama": "Ular Sawah", "hp": 18, "pola": [{"racun": 3}, {"serang": 5}, {"serang": 3, "racun": 2}]},
    "tuyul": {"nama": "Tuyul", "hp": 15, "pola": [{"serang": 3, "kali": 2}, {"blok": 6}, {"serang": 3, "kali": 2}]},
    "babi": {"nama": "Babi Hutan", "hp": 32, "pola": [{"serang": 10}, {"kuat": 2}, {"serang": 7}]},
    "kuntilanak": {"nama": "Kuntilanak", "hp": 26, "pola": [{"lemah": 2}, {"serang": 9}, {"serang": 5, "kali": 2}]},
    "genderuwo": {"nama": "Genderuwo", "hp": 48, "pola": [{"serang": 12}, {"blok": 10, "kuat": 2}, {"serang": 6, "kali": 2}]},
    "banaspati": {"nama": "Banaspati", "hp": 38, "pola": [{"serang": 4, "kali": 3}, {"racun": 4}, {"serang": 9}]},
    "raksasa": {"nama": "Raksasa Batu", "hp": 120, "pola": [{"serang": 14}, {"blok": 18}, {"serang": 7, "kali": 2},
                                                             {"kuat": 3, "blok": 10}, {"serang": 20}]},
}
LEMAH, SEDANG, ELIT = ["kera", "ular", "tuyul"], ["babi", "kuntilanak"], ["genderuwo", "banaspati"]
ISTIRAHAT = (4, 7)
LANTAI = 10
ENERGI, TARIK, TANGAN_MAKS = 3, 5, 10
MARAH_MULAI = 20          # setelah giliran ke-20 di satu pertarungan, musuh makin kuat tiap giliran
MAKS_MAIN_PER_GILIRAN = 40
MAKS_AKSI = 3000


def _intent_text(n: dict[str, Any]) -> str:
    parts = []
    if n.get("serang"):
        parts.append(f"serang {n['serang']}" + (f"×{n['kali']}" if n.get("kali", 1) > 1 else ""))
    for k, label in (("blok", "blok"), ("kuat", "kuat +"), ("racun", "racun"), ("lemah", "lemah")):
        if n.get(k):
            parts.append(f"{label}{'' if label.endswith('+') else ' '}{n[k]}")
    return ", ".join(parts)


class KartuNusantara(Game):
    id = "kartu"
    nama = "Petualangan Kartu Nusantara"
    ringkas = "Deck-builder: lawan makhluk Nusantara di 10 lantai dengan kartu jurus. Semua pemain memakai seed yang sama, adu siapa paling jauh dan sehat."
    kategori = "mandiri"
    mandiri = True
    min_pemain, max_pemain = 1, 8
    hint_aksi = "{'main': i, 'target': j}, 'akhiri', {'pilih': i}, 'lewati', 'pulihkan', atau {'buang': i}"
    timer = 45
    max_frames = 400
    settings = [
        Setting("hp", "HP awal", "int", 70, 20, 200),
        Setting("energi", "Energi per giliran", "int", 3, 2, 5),
    ]
    aturan = f"""
- Setiap pemain menempuh **{LANTAI} lantai** sendiri-sendiri, dengan **musuh dan pilihan hadiah yang sama** untuk semua (seed sama). Tidak saling menunggu.
- Lantai 4 dan 7 adalah **tempat istirahat**: pulihkan 35% HP maksimal, atau buang satu kartu dari dek. Lantai 6 dan 9 dijaga makhluk **elit**
  (mengalahkannya menambah HP maksimal +6). Lantai 10: bos **Raksasa Batu**.
- **Pertarungan:** tiap giliran kamu dapat 3 energi dan mengambil 5 kartu. Mainkan kartu (biaya energi tertulis), lalu akhiri giliran.
  Sisa kartu di tangan dibuang, lalu musuh bertindak sesuai **niat** yang sudah terlihat (serang, blok, dll.).
- **Blok** menahan serangan dan hilang di awal giliranmu berikutnya. **Racun**: kehilangan HP sebesar racun di awal giliran, lalu racun −1.
  **Lemah**: serangan 25% lebih kecil. **Kuat**: setiap serangan bertambah sebesar nilai kuat.
- Tumpukan ambil habis → tumpukan buang dikocok ulang (kocokan juga dari seed). Kartu "hilang setelah dipakai" kembali lagi di pertarungan berikutnya.
- Menang pertarungan → pilih 1 dari 3 kartu hadiah (atau lewati) untuk ditambahkan ke dek.
- Pertarungan yang terlalu lama (lebih dari {MARAH_MULAI} giliran) membuat musuh mengamuk: kuat +2 setiap giliran.
- **Skor** = lantai yang diselesaikan × 100 + sisa HP (kalau masih hidup) + 500 kalau bos kalah. Seri: yang memakai giliran lebih sedikit menang.
"""
    format_aksi = """Tergantung `info()["fase"]`:
- `"tarung"`: `{"main": i, "target": j}` memainkan kartu ke-`i` di tangan (mulai 0) ke musuh ke-`j` (target boleh dihilangkan → musuh hidup pertama), atau `"akhiri"` untuk mengakhiri giliran.
- `"hadiah"`: `{"pilih": i}` mengambil kartu `info()["pilihan"][i]`, atau `"lewati"`.
- `"istirahat"`: `"pulihkan"` atau `{"buang": i}` membuang kartu `info()["dek"][i]` dari dek."""
    format_info = """```
{ "fase": "tarung" | "hadiah" | "istirahat" | "selesai", "lantai": 3, "lantai_total": 10,
  "hp": 52, "hp_maks": 70, "energi": 2, "blok": 5, "kuat": 0, "racun": 0, "lemah": 0, "giliran": 2,
  "tangan": ["tebas", "silat", "tangkis"],     # id kartu; detail lewat kartu(id)
  "tarik": 4, "tarik_isi": [...], "buang": [...], "dek": [...],
  "musuh": [ {"nama": "Babi Hutan", "hp": 20, "hp_maks": 34, "blok": 0, "kuat": 2, "racun": 0, "lemah": 0, "hidup": True,
              "niat": {"serang": 7, "kali": 1}, "niat_teks": "serang 7"} ],
  "pilihan": ["amukan", "keris", "semedi"],   # fase hadiah
  "skor": 240, "pemain": {"Budi": {"lantai": 3, "hp": 52, "fase": "tarung", "skor": 240}, ...},
  "katalog": {"tebas": {"id": "tebas", "nama": "Tebas", "biaya": 1, "serang": 6, "ket": "Serang 6."}, ...} }
```
`niat.serang` sudah termasuk kuat & lemah musuh (belum dikurangi blokmu)."""
    lib_docs = [
        {"nama": "kartu", "jenis": "fungsi", "tanda": "kartu(id)", "ket": "Detail kartu: {'nama', 'biaya', 'serang', 'blok', 'racun', ...}."},
        {"nama": "bisa_main", "jenis": "fungsi", "tanda": "bisa_main(i)", "ket": "True kalau kartu ke-i di tangan bisa dimainkan (energi cukup)."},
        {"nama": "musuh_hidup", "jenis": "fungsi", "tanda": "musuh_hidup()", "ket": "Indeks musuh yang masih hidup."},
        {"nama": "musuh_terlemah", "jenis": "fungsi", "tanda": "musuh_terlemah()", "ket": "Indeks musuh hidup dengan HP + blok paling kecil (atau -1)."},
        {"nama": "perkiraan_serangan", "jenis": "fungsi", "tanda": "perkiraan_serangan()", "ket": "Total kerusakan yang akan dilakukan musuh giliran ini (sebelum dikurangi blokmu)."},
        {"nama": "daftar_kartu", "jenis": "fungsi", "tanda": "daftar_kartu()", "ket": "Semua kartu di game ini (dict id → detail)."},
    ]
    templates = [
        {"id": "seimbang", "nama": "Pendekar Seimbang", "ket": "Blok secukupnya kalau musuh mau menyerang, sisanya menyerang musuh terlemah.", "kode": '''def aksi():
    i = info()
    f = i["fase"]
    if f == "hadiah":
        suka = ["amukan", "tombak_ganda", "silat", "angin_puyuh", "pukulan_tenaga", "perisai_rotan", "keris"]
        for k in suka:
            if k in i["pilihan"]:
                return {"pilih": i["pilihan"].index(k)}
        return "lewati"
    if f == "istirahat":
        if i["hp"] < i["hp_maks"] * 7 // 10 or "tangkis" not in i["dek"]:
            return "pulihkan"
        return {"buang": i["dek"].index("tangkis")}
    tangan = i["tangan"]
    target = musuh_terlemah()
    if perkiraan_serangan() > i["blok"]:
        for k in range(len(tangan)):
            if bisa_main(k) and kartu(tangan[k]).get("blok", 0) > 0:
                return {"main": k, "target": target}
    for k in range(len(tangan)):
        if bisa_main(k) and kartu(tangan[k]).get("blok", 0) == 0:
            return {"main": k, "target": target}
    for k in range(len(tangan)):
        if bisa_main(k):
            return {"main": k, "target": target}
    return "akhiri"
'''},
        {"id": "agresif", "nama": "Si Nekat", "ket": "Serang terus, kartu termahal dulu. Hadiah selalu kartu serangan.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "hadiah":
        for k in range(len(i["pilihan"])):
            d = kartu(i["pilihan"][k])
            if d.get("serang", 0) > 0 or d.get("serang_semua", 0) > 0:
                return {"pilih": k}
        return "lewati"
    if i["fase"] == "istirahat":
        return "pulihkan"
    tangan = i["tangan"]
    urut = sorted(range(len(tangan)), key=lambda k: -kartu(tangan[k])["biaya"])
    for k in urut:
        if bisa_main(k):
            return {"main": k, "target": musuh_terlemah()}
    return "akhiri"
'''},
        {"id": "dukun_racun", "nama": "Dukun Racun", "ket": "Mengumpulkan kartu racun dan bertahan sambil racun bekerja.", "kode": '''def aksi():
    i = info()
    if i["fase"] == "hadiah":
        for suka in ["racun_upas", "keris", "perisai_rotan", "kuda_kuda", "teriakan"]:
            if suka in i["pilihan"]:
                return {"pilih": i["pilihan"].index(suka)}
        return "lewati"
    if i["fase"] == "istirahat":
        return "pulihkan"
    tangan = i["tangan"]
    hidup = musuh_hidup()
    # racuni musuh yang racunnya paling sedikit
    sasaran = hidup[0]
    for m in hidup:
        if i["musuh"][m]["racun"] < i["musuh"][sasaran]["racun"]:
            sasaran = m
    for k in range(len(tangan)):
        if bisa_main(k) and kartu(tangan[k]).get("racun", 0) > 0:
            return {"main": k, "target": sasaran}
    if perkiraan_serangan() > i["blok"]:
        for k in range(len(tangan)):
            if bisa_main(k) and kartu(tangan[k]).get("blok", 0) > 0:
                return {"main": k, "target": sasaran}
    for k in range(len(tangan)):
        if bisa_main(k):
            return {"main": k, "target": musuh_terlemah()}
    return "akhiri"
'''},
    ]

    # ------------------------------------------------------------ run per pemain
    def _new_run(self, s):
        return {"hp": s["cfg"]["hp"], "hp_maks": s["cfg"]["hp"], "lantai": 1, "fase": "tarung", "dek": list(DEK_AWAL),
                "tarik": [], "buang": [], "tangan": [], "habis": [], "energi": 0, "blok": 0, "kuat": 0, "racun": 0, "lemah": 0,
                "musuh": [], "giliran": 0, "kocok_no": 0, "pilihan": [], "log": [], "selesai_lantai": 0, "menang": False,
                "total_giliran": 0, "aksi": 0, "main_giliran": 0, "mati": False}

    def _log(self, run, text):
        run["log"].append(text)
        if len(run["log"]) > 12:
            del run["log"][0]

    def _encounter(self, s, lantai):
        g = rng(s, "musuh", lantai)
        plan = {1: [g.choice(LEMAH)], 2: g.sample(LEMAH, 2), 3: [g.choice(SEDANG)], 5: [g.choice(SEDANG), g.choice(LEMAH)],
                6: [g.choice(ELIT)], 8: [g.choice(SEDANG), g.choice(LEMAH)], 9: [g.choice(ELIT)], 10: ["raksasa"]}[lantai]
        out = []
        for idx, mid in enumerate(plan):
            d = MUSUH[mid]
            hp = d["hp"] if mid == "raksasa" else int(round(d["hp"] * (1 + 0.04 * (lantai - 1))))
            out.append({"id": mid, "nama": d["nama"], "hp": hp, "hp_maks": hp, "blok": 0, "kuat": 0, "racun": 0, "lemah": 0,
                        "pola": rng(s, "pola", lantai, idx).randrange(len(d["pola"])), "hidup": True})
        return out

    def _intent(self, run, m):
        d = MUSUH[m["id"]]
        base = d["pola"][(m["pola"] + run["giliran"] - 1) % len(d["pola"])]
        n = dict(base)
        if n.get("serang"):
            dmg = n["serang"] + m["kuat"]
            if m["lemah"] > 0:
                dmg = dmg * 3 // 4
            n["serang"] = max(0, dmg)
            n["kali"] = base.get("kali", 1)
        return n

    def _shuffle_in(self, s, run):
        run["kocok_no"] += 1
        pile = sorted(run["buang"])
        rng(s, "kocok", run["lantai"], run["kocok_no"]).shuffle(pile)
        run["tarik"] = pile + run["tarik"]
        run["buang"] = []

    def _draw(self, s, run, n):
        for _ in range(n):
            if len(run["tangan"]) >= TANGAN_MAKS:
                return
            if not run["tarik"]:
                if not run["buang"]:
                    return
                self._shuffle_in(s, run)
            run["tangan"].append(run["tarik"].pop())

    def _start_combat(self, s, run):
        run["fase"] = "tarung"
        run["musuh"] = self._encounter(s, run["lantai"])
        run["tarik"] = sorted(run["dek"])
        rng(s, "dek", run["lantai"]).shuffle(run["tarik"])
        run["buang"], run["tangan"], run["habis"] = [], [], []
        run["kuat"] = run["racun"] = run["lemah"] = run["blok"] = 0
        run["giliran"] = 0
        run["kocok_no"] = 0
        self._log(run, f"Lantai {run['lantai']}: " + ", ".join(m["nama"] for m in run["musuh"]))
        self._start_turn(s, run)

    def _start_turn(self, s, run):
        run["giliran"] += 1
        run["total_giliran"] += 1
        run["main_giliran"] = 0
        run["blok"] = 0
        if run["racun"] > 0:
            run["hp"] -= run["racun"]
            self._log(run, f"Racun: −{run['racun']} HP")
            run["racun"] -= 1
            if run["hp"] <= 0:
                self._die(run)
                return
        if run["giliran"] > MARAH_MULAI:
            for m in run["musuh"]:
                if m["hidup"]:
                    m["kuat"] += 2
        for m in run["musuh"]:
            m["niat"] = self._intent(run, m) if m["hidup"] else {}
        run["energi"] = s["cfg"]["energi"]
        self._draw(s, run, TARIK)

    def _die(self, run):
        run["hp"] = 0
        run["mati"] = True
        run["fase"] = "selesai"
        self._log(run, "Kalah. Petualangan berakhir.")

    def _hit(self, run, m, dmg):
        if run["lemah"] > 0:
            dmg = dmg * 3 // 4
        dmg = max(0, dmg)
        blocked = min(m["blok"], dmg)
        m["blok"] -= blocked
        m["hp"] -= dmg - blocked
        if m["hp"] <= 0 and m["hidup"]:
            m["hp"], m["hidup"] = 0, False
            self._log(run, f"{m['nama']} kalah!")
        return dmg - blocked

    def _enemy_turn(self, s, run):
        for m in run["musuh"]:
            if not m["hidup"]:
                continue
            m["blok"] = 0
            if m["racun"] > 0:
                m["hp"] -= m["racun"]
                m["racun"] -= 1
                if m["hp"] <= 0:
                    m["hp"], m["hidup"] = 0, False
                    self._log(run, f"{m['nama']} tumbang karena racun")
                    continue
            n = m.get("niat") or self._intent(run, m)
            if n.get("serang"):
                total = 0
                for _ in range(n.get("kali", 1)):
                    blocked = min(run["blok"], n["serang"])
                    run["blok"] -= blocked
                    run["hp"] -= n["serang"] - blocked
                    total += n["serang"] - blocked
                self._log(run, f"{m['nama']} menyerang: −{total} HP")
            if n.get("blok"):
                m["blok"] += n["blok"]
            if n.get("kuat"):
                m["kuat"] += n["kuat"]
            if n.get("racun"):
                run["racun"] += n["racun"]
            if n.get("lemah"):
                run["lemah"] += n["lemah"]
            if m["lemah"] > 0:
                m["lemah"] -= 1
            if run["hp"] <= 0:
                self._die(run)
                return

    def _won_combat(self, s, run):
        run["selesai_lantai"] += 1
        if run["lantai"] >= LANTAI:
            run["menang"] = True
            run["fase"] = "selesai"
            self._log(run, "Raksasa Batu tumbang! Petualangan selesai dengan kemenangan.")
            return
        if any(m["id"] in ELIT for m in run["musuh"]):
            run["hp_maks"] += 6
            run["hp"] += 6
            self._log(run, "Pusaka elit: HP maksimal +6")
        g = rng(s, "hadiah", run["lantai"])
        run["pilihan"] = g.sample(HADIAH, 3)
        run["fase"] = "hadiah"
        run["tangan"], run["tarik"], run["buang"], run["habis"] = [], [], [], []
        run["blok"] = run["kuat"] = run["racun"] = run["lemah"] = 0

    def _next_floor(self, s, run):
        run["lantai"] += 1
        run["pilihan"] = []
        if run["lantai"] in ISTIRAHAT:
            run["fase"] = "istirahat"
            self._log(run, f"Lantai {run['lantai']}: tempat istirahat")
        else:
            self._start_combat(s, run)

    def _score(self, run):
        return run["selesai_lantai"] * 100 + (run["hp"] if not run["mati"] else 0) + (500 if run["menang"] else 0)

    # ------------------------------------------------------------ kontrak Game
    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "runs": []}
        for _ in names:
            run = self._new_run(s)
            self._start_combat(s, run)
            s["runs"].append(run)
        return s

    def pending(self, s):
        return [i for i, r in enumerate(s["runs"]) if r["fase"] != "selesai"]

    def _summary(self, run):
        return {"lantai": run["lantai"], "hp": run["hp"], "hp_maks": run["hp_maks"], "fase": run["fase"], "skor": self._score(run),
                "menang": run["menang"], "giliran": run["total_giliran"],
                "musuh": [[m["nama"], m["hp"], m["hp_maks"]] for m in run["musuh"] if run["fase"] == "tarung"],
                "log": run["log"][-2:]}

    def public(self, s):
        return {"lantai_total": LANTAI, "pemain": {s["names"][i]: self._summary(r) for i, r in enumerate(s["runs"])}}

    def observe(self, s, p):
        run = s["runs"][p]
        musuh = []
        for m in run["musuh"]:
            niat = m.get("niat", {}) if m["hidup"] else {}
            musuh.append({"nama": m["nama"], "id": m["id"], "hp": m["hp"], "hp_maks": m["hp_maks"], "blok": m["blok"], "kuat": m["kuat"],
                          "racun": m["racun"], "lemah": m["lemah"], "hidup": m["hidup"], "niat": niat, "niat_teks": _intent_text(niat)})
        return {**self.public(s), "saya": p, "nama_saya": s["names"][p], "fase": run["fase"], "lantai": run["lantai"],
                "hp": run["hp"], "hp_maks": run["hp_maks"], "energi": run["energi"], "blok": run["blok"], "kuat": run["kuat"],
                "racun": run["racun"], "lemah": run["lemah"], "giliran": run["giliran"], "tangan": list(run["tangan"]),
                "tarik": len(run["tarik"]), "tarik_isi": sorted(run["tarik"]), "buang": list(run["buang"]), "habis": list(run["habis"]),
                "dek": list(run["dek"]), "musuh": musuh if run["fase"] == "tarung" else [], "pilihan": list(run["pilihan"]),
                "skor": self._score(run), "log": list(run["log"]), "istirahat": list(ISTIRAHAT),
                "katalog": {k: {"id": k, **v} for k, v in KARTU.items()}}

    def validate(self, s, p, a):
        run = s["runs"][p]
        f = run["fase"]
        word = a.strip().lower() if isinstance(a, str) else None
        if f == "tarung":
            if word in ("akhiri", "akhir", "selesai", "end"):
                return {"akhiri": True}
            if not isinstance(a, dict) or "main" not in a:
                raise ActionError("fase tarung: {'main': indeks_kartu, 'target': indeks_musuh} atau 'akhiri'")
            i = as_int(a["main"], "indeks kartu")
            if not 0 <= i < len(run["tangan"]):
                raise ActionError(f"tidak ada kartu ke-{i} di tangan (ada {len(run['tangan'])} kartu)")
            card = KARTU[run["tangan"][i]]
            if card["biaya"] > run["energi"]:
                raise ActionError(f"energi kurang untuk {card['nama']} (butuh {card['biaya']}, sisa {run['energi']})")
            alive = [k for k, m in enumerate(run["musuh"]) if m["hidup"]]
            t = a.get("target")
            t = alive[0] if t is None or t == -1 else as_int(t, "target")
            if t not in alive:
                t = alive[0]
            return {"main": i, "target": t}
        if f == "hadiah":
            if word in ("lewati", "skip"):
                return {"lewati": True}
            if isinstance(a, dict) and "pilih" in a:
                i = as_int(a["pilih"], "pilihan")
                if 0 <= i < len(run["pilihan"]):
                    return {"pilih": i}
                raise ActionError("pilihan hadiah di luar jangkauan")
            if isinstance(a, str) and a in run["pilihan"]:
                return {"pilih": run["pilihan"].index(a)}
            raise ActionError("fase hadiah: {'pilih': i} atau 'lewati'")
        if f == "istirahat":
            if word in ("pulihkan", "istirahat", "tidur"):
                return {"pulihkan": True}
            if isinstance(a, dict) and "buang" in a:
                i = as_int(a["buang"], "indeks kartu dek")
                if not 0 <= i < len(run["dek"]):
                    raise ActionError("indeks kartu dek di luar jangkauan")
                if len(run["dek"]) <= 5:
                    raise ActionError("dek minimal 5 kartu")
                return {"buang": i}
            raise ActionError("fase istirahat: 'pulihkan' atau {'buang': i}")
        raise ActionError("petualanganmu sudah selesai")

    def default(self, s, p):
        f = s["runs"][p]["fase"]
        return {"tarung": {"akhiri": True}, "hadiah": {"lewati": True}, "istirahat": {"pulihkan": True}}.get(f, {"akhiri": True})

    def apply(self, s, actions):
        ev = []
        for p, a in actions.items():
            run = s["runs"][p]
            if run["fase"] == "selesai":
                continue
            before = (run["lantai"], run["fase"])
            run["aksi"] += 1
            self._apply_one(s, run, a)
            if run["aksi"] >= MAKS_AKSI and run["fase"] != "selesai":
                run["fase"] = "selesai"
                self._log(run, "Kelelahan: terlalu banyak langkah.")
            after = (run["lantai"], run["fase"])
            if before != after:
                ev.append({"jenis": "kemajuan", "pemain": s["names"][p], "lantai": run["lantai"], "fase": run["fase"],
                           "hp": run["hp"], "skor": self._score(run)})
        return ev

    def _apply_one(self, s, run, a):
        f = run["fase"]
        if f == "hadiah":
            if "pilih" in a:
                k = run["pilihan"][a["pilih"]]
                run["dek"].append(k)
                self._log(run, f"Mengambil kartu {KARTU[k]['nama']}")
            self._next_floor(s, run)
            return
        if f == "istirahat":
            if "buang" in a:
                k = run["dek"].pop(a["buang"])
                self._log(run, f"Membuang kartu {KARTU[k]['nama']}")
            else:
                heal = run["hp_maks"] * 35 // 100
                run["hp"] = min(run["hp_maks"], run["hp"] + heal)
                self._log(run, f"Istirahat: +{heal} HP")
            run["selesai_lantai"] += 1
            self._next_floor(s, run)
            return
        if "akhiri" in a or run["main_giliran"] >= MAKS_MAIN_PER_GILIRAN:
            self._end_turn(s, run)
            return
        cid = run["tangan"].pop(a["main"])
        c = KARTU[cid]
        run["energi"] -= c["biaya"]
        run["main_giliran"] += 1
        m = run["musuh"][a["target"]]
        bonus = run["kuat"]
        if c.get("serang"):
            dealt = sum(self._hit(run, m, c["serang"] + bonus) for _ in range(c.get("kali", 1)))
            self._log(run, f"{c['nama']} → {m['nama']}: {dealt} kerusakan")
        if c.get("serang_semua"):
            for x in run["musuh"]:
                if x["hidup"]:
                    self._hit(run, x, c["serang_semua"] + bonus)
            self._log(run, f"{c['nama']} mengenai semua musuh")
        if c.get("racun") and m["hidup"]:
            m["racun"] += c["racun"]
        if c.get("lemah") and m["hidup"]:
            m["lemah"] += c["lemah"]
        if c.get("lemah_semua"):
            for x in run["musuh"]:
                if x["hidup"]:
                    x["lemah"] += c["lemah_semua"]
        if c.get("blok"):
            run["blok"] += c["blok"]
        if c.get("kuat"):
            run["kuat"] += c["kuat"]
        if c.get("pulih"):
            run["hp"] = min(run["hp_maks"], run["hp"] + c["pulih"])
        (run["habis"] if c.get("habis") else run["buang"]).append(cid)
        if c.get("tarik"):
            self._draw(s, run, c["tarik"])
        for x in run["musuh"]:
            if x["hidup"]:
                x["niat"] = self._intent(run, x)
        if not any(x["hidup"] for x in run["musuh"]):
            self._won_combat(s, run)

    def _end_turn(self, s, run):
        run["buang"] += run["tangan"]
        run["tangan"] = []
        if run["lemah"] > 0:
            run["lemah"] -= 1
        self._enemy_turn(s, run)
        if run["fase"] == "selesai":
            return
        if not any(x["hidup"] for x in run["musuh"]):
            self._won_combat(s, run)
            return
        self._start_turn(s, run)

    def over(self, s):
        return all(r["fase"] == "selesai" for r in s["runs"])

    def scores(self, s):
        return [float(self._score(r)) for r in s["runs"]]

    def tiebreak(self, s):
        return [-float(r["total_giliran"]) for r in s["runs"]]

    def reveal(self, s):
        return {"dek_akhir": {s["names"][i]: r["dek"] for i, r in enumerate(s["runs"])}}

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        run = s["runs"][p]

        def kartu(cid):
            if cid not in KARTU:
                raise ActionError(f"tidak ada kartu {cid!r}")
            return {"id": cid, **KARTU[cid]}

        def bisa_main(i):
            i = as_int(i, "indeks kartu")
            return run["fase"] == "tarung" and 0 <= i < len(run["tangan"]) and KARTU[run["tangan"][i]]["biaya"] <= run["energi"]

        def musuh_hidup():
            return [k for k, m in enumerate(run["musuh"]) if m["hidup"]] if run["fase"] == "tarung" else []

        def musuh_terlemah():
            alive = musuh_hidup()
            if not alive:
                return -1
            return min(alive, key=lambda k: (run["musuh"][k]["hp"] + run["musuh"][k]["blok"], k))

        def perkiraan_serangan():
            total = 0
            for m in run["musuh"]:
                n = m.get("niat") or {}
                if m["hidup"] and n.get("serang"):
                    total += n["serang"] * n.get("kali", 1)
            return total

        return {"kartu": kartu, "bisa_main": bisa_main, "musuh_hidup": musuh_hidup, "musuh_terlemah": musuh_terlemah,
                "perkiraan_serangan": perkiraan_serangan, "daftar_kartu": lambda: {k: {"id": k, **v} for k, v in KARTU.items()}}
