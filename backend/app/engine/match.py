"""Menjalankan satu match penuh dan menghasilkan data replay."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any

from ..bot.errors import BotError
from ..bot.interpreter import Limits
from ..bot.library import RoundView
from ..bot.runner import run_bot
from ..bot.validator import compile_bot
from .events import EVENT_BY_ID, apply_event, event_info, hide_choices, resolve_event
from .rules import BATU, SENJATA, resolve_round

#: kalau bot error sebanyak ini berturut-turut, bot dimatikan dan otomatis memilih BATU
MAX_ERROR_BERUNTUN = 3
DEFAULT_PILIHAN = BATU


@dataclass
class MatchSettings:
    hp_awal: int = 1000
    hp_kalah: int = 100
    ronde_maks: int = 100
    ingatan: int = 10
    event: str = "normal"

    LIMITS = {
        "hp_awal": (100, 100_000),
        "hp_kalah": (1, 100_000),
        "ronde_maks": (1, 300),
        "ingatan": (1, 50),
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MatchSettings":
        data = data or {}
        base = cls()
        vals: dict[str, int] = {}
        for key, (lo, hi) in cls.LIMITS.items():
            raw = data.get(key, getattr(base, key))
            try:
                v = int(raw)
            except (TypeError, ValueError):
                v = getattr(base, key)
            vals[key] = max(lo, min(hi, v))
        vals["hp_kalah"] = min(vals["hp_kalah"], vals["hp_awal"])
        ev = data.get("event", "normal")
        return cls(**vals, event=ev if ev in EVENT_BY_ID else "normal")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def effective(self, rnd: random.Random | None = None) -> tuple["MatchSettings", dict[str, Any]]:
        """Aturan yang benar-benar dipakai setelah event diterapkan ('acak' diundi dengan ``rnd``)."""
        ev = resolve_event(self.event, rnd)
        vals = apply_event({k: getattr(self, k) for k in self.LIMITS}, ev)
        return MatchSettings(**vals), event_info(ev, kejutan=self.event == "acak")


@dataclass
class BotEntry:
    name: str
    code: str


def run_match(entries: list[BotEntry], settings: MatchSettings, limits: Limits | None = None,
              seed: int | None = None, effective: bool = False) -> dict[str, Any]:
    """Jalankan match. ``entries`` sudah dalam urutan masuk room.

    Event pada ``settings`` diterapkan dulu (event 'acak' diundi dari ``seed``), kecuali ``effective=True``
    yang berarti ``settings`` sudah berupa aturan efektif (dipakai turnamen supaya semua match sama).

    Hasilnya berisi:

    * ``rounds``: data replay per ronde (indeks pemain = posisi di ``entries``)
    * ``logs``: log per pemain (rahasia, hanya dikirim ke pemiliknya)
    * ``ranking``, ``winners``, ``reason``, ``elim_round``
    """
    limits = limits or Limits()
    if effective:
        ev = event_info(settings.event)
    else:
        settings, ev = settings.effective(random.Random(seed))
    kabut = settings.event == "kabut"
    n = len(entries)
    if n < 2:
        raise ValueError("butuh minimal 2 pemain")
    names = [e.name for e in entries]
    order = {i: i for i in range(n)}
    hp = [settings.hp_awal] * n
    logs: list[list[dict[str, Any]]] = [[] for _ in range(n)]
    compiled: list[Any] = []
    for i, e in enumerate(entries):
        try:
            compiled.append(compile_bot(e.code))
        except BotError as err:
            compiled.append(None)
            logs[i].append({"ronde": 0, "error": err.to_dict(), "catatan": "Kode bot tidak valid, bot otomatis memilih BATU sepanjang match."})
    beruntun = [0] * n
    mati = [c is None for c in compiled]
    history: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    elim_round: dict[int, int] = {}
    langkah_total = [0] * n

    for r in range(1, settings.ronde_maks + 1):
        alive = [i for i in range(n) if hp[i] > 0]
        if len(alive) <= 1:
            break
        window = history[-settings.ingatan:]
        if kabut:
            window = hide_choices(window)
        hp_names = {names[i]: hp[i] for i in range(n)}
        choices: dict[int, str] = {}
        for i in alive:
            if mati[i]:
                choices[i] = DEFAULT_PILIHAN
                continue
            view = RoundView(
                me=names[i], ronde=r, hp_awal=settings.hp_awal, hp_kalah=settings.hp_kalah,
                ronde_maks=settings.ronde_maks, ingatan=settings.ingatan, names=names,
                hp=dict(hp_names), history=window,
            )
            turn = run_bot(compiled[i], view, limits)
            langkah_total[i] += turn.langkah
            entry: dict[str, Any] = {"ronde": r, "langkah": turn.langkah}
            if turn.cetak:
                entry["cetak"] = turn.cetak
            if turn.error is not None:
                beruntun[i] += 1
                choices[i] = DEFAULT_PILIHAN
                entry["error"] = turn.error.to_dict()
                entry["pilihan"] = DEFAULT_PILIHAN
                entry["otomatis"] = True
                if beruntun[i] >= MAX_ERROR_BERUNTUN:
                    mati[i] = True
                    entry["catatan"] = (f"Bot error {MAX_ERROR_BERUNTUN} ronde berturut-turut, jadi dimatikan. "
                                        "Sisa match bot otomatis memilih BATU.")
            else:
                beruntun[i] = 0
                choices[i] = turn.pilihan  # type: ignore[assignment]
                entry["pilihan"] = turn.pilihan
            logs[i].append(entry)

        outcome = resolve_round(choices, {i: hp[i] for i in alive}, settings.hp_kalah, order)
        before = hp[:]
        for i, d in outcome.delta.items():
            hp[i] += d
        elim = [i for i in alive if hp[i] <= 0]
        for i in elim:
            elim_round[i] = r
        counts = {s: len(outcome.groups[s]) for s in SENJATA}
        delta_arr = [outcome.delta.get(i, 0) for i in range(n)]
        rounds.append({
            "r": r,
            "alive": alive,
            "choices": [choices.get(i) for i in range(n)],
            "groups": outcome.groups,
            "counts": counts,
            "pairs": [
                {"win": p.win, "lose": p.lose, "losers": [{"id": l.id, "amt": l.amt} for l in p.losers],
                 "pool": p.pool, "winners": p.winners, "share": p.share, "rem_ids": p.rem_ids}
                for p in outcome.pairs
            ],
            "delta": delta_arr,
            "before": before,
            "after": hp[:],
            "elim": elim,
        })
        history.append({
            "ronde": r,
            "jumlah": counts,
            "pilihan": {names[i]: choices[i] for i in alive},
            "perubahan": {names[i]: outcome.delta[i] for i in alive},
            "hp": {names[i]: hp[i] for i in range(n)},
        })

    alive_final = [i for i in range(n) if hp[i] > 0]
    ranking = sorted(range(n), key=lambda i: (-hp[i], -elim_round.get(i, 10**9), i))
    top = hp[ranking[0]]
    winners = [i for i in ranking if hp[i] == top and hp[i] > 0]
    reason = "last_standing" if len(alive_final) == 1 else "max_rounds"
    return {
        "settings": settings.to_dict(),
        "event": ev,
        "names": names,
        "rounds": rounds,
        "logs": logs,
        "ranking": ranking,
        "winners": winners,
        "reason": reason,
        "elim_round": {str(k): v for k, v in elim_round.items()},
        "final_hp": hp[:],
        "langkah_total": langkah_total,
    }
