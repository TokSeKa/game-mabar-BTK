"""File strategi: metadata (dibaca tanpa menjalankan kode), pengaturan, dan konteks ``bt`` untuk ``langkah``.

Bentuk file strategi (lihat ``strategi/README.md``)::

    \"\"\"Deskripsi singkat.\"\"\"
    from app.backtest.ta import ema

    PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "4h", "produk": "spot", "modal": 10_000}
    PARAMETER = {"cepat": 20, "lambat": 50}
    PLOT = ["ema_cepat", "ema_lambat"]

    def siapkan(df, p):              # sekali per aset: tambah kolom indikator (pandas penuh)
        df["ema_cepat"] = ema(df.close, p.cepat)
        df["ema_lambat"] = ema(df.close, p.lambat)
        return df

    def langkah(bt, p):              # tiap candle ditutup
        for a in bt.aset:
            x = bt[a]
            if x.ema_cepat > x.ema_lambat and not bt.posisi(a):
                bt.beli(a, persen=100)
            elif x.ema_cepat < x.ema_lambat and bt.posisi(a) > 0:
                bt.tutup(a)
"""

from __future__ import annotations

import ast
import datetime as dt
import importlib.util
import inspect
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..trading.markets import MARKETS
from ..trading.products import products
from .broker import Broker, OrderError

DEFAULTS: dict[str, Any] = {
    "pasar": "crypto", "aset": "semua", "timeframe": "1d", "mulai": None, "selesai": None, "mode": "per_aset",
    "produk": "spot", "aturan": "nyata", "modal": None, "leverage": 1, "margin": "cross", "slippage": None,
    "fee_beli": None, "fee_jual": None, "fee_maker": None, "fee_taker": None, "bunga": None, "biaya_pinjam": None,
    "pemanasan": 300, "maks_aset": 60,
}
MAKS_BAR = 400_000


class StrategyError(Exception):
    """Kesalahan pada file strategi atau pengaturannya (ditampilkan ke pengguna)."""


def strategi_dir() -> Path:
    from ..config import ROOT
    env = os.environ.get("STRATEGI_DIR")
    return Path(env) if env else ROOT / "strategi"


class P(dict):
    """Parameter dengan akses atribut: ``p.cepat`` sama dengan ``p["cepat"]``."""

    def __getattr__(self, k: str) -> Any:
        try:
            return self[k]
        except KeyError:
            raise AttributeError(f"Parameter '{k}' tidak ada di PARAMETER.") from None


# ---------------------------------------------------------------- metadata tanpa eksekusi
def read_meta(path: Path) -> dict[str, Any]:
    """Docstring, PENGATURAN, PARAMETER, PLOT dari file strategi lewat AST (kode tidak dijalankan)."""
    meta: dict[str, Any] = {"file": path.name, "nama": path.stem, "deskripsi": "", "pengaturan": {}, "parameter": {},
                            "plot": [], "error": None, "fungsi": []}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, SyntaxError, ValueError) as e:
        meta["error"] = f"Tidak bisa dibaca: {e}"
        return meta
    doc = ast.get_docstring(tree) or ""
    meta["deskripsi"] = doc.strip()
    if doc.strip():
        meta["judul"] = doc.strip().splitlines()[0]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            meta["fungsi"].append(node.name)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("PENGATURAN", "PARAMETER", "PLOT", "NAMA"):
                try:
                    val = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    meta["error"] = f"{name} harus berisi nilai biasa (angka, teks, list, dict), bukan rumus."
                    continue
                key = {"PENGATURAN": "pengaturan", "PARAMETER": "parameter", "PLOT": "plot", "NAMA": "nama_tampil"}[name]
                meta[key] = val
    if "langkah" not in meta["fungsi"]:
        meta["error"] = meta["error"] or "Fungsi langkah(bt, p) belum ada."
    return meta


def list_strategies(folder: Path | None = None) -> list[dict[str, Any]]:
    folder = folder or strategi_dir()
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.glob("*.py")):
        if p.name.startswith("_"):
            continue
        out.append(read_meta(p))
    return out


def resolve_path(name: str, folder: Path | None = None) -> Path:
    folder = (folder or strategi_dir()).resolve()
    p = Path(name)
    if not p.suffix:
        p = p.with_suffix(".py")
    cand = p if p.is_absolute() else folder / p.name
    cand = cand.resolve()
    if not cand.is_file():
        alt = Path(name).resolve()
        if alt.is_file():
            return alt
        raise StrategyError(f"File strategi '{name}' tidak ditemukan di {folder}.")
    return cand


