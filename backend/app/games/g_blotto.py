"""Rebutan Lahan: bagi pasukan ke beberapa medan, pasukan terbanyak menguasai medan.

Kustomisasi: alokasi lawan rahasia, nilai ronde berikutnya rahasia, benteng (penguasa lama bertahan lebih kuat),
pasukan menyusut (pasukan di medan yang kalah hilang, ada bala bantuan), dan medan kejutan (ganda / misteri).
"""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

KHUSUS = {"ganda": "⭐×2 nilai ganda", "misteri": "🌫️ nilai misteri (−3 sampai 6, dibuka setelah ronde)"}


class RebutanLahan(Game):
    id = "blotto"
    nama = "Rebutan Lahan"
    ringkas = "Bagi pasukanmu ke beberapa medan. Pasukan terbanyak di sebuah medan menguasainya. Tidak ada strategi yang selalu menang."
    kategori = "simultan"
    min_pemain, max_pemain = 2, 8
    hint_aksi = "list jumlah pasukan per medan"
    timer = 30
    jeda_pada, jeda_hasil = ("ronde",), 6
    settings = [
        Setting("medan", "Jumlah medan", "int", 5, 2, 8),
        Setting("pasukan", "Pasukan per ronde", "int", 100, 10, 1000),
        Setting("ronde", "Jumlah ronde", "int", 10, 1, 50),
        Setting("nilai_acak", "Nilai medan berbeda-beda", "bool", True, ket="Kalau mati, semua medan bernilai 1."),
        Setting("alokasi_rahasia", "Alokasi lawan rahasia", "bool", False, grup="informasi",
                ket="Setelah ronde, hanya penguasa tiap medan yang dibuka; jumlah pasukan lawan tidak."),
        Setting("nilai_besok", "Nilai ronde berikutnya terlihat", "bool", True, grup="informasi"),
        Setting("benteng", "Benteng (%)", "int", 0, 0, 100, grup="aturan",
                ket="Penguasa tunggal sebuah medan di ronde sebelumnya bertahan lebih kuat: pasukannya di medan itu dihitung +sekian persen."),
        Setting("menyusut", "Pasukan menyusut", "bool", False, grup="aturan",
                ket="Pasukan tidak penuh lagi tiap ronde: pasukan di medan yang KALAH hilang; yang menang/seri kembali. Ditambah bala bantuan tiap ronde."),
        Setting("bala_bantuan", "Bala bantuan per ronde (%)", "int", 30, 0, 100, grup="aturan", jika={"menyusut": True},
                ket="Persen dari pasukan awal yang datang tiap ronde (pasukan maksimal 2× pasukan awal)."),
        Setting("medan_kejutan", "Medan kejutan (%)", "int", 0, 0, 100, grup="kejutan",
                ket="Peluang tiap medan jadi istimewa di ronde itu: ⭐×2 (nilai ganda) atau 🌫️ misteri (nilai −3 sampai 6, baru dibuka setelah ronde)."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut", "ket": "Alokasi lawan dan nilai ronde berikutnya rahasia.",
         "nilai": {"alokasi_rahasia": True, "nilai_besok": False}},
        {"id": "kacau", "nama": "Kacau", "ket": "Benteng 30%, pasukan menyusut, dan medan kejutan.",
         "nilai": {"benteng": 30, "menyusut": True, "medan_kejutan": 25}},
    ]
    aturan = """
- Setiap ronde, setiap pemain membagi **pasukan** (default 100) ke beberapa **medan** (default 5), bersamaan dan rahasia.
- Tiap medan punya **nilai** (1–5). Nilai ronde ini dan ronde berikutnya sudah diumumkan (nilai berikutnya bisa dirahasiakan host).
- Pemain dengan pasukan terbanyak di sebuah medan mendapat nilai medan itu. Kalau seri, nilainya dibagi rata. Medan tanpa pasukan tidak dimiliki siapa pun.
- Pasukan tidak berkurang: setiap ronde semua mulai lagi dengan jumlah pasukan penuh (kecuali opsi *pasukan menyusut*). Semua alokasi dibuka setelah ronde selesai (kecuali opsi *alokasi lawan rahasia*).
- Poin terbanyak setelah semua ronde menang.
- Opsi host: **benteng** (penguasa tunggal ronde lalu dihitung +X% di medan itu), **pasukan menyusut** (pasukan di medan yang kalah hilang,
  ada bala bantuan tiap ronde), **medan kejutan** (⭐×2 nilai ganda, atau 🌫️ misteri bernilai −3 sampai 6 yang baru dibuka setelah ronde;
  menguasai medan misteri bernilai minus = poin minus).
"""
    format_aksi = "List angka bulat ≥ 0 sepanjang jumlah medan, totalnya tidak lebih dari pasukanmu. Contoh 5 medan: `[30, 30, 20, 10, 10]`."
    format_info = """```
{
  "ronde": 3, "ronde_total": 10, "medan": 5, "pasukan": 100,
  "pasukan_saya": 100,               # pasukanmu ronde ini (berubah kalau pasukan menyusut)
  "nilai": [3, 1, None, 2, 4],       # nilai medan ronde ini (None = medan misteri)
  "khusus": [None, "ganda", "misteri", None, None],
  "nilai_berikut": [2, 2, 1, 5, 3],  # ronde berikutnya (None kalau dirahasiakan / ronde terakhir)
  "pemilik": ["Budi", None, ...],    # penguasa tunggal tiap medan di ronde lalu (untuk benteng)
  "skor": {"Budi": 12.5, ...},
  "riwayat": [ {"ronde": 1, "nilai": [...], "alokasi": {"Budi": [20, 20, 20, 20, 20], "Ani": None, ...},
                "penguasa": [["Budi"], ["Ani", "Citra"], [], ...], "poin": {"Budi": 4.0, ...}, "hilang": {"Budi": 20, ...},
                "pasukan": {"Budi": 110, ...}} ]   # pasukan tiap pemain setelah ronde itu
}
```
Kalau alokasi lawan rahasia, `alokasi`, `hilang`, dan `pasukan` lawan berisi `None` (milikmu sendiri tetap terlihat)."""
    lib_docs = [
        {"nama": "bagi_rata", "jenis": "fungsi", "tanda": "bagi_rata()", "ket": "Alokasi rata ke semua medan (sisa ke medan pertama)."},
        {"nama": "rata_rata_lawan", "jenis": "fungsi", "tanda": "rata_rata_lawan()", "ket": "Rata-rata pasukan lawan per medan di ronde lalu (list), atau None kalau alokasi lawan rahasia."},
        {"nama": "pasukan_saya", "jenis": "fungsi", "tanda": "pasukan_saya()", "ket": "Jumlah pasukanmu ronde ini."},
    ]
    templates = [
        {"id": "rata", "nama": "Si Rata", "ket": "Membagi rata ke semua medan.", "kode": "def aksi():\n    return bagi_rata()\n"},
        {"id": "fokus", "nama": "Fokus Tiga", "ket": "Menumpuk pasukan di 3 medan bernilai tertinggi (medan misteri dianggap bernilai 1).", "kode": '''def aksi():
    i = info()
    nilai = [v if v != None else 1 for v in i["nilai"]]
    urut = sorted(range(len(nilai)), key=lambda k: -nilai[k])
    pilihan = urut[:3]
    total = sum(max(1, nilai[k]) for k in pilihan)
    alokasi = [0] * i["medan"]
    sisa = pasukan_saya()
    for k in pilihan:
        alokasi[k] = pasukan_saya() * max(1, nilai[k]) // total
        sisa -= alokasi[k]
    alokasi[pilihan[0]] += sisa
    return alokasi
'''},
        {"id": "lawan_rata", "nama": "Pembaca Rata-rata", "ket": "Mengalahkan rata-rata lawan di medan bernilai tinggi, lalu melepas sisanya.", "kode": '''def aksi():
    i = info()
    musuh = rata_rata_lawan()
    if i["ronde"] == 1 or musuh == None:
        return bagi_rata()
    nilai = [v if v != None else 1 for v in i["nilai"]]
    urut = sorted(range(i["medan"]), key=lambda k: -nilai[k] / (musuh[k] + 1))
    alokasi = [0] * i["medan"]
    sisa = pasukan_saya()
    for k in urut:
        butuh = int(musuh[k]) + 1
        if butuh <= sisa:
            alokasi[k] = butuh
            sisa -= butuh
    alokasi[urut[0]] += sisa
    return alokasi
'''},
    ]

    def init(self, cfg: dict[str, Any], names: list[str], seed: int) -> dict[str, Any]:
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0.0] * len(names), "riwayat": [],
             "pool": [cfg["pasukan"]] * len(names), "pemilik": [None] * cfg["medan"]}
        vals, khusus = [], []
        for r in range(cfg["ronde"]):
            g = rng(s, "nilai", r)
            vals.append([g.randint(1, 5) if cfg["nilai_acak"] else 1 for _ in range(cfg["medan"])])
            row = [None] * cfg["medan"]
            if cfg.get("medan_kejutan", 0) > 0:
                gk = rng(s, "khusus", r)
                for k in range(cfg["medan"]):
                    if gk.random() * 100 < cfg["medan_kejutan"]:
                        row[k] = gk.choice(sorted(KHUSUS))
                        vals[r][k] = vals[r][k] * 2 if row[k] == "ganda" else gk.randint(-3, 6)
            khusus.append(row)
        s["nilai"], s["khusus"] = vals, khusus
        return s

    def pending(self, s: dict[str, Any]) -> list[int]:
        return [] if self.over(s) else list(range(len(s["names"])))

    def _shown(self, s, r_idx, viewer):
        vals, kh = s["nilai"][r_idx], s["khusus"][r_idx]
        if viewer == "semua":
            return list(vals)
        return [None if kh[k] == "misteri" else v for k, v in enumerate(vals)]

    def _fog_entry(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"].get("alokasi_rahasia"):
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return {**e, "alokasi": {n: (a if n == me else None) for n, a in e["alokasi"].items()},
                "hilang": {n: (x if n == me else None) for n, x in e.get("hilang", {}).items()},
                "pasukan": {n: (x if n == me else None) for n, x in e.get("pasukan", {}).items()}}

    def _view(self, s, viewer):
        r, c, n = s["ronde"], s["cfg"], s["names"]
        cur = self._shown(s, r - 1, viewer) if r <= c["ronde"] else None
        nxt = None
        if r < c["ronde"] and (c.get("nilai_besok", True) or viewer == "semua"):
            nxt = self._shown(s, r, viewer)
        hide = c.get("alokasi_rahasia") and viewer != "semua"
        return {"ronde": min(r, c["ronde"]), "ronde_total": c["ronde"], "medan": c["medan"], "pasukan": c["pasukan"],
                "nilai": cur, "khusus": s["khusus"][r - 1] if r <= c["ronde"] else None, "nilai_berikut": nxt,
                "khusus_berikut": s["khusus"][r] if nxt is not None else None,
                "pemilik": [n[x] if x is not None else None for x in s["pemilik"]],
                "pasukan_semua": None if hide else dict(zip(n, s["pool"])), "menyusut": bool(c.get("menyusut")),
                "benteng": c.get("benteng", 0), "alokasi_rahasia": bool(c.get("alokasi_rahasia")),
                "skor": {nm: round(x, 3) for nm, x in zip(n, s["skor"])},
                "riwayat": [self._fog_entry(s, e, viewer) for e in s["riwayat"]]}

    def event_for(self, s, e, viewer):
        return self._fog_entry(s, e, viewer) if e.get("jenis") == "ronde" else e

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        return self._view(s, None)

    def full_view(self, s: dict[str, Any]) -> dict[str, Any]:
        return self._view(s, "semua")

    def observe(self, s: dict[str, Any], p: int) -> dict[str, Any]:
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p], "pasukan_saya": s["pool"][p]}

    def validate(self, s: dict[str, Any], p: int, a: Any) -> list[int]:
        c = s["cfg"]
        if not isinstance(a, (list, tuple)) or len(a) != c["medan"]:
            raise ActionError(f"kembalikan list berisi {c['medan']} angka")
        out = [as_int(x, "jumlah pasukan") for x in a]
        if any(x < 0 for x in out):
            raise ActionError("jumlah pasukan tidak boleh negatif")
        if sum(out) > s["pool"][p]:
            raise ActionError(f"total pasukan {sum(out)} melebihi {s['pool'][p]}")
        return out

    def _even(self, s: dict[str, Any], p: int) -> list[int]:
        m = s["cfg"]["medan"]
        total = s["pool"][p]
        base = [total // m] * m
        base[0] += total - sum(base)
        return base

    def default(self, s: dict[str, Any], p: int) -> list[int]:
        return self._even(s, p)

    def apply(self, s: dict[str, Any], actions: dict[int, Any]) -> list[dict[str, Any]]:
        n, c = s["names"], s["cfg"]
        nilai = s["nilai"][s["ronde"] - 1]
        bonus = 1 + c.get("benteng", 0) / 100
        poin = [0.0] * len(n)
        penguasa, hilang = [], {n[i]: 0 for i in actions}
        pemilik_baru: list[int | None] = []
        for k, v in enumerate(nilai):
            eff = {i: actions[i][k] * (bonus if s["pemilik"][k] == i else 1) for i in actions}
            top = max(eff.values())
            win = [i for i in actions if abs(eff[i] - top) < 1e-9] if top > 0 else []
            penguasa.append([n[i] for i in win])
            pemilik_baru.append(win[0] if len(win) == 1 else None)
            for i in win:
                poin[i] += v / len(win)
            if c.get("menyusut"):
                for i in actions:
                    if i not in win and actions[i][k] > 0:
                        hilang[n[i]] += actions[i][k]
        for i in range(len(n)):
            s["skor"][i] += poin[i]
        if c.get("menyusut"):
            bala = c["pasukan"] * c.get("bala_bantuan", 0) // 100
            for i in actions:
                s["pool"][i] = min(2 * c["pasukan"], s["pool"][i] - hilang[n[i]] + bala)
        s["pemilik"] = pemilik_baru
        entry = {"ronde": s["ronde"], "nilai": list(nilai), "khusus": list(s["khusus"][s["ronde"] - 1]),
                 "alokasi": {n[i]: actions[i] for i in actions}, "penguasa": penguasa,
                 "poin": {n[i]: round(poin[i], 3) for i in range(len(n))}, "hilang": hilang,
                 "pasukan": dict(zip(n, s["pool"]))}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **entry}]

    def over(self, s: dict[str, Any]) -> bool:
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s: dict[str, Any]) -> list[float]:
        return [round(x, 3) for x in s["skor"]]

    def bot_library(self, s: dict[str, Any], p: int, obs: dict[str, Any]) -> dict[str, Any]:
        def bagi_rata():
            return self._even(s, p)

        def rata_rata_lawan():
            if not obs["riwayat"]:
                return [0.0] * s["cfg"]["medan"]
            last = obs["riwayat"][-1]["alokasi"]
            others = [v for k, v in last.items() if k != s["names"][p]]
            if any(v is None for v in others):
                return None
            return [sum(v[k] for v in others) / max(1, len(others)) for k in range(s["cfg"]["medan"])]

        return {"bagi_rata": bagi_rata, "rata_rata_lawan": rata_rata_lawan, "pasukan_saya": lambda: s["pool"][p]}
