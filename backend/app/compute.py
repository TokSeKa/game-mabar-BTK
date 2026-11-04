"""Menjalankan match di proses terpisah supaya server tetap responsif."""

from __future__ import annotations

import asyncio
import sys
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
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


class MatchRunner:
    def __init__(self, workers: int, max_steps: int):
        self.max_steps = max_steps
        self.executor: Executor = ProcessPoolExecutor(max_workers=workers) if workers > 0 else ThreadPoolExecutor(max_workers=2)

    async def run(self, entries: list[tuple[str, str]], settings: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, compute_match, entries, settings, self.max_steps)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
