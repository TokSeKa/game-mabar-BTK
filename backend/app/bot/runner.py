"""Menjalankan satu bot untuk satu ronde."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..engine.rules import SENJATA
from .errors import BotError
from .interpreter import Interpreter, Limits, tn
from .library import RoundView, make_library
from .validator import CompiledBot


@dataclass
class BotTurn:
    pilihan: str | None
    langkah: int
    cetak: list[str] = field(default_factory=list)
    error: BotError | None = None


def run_bot(compiled: CompiledBot, view: RoundView, limits: Limits) -> BotTurn:
    interp = Interpreter(compiled, make_library(view), limits)
    try:
        interp.run_module()
        hasil = interp.call_function("pilih")
        if isinstance(hasil, str) and hasil.strip().lower() in SENJATA:
            return BotTurn(hasil.strip().lower(), interp.steps, interp.prints)
        shown = repr(hasil) if isinstance(hasil, str) else tn(hasil)
        raise BotError(f"pilih() harus mengembalikan BATU, GUNTING, atau KERTAS, tapi mengembalikan {shown}")
    except BotError as e:
        return BotTurn(None, interp.steps, interp.prints, e)
    except RecursionError:
        return BotTurn(None, interp.steps, interp.prints, BotError("kode terlalu dalam/bertingkat saat dijalankan"))
    except MemoryError:
        return BotTurn(None, interp.steps, interp.prints, BotError("memori habis"))
