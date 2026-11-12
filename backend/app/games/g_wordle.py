"""Wordle Mabar: tebak kata 5 huruf bahasa Indonesia bareng-bareng.

Mode:
- **Balapan** (real-time, sendiri-sendiri): semua menebak kata yang sama di papan masing-masing secepat mungkin.
- **Serentak**: papan masing-masing, tapi semua menebak satu kata di setiap langkah (adil untuk yang mengetik lambat).
- **Bergiliran**: satu papan bersama, pemain menebak bergantian; yang menebak benar dapat poin.

Opsi: papan lawan (warna saja / huruf & warna / tidak terlihat), mode sulit, kata di luar kamus (ditolak / memakan
baris = anti spam / bebas), bonus tercepat, dan *kata licik* (jawaban belum ditentukan dan selalu menghindar).
Kata jawaban diambil dari seed match; bot tidak punya keacakan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import ActionError, Game, Setting, rng

DATA = Path(__file__).parent / "data"
PANJANG = 5
LEWAT = "-"
HIJAU = "H" * PANJANG
POIN_GANTIAN = 5
BONUS_CEPAT = [3, 2, 1]


def _load(name: str) -> list[str]:
    out = []
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        w = line.strip().lower()
        if w and not w.startswith("#"):
            out.append(w)
    return out


JAWABAN: list[str] = sorted(set(_load("kata5_jawaban.txt")))
KAMUS: frozenset[str] = frozenset(_load("kata5_kamus.txt")) | frozenset(JAWABAN)


def warna(tebakan: str, jawaban: str) -> str:
    """'H' hijau (huruf & posisi benar), 'K' kuning (huruf ada di posisi lain), 'A' abu-abu (tidak ada lagi).
    Huruf kembar dihitung seperti Wordle asli: kuning hanya sebanyak sisa huruf itu di jawaban."""
    res = ["A"] * PANJANG
    sisa: dict[str, int] = {}
    for i, (t, j) in enumerate(zip(tebakan, jawaban)):
        if t == j:
            res[i] = "H"
        else:
            sisa[j] = sisa.get(j, 0) + 1
    for i, t in enumerate(tebakan):
        if res[i] == "A" and sisa.get(t, 0) > 0:
            res[i] = "K"
            sisa[t] -= 1
    return "".join(res)


def cocok_dengan(rows: list[dict[str, Any]], kata: str) -> bool:
    """True kalau ``kata`` bisa jadi jawaban menurut semua petunjuk di ``rows``."""
    for r in rows:
        if r.get("kata") and r.get("warna") and r["warna"] != "?" * PANJANG:
            if warna(r["kata"], kata) != r["warna"]:
                return False
    return True


def _licik(cands: list[str], tebakan: str) -> tuple[str, list[str]]:
    """Kata licik: pilih petunjuk yang menyisakan kandidat terbanyak (seri: lebih sedikit hijau, lalu lebih sedikit kuning,
    lalu urutan pola). Hijau semua hanya kalau memang tinggal kata itu."""
    groups: dict[str, list[str]] = {}
    for c in cands:
        groups.setdefault(warna(tebakan, c), []).append(c)
    best = min(groups, key=lambda pat: (-len(groups[pat]), pat == HIJAU, pat.count("H"), pat.count("K"), pat))
    return best, groups[best]


class WordleMabar(Game):
    id = "wordle"
    nama = "Wordle Mabar"
    ringkas = "Tebak kata 5 huruf bahasa Indonesia bareng-bareng: balapan siapa paling cepat, serentak, atau bergiliran di satu papan."
    kategori = "simultan"
    min_pemain = 1
    max_pemain = 8
    hint_aksi = "kata 5 huruf, misalnya \"rumah\" (atau None untuk melewati)"
    timer = 45
    jeda_pada, jeda_hasil = ("kata",), 6
    label_skor = "Poin"
    settings = [
        Setting("mode", "Mode", "pilihan", "balapan",
                pilihan=[["balapan", "Balapan: papan masing-masing, real-time, siapa paling cepat"],
                         ["serentak", "Serentak: papan masing-masing, semua menebak di setiap langkah"],
                         ["gantian", "Bergiliran: satu papan bersama, menebak bergantian"]]),
        Setting("ronde", "Jumlah kata", "int", 3, 1, 10),
        Setting("maks_tebakan", "Maksimal tebakan per kata", "int", 6, 3, 12,
                ket="Di mode bergiliran ini jumlah baris papan bersama (boleh lebih banyak kalau pemainnya banyak)."),
        Setting("bot_detik", "Waktu berpikir bot di mode balapan (detik)", "int", 12, 1, 60, jika={"mode": "balapan"},
                ket="Bot menebak paling cepat sekali tiap sekian detik, supaya balapan melawan manusia tetap seru."),
        Setting("info_lawan", "Papan lawan", "pilihan", "warna", grup="informasi",
                pilihan=[["warna", "Warna saja (huruf lawan rahasia)"], ["semua", "Huruf dan warna"],
                         ["tidak", "Tidak terlihat (hanya jumlah tebakan)"]],
                jika={"mode": ["balapan", "serentak"]},
                ket="Setelah satu kata selesai, semua papan dibuka."),
        Setting("mode_sulit", "Mode sulit", "bool", False, grup="aturan",
                ket="Huruf hijau harus tetap di tempatnya dan huruf kuning wajib dipakai lagi di tebakan berikutnya."),
        Setting("kata_asal", "Kata di luar kamus", "pilihan", "tolak", grup="aturan",
                pilihan=[["tolak", "Ditolak (tidak memakan baris)"], ["hangus", "Memakan satu baris tanpa petunjuk (anti spam)"],
                         ["bebas", "Diterima seperti kata biasa"]]),
        Setting("bonus_cepat", "Bonus tercepat", "bool", True, grup="aturan", jika={"mode": "balapan"},
                ket="Yang pertama, kedua, dan ketiga menebak benar dapat +3, +2, +1."),
        Setting("hukuman_detik", "Hukuman tebakan salah (detik)", "int", 3, 0, 15, grup="aturan", jika={"mode": "balapan"},
                ket="Anti spam: setelah tebakan yang salah kamu harus menunggu sekian detik sebelum boleh menebak lagi. "
                    "Kata yang ditolak kamus tidak kena hukuman (dan tidak memakan baris). 0 = tanpa hukuman."),
        Setting("licik", "Kata licik", "bool", False, grup="kejutan",
                ket="Jawaban belum ditentukan: setiap tebakan dijawab dengan petunjuk yang menyisakan kata paling banyak "
                    "(gaya Absurdle). Kata baru 'terkunci' kalau tinggal satu kemungkinan. Paling sulit!"),
    ]
    presets = [
        {"id": "santai", "nama": "Santai", "ket": "Papan lawan terlihat lengkap: bisa saling mencontek dan berlomba.",
         "nilai": {"info_lawan": "semua"}},
        {"id": "kabut", "nama": "Kabut", "ket": "Papan lawan tidak terlihat sama sekali, kata asal memakan baris.",
         "nilai": {"info_lawan": "tidak", "kata_asal": "hangus"}},
        {"id": "neraka", "nama": "Neraka", "ket": "Mode sulit + kata licik + kata asal memakan baris.",
         "nilai": {"mode_sulit": True, "licik": True, "kata_asal": "hangus"}},
    ]
    aturan = """
