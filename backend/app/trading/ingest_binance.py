"""Unduh candle kripto dari arsip publik Binance (data.binance.vision).

File zip diambil langsung dari bucket S3-nya. Kalau gagal, dicoba lewat domain CDN.
Format CSV: open_time, open, high, low, close, volume, close_time, ... (12 kolom).
Mulai 2025 kolom waktu memakai mikrodetik; di sini semuanya diubah ke milidetik.
"""

from __future__ import annotations

import io
import re
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree as ET

import numpy as np

from .markets import MARKETS
from .store import derive, read_series, series_path, update_catalog_asset, write_series
from .timeframes import REC, dedupe_sorted

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CDN = "https://data.binance.vision"
UA = {"User-Agent": "suit-bot-arena-kilas-pasar/1.0"}
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

Log = Callable[[str], None]


def _get(url: str, timeout: float = 60, tries: int = 4) -> bytes:
    last: Exception | None = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
        time.sleep(1.5 * (2 ** i))
    raise last if last else RuntimeError(url)


def list_keys(prefix: str) -> list[str]:
    """Daftar file di bucket arsip Binance (dengan paginasi)."""
    keys: list[str] = []
    marker = ""
    while True:
        url = f"{S3}?delimiter=/&prefix={prefix}" + (f"&marker={marker}" if marker else "")
        root = ET.fromstring(_get(url))
        batch = [c.findtext("s3:Key", namespaces=NS) or "" for c in root.findall("s3:Contents", NS)]
        keys += [k for k in batch if k]
        if (root.findtext("s3:IsTruncated", namespaces=NS) or "false") != "true" or not batch:
            return keys
        marker = batch[-1]


def download_zip(key: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = _get(f"{S3}/{key}")
    except Exception:  # noqa: BLE001 - coba lewat CDN
        data = _get(f"{CDN}/{key}")
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def parse_zip(path: Path) -> np.ndarray:
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv"))
        raw = zf.read(name).decode("utf-8", "replace")
    lines = raw.splitlines()
    skip = 1 if lines and not lines[0][:1].isdigit() else 0  # beberapa file punya header
    if len(lines) <= skip:
        return np.empty(0, REC)
    arr = np.loadtxt(io.StringIO(raw), delimiter=",", usecols=range(6), skiprows=skip, dtype=np.float64, ndmin=2)
    t = arr[:, 0].astype(np.int64)
    t = np.where(t > 10**14, t // 1000, t)  # mikrodetik → milidetik
    rec = np.empty(len(arr), REC)
    rec["t"] = t
    rec["lt"] = t  # kripto memakai UTC
    rec["o"], rec["h"], rec["l"], rec["c"], rec["v"] = arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4], arr[:, 5]
    return rec


_MONTH = re.compile(r"-(\d{4})-(\d{2})\.zip$")
_DAY = re.compile(r"-(\d{4})-(\d{2})-(\d{2})\.zip$")


def ingest_symbol(root: Path, symbol: str, since: str | None, log: Log, workers: int = 8,
                  keep_raw: bool = True) -> bool:
    """Unduh/lengkapi 1m untuk satu simbol, lalu bangun semua timeframe turunan."""
    path = series_path(root, "crypto", symbol, "1m")
    existing = read_series(path, mmap=False)
    last_t = int(existing["t"][-1]) if len(existing) else None

    monthly = [k for k in list_keys(f"data/spot/monthly/klines/{symbol}/1m/") if k.endswith(".zip")]
    if not monthly:
        log(f"  {symbol}: tidak ada data di arsip Binance, dilewati")
        return False

    def month_of(k: str) -> str:
        m = _MONTH.search(k)
        return f"{m.group(1)}-{m.group(2)}" if m else ""

    want: list[str] = []
    for k in monthly:
        ym = month_of(k)
        if since and ym < since:
            continue
        if last_t is not None:
            end_of_month = datetime.strptime(ym + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
            nxt = (end_of_month.replace(year=end_of_month.year + 1, month=1) if end_of_month.month == 12
                   else end_of_month.replace(month=end_of_month.month + 1))
            if nxt.timestamp() * 1000 <= last_t + 60_000:
                continue  # bulan ini sudah lengkap di disk
        want.append(k)

    # hari-hari setelah bulan terakhir yang ada di arsip bulanan
    last_month = month_of(monthly[-1])
    y, m = map(int, last_month.split("-"))
    now = datetime.now(timezone.utc)
    daily: list[str] = []
    yy, mm = (y + 1, 1) if m == 12 else (y, m + 1)
    recent = (now.year * 12 + now.month) - (y * 12 + m) <= 2  # simbol yang sudah delisting tidak punya file harian baru
    while recent and (yy, mm) <= (now.year, now.month):
        daily += [k for k in list_keys(f"data/spot/daily/klines/{symbol}/1m/{symbol}-1m-{yy:04d}-{mm:02d}")
                  if k.endswith(".zip")]
        yy, mm = (yy + 1, 1) if mm == 12 else (yy, mm + 1)
    if last_t is not None:
        cutoff = datetime.fromtimestamp(last_t / 1000, timezone.utc).strftime("%Y-%m-%d")
        daily = [k for k in daily if (d := _DAY.search(k)) and f"{d.group(1)}-{d.group(2)}-{d.group(3)}" >= cutoff]

    keys = want + daily
    if not keys:
        log(f"  {symbol}: sudah terbaru ({len(existing):,} candle 1m)")
        return True
    log(f"  {symbol}: mengunduh {len(keys)} file ({len(want)} bulanan, {len(daily)} harian)…")
    raw_dir = root / "raw" / "binance" / symbol
    parts: list[np.ndarray] = []
    failed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(download_zip, k, raw_dir / Path(k).name): k for k in keys}
        for f in as_completed(futs):
            try:
                p = f.result()
                parts.append(parse_zip(p))
                if not keep_raw:
                    p.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                failed += 1
                log(f"    gagal: {Path(futs[f]).name} ({e})")
    if not parts:
        return False
    # file bulanan/harian tidak saling tumpang tindih: cukup diurutkan per file (hemat memori).
    parts = sorted((p for p in parts if len(p)), key=lambda r: int(r["t"][0]))
    merged = np.concatenate([existing] + parts)
    del parts
    t = merged["t"]
    if len(t) > 1 and not bool(np.all(t[1:] > t[:-1])):
        merged = dedupe_sorted(merged)
    write_series(path, merged)
    derive(root, "crypto", symbol, "1m", list(MARKETS["crypto"].tfs))
    update_catalog_asset(root, "crypto", symbol, native={"1m"})
    log(f"  {symbol}: {len(merged):,} candle 1m tersimpan" + (f" ({failed} file gagal)" if failed else ""))
    return True
