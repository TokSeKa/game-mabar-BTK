"""Lelang Rahasia: tawaran tertutup untuk barang bernilai, modal terbatas.

Kustomisasi: jadwal yang terlihat (berapa barang ke depan), nilai pasti/taksiran pribadi/rahasia, koin lawan rahasia,
tawaran yang dibuka, jenis lelang (harga pertama, harga kedua, semua bayar), koin seri ikut hangus (%), koin tambahan
per ronde, barang minus (poin minus untuk penawar tertinggi, terendah, dan tengah), dan bonus koleksi set.
"""

from __future__ import annotations

import math
from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

# 16 barang bernilai, 4 kategori (untuk bonus set)
KATEGORI_BARANG = {
    "Keris Pusaka": "Pusaka", "Mahkota Bambu": "Pusaka", "Cincin Akik": "Pusaka", "Kitab Lontar": "Pusaka",
    "Lukisan Sawah": "Seni", "Wayang Kulit": "Seni", "Topeng Panji": "Seni", "Gamelan Mini": "Seni",
    "Batik Tulis": "Kriya", "Kain Songket": "Kriya", "Guci Antik": "Kriya", "Kendi Perak": "Kriya",
    "Angklung Emas": "Harta", "Peta Harta": "Harta", "Perahu Pinisi": "Harta", "Kotak Cendana": "Harta",
}
BARANG = ["Keris Pusaka", "Batik Tulis", "Wayang Kulit", "Gamelan Mini", "Lukisan Sawah", "Kain Songket", "Topeng Panji",
          "Guci Antik", "Angklung Emas", "Peta Harta", "Kendi Perak", "Mahkota Bambu", "Cincin Akik", "Perahu Pinisi",
          "Kitab Lontar", "Kotak Cendana"]
KUTUKAN = ["Jimat Sial", "Boneka Santet", "Cermin Retak", "Kendi Bocor", "Payung Robek", "Keris Karatan", "Peta Palsu",
           "Guci Berhantu", "Topeng Kutukan", "Kain Lapuk"]
JENIS = {"pertama": "Pemenang bayar tawarannya", "kedua": "Pemenang bayar tawaran tertinggi kedua",
         "semua_bayar": "Semua penawar bayar tawarannya"}


