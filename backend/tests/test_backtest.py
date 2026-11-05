"""Alat backtest: broker portofolio, runner, data pengumpul-data, API."""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.backtest.broker import Broker, BrokerConfig
from app.backtest.data import Eksternal
from app.backtest.runner import run
from app.backtest.strategy import StrategyError, list_strategies, read_meta
from app.trading.derivatives import DerivAccount
from app.trading.markets import MARKETS
from app.trading.products import product_for
from app.trading.store import CandleStore

from .trading_fixtures import make_crypto, make_idx

REPO = Path(__file__).resolve().parents[2]


def strat(folder: Path, name: str, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{name}.py"
    p.write_text(body, encoding="utf-8")
    return p


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "pasar"
    make_crypto(root, "BTCUSDT", days=60, seed=5)
    make_crypto(root, "ETHUSDT", days=60, seed=6)
    make_idx(root, "BBCA")
    make_idx(root, "TLKM")
    sdir = tmp_path / "strategi"
    pdir = tmp_path / "pengumpul"
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("STRATEGI_DIR", str(sdir))
    monkeypatch.setenv("PENGUMPUL_DIR", str(pdir))
    return {"root": root, "store": CandleStore(root), "sdir": sdir, "pdir": pdir, "tmp": tmp_path}


# ---------------------------------------------------------------- broker
def spot_broker(syms, capital=10_000, slip=0.0):
    return Broker(BrokerConfig(market=MARKETS["crypto"], produk="spot", capital=capital, slippage=slip,
                               qty_step=1e-6, min_notional=5), syms)


def perp_broker(syms, capital=1_000, lev=10, mode="cross"):
    prods = {s: product_for("crypto", "futures", s) for s in syms}
    return Broker(BrokerConfig(market=MARKETS["crypto"], produk="futures", products=prods, capital=capital,
                               leverage=lev, margin_mode=mode, qty_step=1e-6, min_notional=5), syms)


def test_spot_market_di_open_berikutnya_dengan_fee():
    b = spot_broker(["A"], slip=0.001)
    b.bar("A", 100, 101, 99, 100, 0)
    b.submit("A", "buy", 10, "market")
    fills = b.bar("A", 102, 103, 101, 102, 60)
    assert fills[0].price == pytest.approx(102 * 1.001)
    assert fills[0].fee == pytest.approx(102 * 1.001 * 10 * 0.001)
    b.submit("A", "sell", 10, "market")
    b.bar("A", 110, 111, 109, 110, 120)
    t = b.trades[0]
    assert t["side"] == "long" and t["pnl"] == pytest.approx(10 * (110 * 0.999 - 102 * 1.001) - b.fees_paid)
    from app.backtest.broker import OrderError
    with pytest.raises(OrderError):
        b.submit("A", "sell", 1, "market")       # spot tidak bisa short


def test_harga_likuidasi_sama_dengan_mesin_game():
    b = perp_broker(["BTCUSDT"], capital=1_000, lev=10)
    b.bar("BTCUSDT", 100, 100, 100, 100, 0)
    b.submit("BTCUSDT", "buy", 99, "market")
    b.bar("BTCUSDT", 100, 100, 100, 100, 60)
    g = DerivAccount(product_for("crypto", "futures", "BTCUSDT"), 1_000, 0.0, 1e-6, 5, symbol="BTCUSDT", leverage=10)
    g.market("buy", 99, 100.0, 1)
    assert b.liq_price("BTCUSDT") == pytest.approx(g.liq_price(), rel=1e-9)
    assert b.equity() == pytest.approx(g.equity(100.0))


def test_isolated_hanya_kehilangan_margin_posisi():
    b = perp_broker(["BTCUSDT"], capital=10_000, lev=10, mode="isolated")
    b.bar("BTCUSDT", 100, 100, 100, 100, 0)
    b.submit("BTCUSDT", "buy", 100, "market")
    b.bar("BTCUSDT", 100, 100, 100, 100, 60)
    lp = b.liq_price("BTCUSDT")
    b.bar("BTCUSDT", 99, 99, lp - 1, lp - 0.5, 120)
    assert b.n_liq == 1 and b.pos["BTCUSDT"].qty == 0
    assert b.wallet == pytest.approx(10_000 - 5 - 1_000, abs=1.0)


def test_cross_banyak_posisi_likuidasi_asumsi_terburuk():
    b = perp_broker(["A", "B"], capital=1_000, lev=10)
    for s in ("A", "B"):
        b.bar(s, 100, 100, 100, 100, 0)
        b.submit(s, "buy", 45, "market")
    for s in ("A", "B"):
        b.bar(s, 100, 100, 100, 100, 60)
    assert b.n_open() == 2
    for s in ("A", "B"):
        b.bar(s, 100, 100, 88, 95, 120)
    b.cross_check({"A": 88, "B": 88}, 120)
    assert b.n_open() == 0 and b.n_liq == 2 and b.wallet >= 0


def test_funding_dan_bunga_margin():
    b = perp_broker(["BTCUSDT"], capital=10_000, lev=5)
    b.bar("BTCUSDT", 100, 100, 100, 100, 0)
    b.submit("BTCUSDT", "sell", 10, "market")
    b.bar("BTCUSDT", 100, 100, 100, 100, 60)
    b.funding("BTCUSDT", 0.001, 100)
    assert b.funding_paid == pytest.approx(-1.0)               # short menerima funding positif
    prods = {"AAPL": product_for("us", "margin", "AAPL")}
    m = Broker(BrokerConfig(market=MARKETS["us"], produk="margin", products=prods, capital=10_000, leverage=2,
                            qty_step=1, min_notional=0), ["AAPL"])
    m.bar("AAPL", 100, 100, 100, 100, 0)
    m.submit("AAPL", "buy", 150, "market")
    m.bar("AAPL", 100, 100, 100, 100, 60)
    debt = -m.cash()
    m.day(2)
    assert m.interest_paid == pytest.approx(debt * 0.0512 / 360 * 2)


def test_rebalance_jual_dulu_baru_beli():
    b = spot_broker(["A", "B"], capital=1_000)
    for s in ("A", "B"):
        b.bar(s, 10, 10, 10, 10, 0)
    b.submit("A", "buy", 99, "market")
    for s in ("A", "B"):
        b.bar(s, 10, 10, 10, 10, 60)
    b.submit("B", "buy", 98, "market")      # B diproses duluan di urutan aset? tidak masalah:
    b.submit("A", "sell", 99, "market")     # penjualan A diisi lebih dulu
    for s in ("A", "B"):
        b.open_reducing(s, 10, 120)
    for s in ("A", "B"):
        b.bar(s, 10, 10, 10, 10, 120)
    assert b.pos["A"].qty == 0 and b.pos["B"].qty == pytest.approx(98)


# ---------------------------------------------------------------- runner
EMA = '''"""EMA tes"""
from app.backtest.ta import ema
PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT", "ETHUSDT"], "timeframe": "1h", "modal": 10000}
PARAMETER = {"n": 20}
PLOT = ["ema"]
def siapkan(df, p):
    df["ema"] = ema(df.close, p.n)
    return df
def langkah(bt, p):
    for a in bt.aset:
        x = bt[a]
        if x.close > x.ema and bt.posisi(a) == 0:
            bt.beli(a, persen=100)
        elif x.close < x.ema and bt.posisi(a) > 0:
            bt.tutup(a)
'''


def test_runner_per_aset_dan_portofolio(env):
    p = strat(env["sdir"], "ema", EMA)
    out = env["tmp"] / "hasil1"
    r = run(p, {"mulai": "2024-01-10"}, {"n": 30}, store=env["store"], out_dir=out)
    assert r["mode"] == "per_aset" and [x["simbol"] for x in r["per_aset"]] == ["BTCUSDT", "ETHUSDT"]
    assert r["parameter"]["n"] == 30 and r["ringkasan"]["n_trades"] > 0
    assert r["ringkasan"]["fees"] > 0 and r["ringkasan"]["cagr_pct"] is not None
    assert r["kurva"][0][0] >= pd.Timestamp("2024-01-10", tz="UTC").timestamp()
    chart = json.loads((out / "aset" / "BTCUSDT.json").read_text())
    assert len(chart["t"]) == len(chart["c"]) and "ema" in chart["plot"] and chart["fills"]
    r2 = run(p, {"mode": "portofolio", "mulai": "2024-01-10"}, {}, store=env["store"])
    assert r2["mode"] == "portofolio" and r2["ringkasan"]["n_trades"] > 0
    # satu aset: per_aset == portofolio
    a = run(p, {"aset": ["BTCUSDT"], "mulai": "2024-01-10"}, {}, store=env["store"])
    b = run(p, {"aset": ["BTCUSDT"], "mode": "portofolio", "mulai": "2024-01-10"}, {}, store=env["store"])
    assert a["ringkasan"]["return_pct"] == pytest.approx(b["ringkasan"]["return_pct"], rel=1e-9)


def test_tidak_ada_data_masa_depan_di_langkah(env):
    p = strat(env["sdir"], "intip", '''"""cek"""
PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "1h", "mulai": "2024-01-05"}
def langkah(bt, p):
    a = bt.aset[0]
    h = bt.hist(a)
    assert h.index[-1] == bt.waktu, (h.index[-1], bt.waktu)
    assert bt[a].close == h.close.iloc[-1]
    if bt.i == 0:
        bt.beli(a, qty=1)
''')
    r = run(p, {}, {}, store=env["store"])
    t0 = r["transaksi"][0] if r["transaksi"] else None
    assert t0 and t0["entry_time"] == pd.Timestamp("2024-01-05 01:00", tz="UTC").timestamp()  # open candle berikutnya


def test_cek_kebocoran_shift_minus(env):
    p = strat(env["sdir"], "bocor", '''"""bocor"""
PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "1h", "mulai": "2024-01-05"}
def siapkan(df, p):
    df["besok"] = df.close.shift(-1)
    df["aman"] = df.close.rolling(5).mean()
    return df
def langkah(bt, p):
    pass
''')
    r = run(p, {}, {}, store=env["store"])
    assert any("'besok'" in w for w in r["peringatan"])
    assert not any("'aman'" in w for w in r["peringatan"])


def test_error_strategi_menunjuk_baris(env):
    p = strat(env["sdir"], "rusak", '''"""rusak"""
PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "1h"}
def langkah(bt, p):
    x = bt[bt.aset[0]]
    y = x.tidak_ada
''')
    with pytest.raises(StrategyError, match="baris 5"):
        run(p, {}, {}, store=env["store"])
    with pytest.raises(StrategyError, match="Parameter"):
        run(p, {}, {"tidak_ada": 1}, store=env["store"])


def test_futures_short_dan_idx_short_aturan_bei(env):
    p = strat(env["sdir"], "short", '''"""short"""
PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "1h", "produk": "futures", "leverage": 5,
              "mulai": "2024-01-05"}
def langkah(bt, p):
    a = bt.aset[0]
    if bt.i == 0:
        bt.jual(a, persen=50)
    if bt.i == 30:
        bt.tutup(a)
''')
    r = run(p, {}, {}, store=env["store"])
    assert r["transaksi"][0]["side"] == "short" and r["ringkasan"]["n_short"] == 1
    assert r["ringkasan"]["funding"] != 0
    r2 = run(p, {"pasar": "idx", "aset": ["TLKM"], "timeframe": "1d", "produk": "margin", "mulai": "2023-06-01",
                 "modal": 100_000_000}, {}, store=env["store"])
    assert r2["ringkasan"]["n_trades"] == 0 and any("short tidak tersedia" in x for x in r2["log"])


def test_data_pengumpul_tersedia_setelah_terbit(env):
    d = env["pdir"] / "idx" / "ringkasan_saham"
    d.mkdir(parents=True)
    for i, day in enumerate(pd.bdate_range("2024-12-02", "2024-12-20")):
        pd.DataFrame([{"tanggal": day, "kode": "BBCA", "asing_bersih": float(i + 1)}]).to_parquet(d / f"{day:%Y-%m-%d}.parquet")
    (env["pdir"] / "yahoo" / "1d").mkdir(parents=True)
    days = pd.date_range("2024-01-01", "2025-03-01", freq="D", tz="UTC")
    pd.DataFrame({"waktu": days, "open": 1.0, "high": 1.0, "low": 1.0, "close": np.arange(len(days), dtype=float),
                  "adj_close": 0.0, "volume": 0}).to_parquet(env["pdir"] / "yahoo" / "1d" / "_VIX.parquet")
    e = Eksternal(tf_ms=3_600_000)
    assert e.status()["idx_saham"] == 15 and "_VIX" in e.status()["yahoo"]["1d"]
    # 2024-12-03 10:00 WIB (03:00 UTC): data asing 12-03 belum terbit, 12-02 sudah
    v = e.pada(pd.Timestamp("2024-12-03 03:00", tz="UTC")).asing("BBCA")
    assert v.index.max() == pd.Timestamp("2024-12-02")
    # gabung di siapkan: candle harian IDX tgl 3 (mulai 2 Des 17:00 UTC = 00:00 WIB) diputuskan setelah hari itu
    # selesai, jadi sudah boleh melihat data asing tgl 3 (terbit 18:00 WIB); candle 1 jam pukul 10:00 WIB belum.
    df = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.DatetimeIndex(["2024-12-02 17:00", "2024-12-03 17:00"], tz="UTC"))
    out = Eksternal(tf_ms=86_400_000).gabung(df, e.asing("BBCA"), "asing_bersih")
    assert out.asing_bersih.tolist() == [2.0, 3.0]
    jam = pd.DataFrame({"close": [1.0]}, index=pd.DatetimeIndex(["2024-12-03 03:00"], tz="UTC"))
    assert Eksternal(tf_ms=3_600_000).gabung(jam, e.asing("BBCA"), "asing_bersih").asing_bersih.tolist() == [1.0]
    vix = e.pada(pd.Timestamp("2024-01-03 12:00", tz="UTC")).yahoo("^VIX")
    assert vix.close.iloc[-1] == 1.0                       # bar 01-03 belum selesai, terakhir bar 01-02


