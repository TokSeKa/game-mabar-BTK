"""Poker Texas Hold'em no-limit untuk 2–8 kursi.

Dek setiap tangan diacak dari seed match. Hash seed diumumkan sejak awal dan seed-nya dibuka
di akhir, jadi siapa pun bisa memeriksa bahwa urutan kartu tidak diatur di tengah jalan.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from functools import lru_cache
from typing import Any

from ..bot.interpreter import LibFunction
from .base import ActionError, Game, Setting, as_int, rng

RANKS = "23456789TJQKA"
SUITS = "shdc"
DECK = [r + s for r in RANKS for s in SUITS]
RV = {r: i + 2 for i, r in enumerate(RANKS)}
KATEGORI = ["Kartu Tinggi", "Satu Pasang", "Dua Pasang", "Tiga Sejenis", "Straight", "Flush", "Full House",
            "Empat Sejenis", "Straight Flush"]
STREETS = ["preflop", "flop", "turn", "river"]
ALIAS = {"fold": "fold", "lipat": "fold", "check": "check", "cek": "check", "call": "call", "ikut": "call",
         "raise": "raise", "naik": "raise", "bet": "raise", "allin": "allin", "all-in": "allin", "all_in": "allin"}
CONTOH_AKSI = "'fold', 'check', 'call', 'allin', atau {'aksi': 'raise', 'ke': jumlah}"


# ---------------------------------------------------------------- evaluator
def _straight(rs: set[int]) -> int:
    if 14 in rs:
        rs = rs | {1}
    run = 0
    for v in range(14, 0, -1):
        run = run + 1 if v in rs else 0
        if run >= 5:
            return v + 4
    return 0


def evaluate(cards: list[str]) -> tuple[int, ...]:
    """Nilai tangan terbaik dari 2–7 kartu. Tuple lebih besar = tangan lebih kuat."""
    ranks = sorted((RV[c[0]] for c in cards), reverse=True)
    suits: dict[str, list[int]] = {}
    for c in cards:
        suits.setdefault(c[1], []).append(RV[c[0]])
    flush = next((sorted(v, reverse=True) for v in suits.values() if len(v) >= 5), None)
    if flush:
        sf = _straight(set(flush))
        if sf:
            return (8, sf)
    cnt = Counter(ranks)
    quads = sorted((r for r, c in cnt.items() if c == 4), reverse=True)
    trips = sorted((r for r, c in cnt.items() if c == 3), reverse=True)
    pairs = sorted((r for r, c in cnt.items() if c == 2), reverse=True)
    if quads:
        q = quads[0]
        return (7, q, max((r for r in ranks if r != q), default=0))
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        return (6, t, max(trips[1:] + pairs))
    if flush:
        return (5, *flush[:5])
    st = _straight(set(ranks))
    if st:
        return (4, st)
    if trips:
        t = trips[0]
        return (3, t, *[r for r in ranks if r != t][:2])
    if len(pairs) >= 2:
        a, b = pairs[:2]
        return (2, a, b, *[r for r in ranks if r not in (a, b)][:1])
    if pairs:
        a = pairs[0]
        return (1, a, *[r for r in ranks if r != a][:3])
    return (0, *ranks[:5])


def hand_name(v: tuple[int, ...]) -> str:
    if v[0] == 8 and v[1] == 14:
        return "Royal Flush"
    return KATEGORI[v[0]]


def preflop_strength(hole: list[str]) -> float:
    """Kekuatan dua kartu awal 0..1 (rumus Chen yang dinormalkan)."""
    a, b = sorted((RV[c[0]] for c in hole), reverse=True)
    pts = {14: 10, 13: 8, 12: 7, 11: 6}.get(a, a / 2)
    if a == b:
        pts = max(5, pts * 2)
    else:
        if hole[0][1] == hole[1][1]:
            pts += 2
        gap = a - b - 1
        pts -= [0, 1, 2, 4][gap] if gap < 4 else 5
        if gap <= 1 and a < 12:
            pts += 1
    return round(min(1.0, max(0.0, (pts + 1) / 21)), 3)


@lru_cache(maxsize=8192)
def equity(hole: tuple[str, ...], board: tuple[str, ...], opp: int, samples: int) -> float:
    """Peluang menang melawan ``opp`` tangan acak (Monte Carlo dengan seed dari kartu yang terlihat,
    jadi hasilnya selalu sama untuk input yang sama)."""
    raw = f"{','.join(hole)}|{','.join(board)}|{opp}|{samples}"
    g = random.Random(int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16))
    used = set(hole) | set(board)
    rest = [c for c in DECK if c not in used]
    need = 5 - len(board)
    score = 0.0
    for _ in range(samples):
        draw = g.sample(rest, need + 2 * opp)
        full = list(board) + draw[:need]
        mine = evaluate(list(hole) + full)
        best = max(evaluate(draw[need + 2 * k: need + 2 * k + 2] + full) for k in range(opp))
        if mine > best:
            score += 1
        elif mine == best:
            score += 0.5
    return score / samples


def _cards(v: Any, what: str = "kartu") -> list[str]:
    if not isinstance(v, (list, tuple)) or not all(isinstance(c, str) and c in DECK for c in v):
        raise ActionError(f"{what} harus list teks kartu seperti ['As', 'Td'] (angka 2-9 T J Q K A + s h d c)")
    if len(set(v)) != len(v):
        raise ActionError(f"{what} berisi kartu kembar")
    return list(v)


class Poker(Game):
    id = "poker"
    nama = "Poker Hold'em"
    ringkas = "Texas Hold'em no-limit untuk 2–8 orang. Dek diacak dari seed yang hash-nya diumumkan dulu dan dibuka di akhir."
    kategori = "giliran"
    min_pemain, max_pemain = 2, 8
    hint_aksi = CONTOH_AKSI
    timer = 25
    label_skor = "Chip"
    settings = [
        Setting("chip", "Chip awal", "int", 1000, 100, 100000),
        Setting("sb", "Small blind awal", "int", 10, 1, 10000, ket="Big blind = 2 × small blind."),
        Setting("naik_tiap", "Blind naik tiap (tangan)", "int", 10, 0, 100, ket="Blind dikali 1,5 setiap sekian tangan. 0 = tetap."),
        Setting("tangan_maks", "Batas tangan", "int", 40, 1, 300, ket="Berhenti setelah sekian tangan; peringkat menurut chip."),
    ]
    aturan = """
