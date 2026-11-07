"""Pasar Malam Tycoon: semua pedagang berjualan di pasar yang sama, berebut pembeli lewat produk, harga, dan iklan."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

PRODUK = {
    "sate": {"nama": "Sate", "modal": 6000, "wajar": 15000, "permintaan": 120},
    "es_teh": {"nama": "Es Teh", "modal": 2000, "wajar": 6000, "permintaan": 200},
    "bakso": {"nama": "Bakso", "modal": 5000, "wajar": 13000, "permintaan": 130},
    "mainan": {"nama": "Mainan", "modal": 8000, "wajar": 20000, "permintaan": 60},
}
CUACA = {
    "cerah": {"sate": 1.0, "es_teh": 1.1, "bakso": 0.9, "mainan": 1.0},
    "panas": {"sate": 0.9, "es_teh": 1.6, "bakso": 0.6, "mainan": 0.9},
    "mendung": {"sate": 1.0, "es_teh": 0.8, "bakso": 1.2, "mainan": 0.9},
    "hujan": {"sate": 0.7, "es_teh": 0.4, "bakso": 1.6, "mainan": 0.5},
}
PELUANG_CUACA = [("cerah", 0.4), ("panas", 0.2), ("mendung", 0.25), ("hujan", 0.15)]
ACARA = ["Konser Dangdut", "Lomba Agustusan", "Pawai Budaya", "Layar Tancap", "Bazar Sekolah"]
NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
IKLAN_SETENGAH = 30000   # iklan sebesar ini = daya tarik ×1,5
KEJADIAN = {"razia": "🚨 Razia: {p} dilarang dijual hari ini", "viral": "📱 Viral: permintaan {p} ×2,5",
            "naik": "📈 Bahan naik: modal {p} ×1,5", "subsidi": "🎁 Subsidi: modal {p} separuh harga"}


def _weight(price: int, ads: int, wajar: int) -> float:
    appeal = max(0.0, 2.0 - price / wajar)
    return appeal * appeal * (1 + ads / (ads + IKLAN_SETENGAH))


class PasarMalamTycoon(Game):
    id = "tycoon"
    nama = "Pasar Malam Tycoon"
    ringkas = "Semua pedagang berjualan di pasar malam yang sama. Pilih dagangan, jumlah, harga, dan iklan; pembeli terbagi ke penjual yang paling menarik."
    kategori = "simultan"
    min_pemain, max_pemain = 2, 8
    hint_aksi = "'tutup' atau {'produk': 'sate', 'jumlah': 30, 'harga': 14000, 'iklan': 0}"
    timer = 40
    jeda_pada, jeda_hasil = ("hari",), 8
    label_skor = "Uang (Rp)"
    settings = [
        Setting("hari", "Jumlah hari", "int", 15, 3, 60),
        Setting("modal", "Modal awal (Rp)", "int", 200000, 50000, 10_000_000),
        Setting("pesaing_rahasia", "Dagangan pesaing rahasia", "bool", False, grup="informasi",
                ket="Produk, harga, iklan, dan hasil jualan pedagang lain tidak dibuka (total uang tetap terlihat); "
                    "yang terlihat hanya jumlah penjual & pembeli tiap produk."),
        Setting("ramalan", "Ketepatan ramalan cuaca (%)", "int", 75, 0, 100, grup="informasi", ket="0 = tidak ada ramalan sama sekali."),
        Setting("stok_awet", "Stok tahan sehari", "bool", False, grup="aturan",
                ket="Barang yang tidak laku tidak langsung basi: bisa dijual lagi besok (produk yang sama, tanpa modal), setelah itu basi."),
        Setting("event_pasar", "Kejadian pasar (%)", "int", 0, 0, 100, grup="kejutan",
                ket="Peluang tiap hari ada kejadian (diumumkan pagi): razia (satu produk dilarang), viral (permintaan ×2,5), "
                    "bahan naik (modal ×1,5), atau subsidi (modal separuh)."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut", "ket": "Dagangan pesaing rahasia dan ramalan cuaca hanya 50% tepat.",
         "nilai": {"pesaing_rahasia": True, "ramalan": 50}},
        {"id": "kacau", "nama": "Kacau", "ket": "Kejadian pasar sering muncul dan stok tahan sehari.", "nilai": {"event_pasar": 40, "stok_awet": True}},
    ]
    aturan = """
- Setiap malam setiap pemain memilih **satu dagangan** (Sate, Es Teh, Bakso, Mainan) atau tutup. Tentukan **jumlah** yang dibeli (bayar modal di muka),
  **harga jual**, dan **iklan** (Rp). Total modal + iklan tidak boleh melebihi uangmu.
