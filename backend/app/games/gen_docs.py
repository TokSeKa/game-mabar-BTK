"""Tulis panduan bot setiap game Arena Mabar ke docs/bot/<id>.md.

    python -m app.games.gen_docs          # dari folder backend

Isinya sama persis dengan tombol "Salin panduan untuk AI" di dalam game (dibuat dari definisi game),
jadi dokumen ini tidak pernah ketinggalan dari aturan yang dipakai server.
"""

from __future__ import annotations

from pathlib import Path

from ..config import ROOT
from .guide import guide_markdown
from .registry import GAMES

OUT = ROOT / "docs" / "bot"


def render_all() -> dict[str, str]:
    files = {f"{g.id}.md": guide_markdown(g) + "\n" for g in GAMES.values()}
    lines = ["# Panduan bot Arena Mabar", "",
             "Satu file per game. Salin isinya ke AI (ChatGPT, Claude, Gemini, dll.) lalu ceritakan strategi yang kamu mau.",
             "File ini dibuat otomatis dari definisi game (`python -m app.games.gen_docs`).", "",
             "| Game | Pemain | Fungsi bot | Panduan |", "|---|---|---|---|"]
    for g in GAMES.values():
        players = f"{g.min_pemain}" if g.min_pemain == g.max_pemain else f"{g.min_pemain}–{g.max_pemain}"
        lines.append(f"| {g.nama} | {players} | `def {g.fungsi_bot}():` | [{g.id}.md]({g.id}.md) |")
    files["README.md"] = "\n".join(lines) + "\n"
    return files


def main(out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, text in render_all().items():
        (out / name).write_text(text, encoding="utf-8")
        print("tulis", out / name)


if __name__ == "__main__":
    main()
