"""Daftar semua game Arena Mabar (urutan = urutan tampil di hub)."""

from __future__ import annotations

from .base import Game
from .g_angka import DuaPertiga, KasDesa, PasarMalamSepi
from .g_blotto import RebutanLahan
from .g_evolusi import EvolusiHex
from .g_kapal import TenggelamkanKapal
from .g_kartu import KartuNusantara
from .g_labirin import Labirin
from .g_lelang import LelangRahasia
from .g_monopoli import JuraganNusantara
from .g_poker import Poker
from .g_robot import RobotGrid
from .g_satu import Satu
from .g_suit import SuitLive
from .g_tycoon import PasarMalamTycoon
from .g_wordle import WordleMabar

GAMES: dict[str, Game] = {g.id: g for g in [
    SuitLive(), Poker(), TenggelamkanKapal(), RobotGrid(), KartuNusantara(), PasarMalamTycoon(), LelangRahasia(),
    RebutanLahan(), KasDesa(), DuaPertiga(), PasarMalamSepi(), WordleMabar(), Labirin(), Satu(), EvolusiHex(), JuraganNusantara(),
]}