- **Pembeli dibagi bersama.** Tiap penjual punya daya tarik = (2 − harga/harga_wajar)² × (1 + iklan/(iklan + 30.000)).
  Penjual seharga wajar tanpa iklan = 1; seharga 2× wajar = 0 (tidak laku). Pangsa pembeli = daya_tarik / (1 + jumlah daya tarik semua penjual produk itu),
  dari pasar sebesar 2 × permintaan. Jadi makin banyak penjual, pasar sedikit membesar tapi tiap penjual kebagian lebih sedikit.
- Barang yang tidak laku **basi** (hangus). Kalau daganganmu habis, separuh pembeli yang kecewa pindah ke penjual lain yang masih punya stok.
- **Permintaan dipengaruhi hari:** cuaca (diumumkan pagi hari), akhir pekan (×1,3; mainan ×1,8), dan acara khusus (×1,6). Ada juga
  gejolak acak ±15% yang baru ketahuan malamnya. Ramalan cuaca besok tersedia, benar sekitar 75%.
- Permintaan dasar membesar sesuai jumlah pemain supaya pasar tidak terlalu sempit.
- Uang terbanyak di akhir menang.
- Opsi host: **dagangan pesaing rahasia**, **ketepatan ramalan** (0 = tanpa ramalan), **stok tahan sehari** (sisa barang bisa dijual
  lagi besok untuk produk yang sama, dijual lebih dulu dari barang baru), dan **kejadian pasar** (razia, viral, bahan naik, subsidi).
"""
    format_aksi = """- `"tutup"` (libur, uang aman), atau