- Tebak kata rahasia **5 huruf bahasa Indonesia**. Setiap tebakan diberi warna:
  🟩 **hijau** = huruf benar di posisi benar, 🟨 **kuning** = huruf ada di kata tapi posisinya lain, ⬜ **abu-abu** = huruf tidak ada
  (huruf kembar dihitung seperti Wordle asli).
- Tebakan harus kata yang ada di kamus (kecuali host mengatur lain). Satu match berisi beberapa kata (default 3).
- **Mode Balapan** (default): semua menebak kata yang sama di papan masing-masing, **real-time**. Menebak benar di tebakan ke-*k*
  memberi **(maksimal tebakan + 1 − k)** poin, ditambah **bonus tercepat** +3 / +2 / +1 untuk tiga orang pertama.
  Asal menebak cepat-cepat itu rugi: setiap baris yang terpakai mengurangi poin, kalau baris habis poinnya 0, dan setelah
  tebakan salah kamu **harus menunggu 3 detik** (hukuman anti spam, bisa diatur host) sebelum boleh menebak lagi.
- **Mode Serentak**: sama, tapi di setiap langkah semua pemain mengirim satu tebakan bersamaan (tanpa bonus tercepat).
- **Mode Bergiliran**: satu papan bersama, pemain menebak bergantian. Yang menebak benar dapat **+5**, dan tebakan yang
  membuka huruf hijau baru dapat **+1** (tapi hati-hati: petunjukmu juga membantu pemain berikutnya!).
