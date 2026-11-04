"""Suit Live: aturan Suit Bot Arena, tapi kursinya boleh manusia (pilih tiap ronde) atau bot."""

from __future__ import annotations

from typing import Any

from ..bot.library import RoundView, make_library
from ..bot.templates import TEMPLATES
from ..engine.events import EVENTS, apply_event, event_info, hide_choices, resolve_event
from ..engine.rules import SENJATA, resolve_round
from .base import ActionError, Game, Setting, rng


class SuitLive(Game):
    id = "suit"
    nama = "Suit Live"
    ringkas = "Batu-gunting-kertas sirkular rame-rame. Manusia memilih tiap ronde, bot memakai kode Suit Bot Arena yang sama."
    kategori = "simultan"
    min_pemain, max_pemain = 2, 8
    fungsi_bot = "pilih"
    hint_aksi = "BATU, GUNTING, atau KERTAS"
    timer = 15
    label_skor = "HP"
    settings = [
        Setting("hp_awal", "HP awal", "int", 1000, 100, 100000),
        Setting("hp_kalah", "HP hilang saat kalah", "int", 100, 1, 100000),
        Setting("ronde_maks", "Batas ronde", "int", 40, 1, 300),
        Setting("ingatan", "Ingatan bot (ronde)", "int", 10, 1, 50),
        Setting("event", "Mode event", "pilihan", "normal", pilihan=[[e["id"], e["nama"]] for e in EVENTS],
                ket="Variasi aturan: taruhan ganda, pikun, kilat, darah tipis, kabut, atau kejutan acak."),
    ]
    templates = [{"id": t["id"], "nama": t["nama"], "ket": t["ket"], "kode": t["kode"]} for t in TEMPLATES]
    aturan = """
- Setiap ronde semua pemain memilih **BATU, GUNTING, atau KERTAS** bersamaan.
- Setiap pemain yang senjatanya dikalahkan kehilangan *HP hilang saat kalah* (default 100). HP itu dikumpulkan lalu dibagi rata ke golongan yang mengalahkannya. Sisa pembagian: +1 ke pemenang ber-HP terendah dulu.
- **Sirkular**: kalau ketiga senjata keluar, setiap golongan sekaligus menang atas satu golongan dan kalah dari golongan lain.
- HP 0 = gugur. Yang terakhir hidup menang, atau HP terbanyak saat batas ronde.
- **Mode event** (diatur host): *Taruhan Ganda* (HP kalah ×2), *Pikun* (ingatan bot 3 ronde), *Kilat* (maks 30 ronde),
  *Darah Tipis* (HP awal 30%), *Kabut* (pilihan tiap pemain tidak terlihat, hanya jumlah per senjata), *Kejutan* (salah satunya diundi).
"""
    format_aksi = "Kembalikan teks `BATU`, `GUNTING`, atau `KERTAS` dari `def pilih():` (sama persis dengan bot Suit Bot Arena)."
    format_info = """Bot Suit memakai library Suit Bot Arena: `ronde()`, `hp_saya()`, `lawan()`, `jumlah_terakhir()`, `pilihan_terakhir(nama)`,
`riwayat()`, `pengalah(s)`, `korban(s)`, `terbanyak(d)`, `hitung_hasil(pilihan)`, `senjata_terbaik()`, dst. `info()` juga tersedia dan berisi
`ronde`, `ronde_maks`, `hp` (dict nama → HP), dan `riwayat` (ronde-ronde terakhir sebanyak ingatan)."""

    def init(self, cfg: dict[str, Any], names: list[str], seed: int) -> dict[str, Any]:
        s = {"seed": seed, "names": names, "ronde": 1, "history": [], "elim": {}}
        ev = resolve_event(cfg.get("event", "normal"), rng(s, "event"))
        s["cfg"] = apply_event({k: cfg[k] for k in ("hp_awal", "hp_kalah", "ronde_maks", "ingatan")}, ev)
        s["event"] = event_info(ev, kejutan=cfg.get("event") == "acak")
        s["hp"] = [s["cfg"]["hp_awal"]] * len(names)
        return s

    def _kabut(self, s: dict[str, Any]) -> bool:
        return s["cfg"].get("event") == "kabut"

    def _visible(self, s: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return hide_choices(entries) if self._kabut(s) else entries

    def _alive(self, s: dict[str, Any]) -> list[int]:
        return [i for i, h in enumerate(s["hp"]) if h > 0]

    def pending(self, s: dict[str, Any]) -> list[int]:
        return [] if self.over(s) else self._alive(s)

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        n = s["names"]
        last = self._visible(s, s["history"][-1:])
        return {"ronde": s["ronde"], "ronde_maks": s["cfg"]["ronde_maks"], "hp_awal": s["cfg"]["hp_awal"],
                "hp_kalah": s["cfg"]["hp_kalah"], "hp": {n[i]: h for i, h in enumerate(s["hp"])},
                "riwayat": self._visible(s, s["history"][-s["cfg"]["ingatan"]:]), "terakhir": last[0] if last else None,
                "event": s.get("event")}

    def validate(self, s: dict[str, Any], p: int, a: Any) -> str:
        if isinstance(a, str) and a.strip().lower() in SENJATA:
            return a.strip().lower()
        raise ActionError("pilih BATU, GUNTING, atau KERTAS")

    def default(self, s: dict[str, Any], p: int) -> str:
        return "batu"

    def apply(self, s: dict[str, Any], actions: dict[int, Any]) -> list[dict[str, Any]]:
        n = s["names"]
        alive = self._alive(s)
        choices = {i: actions[i] for i in alive}
        out = resolve_round(choices, {i: s["hp"][i] for i in alive}, s["cfg"]["hp_kalah"], {i: i for i in range(len(n))})
        for i, d in out.delta.items():
            s["hp"][i] += d
        gugur = [i for i in alive if s["hp"][i] <= 0]
        for i in gugur:
            s["elim"][str(i)] = s["ronde"]
        entry = {
            "ronde": s["ronde"], "jumlah": {w: len(out.groups[w]) for w in SENJATA},
            "pilihan": {n[i]: choices[i] for i in alive}, "perubahan": {n[i]: out.delta[i] for i in alive},
            "hp": {n[i]: s["hp"][i] for i in range(len(n))},
            "pasangan": [{"menang": p.win, "kalah": p.lose, "kumpulan": p.pool, "bagian": p.share} for p in out.pairs],
            "gugur": [n[i] for i in gugur],
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
        n = s["names"]
        view = RoundView(me=n[p], ronde=s["ronde"], hp_awal=s["cfg"]["hp_awal"], hp_kalah=s["cfg"]["hp_kalah"],
                         ronde_maks=s["cfg"]["ronde_maks"], ingatan=s["cfg"]["ingatan"], names=list(n),
                         hp={n[i]: h for i, h in enumerate(s["hp"])},
                         history=self._visible(s, [{k: h[k] for k in ("ronde", "jumlah", "pilihan", "perubahan", "hp")}
                                                   for h in s["history"][-s["cfg"]["ingatan"]:]]))
        return make_library(view)