- `{"produk": "sate", "jumlah": 30, "harga": 14000, "iklan": 5000}`. Produk: `sate`, `es_teh`, `bakso`, `mainan`. Harga 1 sampai 3× harga wajar."""
    format_info = """```
{ "hari": 4, "hari_total": 15, "nama_hari": "Kamis", "akhir_pekan": False, "cuaca": "hujan", "acara": None,
  "ramalan_besok": "mendung",
  "produk": {"sate": {"nama": "Sate", "modal": 6000, "wajar": 15000, "permintaan": 120, "pengaruh": 0.7}, ...},
  "uang": {"Budi": 254000, ...},
  "riwayat": [ {"hari": 1, "cuaca": "cerah", "acara": None, "pembeli": {"sate": 160, ...},
                "jual": {"Budi": {"produk": "sate", "jumlah": 30, "harga": 14000, "iklan": 0, "terjual": 30, "untung": 240000}, "Ani": "tutup"}} ] }
```
`pengaruh` = pengali permintaan hari ini (cuaca × akhir pekan × acara × kejadian), belum termasuk gejolak acak dan jumlah pemain.
`produk[k]["modal"]` adalah modal HARI INI (bisa berubah karena kejadian pasar) dan `dilarang` True kalau produk itu dirazia.
`kejadian` = kejadian pasar hari ini atau None. `stok_saya` = sisa barang kemarin yang masih bisa dijual hari ini (atau None).
Kalau dagangan pesaing rahasia, entri `jual` pedagang lain berisi `{"rahasia": True}` dan setiap hari punya `penjual` (jumlah penjual per produk)."""
    lib_docs = [
        {"nama": "uang_saya", "jenis": "fungsi", "tanda": "uang_saya()", "ket": "Uangmu sekarang (Rp)."},
        {"nama": "maks_beli", "jenis": "fungsi", "tanda": "maks_beli(produk, iklan=0)", "ket": "Jumlah barang terbanyak yang bisa kamu beli dengan uangmu."},
        {"nama": "perkiraan_pembeli", "jenis": "fungsi", "tanda": "perkiraan_pembeli(produk, harga, iklan=0)", "ket": "Perkiraan pembeli untukmu kalau pesaing memakai harga & iklan seperti kemarin (tanpa gejolak acak)."},
        {"nama": "pesaing_kemarin", "jenis": "fungsi", "tanda": "pesaing_kemarin(produk)", "ket": "List penjual produk itu kemarin: {'nama', 'harga', 'iklan', 'jumlah', 'terjual'}. Kosong kalau dagangan pesaing rahasia."},
        {"nama": "jumlah_penjual_kemarin", "jenis": "fungsi", "tanda": "jumlah_penjual_kemarin(produk)", "ket": "Banyaknya pedagang lain yang menjual produk itu kemarin (selalu terlihat)."},
        {"nama": "untung_per_barang", "jenis": "fungsi", "tanda": "untung_per_barang(produk, harga)", "ket": "harga − modal per barang."},
    ]
    templates = [
        {"id": "sate_setia", "nama": "Pedagang Sate Setia", "ket": "Selalu jualan sate dengan harga wajar, jumlah menyesuaikan perkiraan pembeli.", "kode": '''def aksi():
    harga = 15000
    q = min(maks_beli("sate"), perkiraan_pembeli("sate", harga))
    if q <= 0:
        return "tutup"
    return {"produk": "sate", "jumlah": q, "harga": harga, "iklan": 0}
'''},
        {"id": "pembaca_cuaca", "nama": "Pembaca Cuaca", "ket": "Memilih dagangan dengan perkiraan untung terbesar hari ini.", "kode": '''def aksi():
    i = info()
    terbaik = None
    for k in i["produk"]:
        p = i["produk"][k]
        harga = p["wajar"] * 95 // 100
        q = min(maks_beli(k, 5000), perkiraan_pembeli(k, harga, 5000))
        untung = q * untung_per_barang(k, harga) - 5000
        if terbaik == None or untung > terbaik[0]:
            terbaik = [untung, k, q, harga]
    if terbaik == None or terbaik[0] <= 0:
        return "tutup"
    return {"produk": terbaik[1], "jumlah": terbaik[2], "harga": terbaik[3], "iklan": 5000}
'''},
        {"id": "banting_harga", "nama": "Banting Harga", "ket": "Cari produk yang paling sepi pesaing, jual 20% di bawah harga wajar.", "kode": '''def aksi():
    i = info()
    pilihan = sorted(i["produk"].keys(), key=lambda k: len(pesaing_kemarin(k)))
    k = pilihan[0]
    harga = i["produk"][k]["wajar"] * 80 // 100
    q = min(maks_beli(k), perkiraan_pembeli(k, harga) * 11 // 10)
    if q <= 0:
        return "tutup"
    return {"produk": k, "jumlah": q, "harga": harga, "iklan": 0}
'''},
    ]

    # ------------------------------------------------------------ hari
    def _plan(self, s):
        plan = []
        for d in range(1, s["cfg"]["hari"] + 2):
            g = rng(s, "hari", d)
            x, cuaca = g.random(), "cerah"
            for c, pr in PELUANG_CUACA:
                if x < pr:
                    cuaca = c
                    break
                x -= pr
            acara = g.choice(ACARA) if g.random() < 0.12 else None
            plan.append({"cuaca": cuaca, "acara": acara, "gejolak": {k: round(g.uniform(0.85, 1.15), 3) for k in PRODUK}})
        akurasi = s["cfg"].get("ramalan", 75) / 100
        for d in range(len(plan) - 1):
            g = rng(s, "ramalan", d)
            real = plan[d + 1]["cuaca"]
            plan[d]["ramalan"] = (real if g.random() < akurasi else g.choice([c for c in CUACA if c != real])) if akurasi > 0 else None
        plan[-1]["ramalan"] = None
        pct = s["cfg"].get("event_pasar", 0)
        for d, day in enumerate(plan):
            day["kejadian"] = None
            if pct > 0:
                g = rng(s, "kejadian", d)
                if g.random() * 100 < pct:
                    jenis, prod = g.choice(sorted(KEJADIAN)), g.choice(sorted(PRODUK))
                    day["kejadian"] = {"jenis": jenis, "produk": prod, "teks": KEJADIAN[jenis].format(p=PRODUK[prod]["nama"])}
        return plan

    def _kej(self, s, d, k, jenis):
        kj = s["plan"][d - 1].get("kejadian")
        return bool(kj and kj["jenis"] == jenis and kj["produk"] == k)

    def _modal(self, s, d, k):
        m = PRODUK[k]["modal"]
        if self._kej(s, d, k, "naik"):
            return m * 3 // 2
        if self._kej(s, d, k, "subsidi"):
            return m // 2
        return m

    def _weekend(self, d):
        return (d - 1) % 7 >= 5

    def _mult(self, s, d, k):
        day = s["plan"][d - 1]
        m = CUACA[day["cuaca"]][k]
        if self._weekend(d):
            m *= 1.8 if k == "mainan" else 1.3
        if day["acara"]:
            m *= 1.6
        if self._kej(s, d, k, "viral"):
            m *= 2.5
        return round(m, 4)

    def _scale(self, s):
        return 1 + (len(s["names"]) - 1) * 0.35

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "hari": 1, "uang": [cfg["modal"]] * len(names), "riwayat": [],
             "terjual": [0] * len(names), "stok": [None] * len(names)}
        s["plan"] = self._plan(s)
        return s

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    def _fog_day(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"].get("pesaing_rahasia"):
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return {**e, "jual": {nm: (a if nm == me or a == "tutup" else {"rahasia": True}) for nm, a in e["jual"].items()}}

    def _view(self, s, viewer):
        d = min(s["hari"], s["cfg"]["hari"])
        day = s["plan"][d - 1]
        kj = day.get("kejadian")
        return {"hari": d, "hari_total": s["cfg"]["hari"], "nama_hari": NAMA_HARI[(d - 1) % 7], "akhir_pekan": self._weekend(d),
                "cuaca": day["cuaca"], "acara": day["acara"], "ramalan_besok": day["ramalan"] if d < s["cfg"]["hari"] else None,
                "kejadian": kj,
                "produk": {k: {**v, "modal": self._modal(s, d, k), "modal_biasa": v["modal"], "pengaruh": self._mult(s, d, k),
                               "dilarang": self._kej(s, d, k, "razia")} for k, v in PRODUK.items()},
                "uang": dict(zip(s["names"], s["uang"])), "pesaing_rahasia": bool(s["cfg"].get("pesaing_rahasia")),
                "stok_awet": bool(s["cfg"].get("stok_awet")),
                "riwayat": [self._fog_day(s, e, viewer) for e in s["riwayat"]]}

    def event_for(self, s, e, viewer):
        return self._fog_day(s, e, viewer) if e.get("jenis") == "hari" else e

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        st = s["stok"][p]
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p],
                "stok_saya": dict(st) if st and st["hari"] == s["hari"] else None}

    def validate(self, s, p, a):
        if a is None or (isinstance(a, str) and a.strip().lower() in ("tutup", "libur", "")):
            return "tutup"
        if not isinstance(a, dict):
            raise ActionError("aksi: 'tutup' atau {'produk': 'sate', 'jumlah': 30, 'harga': 14000, 'iklan': 0}")
        k = str(a.get("produk", "")).strip().lower().replace(" ", "_")
        if k not in PRODUK:
            raise ActionError(f"produk harus salah satu dari: {', '.join(PRODUK)}")
        info = PRODUK[k]
        d = s["hari"]
        if self._kej(s, d, k, "razia"):
            raise ActionError(f"{info['nama']} sedang dirazia hari ini, pilih dagangan lain")
        q = as_int(a.get("jumlah", 0), "jumlah")
        price = as_int(a.get("harga", info["wajar"]), "harga")
        ads = as_int(a.get("iklan", 0), "iklan")
        if q < 0 or ads < 0:
            raise ActionError("jumlah dan iklan tidak boleh negatif")
        if q > 100_000:
            raise ActionError("jumlah terlalu banyak")
        if not 1 <= price <= info["wajar"] * 3:
            raise ActionError(f"harga {info['nama']} harus 1 sampai {info['wajar'] * 3}")
        cost = q * self._modal(s, d, k) + ads
        if cost > s["uang"][p]:
            raise ActionError(f"uang tidak cukup: butuh Rp{cost}, uangmu Rp{s['uang'][p]}")
        if q == 0 and self._stock_for(s, p, k) == 0:
            return "tutup"
        return {"produk": k, "jumlah": q, "harga": price, "iklan": ads}

    def _stock_for(self, s, p, k):
        st = s["stok"][p]
        return st["jumlah"] if st and st["hari"] == s["hari"] and st["produk"] == k else 0

    def default(self, s, p):
        return "tutup"

    def apply(self, s, actions):
        names = s["names"]
        d = s["hari"]
        day = s["plan"][d - 1]
        hasil: dict[str, Any] = {names[p]: "tutup" for p in actions}
        pembeli: dict[str, int] = {}
        penjual: dict[str, int] = {}
        stok_baru: list[Any] = [None] * len(names)
        for k, info in PRODUK.items():
            sellers = [p for p, a in actions.items() if a != "tutup" and a["produk"] == k]
            if not sellers:
                continue
            penjual[k] = len(sellers)
            carried = {p: self._stock_for(s, p, k) for p in sellers}
            avail = {p: actions[p]["jumlah"] + carried[p] for p in sellers}
            demand = info["permintaan"] * self._scale(s) * self._mult(s, d, k) * day["gejolak"][k]
            market = 2 * demand
            w = {p: _weight(actions[p]["harga"], actions[p]["iklan"], info["wajar"]) for p in sellers}
            total_w = sum(w.values())
            cust = {p: int(market * w[p] / (1 + total_w)) for p in sellers}
            sold = {p: min(avail[p], cust[p]) for p in sellers}
            spill = sum(cust[p] - sold[p] for p in sellers) // 2
            rest = [p for p in sellers if sold[p] < avail[p] and w[p] > 0]
            if spill > 0 and rest:
                wr = sum(w[p] for p in rest)
                for p in rest:
                    sold[p] = min(avail[p], sold[p] + int(spill * w[p] / wr))
            pembeli[k] = sum(cust.values())
            modal = self._modal(s, d, k)
            for p in sellers:
                a = actions[p]
                cost = a["jumlah"] * modal + a["iklan"]
                rev = sold[p] * a["harga"]
                s["uang"][p] += rev - cost
                s["terjual"][p] += sold[p]
                fresh_left = a["jumlah"] - max(0, sold[p] - carried[p])     # stok kemarin dijual lebih dulu
                entry_p = {**a, "terjual": sold[p], "untung": rev - cost}
                if carried[p]:
                    entry_p["stok"] = carried[p]
                if s["cfg"].get("stok_awet") and fresh_left > 0:
                    stok_baru[p] = {"produk": k, "jumlah": fresh_left, "hari": d + 1}
                    entry_p["disimpan"] = fresh_left
                hasil[names[p]] = entry_p
        s["stok"] = stok_baru
        entry = {"hari": d, "nama_hari": NAMA_HARI[(d - 1) % 7], "cuaca": day["cuaca"], "acara": day["acara"],
                 "kejadian": day.get("kejadian"), "gejolak": day["gejolak"], "pembeli": pembeli, "penjual": penjual,
                 "jual": hasil, "uang": dict(zip(names, s["uang"]))}
        s["riwayat"].append(entry)
        s["hari"] += 1
        return [{"jenis": "hari", **entry}]

    def over(self, s):
        return s["hari"] > s["cfg"]["hari"]

    def scores(self, s):
        return [float(u) for u in s["uang"]]

    def tiebreak(self, s):
        return [float(x) for x in s["terjual"]]

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        names = s["names"]
        d = min(s["hari"], s["cfg"]["hari"])

        def _k(produk):
            k = str(produk).strip().lower().replace(" ", "_")
            if k not in PRODUK:
                raise ActionError(f"produk harus salah satu dari: {', '.join(PRODUK)}")
            return k

        def maks_beli(produk, iklan=0):
            k = _k(produk)
            if self._kej(s, d, k, "razia"):
                return 0
            return max(0, (s["uang"][p] - max(0, as_int(iklan, "iklan"))) // max(1, self._modal(s, d, k)))

        rahasia = bool(s["cfg"].get("pesaing_rahasia"))

        def jumlah_penjual_kemarin(produk):
            k = _k(produk)
            if not s["riwayat"]:
                return 0
            last = s["riwayat"][-1]
            return last.get("penjual", {}).get(k, 0) - (1 if isinstance(last["jual"].get(names[p]), dict)
                                                         and last["jual"][names[p]].get("produk") == k else 0)

        def pesaing_kemarin(produk):
            k = _k(produk)
            if not s["riwayat"] or rahasia:
                return []
            out = []
            for nm, a in s["riwayat"][-1]["jual"].items():
                if nm != names[p] and isinstance(a, dict) and a["produk"] == k:
                    out.append({"nama": nm, "harga": a["harga"], "iklan": a["iklan"], "jumlah": a["jumlah"], "terjual": a["terjual"]})
            return out

        def perkiraan_pembeli(produk, harga, iklan=0):
            k = _k(produk)
            info = PRODUK[k]
            if self._kej(s, d, k, "razia"):
                return 0
            market = 2 * info["permintaan"] * self._scale(s) * self._mult(s, d, k)
            mine = _weight(as_int(harga, "harga"), max(0, as_int(iklan, "iklan")), info["wajar"])
            if rahasia:   # harga pesaing tidak terlihat: anggap mereka menjual seharga wajar tanpa iklan (daya tarik 1)
                others = float(jumlah_penjual_kemarin(k))
            else:
                others = sum(_weight(x["harga"], x["iklan"], info["wajar"]) for x in pesaing_kemarin(k))
            return int(market * mine / (1 + mine + others))

        def untung_per_barang(produk, harga):
            k = _k(produk)
            return as_int(harga, "harga") - self._modal(s, d, k)

        return {"uang_saya": lambda: s["uang"][p], "maks_beli": maks_beli, "perkiraan_pembeli": perkiraan_pembeli,
                "pesaing_kemarin": pesaing_kemarin, "untung_per_barang": untung_per_barang,
                "jumlah_penjual_kemarin": jumlah_penjual_kemarin}
