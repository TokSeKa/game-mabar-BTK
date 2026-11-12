"""Juragan Nusantara: permainan papan jual-beli kota bergaya Monopoli, dengan lelang tertutup dan tukar-menukar antarpemain.

Papan 40 petak berisi kota-kota Indonesia, transportasi, utilitas, pajak, kartu Kesempatan & Dana Umum. Dadu dan urutan kartu
diacak dari seed match (bot tidak punya keacakan). Uang ditulis dalam juta (jt)."""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

# (nama, jenis, harga, kelompok)  jenis: mulai, kota, transport, utilitas, pajak, kesempatan, dana, penjara, parkir, ke_penjara
PAPAN: list[tuple[str, str, int, str | None]] = [
    ("Mulai", "mulai", 0, None), ("Pacitan", "kota", 60, "coklat"), ("Dana Umum", "dana", 0, None), ("Wonosobo", "kota", 60, "coklat"),
    ("Pajak Penghasilan", "pajak", 200, None), ("Stasiun Gambir", "transport", 200, "transport"), ("Kupang", "kota", 100, "biru_muda"),
    ("Kesempatan", "kesempatan", 0, None), ("Ternate", "kota", 100, "biru_muda"), ("Ambon", "kota", 120, "biru_muda"),
    ("Penjara", "penjara", 0, None), ("Palu", "kota", 140, "merah_muda"), ("PLN", "utilitas", 150, "utilitas"),
    ("Kendari", "kota", 140, "merah_muda"), ("Mataram", "kota", 160, "merah_muda"), ("Pelabuhan Tanjung Perak", "transport", 200, "transport"),
    ("Pontianak", "kota", 180, "oranye"), ("Dana Umum", "dana", 0, None), ("Banjarmasin", "kota", 180, "oranye"),
    ("Samarinda", "kota", 200, "oranye"), ("Parkir Bebas", "parkir", 0, None), ("Padang", "kota", 220, "merah"),
    ("Kesempatan", "kesempatan", 0, None), ("Pekanbaru", "kota", 220, "merah"), ("Palembang", "kota", 240, "merah"),
    ("Bandara Ngurah Rai", "transport", 200, "transport"), ("Manado", "kota", 260, "kuning"), ("Makassar", "kota", 260, "kuning"),
    ("PDAM", "utilitas", 150, "utilitas"), ("Denpasar", "kota", 280, "kuning"), ("Masuk Penjara", "ke_penjara", 0, None),
    ("Semarang", "kota", 300, "hijau"), ("Yogyakarta", "kota", 300, "hijau"), ("Dana Umum", "dana", 0, None),
    ("Bandung", "kota", 320, "hijau"), ("Bandara Soekarno-Hatta", "transport", 200, "transport"), ("Kesempatan", "kesempatan", 0, None),
    ("Surabaya", "kota", 350, "biru_tua"), ("Pajak Barang Mewah", "pajak", 100, None), ("Jakarta", "kota", 400, "biru_tua"),
]
KELOMPOK = {k: [i for i, p in enumerate(PAPAN) if p[3] == k] for k in
            ("coklat", "biru_muda", "merah_muda", "oranye", "merah", "kuning", "hijau", "biru_tua", "transport", "utilitas")}
HARGA_RUMAH = {"coklat": 50, "biru_muda": 50, "merah_muda": 100, "oranye": 100, "merah": 150, "kuning": 150, "hijau": 200, "biru_tua": 200}
KALI_SEWA = [1, 5, 14, 38, 50, 62]          # 0-4 rumah, 5 = hotel (dikali sewa dasar)
PENJARA, KE_PENJARA = 10, 30
DENDA_PENJARA = 50

KESEMPATAN = [
    ("Mudik lebaran! Maju ke Mulai, terima 200.", "maju", 0), ("Liburan ke Denpasar.", "maju", 29), ("Rapat di Jakarta.", "maju", 39),
    ("Naik kereta: maju ke transportasi terdekat, bayar 2× sewa kalau sudah ada pemiliknya.", "transport", 2),
    ("Kena tilang! Bayar 15.", "bayar", 15), ("Dividen saham: terima 50.", "terima", 50), ("Kartu Bebas Penjara (simpan).", "bebas", 0),
    ("Salah belok: mundur 3 petak.", "mundur", 3), ("Ketahuan main judi online: masuk penjara.", "penjara", 0),
    ("Renovasi rumah: bayar 25 per rumah, 100 per hotel.", "renovasi", 25),
    ("Terpilih jadi ketua RT: bayar 50 ke setiap pemain.", "bayar_semua", 50), ("Investasi berhasil: terima 150.", "terima", 150),
    ("Kuliah ke Yogyakarta.", "maju", 32), ("Tagihan listrik: maju ke utilitas terdekat, bayar 10× dadu kalau sudah ada pemiliknya.", "utilitas", 10),
    ("Ikut pameran di Pontianak.", "maju", 16), ("Menang lomba makan kerupuk: terima 100.", "terima", 100),
]
DANA_UMUM = [
    ("Pulang kampung: maju ke Mulai, terima 200.", "maju", 0), ("Salah transfer bank menguntungkanmu: terima 200.", "terima", 200),
    ("Bayar dokter gigi: 50.", "bayar", 50), ("Jual barang bekas di pasar loak: terima 50.", "terima", 50),
    ("Kartu Bebas Penjara (simpan).", "bebas", 0), ("Lupa bayar pajak: masuk penjara.", "penjara", 0),
    ("Arisan keluarga: terima 10 dari setiap pemain.", "terima_semua", 10), ("Bonus akhir tahun: terima 100.", "terima", 100),
    ("Pengembalian pajak: terima 20.", "terima", 20), ("Ulang tahunmu: terima 10 dari setiap pemain.", "terima_semua", 10),
    ("Asuransi jatuh tempo: terima 100.", "terima", 100), ("Bayar rumah sakit: 100.", "bayar", 100), ("Bayar uang sekolah: 50.", "bayar", 50),
    ("Jasa konsultan: terima 25.", "terima", 25), ("Perbaikan jalan kampung: bayar 40 per rumah, 115 per hotel.", "renovasi", 40),
    ("Juara lomba 17-an: terima 10.", "terima", 10),
]


def sewa_dasar(harga: int) -> int:
    return max(2, round(harga * 0.08))


