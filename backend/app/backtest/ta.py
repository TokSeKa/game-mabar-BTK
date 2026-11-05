"""Indikator teknikal untuk strategi backtest (semua kausal: nilai di baris i hanya memakai data ≤ i).

Pakai di file strategi::

    from app.backtest.ta import ema, rsi, atr, crossover

Semua fungsi menerima/mengembalikan ``pandas.Series`` (atau DataFrame untuk yang punya beberapa garis).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "sma", "ema", "rma", "wma", "rsi", "atr", "true_range", "macd", "bollinger", "donchian", "keltner", "stoch",
    "roc", "momentum", "zscore", "highest", "lowest", "crossover", "crossunder", "obv", "vwap", "adx", "supertrend",
]


def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(int(n), min_periods=int(n)).mean()


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=int(n), adjust=False, min_periods=int(n)).mean()


def rma(x: pd.Series, n: int) -> pd.Series:
    """Rata-rata Wilder (dipakai RSI & ATR)."""
    return x.ewm(alpha=1.0 / int(n), adjust=False, min_periods=int(n)).mean()


def wma(x: pd.Series, n: int) -> pd.Series:
    n = int(n)
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n, min_periods=n).apply(lambda a: float(np.dot(a, w) / w.sum()), raw=True)


def rsi(x: pd.Series, n: int = 14) -> pd.Series:
    d = x.diff()
    up = rma(d.clip(lower=0), n)
    dn = rma(-d.clip(upper=0), n)
    rs = up / dn.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(dn != 0, 100.0).where(up.notna())


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return rma(true_range(df), n)


def macd(x: pd.Series, cepat: int = 12, lambat: int = 26, sinyal: int = 9) -> pd.DataFrame:
    m = ema(x, cepat) - ema(x, lambat)
    s = ema(m, sinyal)
    return pd.DataFrame({"macd": m, "sinyal": s, "hist": m - s})


def bollinger(x: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(x, n)
    sd = x.rolling(int(n), min_periods=int(n)).std(ddof=0)
    return pd.DataFrame({"tengah": mid, "atas": mid + k * sd, "bawah": mid - k * sd})


def highest(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(int(n), min_periods=int(n)).max()


def lowest(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(int(n), min_periods=int(n)).min()


def donchian(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Kanal Donchian dari ``n`` candle SEBELUMNYA (tidak termasuk candle sekarang), cocok untuk breakout."""
    atas = highest(df["high"], n).shift(1)
    bawah = lowest(df["low"], n).shift(1)
    return pd.DataFrame({"atas": atas, "bawah": bawah, "tengah": (atas + bawah) / 2})


def keltner(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = ema(df["close"], n)
    a = atr(df, n)
    return pd.DataFrame({"tengah": mid, "atas": mid + k * a, "bawah": mid - k * a})


def stoch(df: pd.DataFrame, n: int = 14, k: int = 3, d: int = 3) -> pd.DataFrame:
    lo, hi = lowest(df["low"], n), highest(df["high"], n)
    raw = 100 * (df["close"] - lo) / (hi - lo).replace(0, np.nan)
    kk = sma(raw, k)
    return pd.DataFrame({"k": kk, "d": sma(kk, d)})


def roc(x: pd.Series, n: int = 10) -> pd.Series:
    return (x / x.shift(int(n)) - 1) * 100


def momentum(x: pd.Series, n: int = 10) -> pd.Series:
    return x - x.shift(int(n))


def zscore(x: pd.Series, n: int = 20) -> pd.Series:
    m = sma(x, n)
    sd = x.rolling(int(n), min_periods=int(n)).std(ddof=0)
    return (x - m) / sd.replace(0, np.nan)


def crossover(a: pd.Series, b: pd.Series | float) -> pd.Series:
    """True di candle saat ``a`` memotong ``b`` dari bawah ke atas."""
    b = b if isinstance(b, pd.Series) else pd.Series(b, index=a.index)
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series | float) -> pd.Series:
    b = b if isinstance(b, pd.Series) else pd.Series(b, index=a.index)
    return (a < b) & (a.shift(1) >= b.shift(1))


def obv(df: pd.DataFrame) -> pd.Series:
    arah = np.sign(df["close"].diff()).fillna(0)
    return (arah * df["volume"]).cumsum()


def vwap(df: pd.DataFrame, reset: str = "D") -> pd.Series:
    """VWAP yang direset tiap periode (default harian, UTC)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    g = df.index.floor(reset) if reset else np.zeros(len(df))
    pv = (tp * df["volume"]).groupby(g).cumsum()
    vv = df["volume"].groupby(g).cumsum()
    return pv / vv.replace(0, np.nan)


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = rma(true_range(df), n)
    pdi = 100 * rma(plus, n) / tr
    mdi = 100 * rma(minus, n) / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pd.DataFrame({"adx": rma(dx, n), "plus_di": pdi, "minus_di": mdi})


def supertrend(df: pd.DataFrame, n: int = 10, k: float = 3.0) -> pd.DataFrame:
    """Supertrend klasik. Kolom ``arah``: 1 naik, -1 turun."""
    a = atr(df, n).to_numpy()
    hl2 = ((df["high"] + df["low"]) / 2).to_numpy()
    c = df["close"].to_numpy()
    up, dn = hl2 - k * a, hl2 + k * a
    st = np.full(len(df), np.nan)
    arah = np.zeros(len(df))
    fu, fd = np.nan, np.nan
    for i in range(len(df)):
        if np.isnan(a[i]):
            continue
        fu = up[i] if np.isnan(fu) or c[i - 1] < fu else max(up[i], fu)
        fd = dn[i] if np.isnan(fd) or c[i - 1] > fd else min(dn[i], fd)
        prev = arah[i - 1] if i else 1
        arah[i] = 1 if c[i] > fd else -1 if c[i] < fu else (prev or 1)
        st[i] = fu if arah[i] > 0 else fd
    return pd.DataFrame({"supertrend": st, "arah": arah}, index=df.index)
