"""Menjalankan satu backtest: muat data → siapkan → simulasi candle demi candle → statistik → simpan hasil."""

from __future__ import annotations

import json
import math
import secrets
import time
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from ..trading.derivatives import default_schedule
from ..trading.markets import MARKETS, asset_name
from ..trading.products import product_for
from ..trading.store import CandleStore, data_dir
from .broker import Broker, BrokerConfig
from .data import Eksternal, annual_periods, load_candles, market_assets, tf_ms
from .metrics import clean, downsample, equity_stats, monthly, trade_stats
from .strategy import (MAKS_BAR, Ctx, StrategyError, call_siapkan, load_module, lookahead_check, now_iso,
                       read_meta, resolve_params, resolve_path, resolve_settings)

Progress = Callable[[float, str], None]
MAKS_TOTAL_BAR = 4_000_000


def hasil_dir() -> Path:
    return data_dir().parent / "backtest"


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def _strategy_error(e: BaseException, path: Path) -> StrategyError:
    tb = traceback.extract_tb(e.__traceback__)
    lines = [f"baris {f.lineno}: {f.line}" for f in tb if Path(f.filename).name == path.name]
    where = f" ({lines[-1]})" if lines else ""
    return StrategyError(f"Error di strategi{where}: {type(e).__name__}: {e}")


def _symbols(store: CandleStore, s: dict[str, Any], warnings: list[str]) -> list[str]:
    market, tf = s["pasar"], s["timeframe"]
    avail = market_assets(store, market, tf)
    a = s["aset"]
    if a in (None, "", "semua", "*"):
        if len(avail) > s["maks_aset"]:
            warnings.append(f"Aset dibatasi {s['maks_aset']} pertama dari {len(avail)} (ubah 'maks_aset').")
        syms = avail[: s["maks_aset"]]
    else:
        raw = a if isinstance(a, list) else str(a).split(",")
        syms = []
        for x in raw:
            x = str(x).strip().upper()
            if not x:
                continue
            if x not in avail:
                warnings.append(f"{x}: tidak ada data {tf} di pasar {MARKETS[market].nama}, dilewati.")
                continue
            syms.append(x)
    if not syms:
        hint = ", ".join(avail[:15]) or "belum ada (unduh data dulu)"
        raise StrategyError(f"Tidak ada aset yang bisa dipakai. Aset {MARKETS[market].nama} dengan data {tf}: {hint}.")
    return syms


def _funding_sched(store: CandleStore, market: str, sym: str, rate: float, hours: int):
    dflt = default_schedule(rate, hours)
    arr = store.funding(f"{market}:{sym}") if market == "crypto" else None
    if arr is None or len(arr) == 0:
        return dflt
    ts = np.asarray(arr["t"], dtype=np.int64) // 1000
    rs = np.asarray(arr["r"], dtype=np.float64)
    lo, hi, gap = int(ts[0]), int(ts[-1]), hours * 3600

    def sched(t0: int, t1: int):
        a, b = int(np.searchsorted(ts, t0, side="right")), int(np.searchsorted(ts, t1, side="right"))
        out = list(zip(ts[a:b].tolist(), rs[a:b].tolist()))
        out += [(t, r) for t, r in dflt(t0, t1) if t < lo - gap or t > hi + gap]
        out.sort()
        return out
    return sched


def _broker(s: dict[str, Any], syms: list[str]) -> Broker:
    spec = MARKETS[s["pasar"]]
    prods = {}
    if s["produk"] != "spot":
        for sym in syms:
            prods[sym] = product_for(s["pasar"], s["produk"], sym, s["aturan"])
    pct = lambda v: None if v is None else float(v)  # noqa: E731
    if s["produk"] == "futures":
        fb = fs = pct(s["fee_taker"])
        mk = pct(s["fee_maker"])
    else:
        fb, fs, mk = pct(s["fee_beli"]), pct(s["fee_jual"]), None
    cfg = BrokerConfig(market=spec, produk=s["produk"], products=prods, capital=s["modal"], leverage=s["leverage"],
                       margin_mode=s["margin"], slippage=s["slippage"], fee_buy=fb, fee_sell=fs, maker=mk,
                       interest_apr=pct(s["bunga"]), borrow_apr=pct(s["biaya_pinjam"]), qty_step=spec.qty_step,
                       min_notional=spec.min_notional)
    b = Broker(cfg, syms)
    if s["produk"] != "spot" and s["leverage"] > b.lev:
        b.note(f"Leverage {s['leverage']:g}× melebihi batas produk, dipakai {b.lev:g}×.")
    return b


