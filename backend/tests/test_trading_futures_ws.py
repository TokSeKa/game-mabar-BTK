"""Futures & margin lewat server (WebSocket, sesi, balapan, data funding)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.ingest_binance import FUND_REC, funding_path, parse_funding_zip
from app.trading.session import Blind, build_view
from app.trading.store import CandleStore

from .trading_fixtures import T0, make_crypto, make_idx
from .test_trading_ws import until


@pytest.fixture()
def client(tmp_path):
    make_crypto(tmp_path / "pasar", symbol="BTCUSDT", days=20, seed=11)
    make_idx(tmp_path / "pasar", symbol="TLKM")
    make_idx(tmp_path / "pasar", symbol="BBCA")
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        c.svc = svc
        yield c


def test_katalog_produk(client):
    k = client.get("/api/pasar/katalog").json()
    assert set(k["produk"]["nyata"]["crypto"]) == {"futures"}
    assert set(k["produk"]["nyata"]["idx"]) == {"margin"}
    assert k["produk"]["nyata"]["idx"]["margin"]["short_list"] == ["ASII", "BBCA", "BRPT", "BUMI", "INDF"]
    assert set(k["produk"]["bebas"]["idx"]) == {"margin", "futures"}


def test_solo_futures_short_leverage_funding(client):
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_start", "config": {"pasar": "crypto", "tf": "1h", "buta": True, "produk": "futures"}})
        s = until(ws, "session")
        assert s["produk"] == "futures" and s["product"]["kind"] == "perp" and s["product"]["maker"] == 0.0002
        a = until(ws, "account")["account"]
        assert a["lev"] == 10 and a["mode"] == "cross"
        ws.send_json({"type": "leverage", "lev": 25})
        assert until(ws, "account")["account"]["lev"] == 25
        price = s["price"]
        ws.send_json({"type": "order", "side": "sell", "kind": "market", "qty": 20, "sl": price * 1.05, "tp": price * 0.9})
        a = until(ws, "account")
        acc = a["account"]
        assert acc["qty"] == -20 and acc["side"] == "short" and acc["liq_price"] > price
        assert {o["label"] for o in acc["orders"]} == {"SL", "TP"}
        ws.send_json({"type": "margin_mode", "mode": "isolated"})
        assert "tidak ada posisi" in until(ws, "error")["message"]
        ws.send_json({"type": "step", "tf": "1h", "n": 12})
        t = until(ws, "tick")
        assert t["account"]["funding_paid"] != 0 or t["account"]["qty"] == 0
        if t["account"]["qty"]:
            ws.send_json({"type": "close"})
            assert until(ws, "account")["account"]["qty"] == 0
        ws.send_json({"type": "finish"})
        summ = until(ws, "summary")
        assert summ["stats"]["produk"] == "futures" and summ["stats"]["n_short"] == 1
        assert summ["trades"][0]["side"] == "short"


def test_produk_tidak_tersedia(client):
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_start", "config": {"pasar": "idx", "tf": "1d", "buta": False, "produk": "futures"}})
        assert "tidak tersedia" in until(ws, "error")["message"]
        ws.send_json({"type": "solo_start", "config": {"pasar": "crypto", "tf": "1h", "buta": True}})
        until(ws, "session")
        ws.send_json({"type": "leverage", "lev": 5})
        assert "Futures atau Margin" in until(ws, "error")["message"]


def test_idx_short_mengikuti_daftar_bei(client):
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_start", "config": {"pasar": "idx", "aset": "idx:TLKM", "tf": "1d", "buta": False,
                                                     "produk": "margin"}})
        s = until(ws, "session")
        assert s["product"]["short_ok"] is False
        ws.send_json({"type": "order", "side": "sell", "kind": "limit", "price": s["price"] * 1.01, "qty": 1000})
        assert "Daftar Efek Short Selling" in until(ws, "error")["message"]
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_start", "config": {"pasar": "idx", "aset": "idx:TLKM", "tf": "1d", "buta": False,
                                                     "produk": "margin", "aturan": "bebas"}})
        s = until(ws, "session")
        assert s["product"]["short_ok"] is True
        until(ws, "account")
        ws.send_json({"type": "order", "side": "sell", "kind": "market", "qty": 1000})
        assert until(ws, "account")["account"]["qty"] == -1000


def test_balapan_futures(client):
    with client.websocket_connect("/ws/pasar") as a:
        a.send_json({"type": "race_create", "name": "Host",
                     "config": {"tf": "15m", "langkah": 20, "kecepatan": 0.3, "produk": "futures"}})
        until(a, "race_joined")
        st = until(a, "race_state")
        assert st["produk"] == "futures"
        a.send_json({"type": "race_start"})
        s = until(a, "session")
        assert s["produk"] == "futures" and s["market"] == "crypto"
        a.send_json({"type": "order", "side": "sell", "kind": "market", "qty": 1})
        until(a, "account")
        board = until(a, "race_board", limit=500)
        assert board["board"][0]["side"] in ("short", None)


def test_jadwal_funding_dari_file(tmp_path):
    root = tmp_path / "pasar"
    make_crypto(root, symbol="BTCUSDT", days=10)
    times = np.arange(T0, T0 + 10 * 86_400_000, 8 * 3_600_000)
    arr = np.empty(len(times), FUND_REC)
    arr["t"], arr["r"] = times, -0.0005
    funding_path(root, "BTCUSDT").parent.mkdir(parents=True, exist_ok=True)
    np.save(funding_path(root, "BTCUSDT"), arr)
    store = CandleStore(root)
    v = build_view(store, "crypto:BTCUSDT", "1h", np.random.default_rng(1), Blind.from_any(True), steps=40)
    sched = v.funding_schedule(0.0001, 8)
    t0 = v.now()
    ev = list(sched(t0, t0 + 24 * 3600))
    assert len(ev) == 3 and all(r == -0.0005 for _, r in ev)
    assert all(ts % (8 * 3600) == 0 for ts, _ in ev)       # tanggal disamarkan, jam funding tetap


def test_parse_funding_csv(tmp_path):
    import zipfile
    p = tmp_path / "f.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("BTCUSDT-fundingRate-2024-01.csv",
                   "calc_time,funding_interval_hours,last_funding_rate\n1704067200000,8,0.00037409\n1704096000000,8,0.0001\n")
    arr = parse_funding_zip(p)
    assert arr["t"].tolist() == [1704067200000, 1704096000000] and arr["r"][0] == pytest.approx(0.00037409)
