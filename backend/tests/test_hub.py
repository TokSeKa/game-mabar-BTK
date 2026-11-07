"""Tes Arena Mabar lewat HTTP + WebSocket: kursi manusia/bot campur, penonton, reaksi, mode instan, rating."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

BOT_DUAPERTIGA = "def aksi():\n    print('ronde', info()['ronde'])\n    return 20\n"


@pytest.fixture()
def client(tmp_path):
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        c.svc = svc
        yield c


def until(ws, typ, limit=400, pred=None):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == typ and (pred is None or pred(m)):
            return m
        if m["type"] == "error" and typ != "error":
            raise AssertionError(m)
    raise AssertionError(f"tidak menerima {typ}")


def register(c, name):
    r = c.post("/api/akun/daftar", json={"username": name, "password": "rahasia1"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_rest_hub(client):
    games = client.get("/api/main/games").json()
    ids = [g["id"] for g in games]
    assert {"suit", "poker", "kapal", "robot", "kartu", "tycoon", "lelang", "blotto", "kasdesa", "duapertiga", "farol"} <= set(ids)
    md = client.get("/api/main/panduan/poker").text
    assert "def aksi():" in md and "ekuitas" in md
    assert client.get("/api/main/panduan/tidakada").status_code == 404
    ok = client.post("/api/main/validasi", json={"game": "lelang", "kode": "def aksi():\n    return 3\n"}).json()
    assert ok == {"ok": True, "error": None}
    bad = client.post("/api/main/validasi", json={"game": "lelang", "kode": "def pilih():\n    return 3\n"}).json()
    assert bad["ok"] is False and "aksi" in bad["error"]["pesan"]
    r = client.post("/api/main/latihan", json={"game": "duapertiga", "kode": BOT_DUAPERTIGA, "nama": "Aku",
                                              "lawan": ["sepertiga", "level2"], "settings": {"ronde": 3}}).json()
    assert r["ok"] and r["names"][0] == "Aku" and len(r["names"]) == 3
    assert r["log"][0]["cetak"] == ["ronde 1"]
    assert len(r["frames"]) == 4


def test_room_manusia_dan_bot_campur_dengan_penonton(client):
    with client.websocket_connect("/ws/main") as a, client.websocket_connect("/ws/main") as b, \
            client.websocket_connect("/ws/main") as tv:
        a.send_json({"type": "buat", "game": "duapertiga", "nama": "Ani", "settings": {"ronde": 2, "mode_faktor": "tetap"}, "waktu": 30, "jeda_hasil": 0})
        masuk = until(a, "masuk")
        kode = masuk["kode"]
        until(a, "room")
        b.send_json({"type": "gabung", "kode": kode, "nama": "Budi"})
        until(b, "masuk")
        tv.send_json({"type": "gabung", "kode": kode, "nama": "Tono", "tonton": True})
        until(tv, "masuk")
        # Budi menambah bot sendiri di samping kursinya
        b.send_json({"type": "tambah_bot", "nama": "Robo", "kode": BOT_DUAPERTIGA, "label": "Botku"})
        room = until(a, "room", pred=lambda m: len(m["kursi"]) == 3)
        assert [k["kind"] for k in room["kursi"]] == ["manusia", "manusia", "bot"]
        assert room["penonton"] == ["Tono"]
        # hanya host yang boleh mulai
        b.send_json({"type": "mulai"})
        assert "host" in until(b, "error")["message"]
        a.send_json({"type": "mulai"})
        mulai_tv = until(tv, "mulai")
        assert mulai_tv["main_sendiri"] is False and mulai_tv["seat"] is None
        for ronde in (1, 2):
            ua = until(a, "update", pred=lambda m: m["my_turn"])
            assert ua["view"]["ronde"] == ronde
            a.send_json({"type": "aksi", "aksi": 30})
            until(a, "aksi_ok")
            ub = until(b, "update", pred=lambda m: m["my_turn"])
            b.send_json({"type": "aksi", "aksi": "abc"})
            assert "angka" in until(b, "error")["message"]
            b.send_json({"type": "aksi", "aksi": 10})
        tv.send_json({"type": "reaksi", "emoji": "🔥"})
        r = until(a, "reaksi")
        assert r == {"type": "reaksi", "nama": "Tono", "emoji": "🔥"}
        fin = until(a, "selesai")
        assert fin["names"] == ["Ani", "Budi", "Robo"] and fin["kinds"] == ["manusia", "manusia", "bot"]
        assert len(fin["frames"]) == 3
        assert fin["logs"] == {}                     # Ani tidak punya bot
        fin_b = until(b, "selesai")
        assert fin_b["logs"]["Robo"][0]["cetak"] == ["ronde 1"]
        # rata 20 (30,10,20) -> target 13.3: Budi (10) paling dekat di kedua ronde
        assert fin["result"]["pemenang"] == 1
        lobby = until(a, "room", pred=lambda m: m["status"] == "lobby")
        assert lobby["match_no"] == 1


def test_kursi_sendiri_jadi_bot_lalu_manusia_lagi(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "lelang", "nama": "Ani", "settings": {"barang": 3}})
        until(a, "masuk")
        a.send_json({"type": "jadi_bot", "kode": "def aksi():\n    return 1\n", "label": "Auto"})
        room = until(a, "room", pred=lambda m: m["kursi"][0]["kind"] == "bot")
        assert room["kursi"][0]["label"] == "Auto"
        a.send_json({"type": "jadi_bot", "kode": "def aksi(:\n"})
        assert "valid" in until(a, "error")["message"]
        a.send_json({"type": "jadi_manusia"})
        room = until(a, "room", pred=lambda m: m["kursi"][0]["kind"] == "manusia")
        a.send_json({"type": "mulai"})
        assert "minimal" in until(a, "error")["message"]


def test_waktu_habis_pakai_aksi_bawaan(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "kasdesa", "nama": "Ani", "settings": {"ronde": 1, "akhir_rahasia": False}, "waktu": 3})
        until(a, "masuk")
        a.send_json({"type": "tambah_bot", "nama": "B1", "kode": "def aksi():\n    return 10\n"})
        until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        a.send_json({"type": "mulai"})
        u = until(a, "update", pred=lambda m: any(e.get("jenis") == "waktu_habis" for e in m["events"]), limit=50)
        assert u["events"][0]["pemain"] == ["Ani"]
        fin = until(a, "selesai")
        assert fin["result"]["skor"][0] > fin["result"]["skor"][1]   # Ani (0 sumbangan) untung dari bot dermawan


def test_mode_mandiri_kartu(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "kartu", "nama": "Ani", "jeda": 0})
        until(a, "masuk")
        a.send_json({"type": "tambah_bot", "nama": "Bot", "kode": "def aksi():\n    return 'akhiri' if info()['fase'] == 'tarung' else 'lewati'\n"})
        until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        a.send_json({"type": "mulai"})
        u = until(a, "update", pred=lambda m: m["my_turn"])
        assert u["view"]["fase"] == "tarung" and len(u["view"]["tangan"]) == 5
        a.send_json({"type": "aksi", "aksi": "akhiri"})
        u2 = until(a, "update", pred=lambda m: m["view"]["giliran"] == 2)
        assert u2["view"]["energi"] == 3


def test_instan_semua_bot_dan_rating(client, tmp_path):
    tok_a, tok_b = register(client, "andi"), register(client, "bela")
    bot_kecil = "def aksi():\n    return 5\n"
    bot_besar = "def aksi():\n    return 90\n"
    with client.websocket_connect("/ws/main") as a, client.websocket_connect("/ws/main") as b:
        a.send_json({"type": "buat", "game": "duapertiga", "nama": "x", "settings": {"ronde": 3, "mode_faktor": "tetap"}, "jeda": 0, "token": tok_a})
        kode = until(a, "masuk")["kode"]
        b.send_json({"type": "gabung", "kode": kode, "nama": "y", "token": tok_b})
        until(b, "masuk")
        room = until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        assert [k["name"] for k in room["kursi"]] == ["andi", "bela"]   # nama akun dipakai
        a.send_json({"type": "jadi_bot", "kode": bot_kecil})
        b.send_json({"type": "jadi_bot", "kode": bot_besar})
        until(a, "room", pred=lambda m: all(k["kind"] == "bot" for k in m["kursi"]))
        a.send_json({"type": "mulai"})
        fin = until(a, "selesai")
        assert fin["result"]["pemenang"] == 0
        assert fin["ratings"]["andi"]["delta"] > 0 > fin["ratings"]["bela"]["delta"]
    board = client.get("/api/main/liga/duapertiga").json()["board"]
    assert [r["username"] for r in board][:2] == ["andi", "bela"]


def test_kembali_setelah_putus(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "blotto", "nama": "Ani"})
        m = until(a, "masuk")
    with client.websocket_connect("/ws/main") as a2:
        a2.send_json({"type": "kembali", "kode": m["kode"], "member_id": m["member_id"], "token_anggota": "salah"})
        assert "Sesi" in until(a2, "error")["message"]
        a2.send_json({"type": "kembali", "kode": m["kode"], "member_id": m["member_id"], "token_anggota": m["token"]})
        until(a2, "masuk")
        room = until(a2, "room")
        assert room["kursi"][0]["name"] == "Ani" and room["kursi"][0]["online"]