def load_module(path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(f"strategi_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        try:
            sys.path.remove(str(path.parent))
        except ValueError:
            pass
    if not callable(getattr(mod, "langkah", None)):
        raise StrategyError("Fungsi langkah(bt, p) belum ada di file strategi.")
    return mod


# ---------------------------------------------------------------- pengaturan & parameter
def _date_ms(v: Any) -> int | None:
    if v in (None, "", 0):
        return None
    if isinstance(v, (int, float)):
        return int(v * 1000) if v < 1e11 else int(v)
    try:
        ts = pd.Timestamp(str(v))
    except ValueError:
        raise StrategyError(f"Tanggal '{v}' tidak valid (pakai format YYYY-MM-DD).") from None
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return int(ts.value // 1_000_000)


def resolve_settings(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    s = {**DEFAULTS, **(base or {}), **{k: v for k, v in (override or {}).items() if v is not None and v != ""}}
    if s["pasar"] not in MARKETS:
        raise StrategyError(f"Pasar '{s['pasar']}' tidak dikenal. Pilih: {', '.join(MARKETS)}.")
    spec = MARKETS[s["pasar"]]
    if s["timeframe"] not in spec.tfs:
        raise StrategyError(f"Timeframe '{s['timeframe']}' tidak tersedia untuk {spec.nama}: {', '.join(spec.tfs)}.")
    if s["mode"] not in ("per_aset", "portofolio"):
        raise StrategyError("mode harus 'per_aset' atau 'portofolio'.")
    if s["produk"] not in ("spot", "futures", "margin"):
        raise StrategyError("produk harus 'spot', 'futures', atau 'margin'.")
    s["aturan"] = "bebas" if s["aturan"] == "bebas" else "nyata"
    if s["produk"] != "spot" and s["produk"] not in products(s["pasar"], s["aturan"]):
        raise StrategyError(f"Produk {s['produk']} tidak tersedia untuk {spec.nama} dengan aturan {s['aturan']}.")
    s["modal"] = float(s["modal"] or spec.capital)
    if not (s["modal"] > 0):
        raise StrategyError("Modal harus lebih dari 0.")
    s["leverage"] = float(s["leverage"] or 1)
    s["margin"] = "isolated" if s["margin"] == "isolated" else "cross"
    s["slippage"] = spec.slippage if s["slippage"] is None else float(s["slippage"])
    s["mulai_ms"], s["selesai_ms"] = _date_ms(s["mulai"]), _date_ms(s["selesai"])
    if s["selesai_ms"] and isinstance(s["selesai"], str) and len(s["selesai"]) <= 10:
        s["selesai_ms"] += 86_400_000 - 1  # sampai akhir hari itu
    s["pemanasan"] = int(max(0, min(int(s["pemanasan"]), 20_000)))
    return s


def resolve_params(base: dict[str, Any], override: dict[str, Any] | None) -> P:
    out = P(base or {})
    for k, v in (override or {}).items():
        if k not in out:
            raise StrategyError(f"Parameter '{k}' tidak ada di PARAMETER strategi.")
        d = out[k]
        try:
            if isinstance(d, bool):
                v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "ya", "y", "on")
            elif isinstance(d, int):
                v = int(float(v))
            elif isinstance(d, float):
                v = float(v)
            elif isinstance(d, list):
                v = v if isinstance(v, list) else [x.strip() for x in str(v).split(",") if x.strip()]
            else:
                v = str(v)
        except (TypeError, ValueError):
            raise StrategyError(f"Nilai parameter '{k}' tidak valid: {v!r}.") from None
        out[k] = v
    return out


def call_siapkan(mod, df: pd.DataFrame, p: P, ekstra) -> pd.DataFrame:
    fn = getattr(mod, "siapkan", None)
    if fn is None:
        return df
    n = len(inspect.signature(fn).parameters)
    res = fn(df, p, ekstra) if n >= 3 else fn(df, p)
    if res is None:
        res = df
    if not isinstance(res, pd.DataFrame) or len(res) != len(df):
        raise StrategyError("siapkan(df, p) harus mengembalikan DataFrame dengan jumlah baris yang sama.")
    return res


# ---------------------------------------------------------------- konteks bt
class Bar:
    """Satu candle (yang baru ditutup) sebagai objek: ``x.close``, ``x.rsi``, ``x["kolom"]``."""

    __slots__ = ("_cols", "_i", "waktu")

    def __init__(self, cols: dict[str, np.ndarray], i: int, waktu: pd.Timestamp):
        self._cols, self._i, self.waktu = cols, i, waktu

    def __getattr__(self, k: str) -> Any:
        cols = object.__getattribute__(self, "_cols")
        if k in cols:
            v = cols[k][object.__getattribute__(self, "_i")]
            return v.item() if isinstance(v, np.generic) else v
        raise AttributeError(f"Kolom '{k}' tidak ada. Tersedia: {', '.join(cols)}")

    def __getitem__(self, k: str) -> Any:
        return self.__getattr__(k)

    def get(self, k: str, default: Any = None) -> Any:
        return self.__getattr__(k) if k in self._cols else default

    def __repr__(self) -> str:
        return f"Bar({self.waktu}, close={self.close})"


class Ctx:
    """Objek ``bt`` di ``langkah(bt, p)``."""

    def __init__(self, broker: Broker, dfs: dict[str, pd.DataFrame], cols: dict[str, dict[str, np.ndarray]],
                 ekstra, tf_ms: int, settings: dict[str, Any]):
        self._b = broker
        self._dfs = dfs
        self._cols = cols
        self._cur: dict[str, int] = {}
        self._has: dict[str, bool] = {}
        self._ekstra = ekstra
        self._tf = pd.Timedelta(milliseconds=tf_ms)
        self.aset: list[str] = list(dfs)
        self.pengaturan = dict(settings)
        self.waktu: pd.Timestamp | None = None
        self.i = -1
        self.logs: list[str] = []
        self.state: dict[str, Any] = {}

    # ------------------------------------------------------------ data
    def _idx(self, a: str) -> int:
        if a not in self._cur:
            raise KeyError(f"Aset '{a}' tidak ada di backtest ini. Aset: {', '.join(self.aset)}")
        return self._cur[a]

    def __getitem__(self, a: str) -> Bar:
        i = self._idx(a)
        return Bar(self._cols[a], i, self._dfs[a].index[i])

    def ada(self, a: str) -> bool:
        """Apakah aset ini punya candle baru di langkah ini (saham libur/belum listing = False)."""
        return self._has.get(a, False) and self._cur.get(a, -1) >= 0

    def hist(self, a: str, n: int | None = None, kolom: str | list[str] | None = None):
        """Riwayat candle sampai candle sekarang (tidak pernah ada data masa depan)."""
        i = self._idx(a)
        lo = 0 if n is None else max(0, i - int(n) + 1)
        df = self._dfs[a].iloc[lo:i + 1]
        return df[kolom] if kolom is not None else df

    def harga(self, a: str) -> float:
        return float(self._cols[a]["close"][self._idx(a)])

    @property
    def ekstra(self):
        """Data pengumpul-data yang sudah tersedia pada waktu keputusan ini."""
        return self._ekstra.pada(self.waktu + self._tf) if self.waktu is not None else self._ekstra

    # ------------------------------------------------------------ akun
    @property
    def ekuitas(self) -> float:
        return self._b.equity()

    @property
    def kas(self) -> float:
        return self._b.cash()

    @property
    def tersedia(self) -> float:
        return self._b.available()

    @property
    def leverage(self) -> float:
        return self._b.lev

    def posisi(self, a: str) -> float:
        return self._b.pos[a].qty

    def harga_masuk(self, a: str) -> float:
        return self._b.pos[a].entry

    def nilai(self, a: str) -> float:
        return self._b.pos[a].qty * self._b.px(a)

    def laba(self, a: str) -> float:
        return self._b.upnl(a)

    def harga_likuidasi(self, a: str) -> float | None:
        return self._b.liq_price(a)

    def order(self, a: str | None = None) -> list[dict[str, Any]]:
        return [o.public() for o in self._b.orders.values() if o.status == "open" and (a is None or o.sym == a)]

    # ------------------------------------------------------------ order
    def _qty(self, a: str, qty: Any, nilai: Any, persen: Any, ref: float) -> float:
        given = [x is not None for x in (qty, nilai, persen)]
        if sum(given) != 1:
            raise OrderError("Isi tepat satu ukuran: qty=, nilai=, atau persen=.")
        if qty is not None:
            return abs(float(qty))
        if nilai is not None:
            return abs(float(nilai)) / ref
        notional = self._b.equity() * abs(float(persen)) / 100 * self._b.lev
        return notional / ref

    def _order(self, a: str, side: str, qty=None, nilai=None, persen=None, harga=None, stop=None, sl=None, tp=None,
               reduce_only=False, label="") -> int | None:
        try:
            last = self.harga(a)
            ref = float(harga or stop or last)
            q = self._qty(a, qty, nilai, persen, ref)
            if not math.isfinite(q) or q <= 0:
                return None
            kind = "market"
            if harga is not None and stop is not None:
                kind = "stop_limit"
            elif harga is not None:
                kind = "limit"
            elif stop is not None:
                kind = "stop"
            od = self._b.submit(a, side, q, kind, price=float(stop) if kind == "stop" else (float(harga) if harga is not None else None),
                                stop=float(stop) if kind == "stop_limit" else None,
                                sl=None if sl is None else float(sl), tp=None if tp is None else float(tp),
                                reduce_only=bool(reduce_only), label=str(label))
            return od.id
        except OrderError as e:
            self._b.note(f"{self._fmt_t()} {e}")
            return None

    def beli(self, a: str, qty=None, nilai=None, persen=None, harga=None, stop=None, sl=None, tp=None,
             reduce_only=False, label="") -> int | None:
        """Beli / long. Ukuran: ``qty`` (unit), ``nilai`` (uang), atau ``persen`` (% ekuitas sebagai margin × leverage).
        ``harga`` = limit, ``stop`` = stop-market, keduanya = stop-limit. ``sl``/``tp`` dipasang setelah terisi."""
        return self._order(a, "buy", qty, nilai, persen, harga, stop, sl, tp, reduce_only, label)

    def jual(self, a: str, qty=None, nilai=None, persen=None, harga=None, stop=None, sl=None, tp=None,
             reduce_only=False, label="") -> int | None:
        """Jual. Di spot hanya aset yang dimiliki; di futures/margin kelebihannya jadi short."""
        return self._order(a, "sell", qty, nilai, persen, harga, stop, sl, tp, reduce_only, label)

    short = jual

    def tutup(self, a: str | None = None, harga: float | None = None) -> None:
        """Tutup posisi (semua aset kalau ``a`` kosong) di open candle berikutnya, atau limit di ``harga``."""
        for s in ([a] if a else self.aset):
            q = self._b.pos[s].qty
            if abs(q) > 1e-12:
                self._order(s, "sell" if q > 0 else "buy", qty=abs(q), harga=harga, reduce_only=True, label="Tutup")

    def target(self, a: str, persen: float | None = None, qty: float | None = None, nilai: float | None = None,
               toleransi: float = 0.02) -> None:
        """Ubah posisi jadi target (bertanda: negatif = short). ``persen`` = % ekuitas × leverage.
        Selisih kecil (< ``toleransi`` × target) diabaikan supaya tidak bolak-balik kena fee."""
        price = self.harga(a)
        if sum(x is not None for x in (persen, qty, nilai)) != 1:
            raise OrderError("target(): isi tepat satu dari persen=, qty=, nilai=.")
        if qty is not None:
            want = float(qty)
        elif nilai is not None:
            want = float(nilai) / price
        else:
            want = self._b.equity() * float(persen) / 100 * self._b.lev / price
        cur = self._b.pos[a].qty
        delta = want - cur
        if abs(delta) * price < max(self._b.cfg.min_notional, 1e-9) or abs(delta) <= abs(want) * toleransi and abs(want) > 0:
            return
        if abs(want) < 1e-12 and abs(cur) > 1e-12:
            self.tutup(a)
            return
        self._order(a, "buy" if delta > 0 else "sell", qty=abs(delta))

    def batal(self, a: str | None = None, id: int | None = None) -> int:
        """Batalkan order yang menunggu (semua, per aset, atau satu id)."""
        return self._b.cancel(a, id)

    def log(self, *x: Any) -> None:
        if len(self.logs) < 3000:
            self.logs.append(f"{self._fmt_t()} " + " ".join(str(v) for v in x))

    def _fmt_t(self) -> str:
        return self.waktu.strftime("%Y-%m-%d %H:%M") if self.waktu is not None else "-"


def lookahead_check(mod, df: pd.DataFrame, p: P, ekstra, start: int, full: pd.DataFrame) -> list[str]:
    """Bandingkan hasil siapkan() di data penuh vs data yang dipotong di beberapa titik.

    Kalau nilai sebuah kolom di baris i berubah saat data setelah i dibuang, kolom itu memakai data masa depan."""
    if getattr(mod, "siapkan", None) is None or len(df) < 50:
        return []
    n = len(df)
    points = sorted({max(start, 30), start + (n - start) // 3, start + 2 * (n - start) // 3, n - 2})
    bad: set[str] = set()
    base_cols = set(df.columns)
    for c in points:
        if c <= 5 or c >= n:
            continue
        try:
            cut = df.iloc[: c + 1].copy()
            cut.attrs.update(df.attrs)
            part = call_siapkan(mod, cut, p, ekstra)
        except Exception:  # noqa: BLE001 - kalau siapkan butuh data panjang, lewati titik ini
            continue
        for col in full.columns:
            if col in base_cols or col not in part.columns:
                continue
            a, b = full[col].iloc[c], part[col].iloc[-1]
            try:
                fa, fb = float(a), float(b)
            except (TypeError, ValueError):
                if a != b and not (pd.isna(a) and pd.isna(b)):
                    bad.add(col)
                continue
            if (math.isnan(fa) and math.isnan(fb)) or math.isclose(fa, fb, rel_tol=1e-6, abs_tol=1e-9):
                continue
            bad.add(col)
    return [f"Kolom '{c}' memakai data masa depan: nilainya berubah kalau candle setelahnya dibuang "
            "(misalnya shift(-1), center=True, atau normalisasi dengan seluruh data). Hasil backtest jadi tidak jujur."
            for c in sorted(bad)]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
