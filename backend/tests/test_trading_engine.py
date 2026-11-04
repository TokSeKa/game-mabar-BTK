import numpy as np
import pytest

from app.trading.engine import Account, TradeError


def acc(**kw):
    base = dict(capital=10_000, fee_buy=0.001, fee_sell=0.001, slippage=0.0, qty_step=1e-6, min_notional=5)
    base.update(kw)
    return Account(**base)


def run(a, candles):
    c = np.array(candles, dtype=float)
    return a.process(c[:, 0], c[:, 1], c[:, 2], c[:, 3], np.arange(len(c)) + 100)


def test_market_beli_jual_dengan_fee():
    a = acc(slippage=0.001)
    f = a.market("buy", 10, 100.0, 1)
    assert f.price == pytest.approx(100.1)
    assert a.cash == pytest.approx(10_000 - 1001 - 1.001)
    assert a.avg_cost == pytest.approx((1001 + 1.001) / 10)
    s = a.market("sell", 10, 110.0, 2)
    assert s.price == pytest.approx(109.89)
    assert a.qty == 0 and len(a.trades) == 1
    expected_pnl = 1098.9 * 0.999 - 1002.001
    assert a.trades[0]["pnl"] == pytest.approx(expected_pnl)
    assert a.fees_paid == pytest.approx(1.001 + 1.0989)


def test_validasi_spot():
    a = acc()
    with pytest.raises(TradeError):
        a.market("buy", 200, 100.0, 1)        # saldo kurang
    with pytest.raises(TradeError):
        a.market("sell", 1, 100.0, 1)         # belum punya
    with pytest.raises(TradeError):
        a.market("buy", 0.01, 100.0, 1)       # di bawah nilai minimal
    a.market("buy", 5, 100.0, 1)
    a.protect(5, 90, 120, 2, last=100)
    with pytest.raises(TradeError):
        a.market("sell", 1, 100.0, 3)         # terkunci di OCO
    assert a.free_qty() == pytest.approx(0)


def test_lot_idx():
    a = acc(capital=100_000_000, qty_step=100, fee_buy=0.0015, fee_sell=0.0025, min_notional=0)
    f = a.market("buy", 250, 5000.0, 1)
    assert f.qty == 200
    with pytest.raises(TradeError):
        a.market("buy", 50, 5000.0, 1)


def test_limit_beli_dan_gap():
    a = acc()
    a.place("buy", "limit", 95, 10, 1, last=100)
    assert a.free_cash() == pytest.approx(10_000 - 950 * 1.001)
    fills = run(a, [[100, 101, 96, 99], [98, 99, 94, 95]])
    assert len(fills) == 1 and fills[0].price == 95 and fills[0].time == 101
    b = acc()
    b.place("buy", "limit", 95, 10, 1, last=100)
    fills = run(b, [[93, 94, 92, 93]])  # buka di bawah limit
    assert fills[0].price == 93


def test_stop_loss_dengan_slippage_dan_gap():
    a = acc(slippage=0.01)
    a.market("buy", 10, 100.0, 1)
    a.protect(10, 90, None, 2, last=a.fills[-1].price)
    fills = run(a, [[95, 96, 89, 92]])
    assert fills[0].price == pytest.approx(90 * 0.99)
    b = acc(slippage=0.01)
    b.market("buy", 10, 100.0, 1)
    b.protect(10, 90, None, 2)
    fills = run(b, [[80, 85, 79, 84]])
    assert fills[0].price == pytest.approx(80 * 0.99)


def test_bracket_oco_dan_jalur_candle():
    a = acc()
    a.place("buy", "limit", 100, 10, 1, last=105, sl=95, tp=110)
    fills = run(a, [[104, 105, 99, 103], [103, 111, 102, 108]])
    assert [f.label for f in fills] == ["Entry", "TP"]
    assert all(o.status != "open" for o in a.orders.values())
    assert a.qty == 0 and a.trades[0]["pnl"] > 0
    # candle naik besar menyentuh SL dan TP: jalur O→L→H→C, jadi SL dulu
    b = acc()
    b.market("buy", 10, 100, 1)
    b.protect(10, 95, 110, 2)
    fills = run(b, [[100, 112, 94, 111]])
    assert [f.label for f in fills] == ["SL"]
    # candle turun: O→H→L→C, jadi TP dulu
    c = acc()
    c.market("buy", 10, 100, 1)
    c.protect(10, 95, 110, 2)
    fills = run(c, [[100, 112, 94, 96]])
    assert [f.label for f in fills] == ["TP"]


def test_entry_dan_sl_di_candle_yang_sama():
    a = acc()
    a.place("buy", "limit", 100, 10, 1, last=105, sl=97)
    fills = run(a, [[104, 104, 96, 97.5]])  # candle turun: turun ke 100 (beli) lalu ke 96 (SL)
    assert [f.label for f in fills] == ["Entry", "SL"]


def test_stop_buy_breakout():
    a = acc()
    with pytest.raises(TradeError):
        a.place("buy", "stop", 95, 1, 1, last=100)
    a.place("buy", "stop", 105, 10, 1, last=100)
    fills = run(a, [[100, 104, 99, 103], [103, 106, 102, 105]])
    assert len(fills) == 1 and fills[0].price == 105


def test_cancel_melepas_dana():
    a = acc()
    o = a.place("buy", "limit", 90, 10, 1, last=100)
    assert a.reserved_cash > 0
    a.cancel(o.id)
    assert a.reserved_cash == 0 and a.free_cash() == 10_000
    with pytest.raises(TradeError):
        a.cancel(o.id)


def test_drawdown_exposure_dan_ringkasan():
    a = acc(fee_buy=0, fee_sell=0)
    a.market("buy", 100, 100, 1)
    run(a, [[100, 100, 80, 80], [80, 120, 80, 120]])
    assert a.max_dd == pytest.approx(0.2)
    a.market("sell", 100, 120, 3)
    s = a.summary(120, 100)
    assert s["return_pct"] == pytest.approx(20)
    assert s["buy_hold_pct"] == pytest.approx(20)
    assert s["win_rate"] == 100 and s["n_trades"] == 1
    assert s["exposure_pct"] == 100


def test_beli_sebagian_kalau_gap_lebih_mahal():
    a = acc(capital=1000, fee_buy=0, slippage=0.0)
    a.place("buy", "stop", 105, 9.5, 1, last=100)  # cadangan 997.5
    fills = run(a, [[110, 111, 109, 110]])
    assert fills[0].price == 110
    assert fills[0].qty < 9.5 and "sebagian" in fills[0].note
