"""Lelang Rahasia: tawaran tertutup untuk barang bernilai, modal terbatas."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

BARANG = ["Keris Pusaka", "Batik Tulis", "Wayang Kulit", "Gamelan Mini", "Lukisan Sawah", "Kain Songket", "Topeng Panji",
          "Guci Antik", "Angklung Emas", "Peta Harta", "Kendi Perak", "Mahkota Bambu", "Cincin Akik", "Perahu Pinisi",
          "Kitab Lontar", "Kotak Cendana"]


class LelangRahasia(Game):
    id = "lelang"
    nama = "Lelang Rahasia"
    ringkas = "Setiap ronde satu barang dilelang. Semua menawar diam-diam dengan modal terbatas. Penawar tertinggi membayar dan mendapat poin barang."
    hint_aksi = "jumlah tawaran (angka bulat)"
    timer = 25
    settings = [
        Setting("barang", "Jumlah barang", "int", 12, 3, 30),
        Setting("modal", "Modal koin", "int", 100, 10, 10000),
        Setting("nilai_sisa", "Poin per koin sisa", "float", 0.1, 0.0, 1.0, ket="Koin yang tidak terpakai bernilai sekian poin di akhir."),
    ]
    aturan = """
- Ada sejumlah **barang** (default 12) yang dilelang satu per satu. **Nilai poin semua barang sudah diumumkan dari awal** (1–10), jadi kamu bisa merencanakan.
- Setiap ronde semua pemain menawar secara **tertutup**, maksimal sebanyak koin yang dimiliki (modal awal default 100 koin, tidak bertambah).
- **Penawar tertinggi** membayar tawarannya dan mendapat poin barang itu. Kalau tawaran tertinggi **seri**, barang **hangus**: tidak ada yang dapat dan tidak ada yang bayar.
- Skor akhir = poin barang + koin sisa × *poin per koin sisa* (default 0,1).
"""
    format_aksi = "Satu angka bulat 0 sampai koinmu, misalnya `25`."
    format_info = """```
{ "ronde": 3, "ronde_total": 12, "barang": {"nama": "Keris Pusaka", "nilai": 8},
  "jadwal": [5, 2, 8, 3, ...],   # nilai semua barang, urut ronde (indeks 0 = ronde 1)
  "koin": {"Budi": 70, ...}, "poin": {"Budi": 5, ...}, "nilai_sisa": 0.1,
  "riwayat": [ {"ronde": 1, "nilai": 5, "tawaran": {"Budi": 30, "Ani": 20}, "pemenang": "Budi", "harga": 30} ] }
```"""
    templates = [
        {"id": "proporsional", "nama": "Proporsional", "ket": "Menawar sebanding nilai barang dibanding total nilai yang tersisa.", "kode": '''def aksi():
    i = info()
    koin = i["koin"][nama_saya()]
    sisa_nilai = sum(i["jadwal"][i["ronde"] - 1:])
    return int(koin * i["barang"]["nilai"] / sisa_nilai)
'''},
        {"id": "pemburu_mahal", "nama": "Pemburu Barang Mahal", "ket": "Hanya serius menawar barang bernilai 7 ke atas.", "kode": '''def aksi():
    i = info()
    koin = i["koin"][nama_saya()]
    if i["barang"]["nilai"] >= 7:
        return min(koin, i["barang"]["nilai"] * 5)
    return min(koin, 1)
'''},
        {"id": "pengintai", "nama": "Pengintai Dompet", "ket": "Menawar sedikit di atas dompet lawan terkaya untuk barang bagus, kalau masih masuk akal.", "kode": '''def aksi():
    i = info()
    saya = nama_saya()
    koin = i["koin"][saya]
    nilai = i["barang"]["nilai"]
    terkaya = max(v for k, v in i["koin"].items() if k != saya)
    if nilai >= 6 and terkaya + 1 <= koin and terkaya + 1 <= nilai * 8:
        return terkaya + 1
    return min(koin, nilai * 3)
'''},
    ]

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "koin": [cfg["modal"]] * len(names),
             "poin": [0] * len(names), "riwayat": []}
        g = rng(s, "barang")
        nama = BARANG[:]
        g.shuffle(nama)
        s["jadwal"] = [g.randint(1, 10) for _ in range(cfg["barang"])]
        s["nama_barang"] = [nama[k % len(nama)] for k in range(cfg["barang"])]
        return s

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s):
        c, r, n = s["cfg"], s["ronde"], s["names"]
        cur = {"nama": s["nama_barang"][r - 1], "nilai": s["jadwal"][r - 1]} if r <= c["barang"] else None
        return {"ronde": min(r, c["barang"]), "ronde_total": c["barang"], "barang": cur, "jadwal": s["jadwal"],
                "nama_barang": s["nama_barang"], "koin": dict(zip(n, s["koin"])), "poin": dict(zip(n, s["poin"])),
                "nilai_sisa": c["nilai_sisa"], "riwayat": s["riwayat"]}

    def validate(self, s, p, a):
        x = as_int(a, "tawaran")
        if x < 0:
            raise ActionError("tawaran tidak boleh negatif")
        if x > s["koin"][p]:
            raise ActionError(f"tawaran {x} melebihi koinmu ({s['koin'][p]})")
        return x

    def default(self, s, p):
        return 0

    def apply(self, s, actions):
        n, r = s["names"], s["ronde"]
        nilai = s["jadwal"][r - 1]
        top = max(actions.values())
        best = [i for i, v in actions.items() if v == top]
        winner = best[0] if top > 0 and len(best) == 1 else None
        if winner is not None:
            s["koin"][winner] -= top
            s["poin"][winner] += nilai
        entry = {"ronde": r, "nama": s["nama_barang"][r - 1], "nilai": nilai, "tawaran": {n[i]: v for i, v in actions.items()},
                 "pemenang": n[winner] if winner is not None else None, "harga": top if winner is not None else 0,
                 "hangus": winner is None and top > 0}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "lelang", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["barang"]

    def scores(self, s):
        k = s["cfg"]["nilai_sisa"]
        return [round(p + c * k, 2) for p, c in zip(s["poin"], s["koin"])]
