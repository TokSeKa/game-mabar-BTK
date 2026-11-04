"""Menjalankan satu match sampai selesai secara sinkron (semua kursi bot).

Dipakai untuk: arena latihan, mode bot-saja "instan" (di process pool), dan tes.
"""

from __future__ import annotations

import sys
from typing import Any

from ..bot.errors import BotError
from ..bot.interpreter import Limits
from .registry import GAMES
from .runtime import BotSeat, compile_for




def thin_frames(frames: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Kurangi frame replay secara merata; frame pertama & terakhir selalu disimpan."""
    if len(frames) <= limit:
        return frames
    step = len(frames) / (limit - 1)
    keep = {min(len(frames) - 1, int(round(k * step))) for k in range(limit - 1)} | {len(frames) - 1}
    return [f for i, f in enumerate(frames) if i in keep]


def _compile(game, code: str | None) -> tuple[Any, dict | None]:
    if not code:
        return None, None
    try:
        return compile_for(game, code), None
    except BotError as e:
        return None, e.to_dict()


def play_sync(game_id: str, cfg: dict[str, Any], names: list[str], codes: list[str | None], seed: int,
              max_steps: int = 20000, bot_steps: int = 20_000) -> dict[str, Any]:
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    g = GAMES[game_id]
    cfg = g.clean_settings(cfg)
    s = g.init(cfg, names, seed)
    limits = Limits(max_steps=bot_steps)
    bots: list[BotSeat] = []
    for c in codes:
        comp, err = _compile(g, c)
        b = BotSeat(comp)
        if err:
            b.log.append({"langkah": 0, "error": err, "catatan": "Kode bot tidak valid, kursi ini memakai aksi bawaan."})
        bots.append(b)
    frames = [{"step": 0, "view": g.public(s), "events": []}]
    step = 0
    while not g.over(s) and step < max_steps:
        pend = g.pending(s)
        if not pend:
            break
        step += 1
        if g.mandiri:
            events = []
            for p in pend:
                events += g.apply(s, {p: bots[p].act(g, s, p, step, limits)})
        else:
            actions = {p: bots[p].act(g, s, p, step, limits) for p in pend}
            events = g.apply(s, actions)
        frames.append({"step": step, "view": g.public(s), "events": events})
    frames = thin_frames(frames, g.max_frames)
    return {"result": g.result(s), "frames": frames, "logs": [b.log for b in bots], "reveal": g.reveal(s),
            "settings": cfg, "names": names, "steps": step}
