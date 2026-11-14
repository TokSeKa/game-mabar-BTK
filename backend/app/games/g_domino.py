"""Domino Mabar: domino gaya Indonesia dengan aturan Gaple (buntu = lewat) atau Draw (buntu = ambil kartu).

Satu ronde: kartu dibagi dari set balak 6 (28 kartu) atau balak 9 (55 kartu). Pemain bergiliran menempel kartu di
ujung kiri atau kanan meja. Ronde selesai saat ada yang kartunya habis, atau meja buntu (semua lewat berturut-turut),
dan pemenangnya yang sisa matanya paling sedikit. Semua keacakan (pembagian kartu) dari seed match.
"""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

LEWAT, AMBIL = "lewat", "ambil"


def mata(k: list[int]) -> int:
    return k[0] + k[1]


def balak(k: list[int]) -> bool:
    return k[0] == k[1]


def kartu_set(maks: int) -> list[list[int]]:
    return [[a, b] for a in range(maks + 1) for b in range(a, maks + 1)]


def bisa_tempel(k: list[int], ujung: list[int] | None) -> list[str]:
    """Sisi meja tempat kartu ``k`` bisa ditempel. Meja kosong: "kanan" saja (kartu pertama)."""
    if ujung is None:
        return ["kanan"]
    out = []
    if ujung[0] in k:
        out.append("kiri")
    if ujung[1] in k:
        out.append("kanan")
    return out


