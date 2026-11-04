"""Kontrak umum setiap game di Arena Mabar.

Setiap game adalah kelas turunan ``Game``. State game berupa dict biasa (bisa jadi JSON),
semua keacakan game memakai ``rng(state, ...)`` yang diturunkan dari seed, jadi satu match
selalu bisa diulang persis. Bot pemain TIDAK punya akses ke keacakan apa pun.

Alur satu langkah:
    pending(state)  -> kursi yang harus bertindak sekarang
    observe(state, p) -> apa yang dilihat kursi p (rahasia lawan disembunyikan)
    validate(state, p, aksi) -> aksi yang sudah dirapikan, atau ActionError
    apply(state, {p: aksi}) -> daftar event publik
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any


class ActionError(ValueError):
    """Aksi tidak valid. Pesannya ditampilkan ke pemain/bot (turunan ValueError supaya error di fungsi bantu
    bot juga diterjemahkan jadi pesan yang jelas oleh interpreter)."""


@dataclass
class Setting:
    id: str
    label: str
    jenis: str                 # int | float | bool | pilihan
    default: Any
    min: float | None = None
    max: float | None = None
    pilihan: list[list[str]] | None = None   # [[nilai, label], ...]
    ket: str = ""

    def clean(self, v: Any) -> Any:
        try:
            if self.jenis == "bool":
                return bool(v) if not isinstance(v, str) else v.lower() in ("1", "true", "ya", "on")
            if self.jenis == "pilihan":
                ok = [p[0] for p in (self.pilihan or [])]
                return v if v in ok else self.default
            x = float(v)
            if x != x:  # NaN
                return self.default
            if self.min is not None:
                x = max(self.min, x)
            if self.max is not None:
                x = min(self.max, x)
            return int(round(x)) if self.jenis == "int" else x
        except (TypeError, ValueError):
            return self.default

    def meta(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "jenis": self.jenis, "default": self.default,
                "min": self.min, "max": self.max, "pilihan": self.pilihan, "ket": self.ket}


def rng(state: dict[str, Any], *keys: Any) -> random.Random:
    """RNG game yang deterministik: sama untuk seed & kunci yang sama."""
    raw = "|".join([str(state["seed"]), *map(str, keys)])
    return random.Random(int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16))


def rank_by(scores: list[float], tiebreak: list[float] | None = None) -> list[int]:
    """Urutan kursi dari skor tertinggi. Seri dipecah ``tiebreak`` lalu urutan kursi."""
    tb = tiebreak or [0] * len(scores)
    return sorted(range(len(scores)), key=lambda i: (-scores[i], -tb[i], i))


class Game:
    """Kelas dasar. Game turunan cukup mengisi atribut kelas dan method di bawah."""

    id: str = ""
    nama: str = ""
    ringkas: str = ""
    kategori: str = "simultan"       # simultan | giliran | tick | mandiri
    min_pemain: int = 2
    max_pemain: int = 8
    fungsi_bot: str = "aksi"
    hint_aksi: str = "aksi yang valid"
    timer: int = 20                  # detik per keputusan pemain manusia
    mandiri: bool = False            # True: tiap pemain jalan sendiri-sendiri (tidak menunggu pemain lain)
    settings: list[Setting] = []
    templates: list[dict[str, str]] = []
    lib_docs: list[dict[str, str]] = []
    aturan: str = ""                 # markdown: cara main
    format_aksi: str = ""            # markdown: bentuk aksi
    format_info: str = ""            # markdown: isi info()
    label_skor: str = "Poin"
    max_frames: int = 1500           # batas frame replay yang disimpan

    # ------------------------------------------------------------ wajib diisi game
    def init(self, cfg: dict[str, Any], names: list[str], seed: int) -> dict[str, Any]:
        raise NotImplementedError

    def pending(self, s: dict[str, Any]) -> list[int]:
        raise NotImplementedError

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def validate(self, s: dict[str, Any], p: int, a: Any) -> Any:
        raise NotImplementedError

    def default(self, s: dict[str, Any], p: int) -> Any:
        raise NotImplementedError

    def apply(self, s: dict[str, Any], actions: dict[int, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def over(self, s: dict[str, Any]) -> bool:
        raise NotImplementedError

    def scores(self, s: dict[str, Any]) -> list[float]:
        raise NotImplementedError

    # ------------------------------------------------------------ boleh di-override
    def observe(self, s: dict[str, Any], p: int) -> dict[str, Any]:
        return {**self.public(s), "saya": p, "nama_saya": s["names"][p]}

    def tiebreak(self, s: dict[str, Any]) -> list[float] | None:
        return None

    def result(self, s: dict[str, Any]) -> dict[str, Any]:
        sc = self.scores(s)
        order = rank_by(sc, self.tiebreak(s))
        return {"ranking": order, "skor": sc, "label_skor": self.label_skor, "pemenang": order[0]}

    def reveal(self, s: dict[str, Any]) -> dict[str, Any]:
        return {}

    def bot_library(self, s: dict[str, Any], p: int, obs: dict[str, Any]) -> dict[str, Any]:
        """Fungsi bantu tambahan untuk bot (nama → callable atau konstanta)."""
        return {}

    def clean_settings(self, cfg: dict[str, Any] | None) -> dict[str, Any]:
        cfg = cfg or {}
        return {st.id: st.clean(cfg.get(st.id, st.default)) for st in self.settings}

    def meta(self) -> dict[str, Any]:
        return {
            "id": self.id, "nama": self.nama, "ringkas": self.ringkas, "kategori": self.kategori,
            "min_pemain": self.min_pemain, "max_pemain": self.max_pemain, "fungsi_bot": self.fungsi_bot,
            "timer": self.timer, "mandiri": self.mandiri, "settings": [x.meta() for x in self.settings],
            "templates": self.templates, "lib_docs": BASE_DOCS + self.lib_docs, "label_skor": self.label_skor,
            "aturan": self.aturan, "format_aksi": self.format_aksi,
        }


BASE_DOCS = [
    {"nama": "info", "jenis": "fungsi", "tanda": "info()", "ket": "Semua yang bisa kamu lihat sekarang (dict). Isinya dijelaskan di panduan game."},
    {"nama": "saya", "jenis": "fungsi", "tanda": "saya()", "ket": "Nomor kursimu (0, 1, 2, ...)."},
    {"nama": "nama_saya", "jenis": "fungsi", "tanda": "nama_saya()", "ket": "Nama botmu."},
    {"nama": "pemain", "jenis": "fungsi", "tanda": "pemain()", "ket": "Daftar nama semua pemain, urut nomor kursi."},
    {"nama": "jumlah_pemain", "jenis": "fungsi", "tanda": "jumlah_pemain()", "ket": "Banyaknya pemain di match ini."},
]


def as_int(v: Any, what: str = "angka") -> int:
    if isinstance(v, bool):
        raise ActionError(f"{what} harus berupa angka")
    if isinstance(v, (int, float)) and v == v:
        return int(round(v))
    if isinstance(v, str):
        try:
            return int(round(float(v.strip())))
        except ValueError:
            pass
    raise ActionError(f"{what} harus berupa angka")