- Waktu habis: di mode balapan/serentak baris itu hangus (kecuali kata yang sudah kamu ketik lengkap dikirim otomatis),
  di mode bergiliran giliranmu dilewati.
- Opsi host: **papan lawan** (warna saja / huruf & warna / tidak terlihat), **mode sulit**, **kata di luar kamus** (ditolak /
  memakan satu baris / bebas), **hukuman tebakan salah**, **kata licik** (jawaban terus menghindar), jumlah kata, dan maksimal
  tebakan.
- Setelah satu kata selesai (semua menebak benar atau barisnya habis), jawabannya dan semua papan dibuka.
"""
    format_aksi = """Teks kata 5 huruf, misalnya `"rumah"` (huruf besar/kecil sama saja). `None` atau `"lewati"` = lewati
(di mode bergiliran giliran dilewati, di mode lain memakan satu baris)."""
    format_info = """```
{ "mode": "balapan", "ronde": 1, "ronde_total": 3, "maks_tebakan": 6, "panjang": 5,
  "mode_sulit": False, "kata_asal": "tolak", "licik": False, "info_lawan": "warna", "hukuman_detik": 3,
  "skor": {"Budi": 7, ...}, "tebakan_total": {"Budi": 9, ...},
  "papan": {"Budi": {"baris": [{"kata": "tanah", "warna": "AHAKA"}, ...], "selesai": False, "menang": False}, ...},
  "bersama": [ {"pemain": "Budi", "kata": "tanah", "warna": "AHAKA"} ],    # mode bergiliran
  "giliran": "Budi",                                                      # mode bergiliran
  "urut_selesai": ["Ani"],                                                # yang sudah menebak benar (urut)
  "riwayat": [ {"ronde": 1, "jawaban": "rumah", "hasil": {"Budi": {"tebakan": 4, "menang": True, "poin": 5}}, ...} ] }
```
- `warna`: `H` hijau, `K` kuning, `A` abu-abu. Baris yang hangus/dilewati: `"kata": None`, `"warna": None`, `"lewat": True`.
  Baris kata asal (opsi *memakan baris*): `"warna": "?????"`.
