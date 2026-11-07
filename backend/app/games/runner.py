"""Menjalankan satu match sampai selesai secara sinkron (semua kursi bot).

Dipakai untuk: arena latihan, mode bot-saja "instan" (di process pool), dan tes.
"""

from __future__ import annotations

import copy
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
    frames = [{"step": 0, "view": g.frame_view(s), "events": []}]
    langkah: list[dict[str, Any]] = []
    step = 0
    while not g.over(s) and step < max_steps:
        pend = g.pending(s)
        if not pend:
            break
        step += 1
        if g.mandiri:
            events = []
            for p in pend:
                a = bots[p].act(g, s, p, step, limits)
                langkah.append({str(p): a})
                events += g.apply(s, {p: a})
        else:
            actions = {p: bots[p].act(g, s, p, step, limits) for p in pend}
            langkah.append({str(p): a for p, a in actions.items()})
            events = g.apply(s, actions)
        frames.append({"step": step, "view": g.frame_view(s), "events": events})
    frames = thin_frames(frames, g.max_frames)
    return {"result": g.result(s), "frames": frames, "logs": [b.log for b in bots], "reveal": g.reveal(s),
            "settings": cfg, "names": names, "steps": step, "langkah": langkah}


def sudut_sync(game_id: str, cfg: dict[str, Any], names: list[str], seed: int, langkah: list[dict[str, Any]],
               kursi: int) -> list[dict[str, Any]]:
    """Buat ulang match dari seed + aksi tercatat, lalu ambil tampilan untuk satu kursi (-1 = penonton/berkabut).
    Setiap kelompok aksi (satu langkah, atau satu aksi di mode mandiri) menjadi satu frame."""
    g = GAMES[game_id]
    cfg = g.clean_settings(cfg)
    s = g.init(cfg, list(names), int(seed))

    def view() -> dict[str, Any]:
        return copy.deepcopy(g.public(s) if kursi < 0 else g.observe(s, kursi))

    frames = [{"step": 0, "view": view(), "events": []}]
    for k, entry in enumerate(langkah, start=1):
        actions = {int(p): a for p, a in entry.items()}
        events = g.apply(s, actions)
        frames.append({"step": k, "view": view(), "events": events})
    return thin_frames(frames, g.max_frames)