def simulate(mod, p, s: dict[str, Any], syms: list[str], dfs: dict[str, pd.DataFrame], starts: dict[str, int],
             lts: dict[str, np.ndarray], ekstra: Eksternal, store: CandleStore, path: Path,
             progress: Progress | None = None, prog_lo: float = 0.0, prog_hi: float = 1.0) -> dict[str, Any]:
    broker = _broker(s, syms)
    tfm = tf_ms(s["timeframe"])
    t_arr = {a: dfs[a].index.as_unit("ms").asi8 for a in syms}
    T = np.unique(np.concatenate([t_arr[a][starts[a]:] for a in syms]))
    if len(T) < 2:
        raise StrategyError("Candle di rentang ini terlalu sedikit.")
    pos_at = {a: np.searchsorted(t_arr[a], T, side="left") for a in syms}
    has = {a: (pos_at[a] < len(t_arr[a])) & (t_arr[a][np.minimum(pos_at[a], len(t_arr[a]) - 1)] == T) for a in syms}
    le = {a: np.searchsorted(t_arr[a], T, side="right") - 1 for a in syms}
    O = {a: dfs[a]["open"].to_numpy(float) for a in syms}
    H = {a: dfs[a]["high"].to_numpy(float) for a in syms}
    L = {a: dfs[a]["low"].to_numpy(float) for a in syms}
    C = {a: dfs[a]["close"].to_numpy(float) for a in syms}
    cols = {a: {c: dfs[a][c].to_numpy() for c in dfs[a].columns} for a in syms}
    sub = {a: dfs[a] for a in syms}
    ctx = Ctx(broker, sub, cols, ekstra, tfm, s)
    sched = {}
    if broker.kind == "perp":
        for a in syms:
            pr = broker.prod(a)
            sched[a] = _funding_sched(store, s["pasar"], a, pr.funding, pr.funding_hours)
    prev_t = {a: None for a in syms}
    prev_day = None
    curve_eq = np.empty(len(T))
    n_exposed = 0
    langkah = mod.langkah
    step_every = max(1, len(T) // 50)
    for k in range(len(T)):
        ts = int(T[k] // 1000)
        broker.t_now = ts
        if broker.kind == "margin":
            a0 = next((a for a in syms if has[a][k]), None)
            if a0 is not None:
                day = int(lts[a0][pos_at[a0][k]] // 86_400_000)
                if prev_day is not None and day > prev_day:
                    broker.day(day - prev_day)
                prev_day = day if prev_day is None else max(prev_day, day)
        worst: dict[str, float] = {}
        active = [a for a in syms if has[a][k]]
        for a in active:
            i = int(pos_at[a][k])
            if broker.kind == "perp" and prev_t[a] is not None:
                for _, rate in sched[a](prev_t[a], ts):
                    broker.funding(a, rate, O[a][i])
            prev_t[a] = ts
        if len(active) > 1:
            for a in active:
                broker.open_reducing(a, O[a][int(pos_at[a][k])], ts)
        for a in active:
            i = int(pos_at[a][k])
            broker.bar(a, O[a][i], H[a][i], L[a][i], C[a][i], ts)
            q = broker.pos[a].qty
            worst[a] = L[a][i] if q > 0 else H[a][i]
        if worst:
            broker.cross_check(worst, ts)
        curve_eq[k] = broker.equity()
        if broker.n_open():
            n_exposed += 1
        if k < len(T) - 1:
            ctx._cur = {a: int(le[a][k]) for a in syms}
            ctx._has = {a: bool(has[a][k]) for a in syms}
            ctx.waktu = pd.Timestamp(int(T[k]), unit="ms", tz="UTC")
            ctx.i = k
            try:
                langkah(ctx, p)
            except Exception as e:  # noqa: BLE001
                raise _strategy_error(e, path) from None
        if progress and k % step_every == 0:
            progress(prog_lo + (prog_hi - prog_lo) * k / len(T), f"simulasi {', '.join(syms[:3])}{'…' if len(syms) > 3 else ''}")
    last_ts = int(T[-1] // 1000)
    broker.close_all(last_ts)
    curve_eq[-1] = broker.equity()
    # beli-lalu-tahan, bobot sama
    ratios = []
    for a in syms:
        idx = le[a]
        valid = idx >= 0
        if not valid.any():
            continue
        first = C[a][idx[valid][0]]
        r = np.where(valid, C[a][np.maximum(idx, 0)] / first, 1.0)
        ratios.append(r)
    bh = s["modal"] * (np.mean(ratios, axis=0) if ratios else np.ones(len(T)))
    return {
        "syms": syms, "t": T // 1000, "eq": curve_eq, "bh": bh, "broker": broker, "logs": ctx.logs,
        "exposure_pct": n_exposed / len(T) * 100,
    }


def _stats(sim: dict[str, Any], s: dict[str, Any]) -> dict[str, Any]:
    b: Broker = sim["broker"]
    st = equity_stats(sim["t"], sim["eq"], s["modal"], annual_periods(s["pasar"]))
    st.update(trade_stats(b.trades))
    st.update({
        "buy_hold_pct": (sim["bh"][-1] / s["modal"] - 1) * 100, "exposure_pct": sim["exposure_pct"],
        "fees": b.fees_paid, "funding": b.funding_paid, "bunga": b.interest_paid, "biaya_pinjam": b.borrow_paid,
        "liq_loss": b.liq_loss, "n_likuidasi": b.n_liq, "modal": s["modal"],
    })
    return st


def _chart(sim: dict[str, Any], sym: str, df: pd.DataFrame, start: int, plot: list[str]) -> dict[str, Any]:
    lo = max(0, start - 200)
    part = df.iloc[lo:]
    t = part.index.as_unit("s").asi8.tolist()

    def col(name: str) -> list[float | None]:
        v = pd.to_numeric(part[name], errors="coerce").to_numpy(float)
        return [None if not math.isfinite(x) else round(float(x), 8) for x in v]

    b: Broker = sim["broker"]
    fills = [f.__dict__ for f in b.fills if f.sym == sym][-20_000:]
    return clean({
        "simbol": sym, "t": t, "o": col("open"), "h": col("high"), "l": col("low"), "c": col("close"), "v": col("volume"),
        "mulai": int(df.index.as_unit("s").asi8[start]),
        "plot": {c: col(c) for c in plot if c in part.columns and pd.api.types.is_numeric_dtype(part[c])},
        "fills": fills, "trades": [t for t in b.trades if t["sym"] == sym][-5000:],
    })


def run(strategy: str | Path, override: dict[str, Any] | None = None, params: dict[str, Any] | None = None,
        store: CandleStore | None = None, out_dir: Path | None = None, progress: Progress | None = None,
        run_id: str | None = None) -> dict[str, Any]:
    t0 = time.time()
    prog = progress or (lambda f, m: None)
    path = resolve_path(str(strategy))
    meta = read_meta(path)
    prog(0.01, "memuat strategi")
    try:
        mod = load_module(path)
    except StrategyError:
        raise
    except Exception as e:  # noqa: BLE001
        raise _strategy_error(e, path) from None
    s = resolve_settings(getattr(mod, "PENGATURAN", {}) or {}, override)
    p = resolve_params(getattr(mod, "PARAMETER", {}) or {}, params)
    plot = [str(x) for x in (getattr(mod, "PLOT", []) or [])]
    store = store or CandleStore()
    warnings: list[str] = []
    syms = _symbols(store, s, warnings)
    tfm = tf_ms(s["timeframe"])
    ekstra = Eksternal(tf_ms=tfm)
    dfs: dict[str, pd.DataFrame] = {}
    starts: dict[str, int] = {}
    lts: dict[str, np.ndarray] = {}
    total = 0
    for n, sym in enumerate(syms):
        prog(0.02 + 0.18 * n / len(syms), f"menyiapkan {sym}")
        try:
            df, st, lt = load_candles(store, s["pasar"], sym, s["timeframe"], s["mulai_ms"], s["selesai_ms"], s["pemanasan"])
        except ValueError as e:
            warnings.append(str(e))
            continue
        if len(df) - st > MAKS_BAR:
            raise StrategyError(f"{sym}: {len(df) - st:,} candle terlalu banyak (maks {MAKS_BAR:,}). "
                                "Persempit rentang tanggal atau pakai timeframe lebih besar.".replace(",", "."))
        total += len(df)
        if total > MAKS_TOTAL_BAR:
            raise StrategyError("Total candle semua aset terlalu banyak. Kurangi aset, rentang tanggal, atau naikkan timeframe.")
        df.attrs.update({"simbol": sym, "pasar": s["pasar"], "timeframe": s["timeframe"]})
        raw = df.copy()
        try:
            out = call_siapkan(mod, df, p, ekstra)
        except StrategyError:
            raise
        except Exception as e:  # noqa: BLE001
            raise _strategy_error(e, path) from None
        if not dfs:
            warnings += lookahead_check(mod, raw, p, ekstra, st, out)
        dfs[sym], starts[sym], lts[sym] = out, st, lt
    if not dfs:
        raise StrategyError("Tidak ada aset dengan data di rentang ini. " + " ".join(warnings[:3]))
    used = list(dfs)
    if s["mode"] == "portofolio":
        sims = [simulate(mod, p, s, used, dfs, starts, lts, ekstra, store, path, prog, 0.2, 0.95)]
    else:
        sims = []
        for n, sym in enumerate(used):
            lo = 0.2 + 0.75 * n / len(used)
            sims.append(simulate(mod, p, s, [sym], {sym: dfs[sym]}, starts, lts, ekstra, store, path, prog,
                                 lo, lo + 0.75 / len(used)))
    prog(0.96, "menghitung statistik")
    rid = run_id or new_id()
    per_aset, trades, logs = [], [], []
    for sim in sims:
        b: Broker = sim["broker"]
        st = _stats(sim, s)
        trades += b.trades
        logs += b.log[:500] + sim["logs"][:500]
        if s["mode"] == "per_aset":
            sym = sim["syms"][0]
            per_aset.append({"simbol": sym, "nama": asset_name(s["pasar"], sym), **{k: st.get(k) for k in (
                "return_pct", "buy_hold_pct", "max_dd_pct", "sharpe", "cagr_pct", "n_trades", "win_rate",
                "profit_factor", "fees", "funding", "n_likuidasi", "exposure_pct")}})
    if s["mode"] == "portofolio":
        sim = sims[0]
        ringkasan = _stats(sim, s)
        kurva = downsample(sim["t"], sim["eq"], sim["bh"])
        bulanan = monthly(sim["t"], sim["eq"], s["modal"])
        b = sim["broker"]
        for sym in used:
            tr = [t for t in b.trades if t["sym"] == sym]
            ts = trade_stats(tr)
            c = dfs[sym]["close"].to_numpy(float)
            per_aset.append({"simbol": sym, "nama": asset_name(s["pasar"], sym), "n_trades": ts["n_trades"],
                             "win_rate": ts["win_rate"], "profit_factor": ts["profit_factor"],
                             "laba": sum(t["pnl"] for t in tr), "buy_hold_pct": (c[-1] / c[starts[sym]] - 1) * 100,
                             "fees": sum(t["fees"] for t in tr)})
    else:
        # rata-rata kurva ekuitas tiap aset (masing-masing modal penuh) → gambaran umum strategi
        series = [pd.Series(sim["eq"] / s["modal"], index=sim["t"]) for sim in sims]
        bhs = [pd.Series(sim["bh"] / s["modal"], index=sim["t"]) for sim in sims]
        eqm = pd.concat(series, axis=1).sort_index().ffill().fillna(1.0).mean(axis=1) * s["modal"]
        bhm = pd.concat(bhs, axis=1).sort_index().ffill().fillna(1.0).mean(axis=1) * s["modal"]
        t_all = eqm.index.to_numpy(np.int64)
        kurva = downsample(t_all, eqm.to_numpy(float), bhm.to_numpy(float))
        bulanan = monthly(t_all, eqm.to_numpy(float), s["modal"])
        ringkasan = equity_stats(t_all, eqm.to_numpy(float), s["modal"], annual_periods(s["pasar"]))
        ringkasan.update(trade_stats(trades))
        rets = [r["return_pct"] for r in per_aset if r["return_pct"] is not None]
        ringkasan.update({
            "buy_hold_pct": (bhm.iloc[-1] / s["modal"] - 1) * 100, "modal": s["modal"],
            "median_return_pct": float(np.median(rets)) if rets else None,
            "aset_untung_pct": sum(1 for r in rets if r > 0) / len(rets) * 100 if rets else None,
            "fees": sum(sim["broker"].fees_paid for sim in sims),
            "funding": sum(sim["broker"].funding_paid for sim in sims),
            "bunga": sum(sim["broker"].interest_paid for sim in sims),
            "biaya_pinjam": sum(sim["broker"].borrow_paid for sim in sims),
            "n_likuidasi": sum(sim["broker"].n_liq for sim in sims),
            "exposure_pct": float(np.mean([sim["exposure_pct"] for sim in sims])),
        })
    trades.sort(key=lambda t: (t["exit_time"], t["sym"]))
    spec = MARKETS[s["pasar"]]
    settings_pub = {k: v for k, v in s.items() if not k.endswith("_ms")}
    result = {
        "id": rid, "versi": 1, "strategi": path.name, "judul": meta.get("judul") or meta.get("nama_tampil") or path.stem,
        "deskripsi": meta.get("deskripsi", ""), "dibuat": now_iso(), "durasi_detik": round(time.time() - t0, 2),
        "pengaturan": settings_pub, "parameter": dict(p), "plot": plot, "mode": s["mode"], "pasar": s["pasar"],
        "pasar_nama": spec.nama, "currency": spec.currency, "timeframe": s["timeframe"], "aset": used,
        "peringatan": warnings, "ringkasan": ringkasan, "kurva": kurva, "bulanan": bulanan, "per_aset": per_aset,
        "transaksi": trades[-5000:], "n_transaksi": len(trades), "log": logs[:1500],
    }
    result = clean(result)
    if out_dir is not None:
        out = Path(out_dir)
        (out / "aset").mkdir(parents=True, exist_ok=True)
        for sim in sims:
            for sym in sim["syms"]:
                data = _chart(sim, sym, dfs[sym], starts[sym], plot)
                (out / "aset" / f"{sym}.json").write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        tmp = out / "hasil.json.tmp"
        tmp.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        tmp.replace(out / "hasil.json")
    prog(1.0, "selesai")
    return result
