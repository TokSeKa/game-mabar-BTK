"""Suit Live: aturan Suit Bot Arena, tapi kursinya boleh manusia (pilih tiap ronde) atau bot."""

from __future__ import annotations

from typing import Any

from ..bot.library import LIBRARY_DOCS, RoundView, make_library
from ..bot.templates import TEMPLATES
from ..engine.events import EVENTS, apply_event, event_info, hide_choices, resolve_event
from ..engine.rules import DIKALAHKAN_OLEH, SENJATA, resolve_round
from .base import ActionError, Game, Setting, rng

# kejutan per ronde (diumumkan di awal ronde, diambil dari seed)
KEJUTAN = {"ganda": "Ronde Ganda: HP yang hilang ×2", "terbalik": "Ronde Terbalik: urutan menang dibalik (batu kalah dari gunting)",
           "terlarang": "Senjata Terlarang"}
# urutan terbalik = tukar gunting & kertas lalu pakai aturan biasa (permutasi ini kebalikannya sendiri)
BALIK = {"batu": "batu", "gunting": "kertas", "kertas": "gunting"}


class SuitLive(Game):
    id = "suit"
    nama = "Suit Live"
    ringkas = "Batu-gunting-kertas sirkular rame-rame. Manusia memilih tiap ronde, bot memakai kode Suit Bot Arena yang sama."
    kategori = "simultan"
    min_pemain, max_pemain = 2, 8
    fungsi_bot = "pilih"
    hint_aksi = "BATU, GUNTING, atau KERTAS"
    timer = 15
    jeda_pada, jeda_hasil = ("ronde",), 3
    label_skor = "HP"
    settings = [
        Setting("hp_awal", "HP awal", "int", 1000, 100, 100000),
        Setting("hp_kalah", "HP hilang saat kalah", "int", 100, 1, 100000),
        Setting("ronde_maks", "Batas ronde", "int", 40, 1, 300),
        Setting("ingatan", "Ingatan bot (ronde)", "int", 10, 1, 50),
        Setting("event", "Mode event", "pilihan", "normal", pilihan=[[e["id"], e["nama"]] for e in EVENTS], grup="kejutan",
                ket="Variasi aturan: taruhan ganda, pikun, kilat, darah tipis, kabut, atau kejutan acak."),
        Setting("hp_samar", "HP lawan samar", "bool", False, grup="informasi",
                ket="HP lawan dibulatkan ke kelipatan 10% HP awal, dan perubahan HP lawan tiap ronde tidak terlihat. HP-mu sendiri tetap pasti."),
        Setting("ronde_rahasia", "Batas ronde rahasia", "bool", False, grup="informasi",
                ket="Batas ronde sebenarnya acak ±25% dari pengaturan dan tidak diumumkan."),
        Setting("buruan", "Pemimpin jadi buruan (%)", "int", 0, 0, 200, grup="aturan",
                ket="Kalau pemain dengan HP tertinggi (satu orang) kalah, ia kehilangan HP ekstra sekian persen dari HP kalah; ekstranya dibagi ke yang mengalahkannya."),
        Setting("kejutan_ronde", "Kejutan tiap ronde (%)", "int", 0, 0, 100, grup="kejutan",
                ket="Peluang tiap ronde mendapat kejutan yang diumumkan di awal ronde: Ronde Ganda, Ronde Terbalik, atau Senjata Terlarang "
                    "(yang memakainya kehilangan HP kalah, dibagi ke semua yang tidak memakainya)."),
    ]
    presets = [
        {"id": "kabut", "nama": "Kabut", "ket": "HP lawan samar, batas ronde rahasia, pilihan tiap pemain tidak terlihat.",
         "nilai": {"hp_samar": True, "ronde_rahasia": True, "event": "kabut"}},
        {"id": "kacau", "nama": "Kacau", "ket": "Kejutan sering muncul dan pemimpin jadi buruan.",
         "nilai": {"kejutan_ronde": 40, "buruan": 50}},
    ]
    templates = [{"id": t["id"], "nama": t["nama"], "ket": t["ket"], "kode": t["kode"]} for t in TEMPLATES]
    # fungsi library Suit Bot Arena (BATU/GUNTING/KERTAS, pengalah, riwayat, ...) juga tersedia di Suit Live
    lib_docs = [{k: d[k] for k in ("nama", "jenis", "tanda", "ket")} for d in LIBRARY_DOCS]
    aturan = """
- Setiap ronde semua pemain memilih **BATU, GUNTING, atau KERTAS** bersamaan.
- Setiap pemain yang senjatanya dikalahkan kehilangan *HP hilang saat kalah* (default 100). HP itu dikumpulkan lalu dibagi rata ke golongan yang mengalahkannya. Sisa pembagian: +1 ke pemenang ber-HP terendah dulu.
- **Sirkular**: kalau ketiga senjata keluar, setiap golongan sekaligus menang atas satu golongan dan kalah dari golongan lain.
- HP 0 = gugur. Yang terakhir hidup menang, atau HP terbanyak saat batas ronde.
- **Mode event** (diatur host): *Taruhan Ganda* (HP kalah ×2), *Pikun* (ingatan bot 3 ronde), *Kilat* (maks 30 ronde),
  *Darah Tipis* (HP awal 30%), *Kabut* (pilihan tiap pemain tidak terlihat, hanya jumlah per senjata), *Kejutan* (salah satunya diundi).
- **HP lawan samar** (opsi): HP lawan dibulatkan ke kelipatan 10% HP awal. **Batas ronde rahasia** (opsi): ±25%, tidak diumumkan.
- **Pemimpin jadi buruan** (opsi): pemain dengan HP tertinggi yang kalah kehilangan HP ekstra, dibagi ke yang mengalahkannya.
- **Kejutan tiap ronde** (opsi), diumumkan di awal ronde: *Ronde Ganda* (HP kalah ×2), *Ronde Terbalik* (batu kalah dari gunting,
  gunting kalah dari kertas, kertas kalah dari batu), *Senjata Terlarang* (yang memakainya kehilangan HP kalah, dibagi ke semua yang
  tidak memakainya; tidak ikut adu senjata ronde itu).
"""
    format_aksi = "Kembalikan teks `BATU`, `GUNTING`, atau `KERTAS` dari `def pilih():` (sama persis dengan bot Suit Bot Arena)."
    format_info = """Bot Suit memakai library Suit Bot Arena: `ronde()`, `hp_saya()`, `lawan()`, `jumlah_terakhir()`, `pilihan_terakhir(nama)`,
`riwayat()`, `pengalah(s)`, `korban(s)`, `terbanyak(d)`, `hitung_hasil(pilihan)`, `senjata_terbaik()`, dst. `info()` juga tersedia dan berisi
`ronde`, `ronde_maks` (perkiraan kalau `ronde_pasti` False), `hp` (dict nama → HP; dibulatkan untuk lawan kalau HP samar),
`riwayat` (ronde-ronde terakhir sebanyak ingatan; `perubahan` lawan None kalau HP samar), `kejutan` (kejutan ronde ini atau None:
`{"jenis": "ganda" | "terbalik" | "terlarang", "senjata": "batu" (untuk terlarang)}`), dan `pemimpin` (nama yang sedang diburu)."""

    def init(self, cfg: dict[str, Any], names: list[str], seed: int) -> dict[str, Any]:
        s = {"seed": seed, "names": names, "ronde": 1, "history": [], "elim": {}}
        ev = resolve_event(cfg.get("event", "normal"), rng(s, "event"))
        s["cfg"] = apply_event({k: cfg[k] for k in ("hp_awal", "hp_kalah", "ronde_maks", "ingatan")}, ev)
        s["cfg"].update({k: cfg[k] for k in ("hp_samar", "ronde_rahasia", "buruan", "kejutan_ronde")})
        s["event"] = event_info(ev, kejutan=cfg.get("event") == "acak")
        s["hp"] = [s["cfg"]["hp_awal"]] * len(names)
        s["ronde_perkiraan"] = s["cfg"]["ronde_maks"]
        if s["cfg"]["ronde_rahasia"] and s["cfg"]["ronde_maks"] > 1:
            rm = s["cfg"]["ronde_maks"]
            d = max(1, rm // 4)
            s["cfg"]["ronde_maks"] = max(1, rng(s, "akhir").randint(rm - d, rm + d))
        return s

    def _kejutan(self, s: dict[str, Any], r: int) -> dict[str, Any] | None:
        pct = s["cfg"].get("kejutan_ronde", 0)
        if pct <= 0:
            return None
        g = rng(s, "kejutan", r)
        if g.random() * 100 >= pct:
            return None
        jenis = g.choice(list(KEJUTAN))
        out = {"jenis": jenis, "teks": KEJUTAN[jenis]}
        if jenis == "terlarang":
            out["senjata"] = g.choice(list(SENJATA))
            out["teks"] = f"Senjata Terlarang: {out['senjata'].upper()}"
        return out

    def _leader(self, s: dict[str, Any]) -> int | None:
        alive = self._alive(s)
        if not alive or s["cfg"].get("buruan", 0) <= 0:
            return None
        top = max(s["hp"][i] for i in alive)
        tops = [i for i in alive if s["hp"][i] == top]
        return tops[0] if len(tops) == 1 else None

    def _samar(self, s: dict[str, Any], h: int) -> int:
        step = max(1, s["cfg"]["hp_awal"] // 10)
        return 0 if h <= 0 else max(step, int(round(h / step)) * step)

    def _fog_entry(self, s: dict[str, Any], e: dict[str, Any], viewer: Any) -> dict[str, Any]:
        """Entri riwayat menurut penonton: HP lawan dibulatkan & perubahan lawan disembunyikan kalau HP samar."""
        if viewer == "semua" or not s["cfg"].get("hp_samar"):
            return e
        me = s["names"][viewer] if isinstance(viewer, int) else None
        return {**e, "hp": {n: (h if n == me else self._samar(s, h)) for n, h in e["hp"].items()},
                "perubahan": {n: (d if n == me else None) for n, d in e["perubahan"].items()},
                "pasangan": [{**pp, "kumpulan": None, "bagian": None} for pp in e.get("pasangan", [])]}

    def _kabut(self, s: dict[str, Any]) -> bool:
        return s["cfg"].get("event") == "kabut"

    def _visible(self, s: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return hide_choices(entries) if self._kabut(s) else entries

    def _alive(self, s: dict[str, Any]) -> list[int]:
        return [i for i, h in enumerate(s["hp"]) if h > 0]

    def pending(self, s: dict[str, Any]) -> list[int]:
        return [] if self.over(s) else self._alive(s)

    def _view(self, s: dict[str, Any], viewer: Any) -> dict[str, Any]:
        n = s["names"]
        c = s["cfg"]
        samar = c.get("hp_samar") and viewer != "semua"
        hist = s["history"] if viewer == "semua" else self._visible(s, s["history"])
        hist = [self._fog_entry(s, e, viewer) for e in hist]
        pasti = viewer == "semua" or not c.get("ronde_rahasia") or self.over(s)
        lead = self._leader(s)
        return {"ronde": s["ronde"], "ronde_maks": c["ronde_maks"] if pasti else s.get("ronde_perkiraan", c["ronde_maks"]),
                "ronde_pasti": pasti, "hp_awal": c["hp_awal"], "hp_kalah": c["hp_kalah"],
                "hp": {n[i]: (h if not samar or viewer == i else self._samar(s, h)) for i, h in enumerate(s["hp"])},
                "hp_samar": bool(c.get("hp_samar")), "riwayat": hist[-c["ingatan"]:], "terakhir": hist[-1] if hist else None,
                "event": s.get("event"), "kejutan": None if self.over(s) else self._kejutan(s, s["ronde"]),
                "buruan": c.get("buruan", 0), "pemimpin": n[lead] if lead is not None else None}

    def event_for(self, s, e, viewer):
        return self._fog_entry(s, e, viewer) if e.get("jenis") == "ronde" else e

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        return self._view(s, None)

    def full_view(self, s: dict[str, Any]) -> dict[str, Any]:
        return self._view(s, "semua")

    def observe(self, s: dict[str, Any], p: int) -> dict[str, Any]:
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    def validate(self, s: dict[str, Any], p: int, a: Any) -> str:
        if isinstance(a, str) and a.strip().lower() in SENJATA:
            return a.strip().lower()
        raise ActionError("pilih BATU, GUNTING, atau KERTAS")

    def default(self, s: dict[str, Any], p: int) -> str:
        return "batu"

    def _give(self, s: dict[str, Any], amount: int, to: list[int]) -> dict[int, int]:
        """Bagi ``amount`` HP rata ke ``to``; sisa +1 ke HP terendah dulu (seri: kursi lebih awal)."""
        got = {i: 0 for i in to}
        if not to or amount <= 0:
            return got
        share, rem = divmod(amount, len(to))
        for i in to:
            got[i] += share
        for i in sorted(to, key=lambda j: (s["hp"][j] + got[j], j))[:rem]:
            got[i] += 1
        return got

    def apply(self, s: dict[str, Any], actions: dict[int, Any]) -> list[dict[str, Any]]:
        n = s["names"]
        c = s["cfg"]
        alive = self._alive(s)
        kej = self._kejutan(s, s["ronde"])
        lead = self._leader(s)
        hp_kalah = c["hp_kalah"] * (2 if kej and kej["jenis"] == "ganda" else 1)
        choices = {i: actions[i] for i in alive}
        extra: dict[int, int] = {i: 0 for i in alive}
        main = list(alive)
        if kej and kej["jenis"] == "terlarang":
            banned = [i for i in alive if choices[i] == kej["senjata"]]
            main = [i for i in alive if i not in banned]
            if banned and main:
                pool = 0
                for i in banned:
                    lost = min(hp_kalah, s["hp"][i])
                    extra[i] -= lost
                    pool += lost
                for i, g in self._give(s, pool, main).items():
                    extra[i] += g
            else:
                main = list(alive)
        balik = bool(kej and kej["jenis"] == "terbalik")
        fight = {i: (BALIK[choices[i]] if balik else choices[i]) for i in main}
        out = resolve_round(fight, {i: s["hp"][i] + extra[i] for i in main}, hp_kalah, {i: i for i in range(len(n))})
        for i, d in out.delta.items():
            extra[i] += d
        buru = None
        beater = DIKALAHKAN_OLEH[fight[lead]] if lead is not None and lead in main else None
        winners = [i for i in main if fight[i] == beater] if beater else []
        if winners:   # pemimpin dikalahkan (golongannya kalah dari golongan lain), walau totalnya bisa impas
            ekstra = min(s["hp"][lead] + extra[lead], hp_kalah * c.get("buruan", 0) // 100)
            if ekstra > 0:
                extra[lead] -= ekstra
                for i, g in self._give(s, ekstra, winners).items():
                    extra[i] += g
                buru = {"pemimpin": n[lead], "ekstra": ekstra}
        for i, d in extra.items():
            s["hp"][i] += d
        gugur = [i for i in alive if s["hp"][i] <= 0]
        for i in gugur:
            s["elim"][str(i)] = s["ronde"]
        unmap = BALIK if balik else {w: w for w in SENJATA}
        entry = {
            "ronde": s["ronde"], "jumlah": {w: sum(1 for i in alive if choices[i] == w) for w in SENJATA},
            "pilihan": {n[i]: choices[i] for i in alive}, "perubahan": {n[i]: extra[i] for i in alive},
            "hp": {n[i]: s["hp"][i] for i in range(len(n))},
            "pasangan": [{"menang": unmap[p.win], "kalah": unmap[p.lose], "kumpulan": p.pool, "bagian": p.share} for p in out.pairs],
            "gugur": [n[i] for i in gugur], "kejutan": kej, "buruan": buru,
        }
        s["history"].append(entry)
        s["ronde"] += 1
        return [{"jenis": "ronde", **self._visible(s, [entry])[0]}]

    def over(self, s: dict[str, Any]) -> bool:
        return s["ronde"] > s["cfg"]["ronde_maks"] or len(self._alive(s)) <= 1

    def scores(self, s: dict[str, Any]) -> list[float]:
        return [float(h) for h in s["hp"]]

    def tiebreak(self, s: dict[str, Any]) -> list[float]:
        return [10**6 if s["hp"][i] > 0 else s["elim"].get(str(i), 0) for i in range(len(s["names"]))]

    def bot_library(self, s: dict[str, Any], p: int, obs: dict[str, Any]) -> dict[str, Any]:
        # library Suit Bot Arena memakai tampilan yang sama dengan info(): ikut kena kabut (HP samar, ronde rahasia)
        n = s["names"]
        view = RoundView(me=n[p], ronde=s["ronde"], hp_awal=s["cfg"]["hp_awal"], hp_kalah=s["cfg"]["hp_kalah"],
                         ronde_maks=obs["ronde_maks"], ingatan=s["cfg"]["ingatan"], names=list(n),
                         hp=dict(obs["hp"]),
                         history=[{k: h[k] for k in ("ronde", "jumlah", "pilihan", "perubahan", "hp")} for h in obs["riwayat"]])
        return make_library(view)