class LelangRahasia(Game):
    id = "lelang"
    nama = "Lelang Rahasia"
    ringkas = "Setiap ronde satu barang dilelang. Semua menawar diam-diam dengan modal terbatas. Penawar tertinggi membayar dan mendapat poin barang."
    hint_aksi = "jumlah tawaran (angka bulat)"
    timer = 25
    jeda_pada, jeda_hasil = ("lelang",), 5
    settings = [
        Setting("barang", "Jumlah barang", "int", 12, 3, 30),
        Setting("modal", "Modal koin", "int", 100, 10, 10000),
        Setting("nilai_sisa", "Poin per koin sisa", "float", 0.1, 0.0, 1.0, ket="Koin yang tidak terpakai bernilai sekian poin di akhir."),
        Setting("lihat_depan", "Barang terlihat ke depan", "int", 30, 0, 30, grup="informasi",
                ket="Berapa barang SETELAH barang yang sedang dilelang yang sudah terlihat. 0 = rahasia penuh (hanya barang saat ini). "
                    "30 = jadwal terbuka semua."),
        Setting("nilai_mode", "Nilai barang", "pilihan", "pasti", grup="informasi",
                pilihan=[["pasti", "Pasti (nilai asli terlihat)"], ["taksiran", "Taksiran pribadi (tiap pemain melihat perkiraan berbeda)"],
                         ["rahasia", "Rahasia sampai lelang barang itu selesai"]],
                ket="Taksiran: nilai yang kamu lihat bisa meleset; nilai asli dibuka setelah lelang. Pemenang sering kemahalan!"),
        Setting("taksiran_selisih", "Taksiran meleset sampai (poin)", "int", 3, 1, 6, grup="informasi", jika={"nilai_mode": "taksiran"}),
        Setting("koin_rahasia", "Koin lawan rahasia", "bool", False, grup="informasi", ket="Hanya koinmu sendiri yang terlihat."),
        Setting("buka_tawaran", "Yang dibuka setelah lelang", "pilihan", "semua", grup="informasi",
                pilihan=[["semua", "Semua tawaran"], ["pemenang", "Hanya pemenang & harga"], ["tidak", "Hanya nama pemenang"]]),
        Setting("jenis", "Jenis lelang", "pilihan", "pertama", grup="aturan", pilihan=[[k, v] for k, v in JENIS.items()],
                ket="Semua bayar: semua penawar kehilangan tawarannya, tapi hanya yang tertinggi dapat barang."),
        Setting("hangus_persen", "Koin seri ikut hangus (%)", "int", 0, 0, 100, grup="aturan",
                ket="Kalau tawaran tertinggi seri, barang hangus DAN para penawar seri itu kehilangan sekian persen tawarannya."),
        Setting("koin_ronde", "Koin tambahan tiap ronde", "int", 0, 0, 1000, grup="aturan", ket="Semua pemain dapat koin ini setelah setiap lelang."),
        Setting("barang_minus", "Barang minus", "int", 0, 0, 10, grup="kejutan",
                ket="Jumlah barang kutukan (nilai −1 sampai −8) di jadwal. Tidak ada yang membayar barang minus; poin minusnya kena ke "
                    "penawar TERTINGGI dan TERENDAH, plus yang di TENGAH kalau jumlah pemain ganjil dan lebih dari 3."),
        Setting("bonus_set", "Bonus koleksi set", "int", 0, 0, 50, grup="kejutan",
                ket="Setiap 3 barang dari kategori yang sama (Pusaka, Seni, Kriya, Harta) memberi bonus poin ini. 0 = mati."),
    ]
    presets = [
        {"id": "jadwal_rahasia", "nama": "Jadwal Rahasia", "ket": "Barang berikutnya tidak terlihat: kamu tidak tahu apa yang akan datang.",
         "nilai": {"lihat_depan": 0}},
        {"id": "gelap", "nama": "Lelang Gelap", "ket": "Jadwal tertutup, nilai hanya taksiran pribadi, dompet lawan rahasia, tawaran lawan tidak dibuka.",
         "nilai": {"lihat_depan": 0, "nilai_mode": "taksiran", "koin_rahasia": True, "buka_tawaran": "pemenang"}},
        {"id": "kacau", "nama": "Kacau", "ket": "Barang minus, koin seri hangus 50%, bonus set, dan jadwal hanya terlihat 2 barang ke depan.",
         "nilai": {"lihat_depan": 2, "barang_minus": 3, "hangus_persen": 50, "bonus_set": 8}},
    ]
    aturan = """
- Ada sejumlah **barang** (default 12) yang dilelang satu per satu. Default: **nilai poin semua barang sudah diumumkan dari awal** (1–10).
  Host bisa menyembunyikan jadwal (hanya *N* barang ke depan yang terlihat, atau rahasia penuh) dan nilai barang (taksiran pribadi atau rahasia).
- Setiap ronde semua pemain menawar secara **tertutup**, maksimal sebanyak koin yang dimiliki (modal awal default 100 koin).
- **Penawar tertinggi** mendapat poin barang itu dan membayar tawarannya (atau tawaran tertinggi kedua / semua penawar bayar, sesuai *jenis lelang*).
- Kalau tawaran tertinggi **seri**, barang **hangus**: tidak ada yang dapat. Kalau *koin seri ikut hangus* > 0%, para penawar seri itu kehilangan
  sekian persen tawarannya.
- **Barang minus** (kalau diaktifkan): barang kutukan bernilai −1 sampai −8. Tidak ada yang membayar, tapi poin minusnya kena ke penawar
  **tertinggi** dan **terendah** (semua yang seri di ujung ikut kena), plus penawar **tengah** kalau jumlah pemain ganjil dan lebih dari 3.
  Kalau semua menawar sama, semua kena. Jadi tawaran barang minus adalah soal posisi: jangan di ujung, jangan di tengah.
- **Bonus set** (kalau diaktifkan): setiap 3 barang dari kategori yang sama (Pusaka, Seni, Kriya, Harta) memberi bonus poin.
- Skor akhir = poin barang + bonus set + koin sisa × *poin per koin sisa* (default 0,1).
"""
    format_aksi = "Satu angka bulat 0 sampai koinmu, misalnya `25`."
    format_info = """```
{ "ronde": 3, "ronde_total": 12,
  "barang": {"nama": "Keris Pusaka", "kategori": "Pusaka", "nilai": 8},   # nilai: pasti / taksiranmu / None kalau rahasia
  "jadwal": [5, 2, 8, None, ...],     # nilai semua barang urut ronde; None = belum terlihat (lihat_depan / nilai rahasia)
  "nama_barang": ["Batik Tulis", ...], "kategori": ["Kriya", ...],        # None untuk barang yang belum terlihat
  "koin": {"Budi": 70, "Ani": None, ...},   # None kalau koin lawan dirahasiakan (koinmu selalu terlihat)
  "poin": {"Budi": 5, ...}, "nilai_sisa": 0.1, "jenis": "pertama", "hangus_persen": 0, "koin_ronde": 0,
  "nilai_mode": "pasti", "lihat_depan": 30, "bonus_set": 0, "koleksi": {"Budi": {"Pusaka": 1}, ...},
  "riwayat": [ {"ronde": 1, "nama": "Batik Tulis", "nilai": 5, "minus": False, "tawaran": {"Budi": 30, "Ani": 20},
                "pemenang": "Budi", "harga": 30, "hangus": False, "kena_minus": []} ] }
```
- `tawaran` di riwayat bisa `None` (hanya pemenang yang dibuka) dan `harga` bisa `None` (hanya nama pemenang).
- Barang minus: `minus` True, `kena_minus` berisi pemain yang kena poin minus."""
    lib_docs = [
        {"nama": "koin_saya", "jenis": "fungsi", "tanda": "koin_saya()", "ket": "Koinmu sekarang."},
        {"nama": "nilai_sekarang", "jenis": "fungsi", "tanda": "nilai_sekarang()", "ket": "Nilai barang yang sedang dilelang menurut yang kamu lihat (pasti/taksiran), atau None kalau rahasia."},
        {"nama": "nilai_tersisa", "jenis": "fungsi", "tanda": "nilai_tersisa(tebakan=5)", "ket": "Jumlah nilai barang positif dari ronde ini sampai akhir; barang yang belum terlihat dihitung sebesar `tebakan`."},
        {"nama": "kemungkinan_minus", "jenis": "fungsi", "tanda": "kemungkinan_minus()", "ket": "True kalau barang sekarang terlihat bernilai minus (barang kutukan)."},
    ]
    templates = [
        {"id": "proporsional", "nama": "Proporsional", "ket": "Menawar sebanding nilai barang dibanding total nilai yang tersisa. Barang minus: menawar di posisi tengah-bawah.", "kode": '''def aksi():
    i = info()
    koin = koin_saya()
    if kemungkinan_minus():
        return min(koin, 2 + saya())
    nilai = nilai_sekarang()
    if nilai == None:
        nilai = 5
    return int(koin * nilai / max(1, nilai_tersisa()))
'''},
        {"id": "pemburu_mahal", "nama": "Pemburu Barang Mahal", "ket": "Hanya serius menawar barang bernilai 7 ke atas.", "kode": '''def aksi():
    koin = koin_saya()
    nilai = nilai_sekarang()
    if kemungkinan_minus():
        return min(koin, 3)
    if nilai != None and nilai >= 7:
        return min(koin, nilai * 5)
    return min(koin, 1)
'''},
        {"id": "pengintai", "nama": "Pengintai Dompet", "ket": "Menawar sedikit di atas dompet lawan terkaya untuk barang bagus (kalau dompet lawan terlihat).", "kode": '''def aksi():
    i = info()
    saya = nama_saya()
    koin = koin_saya()
    nilai = nilai_sekarang()
    if nilai == None:
        nilai = 5
    if nilai < 0:
        return min(koin, 4)
    dompet = [v for k, v in i["koin"].items() if k != saya and v != None]
    if dompet and nilai >= 6:
        terkaya = max(dompet)
        if terkaya + 1 <= koin and terkaya + 1 <= nilai * 8:
            return terkaya + 1
    return min(koin, nilai * 3)
'''},
    ]

    # ------------------------------------------------------------ jadwal
    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "koin": [cfg["modal"]] * len(names),
             "poin": [0] * len(names), "riwayat": [], "koleksi": [{} for _ in names]}
        g = rng(s, "barang")
        nama = BARANG[:]
        g.shuffle(nama)
        n = cfg["barang"]
        s["jadwal"] = [g.randint(1, 10) for _ in range(n)]
        s["nama_barang"] = [nama[k % len(nama)] for k in range(n)]
        k_minus = min(cfg["barang_minus"], n - 1)
        if k_minus > 0:
            gm = rng(s, "minus")
            kut = KUTUKAN[:]
            gm.shuffle(kut)
            for j, idx in enumerate(sorted(gm.sample(range(1, n), k_minus))):
                s["jadwal"][idx] = -gm.randint(1, 8)
                s["nama_barang"][idx] = kut[j % len(kut)]
        s["kategori"] = [KATEGORI_BARANG.get(x) for x in s["nama_barang"]]
        return s

    def _taksiran(self, s, p, k):
        d = s["cfg"]["taksiran_selisih"]
        return s["jadwal"][k] + rng(s, "taksiran", p, k).randint(-d, d)

    def _seen(self, s, viewer, k):
        """Nilai barang ke-k menurut penonton ``viewer`` (None = penonton umum, "semua" = tanpa kabut)."""
        c = s["cfg"]
        r = s["ronde"]
        if viewer == "semua" or k < r - 1:
            return s["jadwal"][k]                      # sudah dilelang: nilai asli terbuka
        if k > r - 1 + c["lihat_depan"]:
            return None                                # belum terlihat
        if c["nilai_mode"] == "pasti":
            return s["jadwal"][k]
        if c["nilai_mode"] == "taksiran" and viewer is not None:
            return self._taksiran(s, viewer, k)
        return None

    def _name_seen(self, s, viewer, k):
        if viewer == "semua" or k <= s["ronde"] - 1 + s["cfg"]["lihat_depan"]:
            return s["nama_barang"][k]
        return None

    def _entry_for(self, s, e, viewer):
        mode = s["cfg"]["buka_tawaran"]
        if viewer == "semua" or mode == "semua":
            return e
        out = {**e, "tawaran": None, "hangus_koin": None}
        if mode == "tidak":
            out["harga"] = None
        if isinstance(viewer, int):
            me = s["names"][viewer]
            out["tawaran_saya"] = e["tawaran"].get(me)          # tawaranmu sendiri selalu terlihat
            if me in (e.get("hangus_koin") or {}):
                out["hangus_koin"] = {me: e["hangus_koin"][me]}
        return out

    def _set_bonus(self, s, p):
        b = s["cfg"]["bonus_set"]
        return sum(cnt // 3 for cnt in s["koleksi"][p].values()) * b if b > 0 else 0

    def _view(self, s, viewer):
        c, r, n = s["cfg"], s["ronde"], s["names"]
        total = c["barang"]
        cur = None
        if r <= total:
            cur = {"nama": s["nama_barang"][r - 1], "kategori": s["kategori"][r - 1], "nilai": self._seen(s, viewer, r - 1)}
        hide_coins = c["koin_rahasia"] and viewer != "semua"
        koin = {n[i]: (s["koin"][i] if not hide_coins or viewer == i else None) for i in range(len(n))}
        skor = {n[i]: (round(s["poin"][i] + self._set_bonus(s, i) + s["koin"][i] * c["nilai_sisa"], 2)
                       if not hide_coins or viewer == i else None) for i in range(len(n))}
        return {"ronde": min(r, total), "ronde_total": total, "barang": cur,
                "jadwal": [self._seen(s, viewer, k) for k in range(total)],
                "nama_barang": [self._name_seen(s, viewer, k) for k in range(total)],
                "kategori": [s["kategori"][k] if self._name_seen(s, viewer, k) else None for k in range(total)],
                "koin": koin, "poin": dict(zip(n, s["poin"])), "skor": skor, "nilai_sisa": c["nilai_sisa"],
                "jenis": c["jenis"], "hangus_persen": c["hangus_persen"], "koin_ronde": c["koin_ronde"],
                "nilai_mode": c["nilai_mode"], "lihat_depan": c["lihat_depan"], "buka_tawaran": c["buka_tawaran"],
                "koin_rahasia": c["koin_rahasia"], "bonus_set": c["bonus_set"], "ada_minus": c["barang_minus"] > 0,
                "koleksi": {n[i]: dict(s["koleksi"][i]) for i in range(len(n))},
                "riwayat": [self._entry_for(s, e, viewer) for e in s["riwayat"]]}

    def event_for(self, s, e, viewer):
        return self._entry_for(s, e, viewer) if e.get("jenis") == "lelang" else e

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

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
        c, n, r = s["cfg"], s["names"], s["ronde"]
        idx = r - 1
        nilai = s["jadwal"][idx]
        bids = dict(actions)
        top = max(bids.values())
        entry: dict[str, Any] = {"ronde": r, "nama": s["nama_barang"][idx], "kategori": s["kategori"][idx], "nilai": nilai,
                                 "minus": nilai < 0, "tawaran": {n[i]: v for i, v in bids.items()}, "pemenang": None,
                                 "harga": 0, "hangus": False, "hangus_koin": {}, "kena_minus": []}
        if nilai < 0:
            # barang kutukan: tidak ada yang bayar; ujung atas, ujung bawah (dan tengah kalau ganjil > 3) kena poin minus
            vals = sorted(bids.values())
            lo = vals[0]
            kena = {i for i, v in bids.items() if v in (top, lo)}
            if len(vals) % 2 == 1 and len(vals) > 3:
                med = vals[len(vals) // 2]
                kena |= {i for i, v in bids.items() if v == med}
            for i in sorted(kena):
                s["poin"][i] += nilai
            entry["kena_minus"] = [n[i] for i in sorted(kena)]
        else:
            best = [i for i, v in bids.items() if v == top]
            winner = best[0] if top > 0 and len(best) == 1 else None
            if c["jenis"] == "semua_bayar":
                for i, v in bids.items():
                    s["koin"][i] -= v
            if winner is not None:
                others = [v for i, v in bids.items() if i != winner]
                harga = top if c["jenis"] != "kedua" else (max(others) if others else 0)
                if c["jenis"] != "semua_bayar":
                    s["koin"][winner] -= harga
                s["poin"][winner] += nilai
                kat = s["kategori"][idx]
                if kat:
                    s["koleksi"][winner][kat] = s["koleksi"][winner].get(kat, 0) + 1
                entry.update({"pemenang": n[winner], "harga": harga})
            elif top > 0:
                entry["hangus"] = True
                if c["hangus_persen"] > 0 and c["jenis"] != "semua_bayar":
                    for i in best:
                        burn = math.floor(bids[i] * c["hangus_persen"] / 100)
                        s["koin"][i] -= burn
                        entry["hangus_koin"][n[i]] = burn
        if c["koin_ronde"] > 0:
            s["koin"] = [k + c["koin_ronde"] for k in s["koin"]]
        s["riwayat"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "lelang", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["barang"]

    def scores(self, s):
        k = s["cfg"]["nilai_sisa"]
        return [round(p + self._set_bonus(s, i) + c * k, 2) for i, (p, c) in enumerate(zip(s["poin"], s["koin"]))]

    def bot_library(self, s, p, obs):
        def nilai_tersisa(tebakan=5):
            t = as_int(tebakan, "tebakan")
            vals = obs["jadwal"][obs["ronde"] - 1:]
            return sum((t if v is None else v) for v in vals if v is None or v > 0)

        def kemungkinan_minus():
            v = obs["barang"]["nilai"] if obs["barang"] else None
            return v is not None and v < 0

        return {"koin_saya": lambda: s["koin"][p], "nilai_sekarang": lambda: obs["barang"]["nilai"] if obs["barang"] else None,
                "nilai_tersisa": nilai_tersisa, "kemungkinan_minus": kemungkinan_minus}