class DominoMabar(Game):
    id = "domino"
    nama = "Domino (Gaple & Draw)"
    ringkas = "Domino gaya Indonesia: tempel kartu di ujung meja, habiskan kartumu dulu. Aturan Gaple atau Draw, bisa tim 2 lawan 2, plus mode tantangan."
    kategori = "giliran"
    min_pemain = 2
    max_pemain = 6
    hint_aksi = '{"kartu": nomor_kartu_di_tangan, "sisi": "kiri" atau "kanan"}, "ambil", atau "lewat"'
    timer = 25
    jeda_pada, jeda_hasil = ("ronde_selesai",), 7
    label_skor = "Poin"
    settings = [
        Setting("aturan", "Aturan", "pilihan", "gaple",
                pilihan=[["gaple", "Gaple: tidak ada kartu yang cocok = lewat"],
                         ["draw", "Draw: tidak ada kartu yang cocok = ambil dari tumpukan sampai dapat"]]),
        Setting("ronde", "Jumlah ronde", "int", 3, 1, 15),
        Setting("set", "Set kartu", "pilihan", "6",
                pilihan=[["6", "Balak 6 (28 kartu, klasik)"], ["9", "Balak 9 (55 kartu, ronde lebih panjang)"]],
                ket="Dengan 5–6 pemain set balak 6 hanya cukup 4 kartu per orang; balak 9 lebih seru untuk ramai-ramai."),
        Setting("kartu_awal", "Kartu per pemain", "int", 0, 0, 12,
                ket="0 = otomatis (7 kartu; aturan Draw dengan 3+ pemain 5 kartu; dikurangi kalau kartunya tidak cukup)."),
        Setting("skor", "Cara menghitung skor", "pilihan", "sisa_lawan", grup="aturan",
                pilihan=[["sisa_lawan", "Pemenang ronde dapat jumlah mata sisa kartu semua lawan"],
                         ["minus", "Semua pemain kena minus sebanyak mata sisa kartunya sendiri (pemenang 0)"]]),
        Setting("target", "Selesai lebih cepat kalau poin mencapai", "int", 0, 0, 500, grup="aturan",
                jika={"skor": "sisa_lawan"}, ket="0 = main sampai semua ronde selesai."),
        Setting("tim", "Main tim (2 lawan 2)", "bool", False, grup="aturan",
                ket="Hanya untuk 4 pemain: kursi 1 & 3 melawan kursi 2 & 4, duduk berselang. Poin tim dijumlah dan dibagi berdua."),
        Setting("mulai", "Ronde pertama dibuka oleh", "pilihan", "balak_tertinggi", grup="aturan",
                pilihan=[["balak_tertinggi", "Pemegang balak tertinggi (wajib membuka dengan balak itu)"],
                         ["kursi_1", "Kursi pertama, bebas kartu apa saja"]],
                ket="Ronde berikutnya dibuka pemenang ronde sebelumnya."),
        Setting("kartu_terbuka", "Kartu lawan terlihat", "bool", False, grup="informasi",
                ket="Tantangan strategi: semua kartu di tangan terbuka, menang murni dari perhitungan."),
        Setting("bonus_balak", "Bonus tutup balak", "bool", False, grup="kejutan",
                ket="Menghabiskan kartu dengan kartu balak: poin ronde ×2."),
        Setting("denda_lewat", "Denda tiap lewat", "int", 0, 0, 20, grup="kejutan",
                ket="Setiap kali terpaksa lewat, poinmu berkurang sekian. Bikin pemain menyimpan angka yang aman."),
        Setting("bom_kosong", "Kartu 0-0 = bom", "bool", False, grup="kejutan",
                ket="Menempel kartu 0-0 membuat pemain berikutnya wajib ambil 2 kartu (Draw) atau kena denda 10 poin (Gaple)."),
    ]
    presets = [
        {"id": "terbuka", "nama": "Catur Domino", "ket": "Semua kartu terbuka: menang dari perhitungan, bukan keberuntungan.",
         "nilai": {"kartu_terbuka": True}},
        {"id": "pedas", "nama": "Pedas", "ket": "Bonus tutup balak, denda lewat 5, dan kartu 0-0 jadi bom.",
         "nilai": {"bonus_balak": True, "denda_lewat": 5, "bom_kosong": True}},
        {"id": "tim", "nama": "Tim 2 lawan 2", "ket": "Gaple tim klasik (pas untuk 4 pemain).", "nilai": {"tim": True}},
    ]
    aturan = """
- Setiap pemain mendapat kartu domino. Di giliranmu, **tempel satu kartu** di ujung **kiri** atau **kanan** meja: salah satu
  angka kartumu harus sama dengan angka di ujung itu. Kartu pertama ronde boleh apa saja (atau wajib balak tertinggi di
  ronde pertama, tergantung pengaturan).
- **Gaple**: kalau tidak punya kartu yang cocok, kamu **lewat**. **Draw**: kamu harus **ambil** kartu dari tumpukan sampai
  dapat yang cocok (kalau tumpukan habis, baru boleh lewat).
- Ronde selesai saat ada yang **menghabiskan kartu**, atau meja **buntu** (semua pemain lewat berturut-turut). Kalau buntu,
  pemenangnya yang **jumlah mata kartu sisanya paling sedikit** (seri: yang lebih dulu duduk setelah penempel terakhir).
- Skor: pemenang ronde mendapat jumlah mata sisa kartu semua lawan (atau, sesuai pengaturan, semua pemain kena minus
  sebanyak mata kartunya sendiri). Pemenang membuka ronde berikutnya.
- **Tim** (4 pemain): kursi 1 & 3 melawan 2 & 4; kemenangan satu orang adalah kemenangan tim.
- **Tantangan**: kartu terbuka, bonus tutup balak (×2), denda tiap lewat, kartu 0-0 jadi bom, set balak 9.
"""
    format_aksi = """- `{"kartu": 2, "sisi": "kiri"}`: tempel kartu nomor 2 di tanganmu (mulai dari 0) di ujung kiri. `sisi` boleh dihilangkan
  kalau kartu itu cuma cocok di satu sisi (atau langsung kirim angka `2`).
- `"ambil"`: ambil satu kartu dari tumpukan (aturan Draw, hanya kalau tidak ada kartu yang cocok). Giliranmu berlanjut.
- `"lewat"`: lewat (hanya kalau memang tidak bisa menempel dan tidak bisa mengambil)."""
    format_info = """```
{ "aturan": "gaple", "ronde": 1, "ronde_total": 3, "set": 6,
  "meja": [[6, 6], [6, 3], ...],            # urut dari kiri ke kanan, angka sudah diputar sesuai sambungan
  "ujung": [6, 3],                          # angka ujung kiri & kanan (None kalau meja kosong)
  "tangan": [[1, 4], [3, 3], ...],          # kartumu
  "jumlah_kartu": {"Budi": 6, ...}, "tangan_semua": {...} (kalau kartu terbuka),
  "tumpukan": 0, "giliran": "Budi", "skor": {"Budi": 12, ...},
  "lewat_pada": {"Budi": [5, 2], ...},      # angka ujung saat pemain itu terpaksa lewat/ambil (petunjuk!)
  "tim": None atau [["Budi", "Cici"], ["Ani", "Dodi"]],
  "wajib": [6, 6] atau None,                # kartu yang wajib dimainkan pertama
  "riwayat": [ {"ronde": 1, "pemenang": "Budi", "cara": "habis", "poin": {...}, "sisa": {...}} ] }
```"""
    lib_docs = [
        {"nama": "tangan", "jenis": "fungsi", "tanda": "tangan()", "ket": "Kartu di tanganmu: [[a, b], ...]."},
        {"nama": "ujung", "jenis": "fungsi", "tanda": "ujung()", "ket": "[kiri, kanan] angka ujung meja, atau None kalau meja kosong."},
        {"nama": "langkah_sah", "jenis": "fungsi", "tanda": "langkah_sah()", "ket": "Semua aksi tempel yang sah: [{'kartu': i, 'sisi': 'kiri'}, ...]. Kosong = harus ambil/lewat."},
        {"nama": "mata", "jenis": "fungsi", "tanda": "mata(kartu)", "ket": "Jumlah mata sebuah kartu, misalnya mata([6, 3]) = 9."},
        {"nama": "balak", "jenis": "fungsi", "tanda": "balak(kartu)", "ket": "True kalau kartu itu balak (dua angkanya sama)."},
        {"nama": "sudah_keluar", "jenis": "fungsi", "tanda": "sudah_keluar(angka)", "ket": "Berapa kartu berisi `angka` yang sudah ada di meja."},
        {"nama": "lawan_tidak_punya", "jenis": "fungsi", "tanda": "lawan_tidak_punya(nama)", "ket": "Angka-angka yang (kemungkinan besar) tidak dimiliki pemain itu: angka ujung saat ia terpaksa lewat/ambil."},
        {"nama": "berikutnya", "jenis": "fungsi", "tanda": "berikutnya()", "ket": "Nama pemain yang jalan setelahmu."},
        {"nama": "kawan", "jenis": "fungsi", "tanda": "kawan()", "ket": "Nama kawan setimmu (mode tim), atau None."},
        {"nama": "ujung_setelah", "jenis": "fungsi", "tanda": "ujung_setelah(aksi)", "ket": "[kiri, kanan] meja kalau aksi tempel itu dimainkan."},
    ]
    templates = [
        {"id": "buang_besar", "nama": "Buang Besar", "ket": "Selalu menempel kartu dengan mata terbesar (mengurangi risiko kalau meja buntu).", "kode": '''def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    terbaik = sah[0]
    for a in sah:
        if mata(t[a["kartu"]]) > mata(t[terbaik["kartu"]]):
            terbaik = a
    return terbaik
'''},
        {"id": "balak_dulu", "nama": "Balak Dulu", "ket": "Balak susah ditempel, jadi dibuang secepatnya; selain itu buang yang besar.", "kode": '''def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    def nilai(a):
        k = t[a["kartu"]]
        return (100 if balak(k) else 0) + mata(k)
    terbaik = sah[0]
    for a in sah:
        if nilai(a) > nilai(terbaik):
            terbaik = a
    return terbaik
'''},
        {"id": "pengunci", "nama": "Pengunci", "ket": "Membaca lawan: memilih langkah yang membuat ujung meja berisi angka yang tidak dimiliki pemain berikutnya, sambil menjaga variasi angka di tangan sendiri.", "kode": '''def aksi():
    sah = langkah_sah()
    if not sah:
        return "ambil" if info()["tumpukan"] > 0 and info()["aturan"] == "draw" else "lewat"
    t = tangan()
    lawan = berikutnya()
    kosong = lawan_tidak_punya(lawan) if lawan != kawan() else []
    def nilai(a):
        u = ujung_setelah(a)
        v = mata(t[a["kartu"]])
        for x in u:
            if x in kosong:
                v += 15
            # simpan kartu yang bisa menyambung ujung baru
            for i in range(len(t)):
                if i != a["kartu"] and x in t[i]:
                    v += 3
                    break
            v += sudah_keluar(x)
        if balak(t[a["kartu"]]):
            v += 6
        return v
    terbaik = sah[0]
    for a in sah:
        if nilai(a) > nilai(terbaik):
            terbaik = a
    return terbaik
'''},
    ]

    # ------------------------------------------------------------ util
    def _tim(self, s):
        return s["cfg"]["tim"] and len(s["names"]) == 4

    def _kawan(self, s, p):
        return (p + 2) % 4 if self._tim(s) else None

    def _hand_size(self, cfg, n, total):
        k = cfg["kartu_awal"]
        if k <= 0:
            k = 5 if cfg["aturan"] == "draw" and n >= 3 else 7
        return max(1, min(k, total // n - (1 if cfg["aturan"] == "draw" and total // n > 2 else 0)))

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * n, "riwayat": [],
             "pembuka": 0, "lewat_total": [0] * n}
        self._new_round(s)
        return s

    def _new_round(self, s):
        c, n = s["cfg"], len(s["names"])
        deck = kartu_set(int(c["set"]))
        rng(s, "kocok", s["ronde"]).shuffle(deck)
        k = self._hand_size(c, n, len(deck))
        s["tangan"] = [deck[i * k:(i + 1) * k] for i in range(n)]
        s["tumpukan"] = deck[n * k:] if c["aturan"] == "draw" else []
        s["meja"], s["ujung"] = [], None
        s["lewat_beruntun"] = 0
        s["lewat_pada"] = [[] for _ in range(n)]
        s["wajib"] = None
        s["bom"] = 0                      # pemain berikutnya wajib ambil sekian (bom 0-0, aturan Draw)
        s["terakhir"] = None
        if s["ronde"] == 1 and c["mulai"] == "balak_tertinggi":
            best = None
            for p, h in enumerate(s["tangan"]):
                for kk in h:
                    key = (balak(kk), mata(kk))
                    if best is None or key > best[0]:
                        best = (key, p, kk)
            s["giliran"], s["wajib"] = best[1], list(best[2])
        else:
            s["giliran"] = s["pembuka"] % n

    def pending(self, s):
        return [] if self.over(s) else [s["giliran"]]

    def _legal(self, s, p):
        if s["bom"] > 0:
            return []                     # kena bom: wajib ambil dulu
        h = s["tangan"][p]
        out = []
        for i, k in enumerate(h):
            if s["wajib"] is not None and k != s["wajib"]:
                continue
            for side in bisa_tempel(k, s["ujung"]):
                out.append({"kartu": i, "sisi": side})
        return out

    # ------------------------------------------------------------ tampilan
    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        open_all = viewer == "semua" or c["kartu_terbuka"]
        r = min(s["ronde"], c["ronde"])
        v = {"aturan": c["aturan"], "ronde": r, "ronde_total": c["ronde"], "set": int(c["set"]),
             "meja": [list(k) for k in s["meja"]], "ujung": list(s["ujung"]) if s["ujung"] else None,
             "jumlah_kartu": {n[i]: len(h) for i, h in enumerate(s["tangan"])},
             "tangan_semua": {n[i]: [list(k) for k in h] for i, h in enumerate(s["tangan"])} if open_all else None,
             "tumpukan": len(s["tumpukan"]), "giliran": n[s["giliran"]] if not self.over(s) else None,
             "skor": dict(zip(n, s["skor"])), "lewat_pada": {n[i]: list(x) for i, x in enumerate(s["lewat_pada"])},
             "tim": [[n[0], n[2]], [n[1], n[3]]] if self._tim(s) else None, "wajib": s["wajib"],
             "skor_mode": c["skor"], "target": c["target"] if c["skor"] == "sisa_lawan" else 0,
             "bonus_balak": c["bonus_balak"], "denda_lewat": c["denda_lewat"], "bom_kosong": c["bom_kosong"],
             "bom": s["bom"], "kartu_terbuka": c["kartu_terbuka"],
             "riwayat": [dict(e) for e in s["riwayat"]]}
        return v

    def public(self, s):
        return {**self._view(s, None), "tangan": None}

    def full_view(self, s):
        return {**self._view(s, "semua"), "tangan": None}

    def observe(self, s, p):
        v = self._view(s, p)
        v["tangan"] = [list(k) for k in s["tangan"][p]]
        v["sah"] = self._legal(s, p) if s["giliran"] == p and not self.over(s) and s["bom"] <= 0 else []
        v["bisa_ambil"] = bool(s["tumpukan"]) and s["cfg"]["aturan"] == "draw"
        return {**v, "saya": p, "nama_saya": s["names"][p]}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        legal = self._legal(s, p)
        draw_ok = s["cfg"]["aturan"] == "draw" and bool(s["tumpukan"])
        if s["bom"] > 0:
            if a in (AMBIL, None) or (isinstance(a, str) and a.strip().lower() == AMBIL):
                return AMBIL
            raise ActionError("kena bom 0-0: kamu wajib \"ambil\" dulu")
        if isinstance(a, str):
            w = a.strip().lower()
            if w == AMBIL:
                if legal:
                    raise ActionError("masih ada kartu yang bisa ditempel, tidak boleh ambil")
                if not draw_ok:
                    raise ActionError("tidak bisa ambil (aturan Gaple atau tumpukan habis): kirim \"lewat\"")
                return AMBIL
            if w in (LEWAT, "pass", "skip"):
                if legal:
                    raise ActionError("masih ada kartu yang bisa ditempel, tidak boleh lewat")
                if draw_ok:
                    raise ActionError("aturan Draw: ambil kartu dulu (\"ambil\")")
                return LEWAT
            raise ActionError("aksi tidak dikenal: kirim {\"kartu\": i, \"sisi\": \"kiri\"/\"kanan\"}, \"ambil\", atau \"lewat\"")
        if a is None:
            raise ActionError("aksi kosong")
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            a = {"kartu": a}
        if not isinstance(a, dict) or "kartu" not in a:
            raise ActionError("kirim {\"kartu\": nomor_kartu, \"sisi\": \"kiri\" atau \"kanan\"}")
        i = as_int(a.get("kartu"), "nomor kartu")
        h = s["tangan"][p]
        if not 0 <= i < len(h):
            raise ActionError(f"nomor kartu harus 0 sampai {len(h) - 1}")
        if s["wajib"] is not None and h[i] != s["wajib"]:
            raise ActionError(f"ronde ini wajib dibuka dengan kartu {s['wajib'][0]}-{s['wajib'][1]}")
        sides = bisa_tempel(h[i], s["ujung"])
        if not sides:
            raise ActionError(f"kartu {h[i][0]}-{h[i][1]} tidak cocok dengan ujung meja {s['ujung'][0]} / {s['ujung'][1]}")
        side = a.get("sisi")
        if side is None:
            side = "kanan" if "kanan" in sides else sides[0]
        side = str(side).strip().lower()
        if side not in ("kiri", "kanan"):
            raise ActionError("sisi harus \"kiri\" atau \"kanan\"")
        if side not in sides:
            raise ActionError(f"kartu {h[i][0]}-{h[i][1]} tidak cocok di ujung {side}")
        return {"kartu": i, "sisi": side}

    def default(self, s, p):
        legal = self._legal(s, p)
        if s["bom"] > 0:
            return AMBIL
        if legal:
            h = s["tangan"][p]
            return max(legal, key=lambda a: (mata(h[a["kartu"]]), a["sisi"] == "kanan", -a["kartu"]))
        if s["cfg"]["aturan"] == "draw" and s["tumpukan"]:
            return AMBIL
        return LEWAT

    def _next(self, s, p):
        return (p + 1) % len(s["names"])

    def apply(self, s, actions):
        (p, a), = actions.items()
        n, c = s["names"], s["cfg"]
        events: list[dict[str, Any]] = []
        if a == AMBIL:
            if s["tumpukan"]:
                s["tangan"][p].append(s["tumpukan"].pop(0))
            if s["ujung"] is not None:
                s["lewat_pada"][p] = sorted(set(s["lewat_pada"][p]) | set(s["ujung"])) if s["bom"] <= 0 else s["lewat_pada"][p]
            events.append({"jenis": "ambil", "pemain": n[p], "sisa_tumpukan": len(s["tumpukan"]), "bom": s["bom"] > 0})
            if s["bom"] > 0:
                s["bom"] -= 1
                if s["bom"] <= 0 or not s["tumpukan"]:
                    s["bom"] = 0
                    s["giliran"] = self._next(s, p)       # selesai menerima bom: giliran lewat
            return events
        if a == LEWAT:
            s["lewat_beruntun"] += 1
            s["lewat_total"][p] += 1
            if s["ujung"] is not None:
                s["lewat_pada"][p] = sorted(set(s["lewat_pada"][p]) | set(s["ujung"]))
            denda = c["denda_lewat"]
            if denda:
                self._add(s, p, -denda)
            events.append({"jenis": "lewat", "pemain": n[p], "ujung": list(s["ujung"]) if s["ujung"] else None, "denda": denda})
            if s["lewat_beruntun"] >= len(n):
                events += self._end_round(s, None)
            else:
                s["giliran"] = self._next(s, p)
            return events
        i, side = a["kartu"], a["sisi"]
        k = s["tangan"][p].pop(i)
        s["wajib"] = None
        s["lewat_beruntun"] = 0
        if s["ujung"] is None:
            placed = list(k)
            s["meja"] = [placed]
            s["ujung"] = [placed[0], placed[1]]
        elif side == "kiri":
            placed = [k[1], k[0]] if k[1] == s["ujung"][0] else [k[0], k[1]]
            if placed[1] != s["ujung"][0]:
                placed = [placed[1], placed[0]]
            s["meja"].insert(0, placed)
            s["ujung"][0] = placed[0]
        else:
            placed = [k[0], k[1]] if k[0] == s["ujung"][1] else [k[1], k[0]]
            s["meja"].append(placed)
            s["ujung"][1] = placed[1]
        s["terakhir"] = p
        events.append({"jenis": "tempel", "pemain": n[p], "kartu": list(k), "sisi": side, "ujung": list(s["ujung"]),
                       "sisa": len(s["tangan"][p])})
        if not s["tangan"][p]:
            events += self._end_round(s, p, balak_terakhir=balak(k))
            return events
        s["giliran"] = self._next(s, p)
        if c["bom_kosong"] and k == [0, 0]:
            q = s["giliran"]
            if c["aturan"] == "draw" and s["tumpukan"]:
                s["bom"] = 2
                events.append({"jenis": "bom", "pemain": n[p], "korban": n[q], "ambil": 2})
            else:
                self._add(s, q, -10)
                events.append({"jenis": "bom", "pemain": n[p], "korban": n[q], "denda": 10})
        return events

    def _add(self, s, p, pts):
        s["skor"][p] += pts
        if self._tim(s):
            s["skor"][(p + 2) % 4] += pts

    def _end_round(self, s, winner, balak_terakhir=False):
        n, c = s["names"], s["cfg"]
        sisa = [sum(mata(k) for k in h) for h in s["tangan"]]
        cara = "habis"
        if winner is None:
            cara = "buntu"
            start = self._next(s, s["terakhir"]) if s["terakhir"] is not None else 0
            order = [(start + d) % len(n) for d in range(len(n))]
            if self._tim(s):
                tim_sisa = {0: sisa[0] + sisa[2], 1: sisa[1] + sisa[3]}
                winner = min(order, key=lambda q: (tim_sisa[q % 2], sisa[q], order.index(q)))
            else:
                winner = min(order, key=lambda q: (sisa[q], order.index(q)))
        poin = [0] * len(n)
        kali = 2 if (c["bonus_balak"] and balak_terakhir and cara == "habis") else 1
        if c["skor"] == "sisa_lawan":
            lawan = [q for q in range(len(n)) if q != winner and q != self._kawan(s, winner)]
            got = sum(sisa[q] for q in lawan) * kali
            if self._tim(s):
                got //= 2
                poin[winner] = poin[(winner + 2) % 4] = got
                s["skor"][winner] += got
                s["skor"][(winner + 2) % 4] += got
            else:
                poin[winner] = got
                s["skor"][winner] += got
        else:
            for q in range(len(n)):
                if q == winner or (self._tim(s) and q == self._kawan(s, winner)):
                    continue
                poin[q] = -sisa[q] * kali
                s["skor"][q] += poin[q]
        entry = {"ronde": s["ronde"], "pemenang": n[winner], "cara": cara, "kali": kali,
                 "poin": dict(zip(n, poin)), "sisa": dict(zip(n, sisa)),
                 "tangan": {n[q]: [list(k) for k in h] for q, h in enumerate(s["tangan"])},
                 "meja": [list(k) for k in s["meja"]]}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        s["pembuka"] = winner
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "ronde_selesai", **entry}]

    def over(self, s):
        c = s["cfg"]
        if s["ronde"] > c["ronde"]:
            return True
        return c["skor"] == "sisa_lawan" and c["target"] > 0 and max(s["skor"]) >= c["target"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [-float(x) for x in s["lewat_total"]]

    def reveal(self, s):
        return {"ronde": [{"ronde": e["ronde"], "pemenang": e["pemenang"], "cara": e["cara"]} for e in s["riwayat"]]}

    # ------------------------------------------------------------ bot
    def bot_library(self, s, p, obs):
        n = s["names"]

        def tangan():
            return [list(k) for k in s["tangan"][p]]

        def ujung():
            return list(s["ujung"]) if s["ujung"] else None

        def langkah_sah():
            return [dict(a) for a in self._legal(s, p)]

        def _mata(k):
            if not isinstance(k, list) or len(k) != 2:
                raise ActionError("mata() butuh kartu [a, b]")
            return int(k[0]) + int(k[1])

        def _balak(k):
            return isinstance(k, list) and len(k) == 2 and k[0] == k[1]

        def sudah_keluar(x):
            return sum(1 for k in s["meja"] if x in k)

        def lawan_tidak_punya(nama):
            if nama not in n:
                raise ActionError(f"tidak ada pemain bernama {nama}")
            return list(s["lewat_pada"][n.index(nama)])

        def berikutnya():
            return n[self._next(s, p)]

        def kawan():
            k = self._kawan(s, p)
            return n[k] if k is not None else None

        def ujung_setelah(a):
            a = self.validate(s, p, a)
            if not isinstance(a, dict):
                return ujung()
            k = s["tangan"][p][a["kartu"]]
            if s["ujung"] is None:
                return [k[0], k[1]]
            u = list(s["ujung"])
            if a["sisi"] == "kiri":
                u[0] = k[0] if k[1] == u[0] else k[1]
            else:
                u[1] = k[1] if k[0] == u[1] else k[0]
            return u

        return {"tangan": tangan, "ujung": ujung, "langkah_sah": langkah_sah, "mata": _mata, "balak": _balak,
                "sudah_keluar": sudah_keluar, "lawan_tidak_punya": lawan_tidak_punya, "berikutnya": berikutnya,
                "kawan": kawan, "ujung_setelah": ujung_setelah}
