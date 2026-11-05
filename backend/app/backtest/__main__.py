"""CLI backtest.

    python -m app.backtest daftar
    python -m app.backtest jalankan contoh_ema_cross --set aset=BTCUSDT,ETHUSDT --set mulai=2023-01-01 --param cepat=10
    python -m app.backtest jalankan strategi/punyaku.py --keluaran hasil/

``--set`` mengubah PENGATURAN, ``--param`` mengubah PARAMETER. Hasil lengkap (dibuka di tab Backtest) disimpan di
``data/backtest/<id>/`` kecuali ``--keluaran`` diisi.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import hasil_dir, new_id, run
from .strategy import StrategyError, list_strategies


def _kv(items: list[str] | None) -> dict[str, str]:
    out = {}
    for it in items or []:
        if "=" not in it:
            sys.exit(f"Format harus kunci=nilai: {it}")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _num(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def fmt(v, suffix="", dec=2):
    return "–" if v is None else f"{v:,.{dec}f}{suffix}"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m app.backtest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("daftar", help="daftar file strategi")
    j = sub.add_parser("jalankan", help="jalankan backtest")
    j.add_argument("strategi")
    j.add_argument("--set", action="append", help="ubah PENGATURAN, misalnya --set timeframe=1h")
    j.add_argument("--param", action="append", help="ubah PARAMETER, misalnya --param cepat=10")
    j.add_argument("--keluaran", help="folder hasil (default data/backtest/<id>)")
    j.add_argument("--id")
    j.add_argument("--json-input", help="file JSON berisi {pengaturan, parameter} (dipakai server)")
    j.add_argument("--progres-json", action="store_true", help="cetak progres sebagai baris JSON (dipakai server)")
    a = ap.parse_args(argv)

    if a.cmd == "daftar":
        for m in list_strategies():
            status = f"  ERROR: {m['error']}" if m["error"] else ""
            print(f"{m['file']:<34} {m.get('judul', '')}{status}")
        return

    override = {k: _num(v) for k, v in _kv(a.set).items()}
    if "aset" in override and isinstance(override["aset"], str) and override["aset"] not in ("semua", "*"):
        override["aset"] = [x for x in override["aset"].split(",") if x]
    params = _kv(a.param)
    if a.json_input:
        cfg = json.loads(Path(a.json_input).read_text(encoding="utf-8"))
        override.update(cfg.get("pengaturan") or {})
        params.update(cfg.get("parameter") or {})
    rid = a.id or new_id()
    out = Path(a.keluaran) if a.keluaran else hasil_dir() / rid

    def progress(f: float, msg: str) -> None:
        if a.progres_json:
            print(json.dumps({"progres": round(f, 4), "pesan": msg}), flush=True)

    try:
        res = run(a.strategi, override, params, out_dir=out, progress=progress, run_id=rid)
    except StrategyError as e:
        if a.progres_json:
            print(json.dumps({"error": str(e)}), flush=True)
        else:
            print(f"Gagal: {e}", file=sys.stderr)
        sys.exit(2)
    if a.progres_json:
        print(json.dumps({"selesai": rid}), flush=True)
        return
    r = res["ringkasan"]
    cur = res["currency"]
    print(f"\n{res['judul']}  ({res['strategi']}, {res['pasar_nama']} {res['timeframe']}, {res['mode']}, {len(res['aset'])} aset)")
    for w in res["peringatan"]:
        print(f"  ! {w}")
    print(f"  Return        {fmt(r.get('return_pct'), '%')}   (beli-tahan {fmt(r.get('buy_hold_pct'), '%')})")
    print(f"  CAGR          {fmt(r.get('cagr_pct'), '%')}   Max drawdown {fmt(r.get('max_dd_pct'), '%')}")
    print(f"  Sharpe        {fmt(r.get('sharpe'))}   Sortino {fmt(r.get('sortino'))}")
    print(f"  Transaksi     {r.get('n_trades')}   win rate {fmt(r.get('win_rate'), '%', 1)}   profit factor {fmt(r.get('profit_factor'))}")
    print(f"  Fee           {fmt(r.get('fees'))} {cur}   funding {fmt(r.get('funding'))}   bunga {fmt(r.get('bunga'))}")
    if res["mode"] == "per_aset" and len(res["per_aset"]) > 1:
        print("\n  Per aset:")
        for x in sorted(res["per_aset"], key=lambda x: -(x["return_pct"] or -1e9)):
            print(f"    {x['simbol']:<10} {fmt(x['return_pct'], '%'):>10}  beli-tahan {fmt(x['buy_hold_pct'], '%'):>10}  "
                  f"DD {fmt(x['max_dd_pct'], '%'):>8}  {x['n_trades']} transaksi")
    print(f"\nHasil lengkap: {out}  (buka tab Backtest di Kilas Pasar, id {rid})")


if __name__ == "__main__":
    main()
