"""Pengaturan server lewat environment variable (lihat .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # root repo


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    bot_max_steps: int = _int("BOT_MAX_STEPS", 20_000)
    match_workers: int = _int("MATCH_WORKERS", 2)         # 0 = jalankan di thread (untuk tes)
    max_rooms: int = _int("MAX_ROOMS", 200)
    max_players: int = 8
    player_grace_seconds: int = _int("PLAYER_GRACE_SECONDS", 600)   # pemain offline dihapus setelah ini
    room_idle_seconds: int = _int("ROOM_IDLE_SECONDS", 1800)       # room tanpa pemain online dihapus
    practice_concurrency: int = _int("PRACTICE_CONCURRENCY", 4)
    static_dir: Path = Path(os.environ.get("STATIC_DIR", ROOT / "frontend" / "dist"))
    guide_path: Path = Path(os.environ.get("GUIDE_PATH", ROOT / "docs" / "PANDUAN_BOT_LLM.md"))


config = Config()