def test_meta_tanpa_eksekusi_dan_contoh_di_repo(env):
    p = strat(env["sdir"], "jahat", '''"""Judul"""
import os
os.system("echo jangan-dijalankan > %s")
PENGATURAN = {"pasar": "crypto"}
PARAMETER = {"a": 1}
def langkah(bt, p): pass
''' % (env["tmp"] / "jejak.txt"))
    m = read_meta(p)
    assert m["judul"] == "Judul" and m["parameter"] == {"a": 1} and not (env["tmp"] / "jejak.txt").exists()
    contoh = list_strategies(REPO / "strategi")
    assert len(contoh) >= 5 and not [c for c in contoh if c["error"]]


def test_contoh_strategi_jalan(env, monkeypatch):
    monkeypatch.setenv("STRATEGI_DIR", str(REPO / "strategi"))
    r = run("contoh_ema_cross", {"timeframe": "1h", "mulai": "2024-01-05", "aset": ["BTCUSDT", "ETHUSDT"]}, {},
            store=env["store"])
    assert r["ringkasan"]["n_trades"] > 0
    r = run("contoh_futures_breakout", {"timeframe": "1h", "mulai": "2024-01-05"}, {"masuk": 30}, store=env["store"])
    assert r["pengaturan"]["produk"] == "futures"
    r = run("contoh_rsi_reversal", {"mulai": "2023-01-01"}, {"ema_tren": 50}, store=env["store"])
    assert r["pasar"] == "idx"
    r = run("contoh_asing_idx", {"aset": ["BBCA"], "mulai": "2024-06-01"}, {}, store=env["store"])
    assert r["ringkasan"]["n_trades"] == 0                 # tanpa data asing: tidak masuk pasar


