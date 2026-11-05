"""Statistik hasil backtest."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def equity_stats(t_sec: np.ndarray, eq: np.ndarray, capital: float, periods_per_year: int) -> dict[str, Any]:
    if len(eq) == 0:
        return {}
    final = float(eq[-1])
    ret = final / capital - 1
    span_days = max((t_sec[-1] - t_sec[0]) / 86_400, 1e-9) if len(t_sec) > 1 else 0.0
    years = span_days / 365.25
    cagr = (final / capital) ** (1 / years) - 1 if years >= 30 / 365.25 and final > 0 else None
    peak = np.maximum.accumulate(np.concatenate([[capital], eq]))[1:]
    dd = (peak - eq) / np.maximum(peak, 1e-12)
    max_dd = float(dd.max()) if len(dd) else 0.0
    # durasi drawdown terpanjang (hari)
    longest, start = 0.0, None
    for i, v in enumerate(dd):
        if v > 1e-12 and start is None:
            start = t_sec[i]
        elif v <= 1e-12 and start is not None:
            longest = max(longest, (t_sec[i] - start) / 86_400)
            start = None
    if start is not None:
        longest = max(longest, (t_sec[-1] - start) / 86_400)
    s = pd.Series(eq, index=pd.to_datetime(t_sec, unit="s", utc=True))
    daily = s.resample("1D").last().dropna()
    r = daily.pct_change().dropna()
    if periods_per_year == 252:
        r = r[r != 0] if len(r[r != 0]) > 5 else r  # hari libur bursa tidak dihitung
    sharpe = sortino = vol = None
    if len(r) > 2 and r.std() > 0:
        vol = float(r.std() * math.sqrt(periods_per_year))
        sharpe = float(r.mean() / r.std() * math.sqrt(periods_per_year))
        neg = r[r < 0]
        if len(neg) > 1 and neg.std() > 0:
            sortino = float(r.mean() / math.sqrt((neg ** 2).mean()) * math.sqrt(periods_per_year))
    calmar = (cagr / max_dd) if (cagr is not None and max_dd > 0) else None
    return {
        "return_pct": ret * 100, "equity": final, "cagr_pct": None if cagr is None else cagr * 100,
        "max_dd_pct": max_dd * 100, "dd_terlama_hari": longest, "sharpe": _f(sharpe), "sortino": _f(sortino),
        "calmar": _f(calmar), "volatilitas_pct": None if vol is None else vol * 100, "hari": span_days,
    }


def trade_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [t["pnl"] for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    pct = [t["pnl_pct"] for t in trades]
    hold = [t["exit_time"] - t["entry_time"] for t in trades if t.get("exit_time") is not None]
    gp, gl = sum(wins), -sum(losses)
    return {
        "n_trades": len(trades), "n_long": sum(1 for t in trades if t["side"] == "long"),
        "n_short": sum(1 for t in trades if t["side"] == "short"),
        "win_rate": len(wins) / len(pnls) * 100 if pnls else None,
        "profit_factor": (gp / gl) if gl > 0 else (None if not wins else math.inf),
        "rata_pct": (sum(pct) / len(pct)) if pct else None,
        "rata_untung_pct": (sum(p for p in pct if p > 0) / len(wins)) if wins else None,
        "rata_rugi_pct": (sum(p for p in pct if p <= 0) / len(losses)) if losses else None,
        "terbaik_pct": max(pct) if pct else None, "terburuk_pct": min(pct) if pct else None,
        "ekspektasi": (sum(pnls) / len(pnls)) if pnls else None,
        "rata_tahan_jam": (sum(hold) / len(hold) / 3600) if hold else None,
        "n_likuidasi": sum(1 for t in trades if t.get("liquidated")),
    }


def monthly(t_sec: np.ndarray, eq: np.ndarray, capital: float) -> list[dict[str, Any]]:
    if len(eq) == 0:
        return []
    s = pd.Series(np.concatenate([[capital], eq]),
                  index=pd.to_datetime(np.concatenate([[t_sec[0] - 1], t_sec]), unit="s", utc=True))
    m = s.resample("ME").last().dropna()
    prev = capital
    out = []
    for ts, v in m.items():
        out.append({"bulan": ts.strftime("%Y-%m"), "return_pct": (v / prev - 1) * 100 if prev else None})
        prev = v
    return out


def downsample(t: np.ndarray, *cols: np.ndarray, n: int = 2500) -> list[list[float]]:
    if len(t) == 0:
        return []
    if len(t) > n:
        idx = np.unique(np.concatenate([np.linspace(0, len(t) - 1, n).astype(int), [len(t) - 1]]))
    else:
        idx = np.arange(len(t))
    out = [t[idx].astype(float)] + [np.round(c[idx].astype(float), 6) for c in cols]
    return np.column_stack(out).tolist()


def clean(o: Any) -> Any:
    """NaN/inf → None (supaya JSON valid)."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o
