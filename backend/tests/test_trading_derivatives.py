"""Futures perpetual & akun margin (long/short) untuk Kilas Pasar."""

import numpy as np
import pytest

from app.trading.derivatives import DerivAccount
from app.trading.engine import TradeError
from app.trading.products import IDX_MARGIN, US_MARGIN, product_for

H8 = 8 * 3600


def perp(symbol="BTCUSDT", capital=10_000, **kw):
    base = dict(capital=capital, slippage=0.0, qty_step=1e-6, min_notional=5, symbol=symbol)
    base.update(kw)
    return DerivAccount(product_for("crypto", "futures", symbol), **base)


def run(a, candles, t0=1_000, dt=60):
    c = np.array(candles, dtype=float)
    return a.process(c[:, 0], c[:, 1], c[:, 2], c[:, 3], t0 + np.arange(len(c)) * dt)


# ---------------------------------------------------------------- futures kripto
def test_long_short_fee_taker_maker():
    a = perp()
    a.set_leverage(10, 100.0)
    f = a.market("buy", 50, 100.0, 1)                 # notional 5000, taker 0,05%
    assert f.fee == pytest.approx(2.5)
    assert a.qty == 50 and a.entry == 100
    assert a.position_margin(100.0) == pytest.approx(500)
    assert a.available(100.0) == pytest.approx(10_000 - 2.5 - 500)
    a.place("sell", "limit", 110, 50, 2, last=100.0, reduce_only=True)
    fills = run(a, [[100, 111, 99, 108]])
    assert len(fills) == 1 and fills[0].price == 110
    assert fills[0].fee == pytest.approx(5500 * 0.0002)  # limit yang menunggu = maker
    assert a.qty == 0
    t = a.trades[-1]
    assert t["side"] == "long" and t["pnl"] == pytest.approx(500 - 2.5 - 1.1)
    assert t["roe_pct"] == pytest.approx(t["pnl"] / 500 * 100)


def test_short_untung_saat_harga_turun():
    a = perp()
    a.market("sell", 10, 100.0, 1)
    assert a.qty == -10
    assert a.equity(90.0) == pytest.approx(10_000 - 0.5 + 100)
    a.close(90.0, 2)
    assert a.qty == 0 and a.trades[-1]["side"] == "short"
    assert a.wallet == pytest.approx(10_000 - 0.5 - 0.45 + 100)


def test_harga_likuidasi_cocok_dengan_maintenance():
    a = perp(capital=1_000)
    a.set_leverage(10, 100.0)
    a.market("buy", 99, 100.0, 1)                    # notional 9.900 USDT di tier BTC pertama (MMR 0,4%)
    lp = a.liq_price()
    assert lp is not None and 89 < lp < 92
    assert a.equity(lp) == pytest.approx(a.maint(lp), abs=1e-6)
    a2 = perp(capital=1_000)
    a2.set_leverage(10, 100.0)
    a2.market("sell", 99, 100.0, 1)
    lp2 = a2.liq_price()
    assert lp2 > 100 and a2.equity(lp2) == pytest.approx(a2.maint(lp2), abs=1e-6)


def test_likuidasi_cross_menghabiskan_margin_dan_tidak_minus():
    a = perp(capital=1_000)
    a.set_leverage(20, 100.0)
    a.market("buy", 195, 100.0, 1)
    lp = a.liq_price()
    a.place("buy", "limit", 50, 1, 2, last=100.0)    # order lain ikut batal saat likuidasi
    fills = run(a, [[100, 100.5, lp - 1, lp - 0.5], [80, 81, 70, 75]])
    liq = [f for f in fills if f.label == "Likuidasi"]
    assert len(liq) == 1 and liq[0].price == pytest.approx(lp)
    assert a.qty == 0 and a.n_liq == 1 and a.wallet >= 0
    assert a.wallet < 5          # cross: hampir seluruh saldo jadi jaminan posisi ini
    assert not [o for o in a.orders.values() if o.status == "open"]
    assert a.trades[-1]["liquidated"]


def test_gap_melewati_likuidasi_saldo_tetap_nol():
    a = perp(capital=1_000)
    a.set_leverage(50, 100.0)
    a.market("buy", 400, 100.0, 1)
    fills = run(a, [[60, 61, 55, 58]])               # buka jauh di bawah harga likuidasi
    assert fills[0].label == "Likuidasi" and fills[0].price == 60
    assert a.wallet == 0 and a.equity(58) == 0


