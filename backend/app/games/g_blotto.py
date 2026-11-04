"""Rebutan Lahan: bagi pasukan ke beberapa medan, pasukan terbanyak menguasai medan."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng


class RebutanLahan(Game):
    id = "blotto"
    nama = "Rebutan Lahan"
    ringkas = "Bagi pasukanmu ke beberapa medan. Pasukan terbanyak di sebuah medan menguasainya. Tidak ada strategi yang selalu menang."
    kategori = "simultan"
    min_pemain, max_pemain = 2, 8
    hint_aksi = "list jumlah pasukan per medan"
    timer = 30
    settings = [
        Setting("medan", "Jumlah medan", "int", 5, 2, 8),
        Setting("pasukan", "Pasukan per ronde", "int", 100, 10, 1000),
        Setting("ronde", "Jumlah ronde", "int", 10, 1, 50),
        Setting("nilai_acak", "Nilai medan berbeda-beda", "bool", True, ket="Kalau mati, semua medan bernilai 1."),
    ]
    aturan = """
- Setiap ronde, setiap pemain membagi **pasukan** (default 100) ke beberapa **medan** (default 5), bersamaan dan rahasia.
- Tiap medan punya **nilai** (1–5). Nilai ronde ini dan ronde berikutnya sudah diumumkan.
- Pemain dengan pasukan terbanyak di sebuah medan mendapat nilai medan itu. Kalau seri, nilainya dibagi rata. Medan tanpa pasukan tidak dimiliki siapa pun.
- Pasukan tidak berkurang: setiap ronde semua mulai lagi dengan jumlah pasukan penuh. Semua alokasi dibuka setelah ronde selesai.
- Poin terbanyak setelah semua ronde menang.
"""
    format_aksi = "List angka bulat ≥ 0 sepanjang jumlah medan, totalnya tidak lebih dari jumlah pasukan. Contoh 5 medan: `[30, 30, 20, 10, 10]`."
    format_info = """```
{
  "ronde": 3, "ronde_total": 10, "medan": 5, "pasukan": 100,
  "nilai": [3, 1, 5, 2, 4],          # nilai medan ronde ini
  "nilai_berikut": [2, 2, 1, 5, 3],  # ronde berikutnya (None di ronde terakhir)
  "skor": {"Budi": 12.5, ...},
  "riwayat": [ {"ronde": 1, "nilai": [...], "alokasi": {"Budi": [20, 20, 20, 20, 20], ...},
                "penguasa": [["Budi"], ["Ani", "Citra"], [], ...], "poin": {"Budi": 4.0, ...}} ]
}
```"""
    lib_docs = [
        {"nama": "bagi_rata", "jenis": "fungsi", "tanda": "bagi_rata()", "ket": "Alokasi rata ke semua medan (sisa ke medan pertama)."},
        {"nama": "rata_rata_lawan", "jenis": "fungsi", "tanda": "rata_rata_lawan()", "ket": "Rata-rata pasukan lawan per medan di ronde lalu (list)."},
    ]
    templates = [
        {"id": "rata", "nama": "Si Rata", "ket": "Membagi rata ke semua medan.", "kode": "def aksi():\n    return bagi_rata()\n"},
        {"id": "fokus", "nama": "Fokus Tiga", "ket": "Menumpuk pasukan di 3 medan bernilai tertinggi.", "kode": '''def aksi():
    i = info()
    nilai = i["nilai"]
    urut = sorted(range(len(nilai)), key=lambda k: -nilai[k])
    pilihan = urut[:3]
    total = sum(nilai[k] for k in pilihan)
    alokasi = [0] * i["medan"]
    sisa = i["pasukan"]
    for k in pilihan:
        alokasi[k] = i["pasukan"] * nilai[k] // total
        sisa -= alokasi[k]
    alokasi[pilihan[0]] += sisa
    return alokasi
'''},
        {"id": "lawan_rata", "nama": "Pembaca Rata-rata", "ket": "Mengalahkan rata-rata lawan di medan bernilai tinggi, lalu melepas sisanya.", "kode": '''def aksi():
    i = info()
    if i["ronde"] == 1:
        return bagi_rata()
    musuh = rata_rata_lawan()
    nilai = i["nilai"]
    urut = sorted(range(i["medan"]), key=lambda k: -nilai[k] / (musuh[k] + 1))
    alokasi = [0] * i["medan"]
    sisa = i["pasukan"]
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
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0.0] * len(names), "riwayat": []}
        vals = []
        for r in range(cfg["ronde"]):
            g = rng(s, "nilai", r)
            vals.append([g.randint(1, 5) if cfg["nilai_acak"] else 1 for _ in range(cfg["medan"])])
        s["nilai"] = vals
        return s

    def pending(self, s: dict[str, Any]) -> list[int]:
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        r, c = s["ronde"], s["cfg"]
        cur = s["nilai"][r - 1] if r <= c["ronde"] else None
        nxt = s["nilai"][r] if r < c["ronde"] else None
        return {"ronde": min(r, c["ronde"]), "ronde_total": c["ronde"], "medan": c["medan"], "pasukan": c["pasukan"],
                "nilai": cur, "nilai_berikut": nxt, "skor": {n: round(x, 3) for n, x in zip(s["names"], s["skor"])},
                "riwayat": s["riwayat"]}

    def validate(self, s: dict[str, Any], p: int, a: Any) -> list[int]:
        c = s["cfg"]
        if not isinstance(a, (list, tuple)) or len(a) != c["medan"]:
            raise ActionError(f"kembalikan list berisi {c['medan']} angka")
        out = [as_int(x, "jumlah pasukan") for x in a]
        if any(x < 0 for x in out):
            raise ActionError("jumlah pasukan tidak boleh negatif")
        if sum(out) > c["pasukan"]:
            raise ActionError(f"total pasukan {sum(out)} melebihi {c['pasukan']}")
        return out

    def default(self, s: dict[str, Any], p: int) -> list[int]:
        c = s["cfg"]
        base = [c["pasukan"] // c["medan"]] * c["medan"]
        base[0] += c["pasukan"] - sum(base)
        return base

    def apply(self, s: dict[str, Any], actions: dict[int, Any]) -> list[dict[str, Any]]:
        n = s["names"]
        nilai = s["nilai"][s["ronde"] - 1]
        poin = [0.0] * len(n)
        penguasa = []
        for k, v in enumerate(nilai):
            top = max(actions[i][k] for i in actions)
            win = [i for i in actions if actions[i][k] == top] if top > 0 else []
            penguasa.append([n[i] for i in win])
            for i in win:
                poin[i] += v / len(win)
        for i in range(len(n)):
            s["skor"][i] += poin[i]
        entry = {"ronde": s["ronde"], "nilai": nilai, "alokasi": {n[i]: actions[i] for i in actions},
                 "penguasa": penguasa, "poin": {n[i]: round(poin[i], 3) for i in range(len(n))}}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **entry}]

    def over(self, s: dict[str, Any]) -> bool:
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s: dict[str, Any]) -> list[float]:
        return [round(x, 3) for x in s["skor"]]

    def bot_library(self, s: dict[str, Any], p: int, obs: dict[str, Any]) -> dict[str, Any]:
        def bagi_rata():
            return self.default(s, p)

        def rata_rata_lawan():
            if not s["riwayat"]:
                return [0.0] * s["cfg"]["medan"]
            last = s["riwayat"][-1]["alokasi"]
            others = [v for k, v in last.items() if k != s["names"][p]]
            return [sum(v[k] for v in others) / max(1, len(others)) for k in range(s["cfg"]["medan"])]

        return {"bagi_rata": bagi_rata, "rata_rata_lawan": rata_rata_lawan}
