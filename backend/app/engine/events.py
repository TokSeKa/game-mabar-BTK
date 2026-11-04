"""Mode event Suit: variasi aturan per match (dipakai Suit Bot Arena dan Suit Live)."""

from __future__ import annotations

import random
from typing import Any

EVENTS: list[dict[str, str]] = [
    {"id": "normal", "nama": "Normal", "ket": "Aturan biasa."},
    {"id": "ganda", "nama": "Taruhan Ganda", "ket": "HP yang hilang saat kalah dikali 2."},
    {"id": "pikun", "nama": "Pikun", "ket": "Ingatan bot hanya 3 ronde terakhir."},
    {"id": "kilat", "nama": "Kilat", "ket": "Paling lama 30 ronde."},
    {"id": "tipis", "nama": "Darah Tipis", "ket": "HP awal hanya 30% (minimal 100)."},
    {"id": "kabut", "nama": "Kabut", "ket": "Pilihan tiap pemain tidak terlihat oleh bot. Bot hanya tahu jumlah tiap senjata, perubahan HP, dan HP."},
    {"id": "acak", "nama": "Kejutan", "ket": "Salah satu event di atas dipilih acak saat match dimulai."},
]
EVENT_IDS = [e["id"] for e in EVENTS]
EVENT_BY_ID = {e["id"]: e for e in EVENTS}
KONKRET = [e for e in EVENT_IDS if e not in ("normal", "acak")]


def resolve_event(event: str, rnd: random.Random | None = None) -> str:
    """'acak' menjadi salah satu event konkret; event lain apa adanya."""
    if event not in EVENT_BY_ID:
        return "normal"
    if event == "acak":
        return (rnd or random.Random()).choice(KONKRET)
    return event


def apply_event(values: dict[str, Any], event: str) -> dict[str, Any]:
    """Nilai aturan efektif setelah event diterapkan (``event`` harus sudah konkret)."""
    v = dict(values)
    if event == "ganda":
        v["hp_kalah"] = v["hp_kalah"] * 2
    elif event == "pikun":
        v["ingatan"] = min(v["ingatan"], 3)
    elif event == "kilat":
        v["ronde_maks"] = min(v["ronde_maks"], 30)
    elif event == "tipis":
        v["hp_awal"] = max(100, int(v["hp_awal"] * 0.3))
    v["hp_kalah"] = min(v["hp_kalah"], v["hp_awal"])
    v["event"] = event
    return v


def hide_choices(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Untuk event kabut: hapus pilihan per pemain dari riwayat yang dilihat bot."""
    return [{**h, "pilihan": {}} for h in history]


def event_info(event: str, kejutan: bool = False) -> dict[str, Any]:
    e = EVENT_BY_ID.get(event, EVENT_BY_ID["normal"])
    return {**e, "kejutan": kejutan}