def test_isolated_hanya_kehilangan_margin_posisi():
    a = perp(capital=10_000)
    a.set_mode("isolated")
    a.set_leverage(10, 100.0)
    a.market("buy", 100, 100.0, 1)                   # margin 1000
    assert a.iso == pytest.approx(1_000)
    lp = a.liq_price()
    assert 90 < lp < 92
    run(a, [[100, 100, lp - 1, lp - 1]])
    assert a.n_liq == 1
    assert a.wallet == pytest.approx(10_000 - 5 - 1_000, abs=1.0)
    with pytest.raises(TradeError):
        a.set_mode("cross") if a.qty else a.set_mode("tidak-ada")


def test_tambah_margin_isolated_menjauhkan_likuidasi():
    a = perp()
    a.set_mode("isolated")
    a.set_leverage(20, 100.0)
    a.market("buy", 100, 100.0, 1)
    lp1 = a.liq_price()
    a.adjust_margin(500, 100.0)
    assert a.liq_price() < lp1
    with pytest.raises(TradeError):
        a.adjust_margin(-2_000, 100.0)


def test_funding_long_membayar_short_menerima():
    a = perp()
    a.market("buy", 10, 100.0, H8 - 120)
    run(a, [[100, 100, 100, 100]] * 5, t0=H8 - 60, dt=60)   # melewati 08:00
    assert a.funding_paid == pytest.approx(10 * 100 * 0.0001)
    b = perp()
    b.market("sell", 10, 100.0, H8 - 120)
    run(b, [[100, 100, 100, 100]] * 5, t0=H8 - 60, dt=60)
    assert b.funding_paid == pytest.approx(-0.1)
    assert b.wallet > 10_000 - 0.5


def test_jadwal_funding_dari_data_asli():
    a = perp(funding_schedule=lambda t0, t1: [(ts, -0.002) for ts in (H8, 2 * H8) if t0 < ts <= t1])
    a.market("buy", 10, 100.0, H8 - 60)
    run(a, [[100, 100, 100, 100]] * 3, t0=H8 - 30, dt=H8)
    assert a.funding_paid == pytest.approx(-2 * 10 * 100 * 0.002)


def test_limit_marketable_jadi_taker_dan_post_only():
    a = perp()
    fills = a.place("buy", "limit", 105, 10, 1, last=100.0)
    assert len(fills) == 1 and fills[0].price == 100 and fills[0].fee == pytest.approx(1000 * 0.0005)
    with pytest.raises(TradeError):
        a.place("buy", "limit", 105, 10, 1, last=100.0, post_only=True)
    assert a.place("buy", "limit", 95, 10, 1, last=100.0, post_only=True) == []


def test_stop_limit():
    a = perp()
    a.place("buy", "stop_limit", 103, 10, 1, last=100.0, stop=102)
    fills = run(a, [[100, 102.5, 99, 102.2]])       # terpicu di 102, limit 103 langsung terisi
    assert len(fills) == 1 and fills[0].price == 102 and a.qty == 10
    b = perp()
    b.place("sell", "stop_limit", 99, 10, 1, last=100.0, stop=98)   # limit di atas harga picu
    fills = run(b, [[100, 100, 97, 97.5], [97.5, 99.5, 97, 99.2]])
    assert len(fills) == 1 and fills[0].price == 99 and b.qty == -10


def test_tp_sl_untuk_short_dan_flip():
    a = perp()
    a.market("sell", 10, 100.0, 1, sl=105, tp=90)
    assert sorted(o.label for o in a.orders.values() if o.status == "open") == ["SL", "TP"]
    run(a, [[100, 106, 99, 104]])
    assert a.qty == 0 and a.trades[-1]["side"] == "short"
    assert not [o for o in a.orders.values() if o.status == "open"]
    b = perp()
    b.market("buy", 10, 100.0, 1)
    b.market("sell", 25, 100.0, 2)                  # tutup 10 long, buka 15 short
    assert b.qty == -15 and len(b.trades) == 1


def test_batas_tier_dan_reduce_only():
    a = perp(capital=10_000)
    a.set_leverage(125, 100.0)
    with pytest.raises(TradeError):
        a.market("buy", 3_500, 100.0, 1)            # 350.000 USDT > batas 125× (300.000)
    a.market("buy", 100, 100.0, 1)
    with pytest.raises(TradeError):
        a.market("buy", 1, 100.0, 1, reduce_only=True)
    f = a.market("sell", 500, 100.0, 1, reduce_only=True)
    assert f.qty == 100 and a.qty == 0