- Papan lawan: tergantung *papan lawan*, `kata` lawan berisi `None` (warna saja) atau `warna` juga `None` (tidak terlihat).
  Papanmu sendiri selalu lengkap."""
    lib_docs = [
        {"nama": "kandidat", "jenis": "fungsi", "tanda": "kandidat()", "ket": "Semua kata jawaban (urut abjad) yang masih cocok dengan petunjuk di papanmu (mode bergiliran: papan bersama)."},
        {"nama": "cocok", "jenis": "fungsi", "tanda": "cocok(kata)", "ket": "True kalau kata itu masih mungkin jadi jawaban menurut petunjuk di papanmu."},
        {"nama": "warna", "jenis": "fungsi", "tanda": "warna(tebakan, jawaban)", "ket": "Pola warna kalau `tebakan` ditebak dan jawabannya `jawaban`, misalnya \"HKAAA\"."},
        {"nama": "di_kamus", "jenis": "fungsi", "tanda": "di_kamus(kata)", "ket": "True kalau kata itu ada di kamus tebakan."},
        {"nama": "nilai_info", "jenis": "fungsi", "tanda": "nilai_info(kata)", "ket": "Berapa banyak pola warna berbeda yang dihasilkan `kata` terhadap kandidat sekarang (makin besar makin informatif). Mahal: pakai kalau kandidat sudah sedikit (≤ 150)."},
        {"nama": "baris_saya", "jenis": "fungsi", "tanda": "baris_saya()", "ket": "Daftar tebakanmu untuk kata ini (mode bergiliran: papan bersama): [{'kata', 'warna'}, ...]."},
    ]
    templates = [
        {"id": "kandidat_pertama", "nama": "Kandidat Pertama", "ket": "Selalu menebak kandidat pertama menurut abjad (setelah pembuka 'teras').", "kode": '''def aksi():
    if not baris_saya():
        return "teras"
    k = kandidat()
    if not k:
        return "rumah"
    return k[0]
'''},
        {"id": "pemburu_info", "nama": "Pemburu Info", "ket": "Dua pembuka tetap untuk menyapu huruf umum, lalu memilih kandidat yang paling memecah kemungkinan.", "kode": '''def aksi():
    b = [x for x in baris_saya() if x["kata"] != None]
    k = kandidat()
    if len(k) == 1:
        return k[0]
    if len(b) == 0:
        return "kartu"
    if len(b) == 1 and len(k) > 40 and not info()["mode_sulit"]:
        return "selip"
    if not k:
        return "nasib"
    if len(k) > 150:
        return k[len(k) // 2]
    terbaik = k[0]
    nilai = -1
    for kata in k:
        v = nilai_info(kata)
        if v > nilai:
            terbaik = kata
            nilai = v
    return terbaik
'''},
        {"id": "kandidat_tengah", "nama": "Kandidat Tengah", "ket": "Menebak kandidat di tengah daftar (beda dari bot lain, jadi di mode bergiliran tidak saling meniru).", "kode": '''def aksi():
    if not baris_saya():
        return "kapal"
    k = kandidat()
    if not k:
        return "tanah"
    return k[(len(k) + saya()) // 2 % len(k)]
'''},
        {"id": "huruf_umum", "nama": "Huruf Umum", "ket": "Memilih kandidat yang hurufnya paling sering muncul di kandidat lain (heuristik Wordle klasik).", "kode": '''def aksi():
    k = kandidat()
    if not k:
        return "sinar"
    if not baris_saya():
        return "sinar"
    if len(k) > 250:
        return k[0]
    hit = {}
    for kata in k:
        for h in kata:
            hit[h] = hit.get(h, 0) + 1
    terbaik = k[0]
    nilai = -1
    for kata in k:
        unik = []
        for h in kata:
            if h not in unik:
                unik.append(h)
        v = sum(hit[h] for h in unik)
        if v > nilai:
            terbaik = kata
            nilai = v
    return terbaik
'''},
    ]

    # ------------------------------------------------------------ util
    def is_mandiri(self, cfg):
        return cfg.get("mode") == "balapan"

    def jeda_bot(self, cfg):
        return float(cfg.get("bot_detik", 12)) if cfg.get("mode") == "balapan" else 0.0

    def cooldown(self, s, p, events):
        """Balapan: tebakan salah (bukan lewat, bukan benar) membuat pemain menunggu ``hukuman_detik``."""
        c = s["cfg"]
        if c.get("mode") != "balapan" or c.get("hukuman_detik", 0) <= 0:
            return 0.0
        for e in events:
            if e.get("jenis") == "tebak" and e.get("pemain") == s["names"][p] and not e.get("lewat") and e.get("warna") != HIJAU:
                return float(c["hukuman_detik"])
        return 0.0

    def _gantian(self, s):
        return s["cfg"]["mode"] == "gantian"

    def _new_round(self, s):
        n = len(s["names"])
        s["papan"] = [[] for _ in range(n)]
        s["bersama"] = []
        s["selesai"] = [False] * n
        s["menang"] = [False] * n
        s["urut"] = []
        s["poin_ronde"] = [0] * n
        s["tebak_ronde"] = [0] * n
        s["hijau"] = [False] * PANJANG
        if s["cfg"]["licik"]:
            # kumpulan kata licik diacak dari seed tiap ronde (60% kata jawaban), supaya tiap kata terasa berbeda
            pool = sorted(rng(s, "licik", s["ronde"]).sample(JAWABAN, max(50, len(JAWABAN) * 3 // 5)))
            s["kandidat"] = [list(pool) for _ in range(n)] if not self._gantian(s) else [list(pool)]
        s["giliran"] = s["mulai"] % n

    def init(self, cfg, names, seed):
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * len(names),
             "tebakan_total": [0] * len(names), "riwayat": [], "mulai": 0}
        s["kata"] = rng(s, "kata").sample(JAWABAN, cfg["ronde"])
        self._new_round(s)
        return s

    def pending(self, s):
        if self.over(s):
            return []
        if self._gantian(s):
            return [s["giliran"]]
        return [i for i in range(len(s["names"])) if not s["selesai"][i]]

    def _rows_for(self, s, p):
        return s["bersama"] if self._gantian(s) else s["papan"][p]

    # ------------------------------------------------------------ tampilan
    def _row_view(self, r, show_kata, show_warna):
        return {"kata": r.get("kata") if show_kata else None, "warna": r.get("warna") if show_warna else None,
                "lewat": bool(r.get("lewat")), "asal": bool(r.get("asal"))}

    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        mode = c["mode"]
        info = c.get("info_lawan", "warna")
        papan = {}
        for i, nm in enumerate(n):
            mine = viewer == "semua" or viewer == i or info == "semua"
            show_w = mine or info == "warna"
            papan[nm] = {"baris": [self._row_view(r, mine, show_w) for r in s["papan"][i]],
                         "selesai": s["selesai"][i], "menang": s["menang"][i]}
        r = min(s["ronde"], c["ronde"])
        return {"mode": mode, "ronde": r, "ronde_total": c["ronde"], "maks_tebakan": c["maks_tebakan"], "panjang": PANJANG,
                "mode_sulit": c["mode_sulit"], "kata_asal": c["kata_asal"], "licik": c["licik"], "info_lawan": info,
                "bonus_cepat": bool(c.get("bonus_cepat")) and mode == "balapan",
                "hukuman_detik": c.get("hukuman_detik", 0) if mode == "balapan" else 0,
                "skor": dict(zip(n, s["skor"])), "tebakan_total": dict(zip(n, s["tebakan_total"])),
                "papan": papan if mode != "gantian" else {},
                "bersama": [dict(x) for x in s["bersama"]] if mode == "gantian" else [],
                "giliran": n[s["giliran"]] if mode == "gantian" and not self.over(s) else None,
                "urut_selesai": [n[i] for i in s["urut"]],
                "jawaban": (s["kata"][r - 1] if not c["licik"] else None) if viewer == "semua" and not self.over(s) else None,
                "riwayat": [dict(e) for e in s["riwayat"]]}

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def event_for(self, s, e, viewer):
        if e.get("jenis") != "tebak" or e.get("bersama"):
            return e
        info = s["cfg"].get("info_lawan", "warna")
        if viewer == "semua" or info == "semua" or (isinstance(viewer, int) and s["names"][viewer] == e["pemain"]):
            return e
        if info == "warna":
            return {**e, "kata": None}
        return {**e, "kata": None, "warna": None}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if a is None or (isinstance(a, str) and a.strip().lower() in ("", LEWAT, "lewati", "pass", "skip")):
            return LEWAT
        if not isinstance(a, str):
            raise ActionError("kirim kata 5 huruf, misalnya \"rumah\"")
        w = a.strip().lower()
        if len(w) != PANJANG or not all("a" <= ch <= "z" for ch in w):
            raise ActionError(f"tebakan harus {PANJANG} huruf a-z (tanpa spasi atau angka)")
        c = s["cfg"]
        if w not in KAMUS and c["kata_asal"] == "tolak":
            raise ActionError(f"'{w}' tidak ada di kamus")
        if c["mode_sulit"]:
            self._check_hard(self._rows_for(s, p), w)
        return w

    @staticmethod
    def _check_hard(rows, w):
        for r in rows:
            if not r.get("kata") or not r.get("warna") or r.get("asal"):
                continue
            need: dict[str, int] = {}
            for i, (ch, col) in enumerate(zip(r["kata"], r["warna"])):
                if col == "H" and w[i] != ch:
                    raise ActionError(f"mode sulit: huruf ke-{i + 1} harus '{ch.upper()}'")
                if col in "HK":
                    need[ch] = need.get(ch, 0) + 1
            for ch, k in need.items():
                if w.count(ch) < k:
                    raise ActionError(f"mode sulit: tebakan harus memuat '{ch.upper()}'" + (f" {k}×" if k > 1 else ""))

    def default(self, s, p):
        return LEWAT

    def _judge(self, s, board, w):
        """Pola warna untuk tebakan ``w`` di papan ``board`` (indeks pemain, atau 0 untuk papan bersama)."""
        c = s["cfg"]
        if w not in KAMUS and c["kata_asal"] == "hangus":
            return "?" * PANJANG
        if c["licik"]:
            pat, rest = _licik(s["kandidat"][board], w)
            s["kandidat"][board] = rest
            return pat
        return warna(w, s["kata"][s["ronde"] - 1])

    def apply(self, s, actions):
        n = s["names"]
        c = s["cfg"]
        maks = c["maks_tebakan"]
        events: list[dict[str, Any]] = []
        if self._gantian(s):
            (p, w), = actions.items()
            if w == LEWAT:
                events.append({"jenis": "lewat", "pemain": n[p]})
                s["giliran"] = (p + 1) % len(n)
                return events
            pat = self._judge(s, 0, w)
            baru = [i for i, col in enumerate(pat) if col == "H" and not s["hijau"][i]]
            for i in baru:
                s["hijau"][i] = True
            row = {"pemain": n[p], "kata": w, "warna": pat, "asal": pat == "?" * PANJANG}
            s["bersama"].append(row)
            s["tebakan_total"][p] += 1
            s["tebak_ronde"][p] += 1
            if baru and pat != HIJAU:
                s["skor"][p] += 1
                s["poin_ronde"][p] += 1
            events.append({"jenis": "tebak", "bersama": True, "pemain": n[p], "kata": w, "warna": pat,
                           "baris": len(s["bersama"]), "bantu": bool(baru) and pat != HIJAU})
            if pat == HIJAU:
                s["skor"][p] += POIN_GANTIAN
                s["poin_ronde"][p] += POIN_GANTIAN
                s["menang"][p] = True
                s["urut"].append(p)
                events += self._end_round(s)
            elif len(s["bersama"]) >= maks:
                events += self._end_round(s)
            else:
                s["giliran"] = (p + 1) % len(n)
            return events
        for p in sorted(actions):
            if s["selesai"][p]:
                continue
            w = actions[p]
            if w == LEWAT:
                row = {"kata": None, "warna": None, "lewat": True}
                pat = None
            else:
                pat = self._judge(s, p, w)
                row = {"kata": w, "warna": pat, "asal": pat == "?" * PANJANG}
            s["papan"][p].append(row)
            s["tebakan_total"][p] += 1
            s["tebak_ronde"][p] += 1
            k = len(s["papan"][p])
            events.append({"jenis": "tebak", "pemain": n[p], "kata": row["kata"], "warna": pat, "baris": k,
                           "lewat": w == LEWAT})
            if pat == HIJAU:
                s["selesai"][p] = s["menang"][p] = True
                pts = maks + 1 - k
                if c["mode"] == "balapan" and c.get("bonus_cepat") and len(s["urut"]) < len(BONUS_CEPAT):
                    pts += BONUS_CEPAT[len(s["urut"])]
                s["urut"].append(p)
                s["skor"][p] += pts
                s["poin_ronde"][p] += pts
                events.append({"jenis": "benar", "pemain": n[p], "baris": k, "poin": pts, "urutan": len(s["urut"])})
            elif k >= maks:
                s["selesai"][p] = True
        if all(s["selesai"]):
            events += self._end_round(s)
        return events

    def _final_word(self, s, board):
        c = s["cfg"]
        if not c["licik"]:
            return s["kata"][s["ronde"] - 1]
        cands = s["kandidat"][board]
        return cands[0] if cands else "?????"

    def _end_round(self, s):
        n = s["names"]
        gantian = self._gantian(s)
        jawab = self._final_word(s, 0) if gantian or not s["cfg"]["licik"] else None
        per = None if jawab else {n[i]: self._final_word(s, i) for i in range(len(n))}
        entry = {"ronde": s["ronde"], "jawaban": jawab, "jawaban_pemain": per,
                 "hasil": {n[i]: {"tebakan": s["tebak_ronde"][i], "menang": s["menang"][i], "poin": s["poin_ronde"][i]}
                           for i in range(len(n))},
                 "urut": [n[i] for i in s["urut"]],
                 "papan": ({"bersama": [dict(x) for x in s["bersama"]]} if gantian
                           else {n[i]: [dict(x) for x in s["papan"][i]] for i in range(len(n))})}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        s["mulai"] += 1
        if not self.over(s):
            self._new_round(s)
        return [{"jenis": "kata", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [-float(x) for x in s["tebakan_total"]]

    def reveal(self, s):
        return {"kata": [e["jawaban"] or e["jawaban_pemain"] for e in s["riwayat"]]}

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        rows = [r for r in (obs["bersama"] if obs["mode"] == "gantian" else obs["papan"][s["names"][p]]["baris"])]
        cache: dict[str, list[str]] = {}

        def kandidat():
            if "k" not in cache:
                cache["k"] = [w for w in JAWABAN if cocok_dengan(rows, w)]
            return list(cache["k"])

        def cocok(kata):
            return isinstance(kata, str) and cocok_dengan(rows, kata.strip().lower())

        def _warna(tebakan, jawaban):
            t, j = str(tebakan).strip().lower(), str(jawaban).strip().lower()
            if len(t) != PANJANG or len(j) != PANJANG:
                raise ActionError(f"warna() butuh dua kata {PANJANG} huruf")
            return warna(t, j)

        def di_kamus(kata):
            return isinstance(kata, str) and kata.strip().lower() in KAMUS

        def nilai_info(kata):
            k = kandidat()
            if len(k) > 150:
                raise ActionError("nilai_info() hanya untuk kandidat ≤ 150 (terlalu mahal)")
            t = str(kata).strip().lower()
            return len({warna(t, x) for x in k})

        def baris_saya():
            return [{"kata": r.get("kata"), "warna": r.get("warna")} for r in rows]

        return {"kandidat": kandidat, "cocok": cocok, "warna": _warna, "di_kamus": di_kamus,
                "nilai_info": nilai_info, "baris_saya": baris_saya}
