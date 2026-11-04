"""Menjalankan kode bot pemain untuk game di Arena Mabar (memakai sandbox yang sama dengan Suit)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from ..bot.errors import BotError
from ..bot.interpreter import Interpreter, LibFunction, Limits
from ..bot.validator import CompiledBot, compile_bot
from .base import ActionError, Game

MAX_ERROR_BERUNTUN = 3


def compile_for(game: Game, code: str) -> CompiledBot:
    return compile_bot(code, game.fungsi_bot, game.hint_aksi)


def base_library(game: Game, s: dict[str, Any], p: int, obs: dict[str, Any]) -> dict[str, Any]:
    names = list(s["names"])
    lib: dict[str, Any] = {
        "info": LibFunction("info", lambda: copy.deepcopy(obs), 5),
        "saya": LibFunction("saya", lambda: p, 1),
        "nama_saya": LibFunction("nama_saya", lambda: names[p], 1),
        "pemain": LibFunction("pemain", lambda: list(names), 2),
        "jumlah_pemain": LibFunction("jumlah_pemain", lambda: len(names), 1),
    }
    for k, v in game.bot_library(s, p, obs).items():
        lib[k] = v if not callable(v) or isinstance(v, LibFunction) else LibFunction(k, v, 20)
    return lib


@dataclass
class BotResult:
    action: Any
    prints: list[str] = field(default_factory=list)
    error: BotError | None = None
    steps: int = 0


def run_bot(game: Game, compiled: CompiledBot, s: dict[str, Any], p: int, limits: Limits | None = None,
            trace: list | None = None) -> BotResult:
    obs = game.observe(s, p)
    it = Interpreter(compiled, base_library(game, s, p, obs), limits or Limits(), trace=trace)
    try:
        it.run_module()
        raw = it.call_function(game.fungsi_bot)
        return BotResult(game.validate(s, p, raw), it.prints, None, it.steps)
    except ActionError as e:
        return BotResult(None, it.prints, BotError(f"aksi tidak valid: {e}"), it.steps)
    except BotError as e:
        return BotResult(None, it.prints, e, it.steps)
    except RecursionError:
        return BotResult(None, it.prints, BotError("kode terlalu dalam/bertingkat"), it.steps)
    except MemoryError:
        return BotResult(None, it.prints, BotError("memori habis"), it.steps)


@dataclass
class BotSeat:
    """Status bot di satu kursi: error beruntun, dimatikan, dan log."""
    compiled: CompiledBot | None
    fails: int = 0
    disabled: bool = False
    log: list[dict[str, Any]] = field(default_factory=list)

    def act(self, game: Game, s: dict[str, Any], p: int, step: int, limits: Limits | None = None) -> Any:
        if self.compiled is None or self.disabled:
            return game.default(s, p)
        r = run_bot(game, self.compiled, s, p, limits)
        entry: dict[str, Any] = {"langkah": step, "steps": r.steps}
        if r.prints:
            entry["cetak"] = r.prints
        if r.error is not None:
            self.fails += 1
            entry["error"] = r.error.to_dict()
            if self.fails >= MAX_ERROR_BERUNTUN:
                self.disabled = True
                entry["catatan"] = f"Bot error {MAX_ERROR_BERUNTUN} kali berturut-turut, jadi dimatikan. Sisa match memakai aksi bawaan."
            action = game.default(s, p)
        else:
            self.fails = 0
            action = r.action
        if r.prints or r.error is not None or len(self.log) < 40:
            self.log.append(entry)
            if len(self.log) > 300:
                del self.log[:100]
        return action
