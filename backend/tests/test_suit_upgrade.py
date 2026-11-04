"""Upgrade Suit Bot Arena: mode event, debugger, turnamen, penonton + reaksi, rating liga."""

import pytest
from fastapi.testclient import TestClient

from app.compute import compute_tournament
from app.config import Config
from app.engine.events import KONKRET
from app.engine.match import BotEntry, MatchSettings, run_match
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

BATU = "def pilih():\n    return BATU\n"
GUNTING = "def pilih():\n    return GUNTING\n"
KERTAS = "def pilih():\n    return KERTAS\n"
PENGINTIP = """def pilih():
    lalu = pilihan_terakhir(lawan()[0])
    print('lihat', lalu)
    if lalu == BATU:
        return KERTAS
    return GUNTING
"""
PEMUTAR = """def pilih():
    urutan = [BATU, KERTAS, GUNTING]
    return urutan[ronde() % 3]
"""


def entries(*codes):
    return [BotEntry(f"B{i}", c) for i, c in enumerate(codes)]


# ---------------------------------------------------------------- event
def test_event_ganda_pikun_kilat_tipis():
    base = {"hp_awal": 1000, "hp_kalah": 100, "ronde_maks": 100, "ingatan": 10}
    r = run_match(entries(BATU, GUNTING), MatchSettings.from_dict({**base, "event": "ganda"}))
    assert r["rounds"][0]["delta"] == [200, -200] and r["event"]["id"] == "ganda"
    r = run_match(entries(BATU, BATU), MatchSettings.from_dict({**base, "event": "kilat"}))
    assert len(r["rounds"]) == 30 and r["settings"]["ronde_maks"] == 30
    r = run_match(entries(BATU, BATU), MatchSettings.from_dict({**base, "event": "pikun", "ronde_maks": 5}))
    assert r["settings"]["ingatan"] == 3
    r = run_match(entries(BATU, GUNTING), MatchSettings.from_dict({**base, "event": "tipis"}))
    assert r["settings"]["hp_awal"] == 300 and r["final_hp"] == [600, 0]


def test_event_kabut_menyembunyikan_pilihan_dari_bot():
    s = {"hp_awal": 1000, "hp_kalah": 100, "ronde_maks": 3, "ingatan": 10}
    normal = run_match(entries(PENGINTIP, BATU), MatchSettings.from_dict(s))
    kabut = run_match(entries(PENGINTIP, BATU), MatchSettings.from_dict({**s, "event": "kabut"}))
    assert [e["cetak"] for e in normal["logs"][0]] == [["lihat None"], ["lihat batu"], ["lihat batu"]]
    assert [e["cetak"] for e in kabut["logs"][0]] == [["lihat None"]] * 3
    # replay untuk manusia tetap lengkap
    assert kabut["rounds"][0]["choices"] == ["gunting", "batu"]


def test_event_kejutan_diundi_dan_tercatat():
    seen = set()
    for seed in range(40):
        r = run_match(entries(BATU, BATU), MatchSettings.from_dict({"event": "acak", "ronde_maks": 2}), seed=seed)
        assert r["event"]["kejutan"] is True and r["event"]["id"] in KONKRET
        seen.add(r["event"]["id"])
    assert len(seen) >= 4
    assert MatchSettings.from_dict({"event": "ngawur"}).event == "normal"


# ---------------------------------------------------------------- turnamen
def test_turnamen_setengah_kompetisi():
    res = compute_tournament([("Batu", BATU), ("Kertas", KERTAS), ("Gunting", GUNTING), ("Batu2", BATU)],
                             {"hp_awal": 300, "hp_kalah": 100, "ronde_maks": 10}, 20_000)
    assert len(res["matches"]) == 6
    by = {(m["a"], m["b"]): m for m in res["matches"]}
    assert by[(0, 1)]["pemenang"] == 1                     # kertas > batu
    assert by[(0, 3)]["pemenang"] is None                   # batu vs batu seri
    pts = {r["index"]: r["poin"] for r in res["standings"]}
    assert pts == {0: 4, 1: 6, 2: 3, 3: 4}
    assert res["standings"][0]["index"] == 1
    assert sum(r["menang"] for r in res["standings"]) == sum(r["kalah"] for r in res["standings"])


# ---------------------------------------------------------------- server
@pytest.fixture()
def client(tmp_path):
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        yield c


def until(ws, typ, limit=60, pred=None):
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


def test_daftar_event(client):
    ev = client.get("/api/events").json()
    assert [e["id"] for e in ev][:2] == ["normal", "ganda"] and any(e["id"] == "kabut" for e in ev)