- Setiap pemain mulai dengan chip yang sama. Tiap **tangan**, semua mendapat 2 kartu tertutup; 5 kartu meja dibuka bertahap
  (*flop* 3 kartu, *turn* 1, *river* 1). Tangan terbaik dari 5 kartu (gabungan kartu sendiri + meja) menang.
- Urutan tangan: Straight Flush > Empat Sejenis > Full House > Flush > Straight > Tiga Sejenis > Dua Pasang > Satu Pasang > Kartu Tinggi.
  As boleh jadi kartu tertinggi atau terendah (A-2-3-4-5).
- Dua pemain di kiri dealer memasang *small blind* dan *big blind*. Lalu bergiliran: **fold** (menyerah), **check** (lewat kalau tidak ada taruhan),
  **call** (menyamakan taruhan), **raise** (menaikkan; minimal sebesar kenaikan terakhir atau big blind), **all-in** (semua chip).
- *No-limit*: boleh menaikkan sampai seluruh chip. Pemain yang all-in hanya bisa memenangkan bagian pot yang ia ikuti (*side pot*).
- Satu tangan selesai kalau tinggal satu pemain (yang lain fold) atau sampai *showdown* setelah river. Pot seri dibagi rata.
- Blind naik ×1,5 setiap beberapa tangan. Pemain yang chipnya habis tersingkir. Permainan selesai saat tinggal satu pemain
  atau batas tangan tercapai; peringkat menurut chip (yang tersingkir belakangan lebih tinggi).
- **Keadilan dek:** hash seed (`hash_dek`) diumumkan dari awal; seed dibuka di layar hasil supaya bisa dicek ulang.
- Waktu habis = check kalau bisa, kalau tidak fold.
"""
    format_aksi = """Salah satu:
- `"fold"`, `"check"`, `"call"`, `"allin"` (boleh juga `"lipat"`, `"cek"`, `"ikut"`)
- `{"aksi": "raise", "ke": 120}` = naikkan taruhanmu di jalan ini **menjadi** 120 (bukan menambah 120). Fungsi `naik(120)` membuat bentuk ini.
- Raise di bawah minimal dinaikkan otomatis ke minimal; raise melebihi chipmu dianggap all-in. `call` saat tidak ada taruhan dianggap `check`."""
    format_info = """```
{ "tangan": 3, "tangan_maks": 40, "sb": 10, "bb": 20, "dealer": "Budi", "hash_dek": "9f2c...",
  "jalan": "flop",                      # preflop | flop | turn | river | selesai
  "meja": ["Kh", "7d", "2c"],           # kartu meja (teks: angka 2-9 T J Q K A + s ♠ h ♥ d ♦ c ♣)
  "kartu_saya": ["As", "Kd"],
  "chip": {"Budi": 950, ...},           # chip di depan pemain (belum termasuk yang sudah masuk pot)
  "taruhan": {"Budi": 40, ...},         # taruhan di jalan ini
  "masuk": {"Budi": 60, ...},           # total yang sudah dimasukkan di tangan ini
  "status": {"Budi": "main" | "fold" | "allin" | "keluar"},
  "pot": 180, "taruhan_tertinggi": 40, "untuk_ikut": 20, "min_raise_ke": 60, "maks_raise_ke": 990,
  "aksi_valid": ["fold", "call", "raise", "allin"], "giliran": "Budi",
  "aksi_tangan": [ {"pemain": "Ani", "aksi": "raise", "jumlah": 40, "ke": 40, "jalan": "preflop"} ],
  "riwayat": [ {"no": 2, "meja": [...], "pot": 300, "menang": {"Ani": 300}, "showdown": {"Ani": {"kartu": [...], "tangan": "Flush"}}, "aksi": [...]} ] }
```"""
    lib_docs = [
        {"nama": "kartu_saya", "jenis": "fungsi", "tanda": "kartu_saya()", "ket": "Dua kartu tertutupmu, misalnya ['As', 'Kd']."},
        {"nama": "meja", "jenis": "fungsi", "tanda": "meja()", "ket": "Kartu meja yang sudah terbuka (0, 3, 4, atau 5 kartu)."},
        {"nama": "nilai_tangan", "jenis": "fungsi", "tanda": "nilai_tangan(kartu=None)", "ket": "Nilai tangan terbaik: {'kategori': 0-8, 'nama': 'Dua Pasang', 'skor': [...]}. Tanpa argumen = kartumu + meja. 'skor' bisa dibandingkan dengan < >."},
        {"nama": "kekuatan_awal", "jenis": "fungsi", "tanda": "kekuatan_awal(kartu=None)", "ket": "Kekuatan dua kartu awal 0..1 (AA = 1). Berguna sebelum flop."},
        {"nama": "ekuitas", "jenis": "fungsi", "tanda": "ekuitas(sampel=150)", "ket": "Perkiraan peluang menang 0..1 melawan semua lawan yang belum fold (simulasi tetap/deterministik). Mahal: ±300 langkah."},
        {"nama": "untuk_ikut", "jenis": "fungsi", "tanda": "untuk_ikut()", "ket": "Chip yang dibutuhkan untuk call sekarang (0 = boleh check)."},
        {"nama": "pot", "jenis": "fungsi", "tanda": "pot()", "ket": "Total chip di pot sekarang."},
        {"nama": "peluang_pot", "jenis": "fungsi", "tanda": "peluang_pot()", "ket": "untuk_ikut / (pot + untuk_ikut): ekuitas minimal supaya call menguntungkan."},
        {"nama": "aksi_valid", "jenis": "fungsi", "tanda": "aksi_valid()", "ket": "Aksi yang boleh sekarang, misalnya ['fold', 'call', 'raise', 'allin']."},
        {"nama": "min_raise", "jenis": "fungsi", "tanda": "min_raise()", "ket": "Taruhan minimal kalau mau raise (nilai 'ke')."},
        {"nama": "maks_raise", "jenis": "fungsi", "tanda": "maks_raise()", "ket": "Taruhan maksimal (= all-in)."},
        {"nama": "naik", "jenis": "fungsi", "tanda": "naik(ke)", "ket": "Membuat aksi raise: naik(100) sama dengan {'aksi': 'raise', 'ke': 100}."},
        {"nama": "lawan_aktif", "jenis": "fungsi", "tanda": "lawan_aktif()", "ket": "Nama lawan yang belum fold di tangan ini."},
    ]
    templates = [
        {"id": "karang", "nama": "Batu Karang", "ket": "Ketat: hanya main kartu awal kuat, lalu bertaruh kalau tangannya bagus.", "kode": '''def aksi():
    i = info()
    valid = aksi_valid()
    if i["jalan"] == "preflop":
        k = kekuatan_awal()
        if k >= 0.7 and "raise" in valid:
            return naik(min_raise() + i["bb"] * 2)
        if k >= 0.45 and untuk_ikut() <= i["bb"] * 3:
            return "call"
        return "check" if "check" in valid else "fold"
    t = nilai_tangan()
    if t["kategori"] >= 2 and "raise" in valid:
        return naik(min_raise() + pot() // 2)
    if t["kategori"] >= 1:
        return "call"
    return "check" if "check" in valid else "fold"
'''},
        {"id": "kalkulator", "nama": "Kalkulator Ekuitas", "ket": "Membandingkan peluang menang dengan harga call (pot odds).", "kode": '''def aksi():
    valid = aksi_valid()
    e = ekuitas(120)
    if e > 0.75 and "raise" in valid:
        return naik(min_raise() + pot())
    if e > 0.55 and "raise" in valid and untuk_ikut() == 0:
        return naik(min_raise() + pot() // 2)
    if "check" in valid:
        return "check"
    if e > peluang_pot() + 0.05:
        return "call"
    return "fold"
'''},
        {"id": "pemanggil", "nama": "Pemanggil Setia", "ket": "Hampir selalu call. Fold hanya kalau harganya lebih dari separuh chip.", "kode": '''def aksi():
    i = info()
    saya = nama_saya()
    if untuk_ikut() > i["chip"][saya] // 2 and kekuatan_awal() < 0.6:
        return "fold"
    return "call"
'''},
        {"id": "nekat", "nama": "Si Nekat", "ket": "Agresif: sering raise, all-in dengan tangan bagus.", "kode": '''def aksi():
    valid = aksi_valid()
    t = nilai_tangan()
    if t["kategori"] >= 3 or kekuatan_awal() >= 0.85:
        return "allin"
    if "raise" in valid and (kekuatan_awal() >= 0.5 or t["kategori"] >= 1):
        return naik(min_raise() * 2)
    return "check" if "check" in valid else "call" if untuk_ikut() <= info()["bb"] else "fold"
'''},
    ]

    # ------------------------------------------------------------ util
    def _alive(self, s):
        return [i for i, c in enumerate(s["chips"]) if c > 0]

    def _blinds(self, s):
        c = s["cfg"]
        lvl = (max(s["tangan"], 1) - 1) // c["naik_tiap"] if c["naik_tiap"] > 0 else 0
        sb = max(1, int(round(c["sb"] * (1.5 ** lvl))))
        return sb, sb * 2

    def _next(self, s, i, pred):
        n = len(s["names"])
        for k in range(1, n + 1):
            j = (i + k) % n
            if pred(j):
                return j
        return None

    def _live(self, s, j):
        h = s["h"]
        return j in h["in"] and not h["folded"][j] and not h["allin"][j]

    def _contenders(self, s):
        h = s["h"]
        return [j for j in h["in"] if not h["folded"][j]]

    def _needs(self, s, j):
        h = s["h"]
        if not self._live(s, j):
            return False
        if h["bet"][j] < h["cur"]:
            return True
        if h["acted"][j]:
            return False
        return any(k != j and not h["allin"][k] for k in self._contenders(s))

    def _put(self, s, p, amt):
        h = s["h"]
        amt = max(0, min(int(amt), s["chips"][p]))
        s["chips"][p] -= amt
        h["bet"][p] += amt
        h["total"][p] += amt
        if s["chips"][p] == 0:
            h["allin"][p] = True
        return amt

    # ------------------------------------------------------------ alur tangan
    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "chips": [cfg["chip"]] * n, "tangan": 0, "dealer": 0,
             "riwayat": [], "elim": {}, "selesai": False, "h": None, "arsip": [],
             "hash": hashlib.sha256(f"poker|{seed}".encode()).hexdigest()[:16]}
        s["dealer"] = rng(s, "dealer").randrange(n)
        self._start_hand(s, first=True)
        if not s["selesai"]:
            self._progress(s, s["h"]["bb_p"])
        return s

    def _start_hand(self, s, first=False):
        alive = self._alive(s)
        if len(alive) <= 1 or s["tangan"] >= s["cfg"]["tangan_maks"]:
            s["selesai"] = True
            return []
        s["tangan"] += 1
        n = len(s["names"])
        if not first or s["chips"][s["dealer"]] <= 0:
            s["dealer"] = self._next(s, s["dealer"], lambda j: s["chips"][j] > 0)
        d = s["dealer"]
        deck = DECK[:]
        rng(s, "dek", s["tangan"]).shuffle(deck)
        h = {"deck": deck, "hole": [None] * n, "board": [], "street": "preflop", "bet": [0] * n, "total": [0] * n,
             "folded": [j not in alive for j in range(n)], "allin": [False] * n, "acted": [False] * n,
             "can_raise": [True] * n, "cur": 0, "min_raise": 0, "to_act": None, "log": [], "in": alive,
             "start_chips": list(s["chips"])}
        s["h"] = h
        for j in alive:
            h["hole"][j] = [deck.pop(), deck.pop()]
        sb, bb = self._blinds(s)
        if len(alive) == 2:
            sbp = d
            bbp = self._next(s, d, lambda j: j in alive)
        else:
            sbp = self._next(s, d, lambda j: j in alive)
            bbp = self._next(s, sbp, lambda j: j in alive)
        h["sb_p"], h["bb_p"] = sbp, bbp
        for p, amt, label in ((sbp, sb, "small blind"), (bbp, bb, "big blind")):
            got = self._put(s, p, amt)
            h["log"].append({"pemain": s["names"][p], "aksi": label, "jumlah": got, "ke": h["bet"][p], "jalan": "preflop"})
        h["cur"] = max(h["bet"])
        h["min_raise"] = bb
        s["arsip"].append({"no": s["tangan"], "kartu": {s["names"][j]: h["hole"][j] for j in alive}})
        if len(s["arsip"]) > 300:
            del s["arsip"][0]
        return [{"jenis": "tangan_baru", "no": s["tangan"], "dealer": s["names"][d], "sb": sb, "bb": bb,
                 "small_blind": s["names"][sbp], "big_blind": s["names"][bbp]}]

    def _close_street(self, s):
        h = s["h"]
        n = len(s["names"])
        ev = []
        top = max(h["bet"])
        tops = [j for j in range(n) if h["bet"][j] == top]
        if top > 0 and len(tops) == 1:
            j = tops[0]
            second = max([h["bet"][k] for k in range(n) if k != j] or [0])
            back = top - second
            if back > 0:
                s["chips"][j] += back
                h["bet"][j] -= back
                h["total"][j] -= back
                h["allin"][j] = s["chips"][j] == 0
                ev.append({"jenis": "kembali", "pemain": s["names"][j], "jumlah": back})
        h["bet"] = [0] * n
        h["cur"] = 0
        h["min_raise"] = self._blinds(s)[1]
        h["acted"] = [False] * n
        h["can_raise"] = [True] * n
        return ev

    def _deal_street(self, s):
        h = s["h"]
        k = STREETS.index(h["street"]) + 1
        h["street"] = STREETS[k]
        h["deck"].pop()  # kartu dibakar
        new = [h["deck"].pop() for _ in range(3 if k == 1 else 1)]
        h["board"] += new
        return [{"jenis": "jalan", "jalan": h["street"], "kartu": new, "meja": list(h["board"])}]

    def _end_hand(self, s):
        h = s["h"]
        n = len(s["names"])
        names = s["names"]
        ev = self._close_street(s) if any(h["bet"]) else []
        cont = self._contenders(s)
        won = [0] * n
        showdown = None
        order = [(s["dealer"] + k) % n for k in range(1, n + 1)]
        if len(cont) == 1:
            won[cont[0]] = sum(h["total"])
        else:
            while h["street"] != "river":
                ev += self._deal_street(s)
            vals = {j: evaluate(h["hole"][j] + h["board"]) for j in cont}
            showdown = {names[j]: {"kartu": h["hole"][j], "tangan": hand_name(vals[j])} for j in cont}
            prev = 0
            for lv in sorted({h["total"][j] for j in range(n) if h["total"][j] > 0}):
                pot = sum(min(h["total"][j], lv) - min(h["total"][j], prev) for j in range(n))
                elig = [j for j in cont if h["total"][j] >= lv]
                prev = lv
                if pot <= 0:
                    continue
                if not elig:
                    best_total = max(h["total"][j] for j in cont)
                    elig = [j for j in cont if h["total"][j] == best_total]
                best = max(vals[j] for j in elig)
                wins = sorted((j for j in elig if vals[j] == best), key=order.index)
                share, rem = divmod(pot, len(wins))
                for k, j in enumerate(wins):
                    won[j] += share + (1 if k < rem else 0)
        for j in range(n):
            s["chips"][j] += won[j]
        total = sum(h["total"])
        sb, bb = self._blinds(s)
        entry = {"no": s["tangan"], "dealer": names[s["dealer"]], "blinds": [sb, bb], "meja": list(h["board"]), "pot": total,
                 "menang": {names[j]: won[j] for j in range(n) if won[j]}, "showdown": showdown, "aksi": h["log"][-60:]}
        s["riwayat"].append(entry)
        if len(s["riwayat"]) > 12:
            del s["riwayat"][0]
        out = []
        for j in h["in"]:
            if s["chips"][j] == 0 and str(j) not in s["elim"]:
                s["elim"][str(j)] = s["tangan"] * 10**7 + h["start_chips"][j]
                out.append(names[j])
        h["to_act"] = None
        ev.append({"jenis": "tangan_selesai", "no": s["tangan"], "pot": total, "menang": entry["menang"],
                   "showdown": showdown, "meja": list(h["board"]), "tersingkir": out})
        return ev

    def _progress(self, s, last):
        ev: list[dict[str, Any]] = []
        while not s["selesai"]:
            h = s["h"]
            if len(self._contenders(s)) <= 1:
                ev += self._end_hand(s)
                ev += self._start_hand(s)
                if s["selesai"]:
                    break
                last = s["h"]["bb_p"]
                continue
            nxt = self._next(s, last, lambda j: self._needs(s, j))
            if nxt is not None:
                h["to_act"] = nxt
                break
            ev += self._close_street(s)
            live = [j for j in self._contenders(s) if not h["allin"][j]]
            if h["street"] == "river" or len(live) <= 1:
                ev += self._end_hand(s)
                ev += self._start_hand(s)
                if s["selesai"]:
                    break
                last = s["h"]["bb_p"]
                continue
            ev += self._deal_street(s)
            last = s["dealer"]
        return ev

    # ------------------------------------------------------------ kontrak Game
    def pending(self, s):
        if s["selesai"] or s["h"] is None or s["h"]["to_act"] is None:
            return []
        return [s["h"]["to_act"]]

    def _valid(self, s, p):
        h = s["h"]
        if s["selesai"] or h is None or h["to_act"] != p or not self._live(s, p):
            return []
        owe = h["cur"] - h["bet"][p]
        out = ["fold", "check" if owe <= 0 else "call"]
        stack = s["chips"][p]
        if stack > owe and h["can_raise"][p]:
            out += ["raise", "allin"]
        elif stack <= owe:
            out.append("allin")
        return out

    def _raise_range(self, s, p):
        h = s["h"]
        hi = h["bet"][p] + s["chips"][p]
        lo = min(hi, h["cur"] + max(h["min_raise"], 1))
        return lo, hi

    def public(self, s):
        names, n = s["names"], len(s["names"])
        sb, bb = self._blinds(s)
        h = s["h"]
        out = {"tangan": s["tangan"], "tangan_maks": s["cfg"]["tangan_maks"], "sb": sb, "bb": bb,
               "chip": dict(zip(names, s["chips"])), "dealer": names[s["dealer"]], "hash_dek": s["hash"],
               "riwayat": s["riwayat"][-8:], "jalan": "selesai" if s["selesai"] else (h["street"] if h else "preflop")}
        if h is None:
            return {**out, "meja": [], "pot": 0, "taruhan": {}, "masuk": {}, "status": {}, "giliran": None,
                    "taruhan_tertinggi": 0, "aksi_tangan": []}
        status = {}
        for j in range(n):
            status[names[j]] = ("keluar" if j not in h["in"] else "fold" if h["folded"][j] else
                                "allin" if h["allin"][j] else "main")
        out.update({
            "meja": list(h["board"]), "pot": sum(h["total"]), "taruhan": {names[j]: h["bet"][j] for j in range(n)},
            "masuk": {names[j]: h["total"][j] for j in range(n)}, "status": status,
            "giliran": names[h["to_act"]] if h["to_act"] is not None and not s["selesai"] else None,
            "taruhan_tertinggi": h["cur"], "aksi_tangan": h["log"][-40:],
            "small_blind": names[h["sb_p"]], "big_blind": names[h["bb_p"]],
        })
        return out

    def observe(self, s, p):
        o = self.public(s)
        h = s["h"]
        hole = list(h["hole"][p] or []) if h else []
        owe = max(0, min(h["cur"] - h["bet"][p], s["chips"][p])) if h else 0
        lo, hi = self._raise_range(s, p) if h else (0, 0)
        o.update({"saya": p, "nama_saya": s["names"][p], "kartu_saya": hole, "untuk_ikut": owe,
                  "min_raise_ke": lo, "maks_raise_ke": hi, "aksi_valid": self._valid(s, p)})
        return o

    def validate(self, s, p, a):
        h = s["h"]
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            a = {"aksi": "raise", "ke": a}
        elif isinstance(a, (list, tuple)) and len(a) == 2:
            a = {"aksi": a[0], "ke": a[1]}
        elif isinstance(a, str):
            a = {"aksi": a}
        if not isinstance(a, dict):
            raise ActionError(f"aksi poker harus {CONTOH_AKSI}")
        kind = ALIAS.get(str(a.get("aksi", "")).strip().lower())
        if kind is None:
            raise ActionError(f"aksi tidak dikenal; pakai {CONTOH_AKSI}")
        stack, owe = s["chips"][p], h["cur"] - h["bet"][p]
        if kind == "fold":
            return {"aksi": "fold"}
        if kind == "check":
            if owe > 0:
                raise ActionError(f"tidak bisa check: ada taruhan {owe} yang harus di-call (atau fold)")
            return {"aksi": "check"}
        if kind == "call":
            return {"aksi": "check"} if owe <= 0 else {"aksi": "call"}
        lo, hi = self._raise_range(s, p)
        if stack <= owe or not h["can_raise"][p]:
            # tidak bisa menaikkan lagi: all-in/raise di sini berarti call
            return {"aksi": "check"} if owe <= 0 else {"aksi": "call"}
        if kind == "allin":
            return {"aksi": "raise", "ke": hi}
        to = as_int(a.get("ke", a.get("jumlah")), "jumlah raise ('ke')")
        return {"aksi": "raise", "ke": max(lo, min(hi, to))}

    def default(self, s, p):
        h = s["h"]
        return {"aksi": "check"} if h["cur"] - h["bet"][p] <= 0 else {"aksi": "fold"}

    def apply(self, s, actions):
        h = s["h"]
        p = h["to_act"]
        a = actions[p]
        kind = a["aksi"]
        names = s["names"]
        before = h["bet"][p]
        if kind == "fold":
            h["folded"][p] = True
        elif kind == "call":
            self._put(s, p, h["cur"] - h["bet"][p])
        elif kind == "raise":
            to = min(a["ke"], h["bet"][p] + s["chips"][p])
            self._put(s, p, to - h["bet"][p])
            inc = h["bet"][p] - h["cur"]
            if inc >= h["min_raise"]:
                h["min_raise"] = inc
                for j in h["in"]:
                    if j != p:
                        h["acted"][j] = False
                        h["can_raise"][j] = True
            elif inc > 0:
                for j in h["in"]:
                    if j != p and h["acted"][j]:
                        h["acted"][j] = False
                        h["can_raise"][j] = False
            h["cur"] = max(h["cur"], h["bet"][p])
        h["acted"][p] = True
        label = "allin" if h["allin"][p] and kind in ("call", "raise") else kind
        entry = {"pemain": names[p], "aksi": label, "jumlah": h["bet"][p] - before, "ke": h["bet"][p], "jalan": h["street"]}
        h["log"].append(entry)
        return [{"jenis": "aksi", **entry}] + self._progress(s, p)

    def over(self, s):
        return s["selesai"]

    def scores(self, s):
        return [float(c) for c in s["chips"]]

    def tiebreak(self, s):
        return [float(10**12) if c > 0 else float(s["elim"].get(str(i), 0)) for i, c in enumerate(s["chips"])]

    def reveal(self, s):
        return {"seed": str(s["seed"]), "hash_dek": s["hash"], "cara_cek": "sha256('poker|' + seed)[:16] harus sama dengan hash_dek",
                "kartu_semua": s["arsip"][-60:]}

    # ------------------------------------------------------------ library bot
    def bot_library(self, s, p, obs):
        h = s["h"]
        hole = list(h["hole"][p] or []) if h else []
        board = list(h["board"]) if h else []
        opp = max(1, len([j for j in self._contenders(s) if j != p])) if h else 1

        def nilai_tangan(kartu=None):
            cs = hole + board if kartu is None else _cards(kartu)
            if len(cs) < 1:
                raise ActionError("butuh minimal 1 kartu")
            v = evaluate(cs)
            return {"kategori": v[0], "nama": hand_name(v), "skor": list(v)}

        def kekuatan_awal(kartu=None):
            cs = hole if kartu is None else _cards(kartu)
            if len(cs) != 2:
                raise ActionError("kekuatan_awal butuh tepat 2 kartu")
            return preflop_strength(cs)

        def ekuitas(sampel=150):
            if len(hole) != 2:
                return 0.0
            k = max(20, min(400, as_int(sampel, "sampel")))
            return round(equity(tuple(hole), tuple(board), min(opp, 7), k), 4)

        def untuk_ikut():
            return obs["untuk_ikut"]

        def pot():
            return obs["pot"]

        def peluang_pot():
            c = obs["untuk_ikut"]
            return round(c / (obs["pot"] + c), 4) if c > 0 else 0.0

        def naik(ke):
            return {"aksi": "raise", "ke": as_int(ke, "jumlah raise")}

        def lawan_aktif():
            return [s["names"][j] for j in self._contenders(s) if j != p] if h else []

        return {"kartu_saya": lambda: list(hole), "meja": lambda: list(board), "nilai_tangan": nilai_tangan,
                "kekuatan_awal": kekuatan_awal, "ekuitas": LibFunction("ekuitas", ekuitas, 300),
                "untuk_ikut": untuk_ikut, "pot": pot, "peluang_pot": peluang_pot,
                "aksi_valid": lambda: list(obs["aksi_valid"]), "min_raise": lambda: obs["min_raise_ke"],
                "maks_raise": lambda: obs["maks_raise_ke"], "naik": naik, "lawan_aktif": lawan_aktif}
