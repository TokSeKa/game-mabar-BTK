import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app

BATU_BOT = "def pilih():\n    return BATU\n"
KERTAS_BOT = "def pilih():\n    print('halo', ronde())\n    return KERTAS\n"


@pytest.fixture()
def client():
    app = create_app(Config(match_workers=0))
    with TestClient(app) as c:
        yield c


def until(ws, typ, limit=30, pred=None):
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == typ and (pred is None or pred(msg)):
            return msg
        if msg["type"] == "error" and typ != "error":
            raise AssertionError(msg)
    raise AssertionError(f"tidak menerima {typ}")


def test_rest_dasar(client):
    assert client.get("/api/health").json()["ok"] is True
    assert len(client.get("/api/templates").json()) >= 8
    assert any(f["nama"] == "pengalah" for f in client.get("/api/library").json()["fungsi"])
    assert client.post("/api/validate", json={"code": BATU_BOT}).json() == {"ok": True, "error": None}
    bad = client.post("/api/validate", json={"code": "import os"}).json()
    assert bad["ok"] is False and "import" in bad["error"]["pesan"]


def test_latihan(client):
    r = client.post("/api/practice", json={"code": KERTAS_BOT, "nama": "Aku", "lawan": ["si_batu", "si_batu"],
                                           "settings": {"ronde_maks": 30}}).json()
    assert r["ok"] is True
    names = [p["name"] for p in r["match"]["players"]]
    assert names == ["Aku", "Si Batu", "Si Batu 2"]
    assert r["match"]["winners"] == [0]
    assert r["my_log"][0]["cetak"] == ["halo 1"]
    bad = client.post("/api/practice", json={"code": "x"}).json()
    assert bad["ok"] is False


def test_alur_room_lengkap(client):
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "create_room", "name": "Budi"})
        joined_a = until(a, "joined")
        code = joined_a["room_code"]
        until(a, "room_state")

        b.send_json({"type": "join_room", "code": code.lower(), "name": "budi"})
        assert "sudah dipakai" in until(b, "error")["message"]
        b.send_json({"type": "join_room", "code": code, "name": "Ani"})
        joined_b = until(b, "joined")
        state = until(b, "room_state")["room"]
        assert [p["name"] for p in state["players"]] == ["Budi", "Ani"]
        assert state["host_id"] == joined_a["player_id"]

        # hanya host yang boleh mulai / ubah aturan
        b.send_json({"type": "start_match"})
        assert "host" in until(b, "error")["message"]
        a.send_json({"type": "update_settings", "settings": {"hp_awal": 300, "hp_kalah": 100}})
        until(a, "room_state", pred=lambda m: m["room"]["settings"]["hp_awal"] == 300)

        b.send_json({"type": "set_ready", "ready": True})
        assert "bot" in until(b, "error")["message"]

        a.send_json({"type": "submit_bot", "code": "import os"})
        st = until(a, "bot_status")
        assert st["ok"] is False and "import" in st["error"]["pesan"]
        a.send_json({"type": "submit_bot", "code": BATU_BOT})
        assert until(a, "bot_status")["ok"] is True
        b.send_json({"type": "submit_bot", "code": KERTAS_BOT})
        assert until(b, "bot_status")["ok"] is True
        a.send_json({"type": "set_ready", "ready": True})
        b.send_json({"type": "set_ready", "ready": True})
        a.send_json({"type": "start_match"})

        ra = until(a, "match_result")
        rb = until(b, "match_result")
        assert ra["match"]["winners"] == [1]
        assert ra["my_index"] == 0 and rb["my_index"] == 1
        assert "cetak" not in ra["my_log"][0]        # log Budi tidak berisi print Ani
        assert rb["my_log"][0]["cetak"] == ["halo 1"]
        assert "code" not in str(ra["match"]["players"])  # kode tidak bocor
        assert BATU_BOT not in str(rb) and KERTAS_BOT not in str(ra)

        state = until(a, "room_state", pred=lambda m: m["room"]["status"] == "lobby" and m["room"]["match_count"] == 1)["room"]
        wins = {p["name"]: p["wins"] for p in state["players"]}
        assert wins == {"Budi": 0, "Ani": 1}
        assert all(not p["ready"] for p in state["players"])

        b.send_json({"type": "reveal_code"})
        rev = until(a, "code_revealed")
        assert rev["name"] == "Ani" and rev["code"] == KERTAS_BOT

        token_b, pid_b = joined_b["token"], joined_b["player_id"]

    # sambung ulang setelah koneksi putus (misalnya refresh halaman)
    with client.websocket_connect("/ws") as b2:
        b2.send_json({"type": "rejoin", "code": code, "player_id": pid_b, "token": "salah"})
        assert "berakhir" in until(b2, "error")["message"]
        b2.send_json({"type": "rejoin", "code": code, "player_id": pid_b, "token": token_b})
        until(b2, "joined")
        st = until(b2, "bot_status")
        assert st["code"] == KERTAS_BOT
        mr = until(b2, "match_result")
        assert mr["replay"] is False and mr["my_index"] == 1


def test_room_penuh_dan_kode_salah(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join_room", "code": "ZZZZZ", "name": "x"})
        assert "tidak ditemukan" in until(ws, "error")["message"]
        ws.send_json({"type": "submit_bot", "code": BATU_BOT})
        assert "Masuk" in until(ws, "error")["message"]


def test_maksimal_delapan_pemain(client):
    conns = [client.websocket_connect("/ws") for _ in range(9)]
    socks = [c.__enter__() for c in conns]
    try:
        socks[0].send_json({"type": "create_room", "name": "P0"})
        code = until(socks[0], "joined")["room_code"]
        for i in range(1, 8):
            socks[i].send_json({"type": "join_room", "code": code, "name": f"P{i}"})
            until(socks[i], "joined")
        socks[8].send_json({"type": "join_room", "code": code, "name": "P8"})
        assert "penuh" in until(socks[8], "error")["message"]
    finally:
        for c in conns:
            c.__exit__(None, None, None)


def test_kick(client):
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "create_room", "name": "Host"})
        code = until(a, "joined")["room_code"]
        b.send_json({"type": "join_room", "code": code, "name": "Tamu"})
        pid = until(b, "joined")["player_id"]
        a.send_json({"type": "kick", "player_id": pid})
        until(b, "kicked")
        until(a, "room_state", pred=lambda m: len(m["room"]["players"]) == 1)
