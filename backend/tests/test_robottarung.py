"""Tes Robot Tarung: garasi, fisika, kerusakan per komponen, senjata, jebakan, KO, juri, bot, dan room real-time."""

import itertools
import math

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.games.base import ActionError
from app.games.g_robottarung import (CONTOH_RAKITAN, DT, KATALOG, LUBANG_BUKA, SENJATA, berat, bersihkan_rakitan,
                                     pas_berat, rakitan_bawaan)
from app.games.registry import GAMES
from app.games.runner import play_sync
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

from .test_hub import until

G = GAMES["robottarung"]


def _arena(cfg=None, designs=(0, 0), names=("A", "B"), seed=1):
    """State yang sudah lewat garasi & hitung mundur, tanpa jebakan kecuali diminta."""
    c = G.clean_settings({"lubang": False, "gergaji_lantai": False, "palu_arena": False, **(cfg or {})})
    s = G.init(c, list(names), seed)
    acts = {p: G.validate(s, p, {"rakit": CONTOH_RAKITAN[d] if isinstance(d, int) else d}) for p, d in enumerate(designs)}
    G.apply(s, acts)
    assert s["fase"] == "hitung"
    while s["fase"] == "hitung":
        G.apply(s, {})
    return s


def _place(s, p, x, y, deg):
    r = s["robot"][p]
    r.update(x=x, y=y, a=math.radians(deg), vx=0.0, vy=0.0, w=0.0)


def _run(s, ticks, acts=None):
    ev = []
    for _ in range(ticks):
        ev += G.apply(s, acts or {})
        acts = None                 # kendali tetap tersimpan (None = tidak berubah)
    return ev


def test_rakitan_valid_dan_berat():
    d = CONTOH_RAKITAN[0]
    assert berat(d) == 12 + 14 + 10 + 22 + 10 * 2
    with pytest.raises(ActionError, match="melebihi batas"):
        bersihkan_rakitan({**d, "armor": {"depan": 8, "kanan": 8, "belakang": 8, "kiri": 8}}, 100)
    with pytest.raises(ActionError, match="senjata harus"):
        bersihkan_rakitan({**d, "senjata": "laser"}, 100)
    with pytest.raises(ActionError, match="armor depan"):
        bersihkan_rakitan({**d, "armor": {"depan": 9}}, 100)
    for m in (60, 70, 100):
        for c in CONTOH_RAKITAN:
            p = pas_berat(c, m)
            assert berat(p) <= m and p["senjata"] == c["senjata"]
    assert berat(rakitan_bawaan(60)) <= 60
    meta = G.meta()
    assert meta["katalog"]["senjata"]["flipper"]["berat"] == KATALOG["senjata"]["flipper"]["berat"] and meta["detak"] if "detak" in meta else True


def test_garasi_ke_arena_dan_rakitan_bawaan_saat_waktu_habis():
    c = G.clean_settings({"waktu_garasi": 20})
    s = G.init(c, ["A", "B"], 1)
    assert G.detak(c) == DT and G.observe(s, 0)["fase"] == "garasi"
    G.apply(s, {0: G.validate(s, 0, {"rakit": CONTOH_RAKITAN[2]})})
    v = G.observe(s, 1)
    assert v["siap"] == {"A": True, "B": False} and "desain" not in v and v["desain_saya"] is None
    ev = []
    for _ in range(int(20 / DT)):
        ev += G.apply(s, {})
    assert any(e["jenis"] == "siap" and e.get("bawaan") for e in ev) and s["fase"] == "hitung"
    assert s["desain"][1] == rakitan_bawaan(100) and G.validate(s, 0, {"rakit": CONTOH_RAKITAN[0]}) is None


def test_kendali_tank_belok_kanan_dan_kendali_tetap():
    s = _arena()
    _place(s, 0, 4, 7, 0)
    _place(s, 1, 12, 2, 180)
    _run(s, 20, {0: G.validate(s, 0, {"maju": 1, "belok": 0.5})})
    r = s["robot"][0]
    assert r["x"] > 4.5 and 0 < math.degrees(r["a"]) < 180       # belok positif = searah jarum jam (ke kanan, y ke bawah)
    assert r["kontrol"][:2] == [1.0, 0.5]
    _run(s, 10, {0: G.validate(s, 0, {"maju": 0})})
    assert r["kontrol"][:2] == [0.0, 0.5]
    with pytest.raises(ActionError):
        G.validate(s, 0, {"maju": "cepat"})