# ---------------------------------------------------------------- API
def test_api_jalankan_dan_hasil(env, monkeypatch):
    from app.backtest.api import Jobs
    from app.config import Config
    from app.main import create_app
    from app.trading.accounts import AccountDB
    from app.trading.api import create_trading

    strat(env["sdir"], "ema", EMA)
    svc = create_trading(env["store"], AccountDB(env["tmp"] / "akun.db"))
    jobs = Jobs(env["tmp"] / "backtest", timeout=120)
    app = create_app(Config(match_workers=0), trading=svc, backtest=jobs)
    with TestClient(app) as c:
        s = c.get("/api/backtest/strategi").json()
        assert [x["file"] for x in s["strategi"]] == ["ema.py"] and s["pengumpul"]["ada"] is False
        assert c.post("/api/backtest/jalankan", json={"strategi": "../../etc/passwd"}).status_code == 404
        j = c.post("/api/backtest/jalankan", json={"strategi": "ema.py", "pengaturan": {"mulai": "2024-01-20"},
                                                    "parameter": {"n": 10}}).json()
        for _ in range(300):
            st = c.get(f"/api/backtest/job/{j['id']}").json()
            if st["status"] != "jalan":
                break
            time.sleep(0.1)
        assert st["status"] == "selesai", st
        h = c.get(f"/api/backtest/hasil/{j['id']}").json()
        assert h["parameter"]["n"] == 10 and h["per_aset"]
        assert c.get(f"/api/backtest/hasil/{j['id']}/aset/BTCUSDT").json()["t"]
        assert c.get("/api/backtest/hasil").json()["hasil"][0]["id"] == j["id"]
        assert c.get("/api/backtest/hasil/../x").status_code in (400, 404)
        assert c.delete(f"/api/backtest/hasil/{j['id']}").json()["ok"]
        assert c.get("/api/backtest/hasil").json()["hasil"] == []
