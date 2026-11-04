"""Penyimpanan candle di disk dan katalog aset.

Struktur folder ``DATA_DIR``::

    catalog.json                       daftar aset + timeframe yang tersedia
    series/<market>/<symbol>/<tf>.bin  record ``REC`` urut waktu (dibaca dengan memmap)
    raw/...                            file mentah hasil unduhan (cache, boleh dihapus)
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from .markets import MARKETS, asset_name
from .timeframes import REC, aggregate, rank

#: jeda lebih dari ini dianggap putus (data intraday Yahoo yang diunduh tidak rutin)
SEGMENT_GAP_MS = {"default": 4 * 86_400_000, "crypto": 30 * 86_400_000}


def data_dir() -> Path:
    from ..config import ROOT
    return Path(os.environ.get("DATA_DIR", ROOT / "data")) / "pasar"


def series_path(root: Path, market: str, symbol: str, tf: str) -> Path:
    return root / "series" / market / symbol / f"{tf}.bin"


def write_series(path: Path, rec: np.ndarray) -> None:
    """Tulis atomik: file baru dulu, lalu ganti nama."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    np.ascontiguousarray(rec, dtype=REC).tofile(tmp)
    os.replace(tmp, path)


def read_series(path: Path, mmap: bool = True) -> np.ndarray:
    if not path.exists() or path.stat().st_size < REC.itemsize:
        return np.empty(0, REC)
    n = path.stat().st_size // REC.itemsize
    if mmap:
        return np.memmap(path, dtype=REC, mode="r", shape=(n,))
    return np.fromfile(path, dtype=REC, count=n)


def segments(rec: np.ndarray, market: str) -> list[list[int]]:
    """Rentang waktu (UTC ms) yang datanya bersambung."""
    if len(rec) == 0:
        return []
    t = np.asarray(rec["t"])
    gap = SEGMENT_GAP_MS.get(market, SEGMENT_GAP_MS["default"])
    cut = np.flatnonzero(np.diff(t) > gap)
    starts = np.concatenate([[0], cut + 1])
    ends = np.concatenate([cut, [len(t) - 1]])
    return [[int(t[a]), int(t[b])] for a, b in zip(starts, ends)]


def derive(root: Path, market: str, symbol: str, base_tf: str, targets: list[str]) -> None:
    """Bangun timeframe turunan dari ``base_tf`` (misalnya 1m → 5m, 1h, 1d, ...)."""
    base = read_series(series_path(root, market, symbol, base_tf), mmap=True)
    origin = MARKETS[market].origin_ms
    for tf in targets:
        if rank(tf) <= rank(base_tf):
            continue
        write_series(series_path(root, market, symbol, tf), aggregate(base, tf, origin))
    del base


# ---------------------------------------------------------------- katalog
_catalog_lock = threading.Lock()


def _catalog_file(root: Path) -> Path:
    return root / "catalog.json"


def load_catalog(root: Path) -> dict[str, Any]:
    try:
        return json.loads(_catalog_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "assets": {}}


def update_catalog_asset(root: Path, market: str, symbol: str, native: set[str]) -> dict[str, Any] | None:
    """Hitung ulang info satu aset dari file di disk lalu simpan ke katalog."""
    folder = root / "series" / market / symbol
    info: dict[str, Any] = {"market": market, "symbol": symbol, "name": asset_name(market, symbol), "series": {}}
    if folder.is_dir():
        for f in sorted(folder.glob("*.bin")):
            tf = f.stem
            rec = read_series(f, mmap=True)
            if len(rec) == 0:
                continue
            info["series"][tf] = {
                "n": int(len(rec)),
                "t0": int(rec["t"][0]), "t1": int(rec["t"][-1]),
                "native": tf in native,
                "segments": segments(rec, market),
            }
            del rec
    key = f"{market}:{symbol}"
    with _catalog_lock:
        cat = load_catalog(root)
        if info["series"]:
            cat["assets"][key] = info
        else:
            cat["assets"].pop(key, None)
        cat["updated"] = int(time.time())
        root.mkdir(parents=True, exist_ok=True)
        tmp = _catalog_file(root).with_suffix(".tmp")
        tmp.write_text(json.dumps(cat, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, _catalog_file(root))
    return info if info["series"] else None


# ---------------------------------------------------------------- pembaca untuk server
class CandleStore:
    """Membaca katalog & series. Otomatis memuat ulang kalau katalog diperbarui pengunduh."""

    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self._mtime = -1.0
        self._catalog: dict[str, Any] = {"assets": {}}
        self._cache: dict[tuple[str, str], tuple[float, np.ndarray]] = {}
        self._lock = threading.Lock()

    def catalog(self) -> dict[str, Any]:
        f = _catalog_file(self.root)
        try:
            m = f.stat().st_mtime
        except OSError:
            m = 0.0
        if m != self._mtime:
            with self._lock:
                self._catalog = load_catalog(self.root)
                self._mtime = m
        return self._catalog

    def assets(self) -> dict[str, Any]:
        return self.catalog().get("assets", {})

    def asset(self, key: str) -> dict[str, Any] | None:
        return self.assets().get(key)

    def series(self, key: str, tf: str) -> np.ndarray:
        info = self.asset(key)
        if not info or tf not in info["series"]:
            return np.empty(0, REC)
        market, symbol = info["market"], info["symbol"]
        path = series_path(self.root, market, symbol, tf)
        try:
            m = path.stat().st_mtime
        except OSError:
            return np.empty(0, REC)
        ck = (key, tf)
        with self._lock:
            hit = self._cache.get(ck)
            if hit and hit[0] == m:
                return hit[1]
            arr = read_series(path, mmap=True)
            self._cache[ck] = (m, arr)
            return arr

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, a in self.assets().items():
            m = a["market"]
            spec = MARKETS.get(m)
            if spec is None:
                continue
            tfs = [tf for tf in spec.tfs if tf in a["series"]]
            if not tfs:
                continue
            out.setdefault(m, {"id": m, "nama": spec.nama, "currency": spec.currency, "assets": []})
            out[m]["assets"].append({
                "id": key, "symbol": a["symbol"], "name": a["name"], "tfs": tfs,
                "candles": int(sum(s["n"] for s in a["series"].values())),
                "range": {tf: [a["series"][tf]["t0"], a["series"][tf]["t1"]] for tf in tfs},
            })
        for m in out.values():
            m["assets"].sort(key=lambda x: x["symbol"])
        return out
