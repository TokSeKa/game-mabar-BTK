import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

from .trading_fixtures import make_crypto


@pytest.fixture()
def client(tmp_path):
    make_crypto(tmp_path / "pasar", symbol="AAAUSDT", days=20, seed=11)
    make_crypto(tmp_path / "pasar", symbol="BBBUSDT", days=20, seed=12)
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        c.svc = svc
        yield c


def until(ws, typ, limit=200):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == typ:
            return m
        if m["type"] == "error" and typ != "error":
            raise AssertionError(m)
    raise AssertionError(f"tidak menerima {typ}")


def register(c, name="budi", pw="rahasia1"):
    r = c.post("/api/akun/daftar", json={"username": name, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_akun(client):
    tok = register(client)
    assert client.post("/api/akun/daftar", json={"username": "BUDI", "password": "xxxxxx"}).status_code == 400
    assert client.post("/api/akun/masuk", json={"username": "budi", "password": "salah!!"}).status_code == 400
    r = client.post("/api/akun/masuk", json={"username": "budi", "password": "rahasia1"})
    assert r.status_code == 200
    me = client.get("/api/akun/saya", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["user"]["username"] == "budi"
    assert client.get("/api/akun/saya").status_code == 401
    client.post("/api/akun/keluar", headers={"Authorization": f"Bearer {tok}"})
    assert client.get("/api/akun/saya", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_katalog(client):
    k = client.get("/api/pasar/katalog").json()
    assert [a["symbol"] for a in k["pasar"]["crypto"]["assets"]] == ["AAAUSDT", "BBBUSDT"]
    assert k["spec"]["idx"]["lot"] == 100


def test_solo_lengkap(client):
    tok = register(client)
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_start", "token": tok, "config": {"pasar": "crypto", "tf": "15m", "buta": True}})
        s = until(ws, "session")
        assert s["label"] == "Aset rahasia" and s["base_tf"] == "1m" and "1d" in s["tfs"]
        until(ws, "account")
        ws.send_json({"type": "history", "tf": "15m"})
        h = until(ws, "candles")
        assert len(h["candles"]) > 100
        price = s["price"]
        ws.send_json({"type": "order", "side": "buy", "kind": "market", "qty": 10, "sl": price * 0.9, "tp": price * 1.1})
        a = until(ws, "account")
        assert a["fills"][0]["side"] == "buy" and a["account"]["qty"] == 10
        assert {o["label"] for o in a["account"]["orders"]} == {"SL", "TP"}
        ws.send_json({"type": "order", "side": "sell", "kind": "market", "qty": 999})
        assert "tidak cukup" in until(ws, "error")["message"]
        ws.send_json({"type": "subscribe", "tfs": ["15m", "1h"]})
        ws.send_json({"type": "step", "tf": "15m", "n": 3})
        t = until(ws, "tick")
        assert set(t["updates"]) == {"15m", "1h"} and t["updates"]["15m"]
        ws.send_json({"type": "finish"})
        summ = until(ws, "summary")
        assert summ["reveal"]["symbol"] in ("AAAUSDT", "BBBUSDT")
        assert "return_pct" in summ["stats"] and summ["curve"]
        sid, secret = s["id"], s["secret"]
    # sambung ulang ke sesi yang sama
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "solo_resume", "id": sid, "secret": "salah"})
        assert until(ws, "error")
        ws.send_json({"type": "solo_resume", "id": sid, "secret": secret})
        assert until(ws, "session")["resumed"] is True
        until(ws, "summary")
    hist = client.get("/api/pasar/riwayat", headers={"Authorization": f"Bearer {tok}"}).json()
    assert hist["hasil"][0]["mode"] == "solo" and hist["profil"]["sesi"] == 1


def test_harian_peringkat_sekali(client):
    tok = register(client, "ani", "rahasia2")
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "daily_start", "token": tok})
        s = until(ws, "session")
        assert s["mode"] == "harian" and s["fixed_end"] is True
        ws.send_json({"type": "order", "side": "buy", "kind": "market", "qty": 5})
        until(ws, "account")
        done = None
        for _ in range(200):
            ws.send_json({"type": "step", "tf": s["chart_tf"], "n": 5})
            t = until(ws, "tick")
            if t["done"]:
                done = until(ws, "summary")
                break
        assert done and done["mode"] == "harian" and done["rank"] == 1
    info = client.get("/api/pasar/harian", headers={"Authorization": f"Bearer {tok}"}).json()
    assert info["board"][0]["username"] == "ani" and info["me"]["status"] == "done"
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "daily_start", "token": tok})
        assert until(ws, "session")["mode"] == "harian-latihan"
    # semua pemain mendapat soal yang sama
    tok2 = register(client, "citra", "rahasia3")
    with client.websocket_connect("/ws/pasar") as ws:
        ws.send_json({"type": "daily_start", "token": tok2})
        s2 = until(ws, "session")
        assert s2["start_time"] == s["start_time"] and s2["price"] == s["price"]


def test_balapan(client):
    with client.websocket_connect("/ws/pasar") as a, client.websocket_connect("/ws/pasar") as b:
        a.send_json({"type": "race_create", "name": "Host", "config": {"tf": "15m", "langkah": 20, "kecepatan": 0.3}})
        j = until(a, "race_joined")
        b.send_json({"type": "race_join", "code": j["code"], "name": "host"})
        assert "dipakai" in until(b, "error")["message"]
        b.send_json({"type": "race_join", "code": j["code"], "name": "Tamu"})
        until(b, "race_joined")
        b.send_json({"type": "race_start"})
        assert "host" in until(b, "error")["message"]
        a.send_json({"type": "race_start"})
        sa = until(a, "session")
        until(b, "session")
        assert sa["mode"] == "balapan"
        b.send_json({"type": "order", "side": "buy", "kind": "market", "qty": 3})
        until(b, "account")
        b.send_json({"type": "step"})
        assert "otomatis" in until(b, "error")["message"]
        until(a, "tick")
        board = until(a, "race_board")
        assert {r["name"] for r in board["board"]} == {"Host", "Tamu"}
        summ = until(b, "summary", limit=500)
        assert summ["mode"] == "balapan" and len(summ["board"]) == 2
