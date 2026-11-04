"""Semua contoh bot di panduan LLM harus valid dan berjalan tanpa error."""
import re

from app.bot.templates import TEMPLATE_BY_ID
from app.config import ROOT
from app.engine.match import BotEntry, MatchSettings, run_match

GUIDE = (ROOT / "docs" / "PANDUAN_BOT_LLM.md").read_text(encoding="utf-8")
BOTS = [b for b in re.findall(r"```python\n(.*?)```", GUIDE, re.S) if "def pilih" in b]


def test_ada_contoh():
    assert len(BOTS) >= 5


def test_semua_contoh_berjalan():
    lawan = [TEMPLATE_BY_ID[t]["kode"] for t in ("anti_mayoritas", "pemutar", "pembalas")]
    for i, code in enumerate(BOTS):
        entries = [BotEntry("Aku", code)] + [BotEntry(f"L{j}", c) for j, c in enumerate(lawan)]
        res = run_match(entries, MatchSettings(ronde_maks=40))
        errors = [e for e in res["logs"][0] if "error" in e]
        assert not errors, (i, errors[:2])
