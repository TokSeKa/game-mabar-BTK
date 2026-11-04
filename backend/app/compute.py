"""Menjalankan match di proses terpisah supaya server tetap responsif."""

from __future__ import annotations

import asyncio
import random
import sys
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from itertools import combinations
from typing import Any

from .bot.interpreter import Limits
from .engine.match import BotEntry, MatchSettings, run_match


def compute_match(entries: list[tuple[str, str]], settings: dict[str, Any], max_steps: int) -> dict[str, Any]:
    """Fungsi top-level (bisa di-pickle) untuk process pool."""
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    return run_match(
        [BotEntry(name, code) for name, code in entries],
        MatchSettings.from_dict(settings),
        Limits(max_steps=max_steps),
    )


def compute_tournament(entries: list[tuple[str, str]], settings: dict[str, Any], max_steps: int) -> dict[str, Any]:
    """Turnamen setengah kompetisi: setiap pasangan main 1 lawan 1 sekali (menang 3, seri 1, kalah 0).

    Event 'acak' diundi sekali untuk seluruh turnamen supaya semua pasangan memakai aturan yang sama.
    """
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    eff, ev = MatchSettings.from_dict(settings).effective(random.Random())
    limits = Limits(max_steps=max_steps)
    n = len(entries)
    table = [{"index": i, "poin": 0, "menang": 0, "seri": 0, "kalah": 0, "selisih_hp": 0} for i in range(n)]
    matches = []
    for a, b in combinations(range(n), 2):
        res = run_match([BotEntry(*entries[a]), BotEntry(*entries[b])], eff, limits, effective=True)
        hp_a, hp_b = res["final_hp"]
        if len(res["winners"]) == 1:
            win = (a, b)[res["winners"][0]]
            lose = b if win == a else a
            table[win]["poin"] += 3
            table[win]["menang"] += 1
            table[lose]["kalah"] += 1
        else:
            win = None
            for x in (a, b):
                table[x]["poin"] += 1
                table[x]["seri"] += 1
        table[a]["selisih_hp"] += hp_a - hp_b
        table[b]["selisih_hp"] += hp_b - hp_a
        matches.append({"a": a, "b": b, "pemenang": win, "hp": [hp_a, hp_b], "ronde": len(res["rounds"]),
                        "alasan": res["reason"], "rounds": res["rounds"], "ranking": res["ranking"], "winners": res["winners"],
                        "elim_round": res["elim_round"], "final_hp": res["final_hp"], "logs": res["logs"]})
    standings = sorted(table, key=lambda r: (-r["poin"], -r["selisih_hp"], -r["menang"], r["index"]))
    return {"settings": eff.to_dict(), "event": ev, "matches": matches, "standings": standings}


class MatchRunner:
    def __init__(self, workers: int, max_steps: int):
        self.max_steps = max_steps
        self.executor: Executor = ProcessPoolExecutor(max_workers=workers) if workers > 0 else ThreadPoolExecutor(max_workers=2)

    async def run(self, entries: list[tuple[str, str]], settings: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, compute_match, entries, settings, self.max_steps)

    async def tournament(self, entries: list[tuple[str, str]], settings: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, compute_tournament, entries, settings, self.max_steps)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
