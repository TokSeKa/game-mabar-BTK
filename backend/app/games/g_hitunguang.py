"""Hitung Uang: adu cepat menghitung segepok uang rupiah. Khusus pemain manusia.

Semua pemain mendapat gepokan yang sama (dari seed). Uang dihitung di layar masing-masing: klik lembar teratas untuk
menggesernya ke tumpukan "sudah dihitung", lalu ketik jumlahnya. Yang benar lebih dulu mendapat poin lebih besar;
jawaban salah kena hukuman tunggu. Tantangan: uang berantakan, terbalik, uang palsu, kupon, dan koin.
"""

from __future__ import annotations

from typing import Any

from .base import ActionError, Game, Setting, as_int, rng

KERTAS = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
KOIN = [100, 200, 500, 1000]
POIN_URUT = [15, 12, 10, 8, 7, 6, 5, 4]
POIN_SALAH = -3
KESEMPATAN = 3


class HitungUang(Game):
    id = "hitunguang"
    nama = "Hitung Uang"
    ringkas = "Segepok uang rupiah: siapa paling cepat menghitung dengan benar? Ada uang berantakan, terbalik, palsu, dan kupon yang tidak boleh dihitung."
    kategori = "mandiri"
    min_pemain = 1
    max_pemain = 12
    mandiri = True
    bot = False
    hint_aksi = '{"jawab": 125000} atau "lewat"'
    timer = 120
    jeda_pada, jeda_hasil = ("ronde_selesai",), 8
    label_skor = "Poin"
    settings = [
        Setting("ronde", "Jumlah gepok", "int", 5, 1, 12),
        Setting("lembar", "Lembar per gepok", "int", 12, 4, 40),
        Setting("pecahan", "Pecahan", "pilihan", "semua",
                pilihan=[["semua", "Semua pecahan kertas (Rp1.000–Rp100.000)"], ["kecil", "Pecahan kecil (Rp1.000–Rp10.000)"],
                         ["besar", "Pecahan besar (Rp10.000–Rp100.000)"]]),
        Setting("tampilan", "Cara melihat uang", "pilihan", "tumpuk",
                pilihan=[["tumpuk", "Satu tumpukan: hanya lembar teratas yang terlihat (geser satu per satu)"],
                         ["sebar", "Disebar di meja (semua terlihat, saling menumpuk)"]]),
        Setting("hukuman_detik", "Hukuman jawaban salah (detik)", "int", 4, 0, 20, grup="aturan",
                ket=f"Jawaban salah: {POIN_SALAH} poin dan harus menunggu sekian detik. Maksimal {KESEMPATAN} kali salah per gepok."),
        Setting("berantakan", "Uang berantakan", "bool", True, grup="kejutan", ket="Lembar uang miring dan bergeser."),
        Setting("terbalik", "Ada uang terbalik", "bool", False, grup="kejutan",
                ket="Sebagian lembar terbalik (sisi belakang, angkanya kecil dan posisinya terbalik)."),
        Setting("koin", "Campur koin", "bool", False, grup="kejutan", ket="Ada koin Rp100–Rp1.000 di antara lembaran."),
        Setting("palsu", "Ada uang palsu", "bool", False, grup="kejutan",
                ket="Uang asli punya pita perak mengilap; yang tidak punya pita adalah PALSU dan tidak dihitung."),
        Setting("kupon", "Ada kupon/uang mainan", "bool", False, grup="kejutan",
                ket="Kupon belanja dan uang mainan bentuknya mirip uang, tapi tidak dihitung."),
    ]
    presets = [
        {"id": "kasir", "nama": "Kasir Teliti", "ket": "Terbalik, koin, dan uang palsu.",
         "nilai": {"terbalik": True, "koin": True, "palsu": True}},
        {"id": "neraka", "nama": "Teller Bank", "ket": "Semua tantangan menyala.",
         "nilai": {"terbalik": True, "koin": True, "palsu": True, "kupon": True}},
    ]
    aturan = f"""
- Setiap ronde semua pemain mendapat **gepokan uang yang sama**. Hitung totalnya secepat mungkin lalu **ketik jumlahnya**.
- Mode tumpukan: hanya lembar teratas yang terlihat. **Klik/ketuk lembarnya** untuk menggeser ke tumpukan "sudah dihitung"
  (bisa dikembalikan lagi kalau ragu). Mode sebar: semua lembar disebar di meja dan saling menumpuk.
- Jawaban benar: yang pertama **+{POIN_URUT[0]}**, kedua +{POIN_URUT[1]}, ketiga +{POIN_URUT[2]}, dan seterusnya.
  Jawaban salah: **{POIN_SALAH} poin** dan hukuman tunggu beberapa detik (maksimal {KESEMPATAN} kali salah per gepok).
- Tantangan (opsi host): uang **berantakan**, **terbalik**, campur **koin**, uang **palsu** (tanpa pita perak mengilap ✨,
  tidak dihitung), dan **kupon / uang mainan** (tidak dihitung).
- Waktu dan perhitungan berjalan di layar masing-masing, jadi koneksi lambat tidak merugikan.
"""
    format_aksi = '`{"jawab": 125000}` (jumlah rupiah) atau `"lewat"` (menyerah untuk gepok ini).'

    # ------------------------------------------------------------ util
    def cooldown(self, s, p, events):
        h = s["cfg"].get("hukuman_detik", 0)
        if h <= 0:
            return 0.0
        for e in events:
            if e.get("jenis") == "jawab" and e.get("pemain") == s["names"][p] and not e.get("benar") and not e.get("lewat") \
                    and not e.get("habis"):
                return float(h)
        return 0.0

    def _gepok(self, s, ronde):
        c = s["cfg"]
        r = rng(s, "gepok", ronde)
        pool = {"semua": KERTAS, "kecil": KERTAS[:4], "besar": KERTAS[3:]}[c["pecahan"]]
        items = []
        for i in range(c["lembar"]):
            roll = r.random()
            if c["koin"] and roll < 0.18:
                it = {"jenis": "koin", "nilai": r.choice(KOIN)}
            elif c["kupon"] and roll > 0.9:
                it = {"jenis": r.choice(["kupon", "mainan"]), "nilai": r.choice([10000, 20000, 50000, 100000])}
            else:
                it = {"jenis": "kertas", "nilai": r.choice(pool)}
                if c["palsu"] and r.random() < 0.12:
                    it["palsu"] = True
            if c["terbalik"] and it["jenis"] != "koin" and r.random() < 0.3:
                it["terbalik"] = True
            if c["berantakan"]:
                it["putar"] = round(r.uniform(-24, 24), 1)
                it["geser"] = [round(r.uniform(-0.12, 0.12), 3), round(r.uniform(-0.1, 0.1), 3)]
            else:
                it["putar"] = round(r.uniform(-2, 2), 1)
                it["geser"] = [0, 0]
            it["sebar"] = [round(r.uniform(0.05, 0.75), 3), round(r.uniform(0.05, 0.7), 3)]
            it["no"] = i
            items.append(it)
        return items

    @staticmethod
    def total(items: list[dict[str, Any]]) -> int:
        return sum(it["nilai"] for it in items if it["jenis"] in ("kertas", "koin") and not it.get("palsu"))

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * n, "riwayat": [],
             "benar_total": [0] * n, "salah_total": [0] * n}
        self._new_round(s)
        return s

    def _new_round(self, s):
        n = len(s["names"])
        s["gepok"] = self._gepok(s, s["ronde"])
        s["selesai"] = [False] * n
        s["salah"] = [0] * n
        s["urut"] = []
        s["poin_ronde"] = [0] * n
        s["jawaban"] = [[] for _ in range(n)]

    def pending(self, s):
        if self.over(s):
            return []
        return [i for i in range(len(s["names"])) if not s["selesai"][i]]

    # ------------------------------------------------------------ tampilan
    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        v = {"ronde": min(s["ronde"], c["ronde"]), "ronde_total": c["ronde"], "tampilan": c["tampilan"],
             "lembar": len(s["gepok"]), "skor": dict(zip(n, s["skor"])), "poin_ronde": dict(zip(n, s["poin_ronde"])),
             "status": {n[i]: {"selesai": s["selesai"][i], "salah": s["salah"][i],
                               "urutan": (s["urut"].index(i) + 1) if i in s["urut"] else None} for i in range(len(n))},
             "kesempatan": KESEMPATAN, "hukuman_detik": c["hukuman_detik"],
             "aturan_aktif": {k: c[k] for k in ("terbalik", "koin", "palsu", "kupon", "berantakan")},
             "riwayat": [dict(e) for e in s["riwayat"]]}
        if viewer is not None and not self.over(s):
            v["gepok"] = [dict(it) for it in s["gepok"]]
        if viewer == "semua" and not self.over(s):
            v["total"] = self.total(s["gepok"])
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        v = self._view(s, p)
        v["jawaban_saya"] = list(s["jawaban"][p])
        return {**v, "saya": p, "nama_saya": s["names"][p]}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if a is None or (isinstance(a, str) and a.strip().lower() in ("lewat", "menyerah")):
            return "lewat"
        if isinstance(a, dict):
            a = a.get("jawab")
        if isinstance(a, str):
            a = a.replace(".", "").replace(",", "").replace("Rp", "").replace("rp", "").strip()
        x = as_int(a, "jumlah uang")
        if x < 0 or x > 100_000_000:
            raise ActionError("jumlah uang tidak masuk akal")
        return x

    def default(self, s, p):
        return "lewat"

    def apply(self, s, actions):
        n = s["names"]
        events: list[dict[str, Any]] = []
        benar_total = self.total(s["gepok"])
        for p, a in sorted(actions.items()):
            if s["selesai"][p]:
                continue
            if a == "lewat":
                s["selesai"][p] = True
                events.append({"jenis": "jawab", "pemain": n[p], "lewat": True})
                continue
            s["jawaban"][p].append(a)
            if a == benar_total:
                s["selesai"][p] = True
                s["urut"].append(p)
                pts = POIN_URUT[min(len(s["urut"]) - 1, len(POIN_URUT) - 1)]
                s["skor"][p] += pts
                s["poin_ronde"][p] += pts
                s["benar_total"][p] += 1
                events.append({"jenis": "jawab", "pemain": n[p], "benar": True, "urutan": len(s["urut"]), "poin": pts})
            else:
                s["salah"][p] += 1
                s["salah_total"][p] += 1
                s["skor"][p] += POIN_SALAH
                s["poin_ronde"][p] += POIN_SALAH
                habis = s["salah"][p] >= KESEMPATAN
                if habis:
                    s["selesai"][p] = True
                events.append({"jenis": "jawab", "pemain": n[p], "benar": False, "poin": POIN_SALAH,
                               "sisa_kesempatan": KESEMPATAN - s["salah"][p], "habis": habis,
                               "arah": "kurang" if a < benar_total else "lebih"})
        if all(s["selesai"]):
            events += self._end_round(s)
        return events

    def _end_round(self, s):
        n = s["names"]
        g = s["gepok"]
        rinci: dict[str, int] = {}
        for it in g:
            if it["jenis"] in ("kertas", "koin") and not it.get("palsu"):
                key = f"{it['nilai']}"
                rinci[key] = rinci.get(key, 0) + 1
        entry = {"ronde": s["ronde"], "total": self.total(g), "rinci": rinci,
                 "abaikan": sum(1 for it in g if it.get("palsu") or it["jenis"] in ("kupon", "mainan")),
                 "urut": [n[i] for i in s["urut"]], "poin": dict(zip(n, s["poin_ronde"])),
                 "jawaban": {n[i]: list(s["jawaban"][i]) for i in range(len(n))}}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "ronde_selesai", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [float(b) - x for b, x in zip(s["benar_total"], s["salah_total"])]

    def reveal(self, s):
        return {"ronde": [{"ronde": e["ronde"], "total": e["total"]} for e in s["riwayat"]]}