class JuraganNusantara(Game):
    id = "monopoli"
    nama = "Juragan Nusantara (gaya Monopoli)"
    ringkas = "Kelilingi papan kota-kota Indonesia: beli, bangun rumah & hotel, tagih sewa, lelang, dan tukar properti dengan pemain lain."
    kategori = "giliran"
    min_pemain, max_pemain = 2, 6
    hint_aksi = "'lempar', 'beli', 'tolak', 'selesai', {'bangun': petak}, {'lelang': harga}, {'tawar': {...}}, 'terima', ..."
    timer = 25
    label_skor = "Kekayaan"
    max_frames = 1200
    settings = [
        Setting("uang_awal", "Uang awal (jt)", "int", 1500, 500, 5000),
        Setting("batas_putaran", "Batas putaran", "int", 25, 5, 100,
                ket="Kalau belum ada pemenang setelah sekian putaran, pemain dengan kekayaan bersih terbesar menang."),
        Setting("gaji", "Gaji lewat Mulai (jt)", "int", 200, 0, 500),
        Setting("lelang_properti", "Lelang kalau tidak dibeli", "bool", True, grup="aturan",
                ket="Petak yang tidak dibeli dilelang tertutup ke semua pemain (penawaran rahasia, tertinggi menang)."),
        Setting("tukar", "Boleh tukar-menukar", "bool", True, grup="aturan",
                ket="Di gilirannya, pemain boleh menawarkan tukar properti/uang ke pemain lain (maks 3 tawaran per giliran)."),
        Setting("parkir_jackpot", "Jackpot Parkir Bebas", "bool", False, grup="aturan",
                ket="Semua pajak & denda dikumpulkan di Parkir Bebas dan diambil pemain yang berhenti di sana."),
        Setting("uang_rahasia", "Uang lawan rahasia", "bool", False, grup="informasi",
                ket="Uang tunai pemain lain tidak terlihat (properti tetap terlihat)."),
    ]
    presets = [
        {"id": "cepat", "nama": "Cepat", "ket": "Uang awal 1000, batas 12 putaran, jackpot parkir.",
         "nilai": {"parkir_jackpot": True}},
        {"id": "kabut", "nama": "Dompet Rahasia", "ket": "Uang tunai lawan dirahasiakan.", "nilai": {"uang_rahasia": True}},
    ]
    aturan = """
- Semua pemain mulai di **Mulai** dengan **1.500 jt**. Di giliranmu **lempar dua dadu** lalu maju. Lewat Mulai = gaji **200**.
  Dadu kembar = lempar lagi (tiga kali kembar berturut-turut = masuk penjara).
- Berhenti di **kota / transportasi / utilitas** tanpa pemilik: **beli** atau **tolak** (yang ditolak dilelang tertutup ke semua pemain;
  tawaran tertinggi menang, seri dimenangkan pemain yang lebih dekat urutannya).
- Berhenti di petak milik orang lain: bayar **sewa**. Kota: sewa dasar = 8% harga (×2 kalau pemiliknya memiliki **satu kelompok
  warna lengkap** tanpa rumah), lalu naik besar dengan **rumah** (1–4) dan **hotel**. Transportasi: 25 / 50 / 100 / 200 tergantung
  jumlah yang dimiliki. Utilitas: 4× dadu (10× kalau punya keduanya). Petak yang digadai tidak menarik sewa.
- **Bangun** rumah kalau punya satu kelompok warna lengkap (tanpa gadai), merata (selisih rumah antar petak maksimal 1). Rumah ke-5 = hotel.
  **Gadai** properti = dapat 50% harga; **tebus** = bayar 55%.
- **Kesempatan / Dana Umum**: kartu kejutan (maju, bayar, terima, masuk penjara, kartu bebas penjara, ...).
- **Penjara**: keluar dengan bayar 50, kartu bebas, atau dadu kembar (maksimal 3 giliran, lalu wajib bayar).
- **Tukar-menukar**: di gilirannya pemain boleh menawarkan properti/uang ke pemain lain; pemain itu menerima atau menolak.
- Tidak bisa bayar: rumah dijual (setengah harga) dan properti digadai otomatis; kalau masih kurang = **bangkrut** (semua harta ke
  penagih). Pemain terakhir yang bertahan menang, atau kekayaan bersih terbesar setelah batas putaran (default 25).
"""
    format_aksi = """- `"lempar"` (fase awal), `"beli"` / `"tolak"` (fase beli), `"selesai"` (akhiri giliran, fase akhir).
- Kapan saja di gilirannya (fase awal/akhir): `{"bangun": petak}`, `{"jual_rumah": petak}`, `{"gadai": petak}`, `{"tebus": petak}`,
  `"bayar_penjara"`, `"kartu_bebas"`, dan tawaran tukar:
  `{"tawar": {"ke": "Budi", "beri": {"uang": 100, "properti": [6]}, "minta": {"uang": 0, "properti": [8]}}}`.
- Fase lelang (semua pemain): `{"lelang": harga}` (0 = tidak ikut). Fase tawaran (pemain yang ditawari): `"terima"` atau `"tolak"`."""
    format_info = """```
{ "putaran": 3, "batas_putaran": 25, "giliran": "Budi", "fase": "awal",   # awal / beli / akhir / lelang / tawaran
  "dadu": [3, 4], "kembar": 0,
  "papan": [ {"id": 1, "nama": "Pacitan", "jenis": "kota", "harga": 60, "kelompok": "coklat", "pemilik": "Ani",
              "rumah": 0, "gadai": False, "sewa": 10, "harga_rumah": 50}, ... ],     # 40 petak
  "pemain": {"Ani": {"uang": 1340, "posisi": 6, "penjara": False, "giliran_penjara": 0, "kartu_bebas": 0,
                     "bangkrut": False, "kekayaan": 1560}, ...},      # uang None kalau dirahasiakan
  "lelang": {"petak": 8, "harga": 100} | None, "tawaran": {"dari": "Ani", "ke": "Budi", "beri": {...}, "minta": {...}} | None,
  "jackpot": 0, "kartu_terakhir": "Dividen saham: terima 50.", "riwayat": [...],
  "bisa_bangun": [16, 18], "boleh_tawar": True }
```"""
    lib_docs = [
        {"nama": "petak", "jenis": "fungsi", "tanda": "petak(id)", "ket": "Info satu petak (sama dengan info()['papan'][id])."},
        {"nama": "milik", "jenis": "fungsi", "tanda": "milik(nama=None)", "ket": "Daftar id properti milik pemain itu (default: kamu)."},
        {"nama": "kelompok", "jenis": "fungsi", "tanda": "kelompok(warna)", "ket": "Daftar id petak dalam kelompok itu (coklat, biru_muda, ..., transport, utilitas)."},
        {"nama": "lengkap", "jenis": "fungsi", "tanda": "lengkap(warna, nama=None)", "ket": "True kalau pemain itu memiliki semua petak di kelompok itu."},
        {"nama": "bisa_bangun", "jenis": "fungsi", "tanda": "bisa_bangun()", "ket": "Daftar petak yang boleh kamu bangun rumah sekarang (aturan merata, uang cukup)."},
        {"nama": "kekayaan", "jenis": "fungsi", "tanda": "kekayaan(nama=None)", "ket": "Kekayaan bersih pemain itu (uang + properti + rumah; None kalau uangnya rahasia)."},
        {"nama": "uang", "jenis": "fungsi", "tanda": "uang(nama=None)", "ket": "Uang tunai pemain itu (None kalau dirahasiakan)."},
    ]
    templates = [
        {"id": "pembeli", "nama": "Pembeli Rajin", "ket": "Membeli hampir semua properti, membangun kalau ada sisa 250, menawar lelang sampai 80% harga.", "kode": '''def aksi():
    i = info()
    saya = nama_saya()
    me = i["pemain"][saya]
    f = i["fase"]
    if f == "tawaran":
        t = i["tawaran"]
        nilai_dapat = t["beri"]["uang"] + sum(petak(p)["harga"] for p in t["beri"]["properti"])
        nilai_beri = t["minta"]["uang"] + sum(petak(p)["harga"] for p in t["minta"]["properti"])
        return "terima" if nilai_dapat >= nilai_beri * 1.2 else "tolak"
    if f == "lelang":
        h = petak(i["lelang"]["petak"])["harga"]
        return {"lelang": min(me["uang"] - 50, int(h * 0.8))} if me["uang"] > 150 else {"lelang": 0}
    if f == "beli":
        p = petak(me["posisi"])
        return "beli" if me["uang"] - p["harga"] >= 80 else "tolak"
    b = bisa_bangun()
    if b and me["uang"] > 250:
        return {"bangun": b[0]}
    if me["penjara"] and me["uang"] > 300 and f == "awal":
        return "bayar_penjara"
    return "lempar" if f == "awal" else "selesai"
'''},
        {"id": "hati_hati", "nama": "Investor Hati-hati", "ket": "Hanya membeli kalau tetap punya cadangan 300, fokus kelompok oranye & merah, membangun sampai 3 rumah.", "kode": '''def aksi():
    i = info()
    me = i["pemain"][nama_saya()]
    f = i["fase"]
    if f == "tawaran":
        return "tolak"
    if f == "lelang":
        p = petak(i["lelang"]["petak"])
        suka = p["kelompok"] in ["oranye", "merah"]
        batas = int(p["harga"] * (0.9 if suka else 0.5))
        return {"lelang": max(0, min(batas, me["uang"] - 300))}
    if f == "beli":
        p = petak(me["posisi"])
        cadangan = 200 if p["kelompok"] in ["oranye", "merah"] else 300
        return "beli" if me["uang"] - p["harga"] >= cadangan else "tolak"
    for b in bisa_bangun():
        if petak(b)["rumah"] < 3 and me["uang"] - petak(b)["harga_rumah"] >= 300:
            return {"bangun": b}
    return "lempar" if f == "awal" else "selesai"
'''},
        {"id": "pedagang", "nama": "Pedagang", "ket": "Menawar properti terakhir yang melengkapi kelompoknya (1,5× harga), dan menerima tawaran yang lebih menguntungkan.", "kode": '''def aksi():
    i = info()
    saya = nama_saya()
    me = i["pemain"][saya]
    f = i["fase"]
    if f == "tawaran":
        t = i["tawaran"]
        dapat = t["beri"]["uang"] + sum(petak(p)["harga"] * 1.3 for p in t["beri"]["properti"])
        beri = t["minta"]["uang"] + sum(petak(p)["harga"] * 1.3 for p in t["minta"]["properti"])
        for p in t["minta"]["properti"]:
            if lengkap(petak(p)["kelompok"], saya):
                return "tolak"
        return "terima" if dapat > beri else "tolak"
    if f == "lelang":
        h = petak(i["lelang"]["petak"])["harga"]
        return {"lelang": min(h, max(0, me["uang"] - 200))}
    if f == "beli":
        return "beli" if me["uang"] - petak(me["posisi"])["harga"] >= 50 else "tolak"
    if i["boleh_tawar"]:
        for w in ["coklat", "biru_muda", "merah_muda", "oranye", "merah", "kuning", "hijau", "biru_tua"]:
            ids = kelompok(w)
            mine = [x for x in ids if petak(x)["pemilik"] == saya]
            if len(mine) == len(ids) - 1:
                sisa = [x for x in ids if petak(x)["pemilik"] != saya][0]
                p = petak(sisa)
                if p["pemilik"] != None and p["rumah"] == 0 and me["uang"] > p["harga"] * 2:
                    return {"tawar": {"ke": p["pemilik"], "beri": {"uang": int(p["harga"] * 1.5), "properti": []},
                                      "minta": {"uang": 0, "properti": [sisa]}}}
    b = bisa_bangun()
    if b and me["uang"] > 200:
        return {"bangun": b[0]}
    return "lempar" if f == "awal" else "selesai"
'''},
        {"id": "raja_transport", "nama": "Raja Transportasi", "ket": "Mengincar transportasi, utilitas, dan kota murah; menolak semua tawaran tukar.", "kode": '''def aksi():
    i = info()
    me = i["pemain"][nama_saya()]
    f = i["fase"]
    if f == "tawaran":
        return "tolak"
    if f == "lelang":
        p = petak(i["lelang"]["petak"])
        suka = p["jenis"] in ["transport", "utilitas"]
        return {"lelang": max(0, min(p["harga"] if suka else p["harga"] // 3, me["uang"] - 100))}
    if f == "beli":
        p = petak(me["posisi"])
        if p["jenis"] in ["transport", "utilitas"] or p["harga"] <= 160:
            return "beli" if me["uang"] >= p["harga"] + 20 else "tolak"
        return "beli" if me["uang"] - p["harga"] >= 400 else "tolak"
    b = bisa_bangun()
    if b and me["uang"] > 350:
        return {"bangun": b[0]}
    return "lempar" if f == "awal" else "selesai"
'''},
    ]

    # ------------------------------------------------------------ dasar
    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "uang": [cfg["uang_awal"]] * n, "posisi": [0] * n,
             "bangkrut": [False] * n, "urut_bangkrut": [], "penjara": [False] * n, "giliran_penjara": [0] * n,
             "kartu_bebas": [0] * n, "milik": {}, "rumah": {}, "gadai": {}, "giliran": 0, "fase": "awal", "dadu": None,
             "kembar": 0, "putaran": 1, "lempar_no": 0, "tawar_count": 0, "lelang": None, "tawaran": None, "jackpot": 0,
             "kartu_terakhir": None, "riwayat": [], "langkah_no": 0}
        g = rng(s, "kartu")
        ks, du = list(range(len(KESEMPATAN))), list(range(len(DANA_UMUM)))
        g.shuffle(ks)
        g.shuffle(du)
        s["dek"] = {"kesempatan": ks, "dana": du, "ik": 0, "id": 0}
        return s

    def _alive(self, s):
        return [p for p in range(len(s["names"])) if not s["bangkrut"][p]]

    def _owner(self, s, i):
        return s["milik"].get(str(i))

    def _houses(self, s, i):
        return s["rumah"].get(str(i), 0)

    def _mortgaged(self, s, i):
        return s["gadai"].get(str(i), False)

    def _owns_group(self, s, p, grp):
        return all(self._owner(s, i) == p for i in KELOMPOK[grp])

    def _rent(self, s, i, dice=7):
        nama, jenis, harga, grp = PAPAN[i]
        o = self._owner(s, i)
        if o is None or self._mortgaged(s, i):
            return 0
        if jenis == "kota":
            h = self._houses(s, i)
            base = sewa_dasar(harga)
            if h == 0:
                return base * (2 if self._owns_group(s, o, grp) else 1)
            return base * KALI_SEWA[h]
        if jenis == "transport":
            k = sum(1 for j in KELOMPOK["transport"] if self._owner(s, j) == o)
            return 25 * 2 ** (k - 1)
        if jenis == "utilitas":
            k = sum(1 for j in KELOMPOK["utilitas"] if self._owner(s, j) == o)
            return dice * (10 if k == 2 else 4)
        return 0

    def _worth(self, s, p):
        w = s["uang"][p]
        for k, o in s["milik"].items():
            if o != p:
                continue
            i = int(k)
            w += PAPAN[i][2] // 2 if self._mortgaged(s, i) else PAPAN[i][2]
            if PAPAN[i][3] in HARGA_RUMAH:
                w += self._houses(s, i) * HARGA_RUMAH[PAPAN[i][3]]
        return w

    # ------------------------------------------------------------ tampilan
    def _square_view(self, s, i):
        nama, jenis, harga, grp = PAPAN[i]
        o = self._owner(s, i)
        return {"id": i, "nama": nama, "jenis": jenis, "harga": harga, "kelompok": grp,
                "pemilik": s["names"][o] if o is not None else None, "rumah": self._houses(s, i), "gadai": self._mortgaged(s, i),
                "sewa": self._rent(s, i) if jenis != "utilitas" else None, "sewa_dasar": sewa_dasar(harga) if jenis == "kota" else None,
                "harga_rumah": HARGA_RUMAH.get(grp or "", None)}

    def _view(self, s, viewer):
        c, names = s["cfg"], s["names"]
        hide = c["uang_rahasia"] and viewer != "semua"
        pemain = {}
        for p, nm in enumerate(names):
            see = not hide or viewer == p
            pemain[nm] = {"uang": s["uang"][p] if see else None, "posisi": s["posisi"][p], "penjara": s["penjara"][p],
                          "giliran_penjara": s["giliran_penjara"][p], "kartu_bebas": s["kartu_bebas"][p],
                          "bangkrut": s["bangkrut"][p], "kekayaan": self._worth(s, p) if see else None}
        lel = s["lelang"]
        v = {"putaran": min(s["putaran"], c["batas_putaran"]), "batas_putaran": c["batas_putaran"],
             "giliran": names[s["giliran"]] if not self.over(s) else None, "fase": s["fase"],
             "dadu": list(s["dadu"]) if s["dadu"] else None, "kembar": s["kembar"],
             "papan": [self._square_view(s, i) for i in range(len(PAPAN))], "pemain": pemain,
             "lelang": {"petak": lel["petak"], "harga": PAPAN[lel["petak"]][2],
                        "sudah": [names[q] for q in sorted(lel["tawaran"])]} if lel else None,
             "tawaran": dict(s["tawaran"]) if s["tawaran"] else None, "jackpot": s["jackpot"],
             "kartu_terakhir": s["kartu_terakhir"], "gaji": c["gaji"],
             "boleh_tawar": c["tukar"] and s["tawar_count"] < 3 and s["fase"] in ("awal", "akhir"),
             "riwayat": [dict(e) for e in s["riwayat"][-12:]]}
        if viewer == "semua" and lel:
            v["lelang"]["tawaran"] = {names[q]: x for q, x in lel["tawaran"].items()}
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        mine = s["giliran"] == p and s["fase"] in ("awal", "akhir") and not self.over(s)
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p],
                "bisa_bangun": sorted(self._buildable(s, p)) if mine else []}

    def event_for(self, s, e, viewer):
        if viewer == "semua" or not s["cfg"]["uang_rahasia"] or e.get("jenis") != "lelang_hasil":
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return {**e, "tawaran": {k: (v if k == me else None) for k, v in e.get("tawaran", {}).items()}}

    # ------------------------------------------------------------ alur
    def pending(self, s):
        if self.over(s):
            return []
        if s["fase"] == "lelang":
            return [p for p in self._alive(s) if p not in s["lelang"]["tawaran"]]
        if s["fase"] == "tawaran":
            return [s["names"].index(s["tawaran"]["ke"])]
        return [s["giliran"]]

    def _turn_actions(self, s, p, a):
        """Aksi yang boleh kapan saja di gilirannya (fase awal/akhir). Mengembalikan aksi rapi atau None."""
        if not isinstance(a, dict):
            return None
        names = s["names"]
        if s.get("aksi_giliran", 0) >= 40:
            raise ActionError("terlalu banyak aksi di giliran ini: lempar dadu atau selesaikan giliran")
        if "bangun" in a or "jual_rumah" in a or "gadai" in a or "tebus" in a:
            kind = next(k for k in ("bangun", "jual_rumah", "gadai", "tebus") if k in a)
            i = as_int(a[kind], "petak")
            if not 0 <= i < len(PAPAN) or self._owner(s, i) != p:
                raise ActionError("itu bukan propertimu")
            grp = PAPAN[i][3]
            if kind == "bangun":
                if i not in self._buildable(s, p):
                    raise ActionError("belum bisa membangun di situ (kelompok harus lengkap, tanpa gadai, merata, dan uang cukup)")
            elif kind == "jual_rumah":
                if self._houses(s, i) == 0 or self._houses(s, i) < max(self._houses(s, j) for j in KELOMPOK[grp]):
                    raise ActionError("jual rumah merata: mulai dari petak dengan rumah terbanyak")
            elif kind == "gadai":
                if self._mortgaged(s, i) or any(self._houses(s, j) for j in KELOMPOK[grp]):
                    raise ActionError("tidak bisa digadai (sudah digadai, atau kelompoknya masih punya rumah)")
            else:
                if not self._mortgaged(s, i):
                    raise ActionError("properti itu tidak sedang digadai")
                if s["uang"][p] < PAPAN[i][2] * 55 // 100:
                    raise ActionError("uang tidak cukup untuk menebus")
            return {kind: i}
        if "tawar" in a:
            if not s["cfg"]["tukar"]:
                raise ActionError("tukar-menukar dimatikan host")
            if s["tawar_count"] >= 3:
                raise ActionError("maksimal 3 tawaran per giliran")
            t = a["tawar"]
            if not isinstance(t, dict) or t.get("ke") not in names or t.get("ke") == names[p]:
                raise ActionError("tawar: 'ke' harus nama pemain lain")
            q = names.index(t["ke"])
            if s["bangkrut"][q]:
                raise ActionError("pemain itu sudah bangkrut")

            def part(x, who):
                x = x or {}
                if not isinstance(x, dict):
                    raise ActionError("beri/minta harus dict {'uang', 'properti'}")
                u = max(0, as_int(x.get("uang", 0), "uang"))
                props = sorted({as_int(v, "properti") for v in (x.get("properti") or [])})
                for i in props:
                    if not 0 <= i < len(PAPAN) or self._owner(s, i) != who:
                        raise ActionError(f"petak {i} bukan milik {names[who]}")
                    if any(self._houses(s, j) for j in KELOMPOK[PAPAN[i][3]]):
                        raise ActionError(f"{PAPAN[i][0]}: jual dulu rumah di kelompoknya sebelum ditukar")
                return {"uang": u, "properti": props}

            beri, minta = part(t.get("beri"), p), part(t.get("minta"), q)
            if beri["uang"] > s["uang"][p]:
                raise ActionError("uangmu tidak cukup untuk tawaran itu")
            if not (beri["uang"] or beri["properti"] or minta["uang"] or minta["properti"]):
                raise ActionError("tawaran kosong")
            return {"tawar": {"ke": t["ke"], "beri": beri, "minta": minta}}
        return None

    def validate(self, s, p, a):
        f = s["fase"]
        if f == "lelang":
            if isinstance(a, dict) and "lelang" in a:
                x = max(0, as_int(a["lelang"], "harga"))
            elif a is None or a in ("tolak", "lewat", 0):
                x = 0
            else:
                x = max(0, as_int(a, "harga"))
            if x > s["uang"][p]:
                raise ActionError("tawaran lelang melebihi uangmu")
            return {"lelang": x}
        if f == "tawaran":
            if a in ("terima", True):
                t = s["tawaran"]
                if t["minta"]["uang"] > s["uang"][p]:
                    raise ActionError("uangmu tidak cukup untuk menerima tawaran ini")
                return "terima"
            if a in ("tolak", None, False):
                return "tolak"
            raise ActionError("jawab 'terima' atau 'tolak'")
        if f == "beli":
            if a == "beli":
                if s["uang"][p] < PAPAN[s["posisi"][p]][2]:
                    raise ActionError("uangmu tidak cukup")
                return "beli"
            if a in ("tolak", None):
                return "tolak"
            raise ActionError("pilih 'beli' atau 'tolak'")
        t = self._turn_actions(s, p, a)
        if t is not None:
            return t
        if f == "awal":
            if a in ("lempar", None, "selesai"):
                return "lempar"
            if a == "bayar_penjara":
                if not s["penjara"][p] or s["uang"][p] < DENDA_PENJARA:
                    raise ActionError("tidak sedang di penjara atau uang tidak cukup")
                return a
            if a == "kartu_bebas":
                if not s["penjara"][p] or s["kartu_bebas"][p] <= 0:
                    raise ActionError("tidak sedang di penjara atau tidak punya kartu bebas")
                return a
            raise ActionError("fase awal: 'lempar', bangun/gadai/tebus/tawar, 'bayar_penjara', atau 'kartu_bebas'")
        if f == "akhir":
            if a in ("selesai", None, "lempar"):
                return "selesai"
            raise ActionError("fase akhir: 'selesai', atau bangun/gadai/tebus/tawar")
        raise ActionError("aksi tidak dikenal")

    def default(self, s, p):
        f = s["fase"]
        if f == "lelang":
            return {"lelang": 0}
        if f == "tawaran":
            return "tolak"
        if f == "beli":
            harga = PAPAN[s["posisi"][p]][2]
            return "beli" if s["uang"][p] >= 2 * harga + 100 else "tolak"
        if f == "awal" and s["penjara"][p] and s["giliran_penjara"][p] >= 2 and s["uang"][p] >= DENDA_PENJARA:
            return "bayar_penjara"
        return "lempar" if f == "awal" else "selesai"

    # ------------------------------------------------------------ uang
    def _gain(self, s, p, x):
        s["uang"][p] += x

    def _pay(self, s, p, x, to, events, why=""):
        """Bayar x dari p ke ``to`` (pemain atau None = bank/jackpot). Jual rumah & gadai otomatis kalau kurang;
        kalau tetap kurang, p bangkrut dan hartanya pindah ke penagih."""
        if x <= 0:
            return
        if s["uang"][p] < x:
            self._liquidate(s, p, x, events)
        if s["uang"][p] >= x:
            s["uang"][p] -= x
            if to is not None:
                s["uang"][to] += x
            elif s["cfg"]["parkir_jackpot"] and why in ("pajak", "denda", "kartu"):
                s["jackpot"] += x
            return
        self._bankrupt(s, p, to, events)

    def _liquidate(self, s, p, need, events):
        names = s["names"]
        sold = 0
        while s["uang"][p] < need:
            houses = [int(k) for k, o in s["milik"].items() if o == p and self._houses(s, int(k)) > 0]
            if not houses:
                break
            i = max(houses, key=lambda j: (self._houses(s, j), HARGA_RUMAH[PAPAN[j][3]], j))
            s["rumah"][str(i)] -= 1
            s["uang"][p] += HARGA_RUMAH[PAPAN[i][3]] // 2
            sold += 1
        gadai = []
        while s["uang"][p] < need:
            props = [int(k) for k, o in s["milik"].items() if o == p and not self._mortgaged(s, int(k))]
            if not props:
                break
            i = min(props, key=lambda j: (PAPAN[j][2], j))
            s["gadai"][str(i)] = True
            s["uang"][p] += PAPAN[i][2] // 2
            gadai.append(PAPAN[i][0])
        if sold or gadai:
            events.append({"jenis": "likuidasi", "pemain": names[p], "rumah_dijual": sold, "digadai": gadai})

    def _bankrupt(self, s, p, to, events):
        names = s["names"]
        cash = s["uang"][p]
        s["uang"][p] = 0
        if to is not None:
            s["uang"][to] += cash
            s["kartu_bebas"][to] += s["kartu_bebas"][p]
        for k, o in list(s["milik"].items()):
            if o != p:
                continue
            s["rumah"].pop(k, None)
            if to is None:
                s["milik"].pop(k)
                s["gadai"].pop(k, None)
            else:
                s["milik"][k] = to
        s["kartu_bebas"][p] = 0
        s["bangkrut"][p] = True
        s["penjara"][p] = False
        s["urut_bangkrut"].append(p)
        events.append({"jenis": "bangkrut", "pemain": names[p], "ke": names[to] if to is not None else None})

    # ------------------------------------------------------------ bangun
    def _buildable(self, s, p):
        out = []
        for grp, cost in HARGA_RUMAH.items():
            ids = KELOMPOK[grp]
            if not self._owns_group(s, p, grp) or any(self._mortgaged(s, i) for i in ids) or s["uang"][p] < cost:
                continue
            low = min(self._houses(s, i) for i in ids)
            out += [i for i in ids if self._houses(s, i) == low and low < 5]
        return out

    # ------------------------------------------------------------ apply
    def apply(self, s, actions):
        events: list[dict[str, Any]] = []
        names = s["names"]
        s["langkah_no"] += 1
        if s["fase"] == "lelang":
            for q, a in actions.items():
                s["lelang"]["tawaran"][q] = a["lelang"]
            if not self.pending(s):
                self._close_auction(s, events)
            self._log(s, events)
            return events
        (p, a), = actions.items()
        if s["fase"] == "tawaran":
            t = s["tawaran"]
            frm = names.index(t["dari"])
            if a == "terima" and self._trade_ok(s, frm, p, t):
                self._do_trade(s, frm, p, t)
                events.append({"jenis": "tukar_diterima", "dari": t["dari"], "ke": t["ke"], "beri": t["beri"], "minta": t["minta"]})
            else:
                events.append({"jenis": "tukar_ditolak", "dari": t["dari"], "ke": t["ke"]})
            s["tawaran"] = None
            s["fase"] = s.pop("fase_sebelum", "awal")
            self._log(s, events)
            return events
        if isinstance(a, dict):
            s["aksi_giliran"] = s.get("aksi_giliran", 0) + 1
            kind = next(iter(a))
            i = a[kind]
            if kind == "tawar":
                s["tawar_count"] += 1
                s["tawaran"] = {"dari": names[p], **a["tawar"]}
                s["fase_sebelum"] = s["fase"]
                s["fase"] = "tawaran"
                events.append({"jenis": "tawar", "dari": names[p], "ke": a["tawar"]["ke"], "beri": a["tawar"]["beri"], "minta": a["tawar"]["minta"]})
            elif kind == "bangun":
                s["uang"][p] -= HARGA_RUMAH[PAPAN[i][3]]
                s["rumah"][str(i)] = self._houses(s, i) + 1
                events.append({"jenis": "bangun", "pemain": names[p], "petak": i, "nama": PAPAN[i][0], "rumah": s["rumah"][str(i)]})
            elif kind == "jual_rumah":
                s["rumah"][str(i)] -= 1
                s["uang"][p] += HARGA_RUMAH[PAPAN[i][3]] // 2
                events.append({"jenis": "jual_rumah", "pemain": names[p], "petak": i, "nama": PAPAN[i][0]})
            elif kind == "gadai":
                s["gadai"][str(i)] = True
                s["uang"][p] += PAPAN[i][2] // 2
                events.append({"jenis": "gadai", "pemain": names[p], "petak": i, "nama": PAPAN[i][0]})
            elif kind == "tebus":
                s["gadai"][str(i)] = False
                s["uang"][p] -= PAPAN[i][2] * 55 // 100
                events.append({"jenis": "tebus", "pemain": names[p], "petak": i, "nama": PAPAN[i][0]})
            self._log(s, events)
            return events
        if a == "beli":
            i = s["posisi"][p]
            s["uang"][p] -= PAPAN[i][2]
            s["milik"][str(i)] = p
            events.append({"jenis": "beli", "pemain": names[p], "petak": i, "nama": PAPAN[i][0], "harga": PAPAN[i][2]})
            self._after_landing(s, p, events)
        elif a == "tolak":
            i = s["posisi"][p]
            events.append({"jenis": "tolak_beli", "pemain": names[p], "petak": i, "nama": PAPAN[i][0]})
            if s["cfg"]["lelang_properti"] and len(self._alive(s)) > 1:
                s["lelang"] = {"petak": i, "tawaran": {}, "pemain": p}
                s["fase"] = "lelang"
            else:
                self._after_landing(s, p, events)
        elif a == "selesai":
            self._next_turn(s, events)
        elif a == "bayar_penjara":
            self._pay(s, p, DENDA_PENJARA, None, events, "denda")
            s["penjara"][p] = False
            s["giliran_penjara"][p] = 0
            events.append({"jenis": "keluar_penjara", "pemain": names[p], "cara": "bayar"})
        elif a == "kartu_bebas":
            s["kartu_bebas"][p] -= 1
            s["penjara"][p] = False
            s["giliran_penjara"][p] = 0
            events.append({"jenis": "keluar_penjara", "pemain": names[p], "cara": "kartu"})
        elif a == "lempar":
            self._roll(s, p, events)
        self._log(s, events)
        return events

    def _log(self, s, events):
        keep = [e for e in events if e["jenis"] not in ("lempar",)]
        s["riwayat"] = (s["riwayat"] + keep)[-40:]

    def _roll(self, s, p, events):
        names = s["names"]
        s["lempar_no"] += 1
        g = rng(s, "dadu", s["lempar_no"])
        d = [g.randint(1, 6), g.randint(1, 6)]
        s["dadu"] = d
        double = d[0] == d[1]
        events.append({"jenis": "lempar", "pemain": names[p], "dadu": d})
        if s["penjara"][p]:
            if double:
                s["penjara"][p] = False
                s["giliran_penjara"][p] = 0
                events.append({"jenis": "keluar_penjara", "pemain": names[p], "cara": "kembar"})
                self._move(s, p, sum(d), events)
                s["kembar"] = 0
                s["_lagi"] = False
                self._resolve(s, p, events, sum(d))
                return
            s["giliran_penjara"][p] += 1
            if s["giliran_penjara"][p] >= 3:
                self._pay(s, p, DENDA_PENJARA, None, events, "denda")
                if s["bangkrut"][p]:
                    self._next_turn(s, events)
                    return
                s["penjara"][p] = False
                s["giliran_penjara"][p] = 0
                events.append({"jenis": "keluar_penjara", "pemain": names[p], "cara": "wajib bayar"})
                self._move(s, p, sum(d), events)
                s["_lagi"] = False
                self._resolve(s, p, events, sum(d))
                return
            s["fase"] = "akhir"
            return
        if double:
            s["kembar"] += 1
            if s["kembar"] >= 3:
                self._to_jail(s, p, events, "tiga kali kembar")
                s["fase"] = "akhir"
                return
        s["_lagi"] = double
        self._move(s, p, sum(d), events)
        self._resolve(s, p, events, sum(d))

    def _move(self, s, p, k, events, collect=True):
        old = s["posisi"][p]
        new = (old + k) % len(PAPAN)
        if collect and k > 0 and new < old:
            self._gain(s, p, s["cfg"]["gaji"])
            events.append({"jenis": "gaji", "pemain": s["names"][p], "jumlah": s["cfg"]["gaji"]})
        s["posisi"][p] = new

    def _to_jail(self, s, p, events, why):
        s["posisi"][p] = PENJARA
        s["penjara"][p] = True
        s["giliran_penjara"][p] = 0
        s["kembar"] = 0
        s["_lagi"] = False
        events.append({"jenis": "penjara", "pemain": s["names"][p], "sebab": why})

    def _resolve(self, s, p, events, dice, mult=1):
        """Akibat berhenti di petak sekarang."""
        names = s["names"]
        i = s["posisi"][p]
        nama, jenis, harga, grp = PAPAN[i]
        if jenis in ("kota", "transport", "utilitas"):
            o = self._owner(s, i)
            if o is None:
                if s["uang"][p] >= harga or s["cfg"]["lelang_properti"]:
                    s["fase"] = "beli"
                    events.append({"jenis": "tawar_beli", "pemain": names[p], "petak": i, "nama": nama, "harga": harga})
                    return
            elif o != p and not s["bangkrut"][o]:
                rent = self._rent(s, i, dice) * mult
                if jenis == "utilitas" and mult > 1:
                    rent = dice * 10
                if rent > 0:
                    self._pay(s, p, rent, o, events, "sewa")
                    events.append({"jenis": "sewa", "pemain": names[p], "ke": names[o], "petak": i, "nama": nama, "jumlah": rent})
        elif jenis == "pajak":
            self._pay(s, p, harga, None, events, "pajak")
            events.append({"jenis": "pajak", "pemain": names[p], "nama": nama, "jumlah": harga})
        elif jenis == "ke_penjara":
            self._to_jail(s, p, events, "petak Masuk Penjara")
        elif jenis == "parkir" and s["cfg"]["parkir_jackpot"] and s["jackpot"] > 0:
            self._gain(s, p, s["jackpot"])
            events.append({"jenis": "jackpot", "pemain": names[p], "jumlah": s["jackpot"]})
            s["jackpot"] = 0
        elif jenis in ("kesempatan", "dana"):
            self._card(s, p, jenis, events, dice)
            if s["fase"] == "beli":
                return
        self._after_landing(s, p, events)

    def _after_landing(self, s, p, events):
        if s["bangkrut"][p]:
            self._next_turn(s, events)
            return
        if s.get("_lagi") and not s["penjara"][p]:
            s["fase"] = "awal"
        else:
            s["fase"] = "akhir"

    def _card(self, s, p, jenis, events, dice):
        names = s["names"]
        dek = s["dek"]
        if jenis == "kesempatan":
            idx = dek["kesempatan"][dek["ik"] % len(KESEMPATAN)]
            dek["ik"] += 1
            teks, kind, x = KESEMPATAN[idx]
        else:
            idx = dek["dana"][dek["id"] % len(DANA_UMUM)]
            dek["id"] += 1
            teks, kind, x = DANA_UMUM[idx]
        s["kartu_terakhir"] = teks
        events.append({"jenis": "kartu", "pemain": names[p], "dek": "Kesempatan" if jenis == "kesempatan" else "Dana Umum", "teks": teks})
        if kind == "maju":
            k = (x - s["posisi"][p]) % len(PAPAN)
            self._move(s, p, k, events)
            if x == 0:
                return
            self._resolve_card_landing(s, p, events, dice)
        elif kind == "mundur":
            s["posisi"][p] = (s["posisi"][p] - x) % len(PAPAN)
            self._resolve_card_landing(s, p, events, dice)
        elif kind in ("transport", "utilitas"):
            grp = KELOMPOK[kind]
            pos = s["posisi"][p]
            tgt = min(grp, key=lambda j: (j - pos) % len(PAPAN) or len(PAPAN))
            self._move(s, p, (tgt - pos) % len(PAPAN), events)
            self._resolve_card_landing(s, p, events, dice, mult=x)
        elif kind == "bayar":
            self._pay(s, p, x, None, events, "kartu")
        elif kind == "terima":
            self._gain(s, p, x)
        elif kind == "bebas":
            s["kartu_bebas"][p] += 1
        elif kind == "penjara":
            self._to_jail(s, p, events, "kartu")
        elif kind == "renovasi":
            h = sum(self._houses(s, int(k)) for k, o in s["milik"].items() if o == p and self._houses(s, int(k)) < 5)
            hotel = sum(1 for k, o in s["milik"].items() if o == p and self._houses(s, int(k)) == 5)
            self._pay(s, p, h * x + hotel * (100 if x == 25 else 115), None, events, "kartu")
        elif kind == "bayar_semua":
            for q in self._alive(s):
                if q != p and not s["bangkrut"][p]:
                    self._pay(s, p, x, q, events, "kartu")
        elif kind == "terima_semua":
            for q in self._alive(s):
                if q != p:
                    self._pay(s, q, x, p, events, "kartu")

    def _resolve_card_landing(self, s, p, events, dice, mult=1):
        i = s["posisi"][p]
        jenis = PAPAN[i][1]
        if jenis in ("kota", "transport", "utilitas", "pajak", "ke_penjara", "parkir"):
            nama, _, harga, _ = PAPAN[i]
            if jenis in ("kota", "transport", "utilitas"):
                o = self._owner(s, i)
                if o is None:
                    s["fase"] = "beli"
                    events.append({"jenis": "tawar_beli", "pemain": s["names"][p], "petak": i, "nama": nama, "harga": harga})
                    return
                if o != p and not s["bangkrut"][o]:
                    rent = self._rent(s, i, dice)
                    if jenis == "utilitas" and mult > 1:
                        rent = dice * 10
                    elif mult > 1:
                        rent *= mult
                    if rent > 0:
                        self._pay(s, p, rent, o, events, "sewa")
                        events.append({"jenis": "sewa", "pemain": s["names"][p], "ke": s["names"][o], "petak": i, "nama": nama, "jumlah": rent})
            elif jenis == "pajak":
                self._pay(s, p, harga, None, events, "pajak")
                events.append({"jenis": "pajak", "pemain": s["names"][p], "nama": nama, "jumlah": harga})
            elif jenis == "ke_penjara":
                self._to_jail(s, p, events, "petak Masuk Penjara")

    def _close_auction(self, s, events):
        names = s["names"]
        lel = s["lelang"]
        i = lel["petak"]
        bids = {q: x for q, x in lel["tawaran"].items() if not s["bangkrut"][q] and x <= s["uang"][q]}
        top = max(bids.values(), default=0)
        p = lel["pemain"]
        n = len(names)
        winner = None
        if top > 0:
            cands = [q for q, x in bids.items() if x == top]
            winner = min(cands, key=lambda q: (q - p) % n)
            s["uang"][winner] -= top
            s["milik"][str(i)] = winner
        events.append({"jenis": "lelang_hasil", "petak": i, "nama": PAPAN[i][0], "pemenang": names[winner] if winner is not None else None,
                       "harga": top, "tawaran": {names[q]: x for q, x in lel["tawaran"].items()}})
        s["lelang"] = None
        self._after_landing(s, p, events)

    def _trade_ok(self, s, a, b, t):
        if s["bangkrut"][a] or s["bangkrut"][b]:
            return False
        if s["uang"][a] < t["beri"]["uang"] or s["uang"][b] < t["minta"]["uang"]:
            return False
        for i in t["beri"]["properti"]:
            if self._owner(s, i) != a:
                return False
        for i in t["minta"]["properti"]:
            if self._owner(s, i) != b:
                return False
        return True

    def _do_trade(self, s, a, b, t):
        s["uang"][a] += t["minta"]["uang"] - t["beri"]["uang"]
        s["uang"][b] += t["beri"]["uang"] - t["minta"]["uang"]
        for i in t["beri"]["properti"]:
            s["milik"][str(i)] = b
        for i in t["minta"]["properti"]:
            s["milik"][str(i)] = a

    def _next_turn(self, s, events):
        n = len(s["names"])
        s["kembar"] = 0
        s["tawar_count"] = 0
        s["aksi_giliran"] = 0
        s["_lagi"] = False
        if len(self._alive(s)) <= 1:
            s["fase"] = "awal"
            return
        p, wrapped = s["giliran"], False
        for _ in range(n):
            p = (p + 1) % n
            if p == 0:
                wrapped = True
            if not s["bangkrut"][p]:
                break
        if wrapped:
            s["putaran"] += 1
        s["giliran"] = p
        s["fase"] = "awal"
        s["dadu"] = None
        events.append({"jenis": "giliran", "pemain": s["names"][p], "putaran": s["putaran"]})

    def over(self, s):
        return len(self._alive(s)) <= 1 or s["putaran"] > s["cfg"]["batas_putaran"]

    def scores(self, s):
        out = []
        for p in range(len(s["names"])):
            if s["bangkrut"][p]:
                out.append(float(-10000 + s["urut_bangkrut"].index(p)))
            else:
                out.append(float(self._worth(s, p)))
        return out

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        names = s["names"]

        def _who(nama):
            if nama is None:
                return p
            if nama not in names:
                raise ActionError(f"tidak ada pemain bernama {nama!r}")
            return names.index(nama)

        def petak(i):
            i = as_int(i, "petak")
            if not 0 <= i < len(PAPAN):
                raise ActionError("petak harus 0 sampai 39")
            return dict(obs["papan"][i])

        def milik(nama=None):
            q = _who(nama)
            return sorted(int(k) for k, o in s["milik"].items() if o == q)

        def kelompok(w):
            if w not in KELOMPOK:
                raise ActionError("kelompok tidak dikenal")
            return list(KELOMPOK[w])

        def lengkap(w, nama=None):
            return w in KELOMPOK and self._owns_group(s, _who(nama), w)

        def kekayaan(nama=None):
            return obs["pemain"][names[_who(nama)]]["kekayaan"]

        def uang(nama=None):
            return obs["pemain"][names[_who(nama)]]["uang"]

        return {"petak": petak, "milik": milik, "kelompok": kelompok, "lengkap": lengkap,
                "bisa_bangun": lambda: sorted(self._buildable(s, p)) if s["giliran"] == p else [], "kekayaan": kekayaan, "uang": uang}