def test_margin_tidak_cukup():
    a = perp(capital=100)
    a.set_leverage(5, 100.0)
    with pytest.raises(TradeError):
        a.market("buy", 10, 100.0, 1)               # butuh 200 + fee
    assert a.max_qty("buy", 100.0) == pytest.approx(4.99, abs=0.01)


# ---------------------------------------------------------------- saham US (Reg T)
def us(**kw):
    base = dict(capital=10_000, slippage=0.0, qty_step=1, min_notional=0, symbol="AAPL")
    base.update(kw)
    return DerivAccount(US_MARGIN, **base)


def test_us_komisi_per_lembar_sec_taf():
    a = us()
    f = a.market("buy", 100, 100.0, 1)
    assert f.fee == pytest.approx(1.0)               # 100 × 0,005 = 0,5 → minimal USD 1
    s = a.market("sell", 100, 110.0, 2)
    assert s.fee == pytest.approx(1.0 + 11_000 * 20.60e-6 + 100 * 0.000195)


def test_us_margin_bunga_dan_likuidasi_short():
    a = us()
    a.market("buy", 180, 100.0, 0)                   # 18.000 dengan modal 10.000 → pinjam ±8.000
    day = 86_400
    run(a, [[100, 100, 100, 100]] * 3, t0=day * 1 + 3600, dt=day)
    debt = 180 * 100 + 1 - 10_000
    assert a.interest_paid == pytest.approx(debt * 0.0512 / 360 * 3, rel=1e-3)
    b = us()
    b.market("sell", 150, 100.0, 0)                  # short 15.000
    lp = b.liq_price()
    assert lp > 100
    assert b.equity(lp) == pytest.approx(0.30 * 150 * lp, rel=1e-6)
    run(b, [[100, lp + 1, 99, lp + 0.5]], t0=10)
    assert b.qty == 0 and b.fills[-1].label == "Forced buy"


def test_us_tidak_bisa_lebih_dari_2x():
    a = us()
    with pytest.raises(TradeError):
        a.market("buy", 210, 100.0, 1)


# ---------------------------------------------------------------- saham IDX (BEI)
def idx(symbol="BBCA", capital=100_000_000, **kw):
    base = dict(capital=capital, slippage=0.0, qty_step=100, min_notional=0, symbol=symbol)
    base.update(kw)
    return DerivAccount(IDX_MARGIN, **base)


def test_idx_short_hanya_daftar_efek_dan_uptick():
    a = idx("TLKM")
    with pytest.raises(TradeError, match="Daftar Efek Short Selling"):
        a.place("sell", "limit", 3000, 1000, 1, last=3000)
    b = idx("BBCA")
    with pytest.raises(TradeError, match="uptick"):
        b.market("sell", 1000, 9000, 1)
    with pytest.raises(TradeError, match="uptick"):
        b.place("sell", "limit", 8975, 1000, 1, last=9000)
    assert b.place("sell", "limit", 9025, 1000, 1, last=9000) == []
    fills = run(b, [[9000, 9050, 8990, 9010]])
    assert len(fills) == 1 and b.qty == -1000
    assert fills[0].fee == pytest.approx(9025 * 1000 * 0.0025)


def test_idx_short_butuh_jaminan_50_juta_dan_forced_buy_120():
    a = idx("BBCA", capital=40_000_000)
    with pytest.raises(TradeError, match="jaminan awal"):
        a.place("sell", "limit", 9000, 1000, 1, last=9000)
    b = idx("BBCA")
    b.place("sell", "limit", 10_000, 10_000, 1, last=10_000)
    run(b, [[10_000, 10_000, 10_000, 10_000]])
    lp = b.liq_price()
    sv = 10_000 * lp
    assert (b.equity(lp) + sv) / sv == pytest.approx(1.20, rel=1e-6)     # rasio jaminan 120%
    cp = b.call_price()
    assert (b.equity(cp) + 10_000 * cp) / (10_000 * cp) == pytest.approx(1.35, rel=1e-6)
    assert b.snapshot(cp + 1)["margin_call"]


def test_idx_long_margin_tetap_lot():
    a = idx("TLKM")
    f = a.market("buy", 50_050, 3000, 1)
    assert f.qty == 50_000                           # dibulatkan ke lot (100 lembar)
    assert a.cash == 0 if hasattr(a, "cash") else True
    assert a.snapshot(3000)["cash"] < 0               # sebagian dibiayai broker