def test_kerusakan_armor_lalu_komponen_sisi_dan_kubah():
    s = _arena(designs=(0, 1))
    r = s["robot"][0]
    kali = 0.55
    G._damage(s, 0, "kanan", 30 / kali, attacker=1)              # armor kanan 2 tingkat = 30 HP habis pas
    assert r["armor"]["kanan"] == pytest.approx(0) and r["motor"][1] == 40
    G._damage(s, 0, "kanan", 10 / kali, attacker=1)
    assert r["motor"][1] == pytest.approx(40 - 8) and r["rangka"] == pytest.approx(100 - 6)
    G._damage(s, 0, "bawah", 10 / kali)
    assert r["rangka"] == pytest.approx(94 - 8)
    k = s["robot"][1]
    G._damage(s, 1, "kiri", 10 / kali)
    assert k["armor"]["kiri"] == pytest.approx(30 - 7)             # kubah: pukulan samping −30%
    assert s["robot"][1]["rusak"] == pytest.approx(30 / kali * kali + 10)


def test_spinner_perlu_putaran_dan_drum_tetap_jalan_terbalik():
    s = _arena(designs=(0, 4))
    _place(s, 0, 5.0, 7.0, 0)
    _place(s, 1, 6.12, 7.0, 180)
    G.apply(s, {0: G.validate(s, 0, {"senjata": True})})
    assert s["robot"][0]["rpm"] == pytest.approx(DT / SENJATA["spinner_v"]["naik"])
    ev = _run(s, 3)
    assert not any(e["jenis"] == "hantam" for e in ev)              # putaran masih < 0.2
    ev = _run(s, 60)
    hit = [e for e in ev if e["jenis"] == "hantam"]
    assert hit and hit[0]["senjata"] == "spinner_v" and s["robot"][1]["rusak"] == 0 and s["robot"][0]["rusak"] > 0
    s2 = _arena(designs=(0, 4))
    s2["robot"][0]["terbalik"] = True
    _place(s2, 0, 5.0, 7.0, 0)
    _place(s2, 1, 6.12, 7.0, 180)
    ev = _run(s2, 60, {0: G.validate(s2, 0, {"senjata": True})})
    assert s2["robot"][0]["rpm"] <= 0.7 + 1e-9 and any(e["jenis"] == "hantam" for e in ev)


def test_flipper_melempar_membalik_dan_membalikkan_diri():
    s = _arena(designs=(2, 3), seed=4)
    _place(s, 0, 5.0, 7.0, 0)
    _place(s, 1, 6.2, 7.0, 180)
    flips = 0
    for k in range(12):
        s["robot"][1].update(terbalik=False, udara=0.0)
        _place(s, 0, 5.0, 7.0, 0)
        _place(s, 1, 6.2, 7.0, 180)
        s["robot"][0]["cd"] = 0.0
        ev = _run(s, 1, {0: G.validate(s, 0, {"senjata": True})})
        assert any(e["jenis"] == "terbang" for e in ev)
        ev = _run(s, 25, {0: G.validate(s, 0, {"senjata": False})})
        flips += s["robot"][1]["terbalik"]
    assert 2 <= flips <= 11                                        # ±55%, ditentukan seed (deterministik)
    s["robot"][1].update(terbalik=True, udara=0.0)
    ev = _run(s, 30, {1: G.validate(s, 1, {"balik": True})})       # Godam punya pembalik badan (1,2 detik)
    assert not s["robot"][1]["terbalik"] and any(e["jenis"] == "tegak" and e.get("sendiri") for e in ev)


def test_palu_dua_kali_untuk_lawan_terbalik():
    s = _arena(designs=(3, 4))
    _place(s, 0, 5.0, 7.0, 0)
    _place(s, 1, 6.4, 7.0, 180)
    s["robot"][1]["terbalik"] = True
    G.apply(s, {0: G.validate(s, 0, {"senjata": True})})
    assert s["robot"][0]["rusak"] == pytest.approx(SENJATA["palu"]["dmg"] * 2 * 0.55)


