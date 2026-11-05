"""Pengunduh data pasar untuk Kilas Pasar.

Contoh:
    python -m app.trading.unduh semua --preset cepat     # ±beberapa menit, cukup untuk mulai main
    python -m app.trading.unduh semua --preset penuh     # semua aset, kripto 1m sejak 2017 (puluhan GB)
    python -m app.trading.unduh kripto --simbol BTCUSDT,ETHUSDT --mulai 2020-01
    python -m app.trading.unduh idx --simbol BBCA,TLKM
    python -m app.trading.unduh saham --preset penuh     # IDX + US saja (tanpa kripto)
    python -m app.trading.unduh funding                  # riwayat funding rate untuk kripto yang sudah ada
    python -m app.trading.unduh update                   # lengkapi semua aset yang sudah ada

Urutan "semua": saham IDX & US dulu (beberapa menit), baru kripto (bisa berjam-jam di preset penuh),
supaya saham tetap tersedia walaupun unduhan kripto dihentikan di tengah jalan.
    python -m app.trading.unduh contoh                   # data buatan, tanpa internet
    python -m app.trading.unduh status
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .markets import PRESETS
from .store import CandleStore, data_dir


def log(msg: str) -> None:
    print(msg, flush=True)


class Lock:
    def __init__(self, root: Path):
        self.path = root / ".unduh.lock"

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if age < 6 * 3600:
                sys.exit("Pengunduh lain sedang berjalan (hapus file .unduh.lock kalau yakin tidak ada).")
        self.path.write_text(str(os.getpid()))
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def run_crypto(root: Path, symbols: list[str], since: str | None, workers: int, keep_raw: bool) -> None:
    from .ingest_binance import ingest_symbol

    log(f"== Kripto (Binance): {len(symbols)} aset" + (f", mulai {since}" if since else ", sejak awal"))
    for i, s in enumerate(symbols, 1):
        log(f"[{i}/{len(symbols)}] {s}")
        try:
            ok = ingest_symbol(root, s.upper(), since, log, workers=workers, keep_raw=keep_raw)
        except Exception as e:  # noqa: BLE001
            log(f"  {s}: gagal ({e})")
            continue
        if ok:
            run_funding(root, s.upper(), workers)


def run_funding(root: Path, symbol: str, workers: int = 8) -> None:
    """Riwayat funding rate untuk mode Futures. Kalau gagal, game memakai 0,01% per 8 jam."""
    from .ingest_binance import ingest_funding

    try:
        n = ingest_funding(root, symbol, log, workers=workers)
    except Exception as e:  # noqa: BLE001
        log(f"  {symbol}: funding rate tidak terunduh ({e}); mode Futures memakai 0,01%/8 jam")
        return
    log(f"  {symbol}: {n:,} data funding rate" if n else f"  {symbol}: tidak ada data funding (bukan perpetual?), "
        "mode Futures memakai 0,01%/8 jam")


def run_yahoo(root: Path, market: str, symbols: list[str]) -> None:
    try:
        from .ingest_yahoo import ingest_symbol
    except ImportError:
        log("yfinance belum terpasang: pip install -r requirements.txt")
        return
    label = {"idx": "Saham IDX", "us": "Saham US"}[market]
    log(f"== {label} (Yahoo Finance): {len(symbols)} aset")
    for i, s in enumerate(symbols, 1):
        log(f"[{i}/{len(symbols)}] {s}")
        try:
            ingest_symbol(root, market, s.upper(), log)
        except Exception as e:  # noqa: BLE001
            log(f"  {s}: gagal ({e})")


def status(root: Path) -> None:
    store = CandleStore(root)
    summ = store.summary()
    if not summ:
        log("Belum ada data. Jalankan: python -m app.trading.unduh semua --preset cepat")
        return
    for m, label in (("idx", "Saham IDX"), ("us", "Saham US")):
        if m not in summ:
            log(f"{label:<12}    0 aset  (belum diunduh: python -m app.trading.unduh saham)")
    total = 0
    for m in summ.values():
        n = sum(a["candles"] for a in m["assets"])
        total += n
        log(f"{m['nama']:<12} {len(m['assets']):>4} aset  {n:>14,} candle")
    size = sum(f.stat().st_size for f in (root / "series").rglob("*.bin")) if (root / "series").exists() else 0
    log(f"{'Total':<12} {'':>9} {total:>14,} candle  ({size / 1e9:.2f} GB di {root})")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m app.trading.unduh", description="Unduh data pasar untuk Kilas Pasar")
    p.add_argument("perintah", choices=["kripto", "idx", "us", "saham", "semua", "update", "funding", "contoh", "status"])
    p.add_argument("--preset", choices=list(PRESETS), default="cepat")
    p.add_argument("--simbol", help="daftar simbol dipisah koma (menggantikan preset)")
    p.add_argument("--mulai", help="kripto: bulan awal YYYY-MM")
    p.add_argument("--paralel", type=int, default=8, help="jumlah unduhan bersamaan (kripto)")
    p.add_argument("--hapus-mentah", action="store_true", help="hapus file zip setelah diproses")
    a = p.parse_args(argv)

    root = data_dir()
    if a.perintah == "status":
        status(root)
        return
    preset = PRESETS[a.preset]
    custom = [s.strip() for s in a.simbol.split(",") if s.strip()] if a.simbol else None
    started = time.time()
    with Lock(root):
        if a.perintah == "contoh":
            from .demo import build_demo
            log("== Data contoh")
            build_demo(root, log=log)
        elif a.perintah == "kripto":
            run_crypto(root, custom or preset.crypto, a.mulai or (None if custom else preset.crypto_since),
                       a.paralel, not a.hapus_mentah)
        elif a.perintah in ("idx", "us"):
            run_yahoo(root, a.perintah, custom or getattr(preset, a.perintah))
        elif a.perintah == "saham":
            run_yahoo(root, "idx", preset.idx)
            run_yahoo(root, "us", preset.us)
        elif a.perintah == "semua":
            # saham dulu: cepat (beberapa menit). Kripto belakangan karena preset penuh butuh berjam-jam.
            run_yahoo(root, "idx", preset.idx)
            run_yahoo(root, "us", preset.us)
            run_crypto(root, preset.crypto, a.mulai or preset.crypto_since, a.paralel, not a.hapus_mentah)
        elif a.perintah == "funding":
            syms = custom or sorted(x["symbol"] for x in CandleStore(root).assets().values() if x["market"] == "crypto")
            if not syms:
                log("Belum ada data kripto.")
            log(f"== Funding rate futures (Binance): {len(syms)} aset")
            for s in syms:
                run_funding(root, s.upper(), a.paralel)
        elif a.perintah == "update":
            assets = CandleStore(root).assets().values()
            by = {"crypto": [], "idx": [], "us": []}
            for x in assets:
                if x["market"] in by:
                    by[x["market"]].append(x["symbol"])
            if not any(by.values()):
                log("Belum ada data untuk di-update. Jalankan dulu: semua --preset cepat")
            for m in ("idx", "us"):
                if by[m]:
                    run_yahoo(root, m, by[m])
            if by["crypto"]:
                run_crypto(root, by["crypto"], None, a.paralel, not a.hapus_mentah)
    log(f"Selesai dalam {(time.time() - started) / 60:.1f} menit.")
    status(root)


if __name__ == "__main__":
    main()