def test_debugger_sama_dengan_match_asli(client):
    r = client.post("/api/practice", json={"code": PENGINTIP, "nama": "Aku", "lawan": ["pemutar", "si_batu"],
                                           "settings": {"ronde_maks": 8}}).json()
    m = r["match"]
    assert m["event"]["id"] == "normal"
    names = [p["name"] for p in m["players"]]
    for ronde in (1, 3, 6):
        before = [R for R in m["rounds"] if R["r"] < ronde]
        d = client.post("/api/debug", json={"code": PENGINTIP, "settings": m["settings"], "names": names, "my_index": 0,
                                            "ronde": ronde, "rounds": before[-11:]}).json()
        assert d["ok"] and d["error"] is None
        assert d["pilihan"] == m["rounds"][ronde - 1]["choices"][0], ronde
        assert d["trace"] and d["trace"][-1]["kembali"] in ("'kertas'", "'gunting'")
        assert any(t["baris"] == 2 for t in d["trace"]) and d["cetak"][0].startswith("lihat")
    bad = client.post("/api/debug", json={"code": PENGINTIP, "settings": m["settings"], "names": names, "my_index": 0,
                                          "ronde": 4, "rounds": m["rounds"][:1]})
    assert bad.status_code == 400
    err = client.post("/api/debug", json={"code": "def pilih():\n    return 1 / 0\n", "settings": m["settings"],
                                          "names": names, "my_index": 0, "ronde": 1, "rounds": []}).json()
    assert err["ok"] and err["pilihan"] is None and "nol" in err["error"]["pesan"] and err["error"]["baris"] == 2


def test_penonton_reaksi_turnamen_dan_rating(client):
    toks = [register(client, n) for n in ("andi", "bela", "cici")]
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b, \
            client.websocket_connect("/ws") as c, client.websocket_connect("/ws") as tv:
        a.send_json({"type": "create_room", "name": "Andi", "akun_token": toks[0]})
        code = until(a, "joined")["room_code"]
        b.send_json({"type": "join_room", "code": code, "name": "Bela", "akun_token": toks[1]})
        until(b, "joined")
        c.send_json({"type": "join_room", "code": code, "name": "Cici", "akun_token": toks[2]})
        until(c, "joined")
        tv.send_json({"type": "join_room", "code": code, "name": "Tono", "spectator": True})
        until(tv, "joined")
        st = until(a, "room_state", pred=lambda m: len(m["room"]["penonton"]) == 1)["room"]
        assert [p["name"] for p in st["players"]] == ["Andi", "Bela", "Cici"]
        assert st["players"][0]["akun"] == "andi" and st["penonton"][0]["name"] == "Tono"
        tv.send_json({"type": "submit_bot", "code": BATU})
        assert "Penonton" in until(tv, "error")["message"]
        tv.send_json({"type": "react", "emoji": "🔥"})
        assert until(a, "reaction") == {"type": "reaction", "name": "Tono", "emoji": "🔥"}

        for ws, code_bot in ((a, BATU), (b, KERTAS), (c, PEMUTAR)):
            ws.send_json({"type": "submit_bot", "code": code_bot})
            assert until(ws, "bot_status", pred=lambda m, cb=code_bot: m["code"] == cb)["ok"]
            ws.send_json({"type": "set_ready", "ready": True})
        until(a, "room_state", pred=lambda m: sum(p["ready"] for p in m["room"]["players"]) == 3)
        a.send_json({"type": "update_settings", "settings": {"hp_awal": 300, "ronde_maks": 12, "event": "ganda"}})
        until(a, "room_state", pred=lambda m: m["room"]["settings"]["event"] == "ganda")
        a.send_json({"type": "start_tournament"})
        tr = until(tv, "tournament_result")
        assert tr["baru"] and len(tr["matches"]) == 3 and tr["event"]["id"] == "ganda"
        assert tr["settings"]["hp_kalah"] == 200
        assert {p["name"] for p in tr["players"]} == {"Andi", "Bela", "Cici"}
        m01 = next(x for x in tr["matches"] if (x["a"], x["b"]) == (0, 1))
        assert m01["pemenang"] == 1 and len(m01["match"]["players"]) == 2
        assert set(tr["ratings"]) == {p["id"] for p in tr["players"]}
        champion = tr["players"][tr["standings"][0]["index"]]["id"]
        assert tr["ratings"][champion]["delta"] > 0

        # match biasa juga memberi rating
        for ws in (a, b, c):
            ws.send_json({"type": "set_ready", "ready": True})
        until(a, "room_state", pred=lambda m: sum(p["ready"] for p in m["room"]["players"]) == 3)
        a.send_json({"type": "start_match"})
        mr = until(a, "match_result")
        assert mr["match"]["ratings"] and mr["match"]["event"]["id"] == "ganda"
        assert until(tv, "match_result")["match"]["id"] == mr["match"]["id"]   # penonton ikut menonton replay

        # penonton boleh ambil kursi, pemain boleh jadi penonton
        tv.send_json({"type": "play"})
        st = until(tv, "room_state", pred=lambda m: len(m["room"]["players"]) == 4)["room"]
        assert st["penonton"] == []
    board = client.get("/api/main/liga/suit_arena").json()["board"]
    assert {r["username"] for r in board} == {"andi", "bela", "cici"}


def test_turnamen_butuh_tiga_pemain(client):
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "create_room", "name": "A"})
        code = until(a, "joined")["room_code"]
        b.send_json({"type": "join_room", "code": code, "name": "B"})
        until(b, "joined")
        for ws in (a, b):
            ws.send_json({"type": "submit_bot", "code": BATU})
            until(ws, "bot_status", pred=lambda m: m["code"] == BATU)
            ws.send_json({"type": "set_ready", "ready": True})
        until(a, "room_state", pred=lambda m: sum(p["ready"] for p in m["room"]["players"]) == 2)
        a.send_json({"type": "start_tournament"})
        assert "minimal 3" in until(a, "error")["message"]