def test_lubang_terbuka_setelah_45_detik_dan_ko_mogok():
    s = _arena({"lubang": True})
    pit = next(h for h in s["jebakan"] if h["jenis"] == "lubang")
    _place(s, 1, 12, 12, 0)
    _place(s, 0, pit["x"], pit["y"], 0)
    _run(s, 5)
    assert s["robot"][0]["hidup"]
    s["fase_t"] = int(LUBANG_BUKA / DT)
    _place(s, 0, pit["x"], pit["y"], 0)
    ev = _run(s, 1)
    assert not s["robot"][0]["hidup"] and s["robot"][0]["ko"] == "lubang"
    assert any(e["jenis"] == "ronde_selesai" and e["pemenang"] == "B" and e["cara"] == "ko" for e in ev)
    s2 = _arena()
    s2["robot"][0]["motor"] = [0.0, 0.0]
    ev = _run(s2, int(10 / DT) + 1)
    assert s2["robot"][0]["ko"] == "mogok"


def test_juri_saat_waktu_habis():
    s = _arena({"durasi": 45})
    _place(s, 0, 3, 3, 0)
    _place(s, 1, 11, 11, 0)
    s["robot"][0]["rusak"], s["robot"][0]["agresi"] = 50.0, 4.0
    s["robot"][1]["rusak"], s["robot"][1]["kontrol_poin"] = 10.0, 1.0
    ev = _run(s, int(45 / DT))
    end = next(e for e in ev if e["jenis"] == "ronde_selesai")
    assert end["cara"] == "juri" and end["pemenang"] == "A" and end["juri"]["A"] > end["juri"]["B"] and G.over(s)


def test_semua_template_bot_tanpa_error_dan_deterministik():
    T = [t["kode"] for t in G.templates]
    for a, b in itertools.combinations(range(len(T)), 2):
        out = play_sync("robottarung", {"durasi": 45}, ["A", "B"], [T[a], T[b]], 2)
        assert [e for lg in out["logs"] for e in lg if "error" in e] == []
    o1 = play_sync("robottarung", {"durasi": 60}, ["A", "B", "C", "D"], T[:4], 7)
    o2 = play_sync("robottarung", {"durasi": 60}, ["A", "B", "C", "D"], T[:4], 7)
    assert o1["result"]["skor"] == o2["result"]["skor"] and o1["steps"] == o2["steps"]
    out = play_sync("robottarung", {"berat_maks": 60}, ["A", "B"], [T[0], T[1]], 1)
    assert out["steps"] < 2000                                      # bot langsung siap di garasi walau batas berat kecil


@pytest.fixture()
def client(tmp_path):
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        yield c


def test_room_robot_tarung_garasi_dan_kendali_langsung(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "robottarung", "nama": "Ani", "settings": {"durasi": 45}, "jeda_hasil": 0})
        until(a, "masuk")
        a.send_json({"type": "tambah_bot", "nama": "Bot", "kode": G.templates[3]["kode"]})
        until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        a.send_json({"type": "mulai"})
        u = until(a, "update", pred=lambda m: m["view"]["fase"] == "garasi" and m["view"]["siap"].get("Bot"), limit=100)
        assert u["my_turn"] and u["detak"] == pytest.approx(DT)
        a.send_json({"type": "aksi", "aksi": {"rakit": {**CONTOH_RAKITAN[0], "armor": {"depan": 8, "kanan": 8, "belakang": 8, "kiri": 8}}}})
        assert "melebihi" in until(a, "error")["message"]
        a.send_json({"type": "aksi", "aksi": {"rakit": CONTOH_RAKITAN[1]}})
        u = until(a, "update", pred=lambda m: m["view"]["fase"] == "tarung", limit=200)
        assert u["view"]["robot"]["Ani"]["desain"]["senjata"] == "spinner_h"
        a.send_json({"type": "aksi", "aksi": {"maju": 1, "senjata": True}})
        u2 = until(a, "update", pred=lambda m: m["view"]["robot"]["Ani"]["v"] > 0.5 and m["view"]["robot"]["Ani"]["rpm"] > 0, limit=60)
        assert u2["my_turn"]
