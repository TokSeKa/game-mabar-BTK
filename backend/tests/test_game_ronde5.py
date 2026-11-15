"""Tes ronde 5: Domino, Ular (real-time), Tembak Jitu, Hitung Uang, Tebak Gambar, dan fitur room baru
(mode detak, game khusus manusia, unggah foto)."""

import base64

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.games.base import ActionError
from app.games.registry import GAMES
from app.games.runner import play_sync
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

from .test_hub import until


def _templates_ok(gid, cfg, names, seed=3):
    g = GAMES[gid]
    codes = [g.templates[i % len(g.templates)]["kode"] for i in range(len(names))]
    out = play_sync(gid, cfg, list(names), codes, seed)
    errs = [e for lg in out["logs"] for e in lg if "error" in e]
    assert errs == [], errs[:2]
    return out


# ------------------------------------------------------------------ Domino
def _dm(cfg=None, names=("A", "B", "C", "D"), seed=1):
    g = GAMES["domino"]
    return g, g.init(g.clean_settings(cfg or {}), list(names), seed)


def test_domino_pembagian_dan_balak_tertinggi_membuka():
    g, s = _dm()
    assert [len(h) for h in s["tangan"]] == [7, 7, 7, 7] and s["tumpukan"] == []
    semua = sorted(tuple(k) for h in s["tangan"] for k in h)
    assert semua == sorted((a, b) for a in range(7) for b in range(a, 7))
    p = s["giliran"]
    assert s["wajib"] == [6, 6] and [6, 6] in s["tangan"][p]
    assert g.observe(s, p)["sah"] == [{"kartu": s["tangan"][p].index([6, 6]), "sisi": "kanan"}]
    with pytest.raises(ActionError, match="wajib"):
        g.validate(s, p, {"kartu": (s["tangan"][p].index([6, 6]) + 1) % 7})


def test_domino_tempel_kiri_kanan_memutar_kartu():
    g, s = _dm()
    s["tangan"] = [[[6, 6], [3, 6], [6, 1], [2, 2]], [[1, 2]], [[5, 5]], [[0, 0]]]
    s["giliran"], s["wajib"] = 0, [6, 6]
    g.apply(s, {0: g.validate(s, 0, 0)})
    assert s["ujung"] == [6, 6] and s["giliran"] == 1
    s["giliran"] = 0
    g.apply(s, {0: g.validate(s, 0, {"kartu": 0, "sisi": "kiri"})})       # [3,6] di kiri → meja [3,6][6,6]
    assert s["meja"][0] == [3, 6] and s["ujung"] == [3, 6]
    s["giliran"] = 0
    g.apply(s, {0: g.validate(s, 0, {"kartu": 0})})                       # [6,1] hanya cocok di kanan
    assert s["meja"][-1] == [6, 1] and s["ujung"] == [3, 1]
    with pytest.raises(ActionError, match="tidak cocok"):
        g.validate(s, 2, {"kartu": 0})


def test_domino_gaple_buntu_pemenang_sisa_terkecil_dan_skor():
    g, s = _dm()
    s["tangan"] = [[[0, 1]], [[5, 5]], [[4, 4], [2, 2]], [[6, 5]]]
    s["meja"], s["ujung"], s["wajib"], s["giliran"], s["terakhir"] = [[3, 3]], [3, 3], None, 0, 3
    for p in range(4):
        assert g.validate(s, p, "lewat") == "lewat"
        ev = g.apply(s, {p: "lewat"})
    akhir = ev[-1]
    assert akhir["jenis"] == "ronde_selesai" and akhir["cara"] == "buntu" and akhir["pemenang"] == "A"
    assert akhir["poin"]["A"] == 10 + 12 + 11 and s["skor"][0] == 33
    assert s["lewat_pada"] == [[], [], [], []]           # ronde baru sudah dimulai
    with pytest.raises(ActionError):
        g.validate(s, s["giliran"], "lewat")            # masih punya kartu yang bisa dibuka


def test_domino_draw_wajib_ambil_dan_bom():
    g, s = _dm({"aturan": "draw", "bom_kosong": True}, names=("A", "B"))
    assert len(s["tangan"][0]) == 7 and len(s["tumpukan"]) == 14
    s["tangan"] = [[[0, 0], [1, 1]], [[5, 6], [4, 4]]]
    s["meja"], s["ujung"], s["wajib"], s["giliran"] = [[0, 2]], [0, 2], None, 0
    with pytest.raises(ActionError, match="tidak boleh ambil"):
        g.validate(s, 0, "ambil")
    ev = g.apply(s, {0: g.validate(s, 0, {"kartu": 0, "sisi": "kiri"})})
    assert any(e["jenis"] == "bom" and e["ambil"] == 2 for e in ev) and s["bom"] == 2
    with pytest.raises(ActionError, match="bom"):
        g.validate(s, 1, {"kartu": 0})
    g.apply(s, {1: g.validate(s, 1, "ambil")})
    g.apply(s, {1: g.validate(s, 1, "ambil")})
    assert len(s["tangan"][1]) == 4 and s["giliran"] == 0 and s["bom"] == 0
    with pytest.raises(ActionError, match="ambil kartu dulu"):
        s["giliran"] = 1
        s["tangan"][1] = [[5, 6]]
        g.validate(s, 1, "lewat")


def test_domino_tim_dan_bonus_balak():
    g, s = _dm({"tim": True, "bonus_balak": True})
    s["tangan"] = [[[3, 3]], [[1, 2]], [[6, 6]], [[0, 4]]]
    s["meja"], s["ujung"], s["wajib"], s["giliran"] = [[3, 5]], [3, 5], None, 0
    ev = g.apply(s, {0: g.validate(s, 0, {"kartu": 0, "sisi": "kiri"})})
    akhir = ev[-1]
    assert akhir["kali"] == 2 and akhir["pemenang"] == "A"
    # lawan (B & D) punya 3 + 4 = 7 mata, ×2 = 14, dibagi berdua untuk tim A & C
    assert akhir["poin"]["A"] == akhir["poin"]["C"] == 7 and s["skor"][0] == s["skor"][2] == 7


def test_domino_template_bot_semua_variasi():
    for cfg, n in [({}, 4), ({"aturan": "draw"}, 3), ({"set": "9", "aturan": "draw", "bom_kosong": True}, 6),
                   ({"tim": True, "denda_lewat": 3}, 4), ({"skor": "minus", "kartu_terbuka": True}, 2)]:
        out = _templates_ok("domino", {**cfg, "ronde": 2}, [f"P{i}" for i in range(n)])
        assert out["frames"][-1]["view"]["riwayat"]


# ------------------------------------------------------------------ Ular
def _ul(cfg=None, names=("A", "B"), seed=2):
    g = GAMES["ular"]
    s = g.init(g.clean_settings({"rintangan": "kosong", "buah": 1, **(cfg or {})}), list(names), seed)
    s["t"] = s["mulai"]                       # lewati hitung mundur
    return g, s


def _set_snakes(s, bodies, arah):
    for u, b, a in zip(s["ular"], bodies, arah):
        u.update(badan=[list(x) for x in b], arah=a, hidup=True, tumbuh=0, keluar=False)
    s["buah"] = []


def test_ular_detak_dan_hitung_mundur():
    g = GAMES["ular"]
    cfg = g.clean_settings({"kecepatan": 8})
    assert g.detak(cfg) == 1 / 8 and g.bot and g.bot_langkah < 20000
    s = g.init(cfg, ["A"], 1)
    before = [list(x) for x in s["ular"][0]["badan"]]
    g.apply(s, {0: None})
    assert s["ular"][0]["badan"] == before          # masih hitung mundur
    assert g.validate(s, 0, "W") == "atas" and g.validate(s, 0, None) is None
    with pytest.raises(ActionError):
        g.validate(s, 0, "naik")


def test_ular_makan_tumbuh_dan_tidak_bisa_berbalik():
    g, s = _ul()
    _set_snakes(s, [[[5, 5], [4, 5], [3, 5]], [[5, 15], [4, 15], [3, 15]]], ["kanan", "kanan"])
    s["buah"] = [[6, 5, "apel"]]
    ev = g.apply(s, {0: "kiri", 1: None})           # berbalik diabaikan
    assert s["ular"][0]["arah"] == "kanan" and s["ular"][0]["badan"][0] == [6, 5]
    assert any(e["jenis"] == "makan" for e in ev) and s["skor"][0] == 1 and s["ular"][0]["tumbuh"] == 1
    g.apply(s, {0: "bawah", 1: None})
    assert len(s["ular"][0]["badan"]) == 4 and s["ular"][0]["badan"][0] == [6, 6]


def test_ular_tabrak_badan_lawan_dan_adu_kepala():
    g, s = _ul()
    _set_snakes(s, [[[5, 5], [4, 5], [3, 5]], [[6, 7], [6, 6], [6, 5], [6, 4]]], ["kanan", "bawah"])
    # A menabrak badan B (petak [6,5] tetap terisi karena B bergerak dari kepala, ekor [6,4] yang pindah)
    ev = g.apply(s, {0: None, 1: None})
    t = next(e for e in ev if e["jenis"] == "tumbang")
    assert t["pemain"] == "A" and t["oleh"] == "B" and s["skor"] == [-3, 2] and not s["ular"][0]["hidup"]
    g2, s2 = _ul({"adu_kepala": "panjang"})
    _set_snakes(s2, [[[5, 5], [4, 5], [3, 5], [2, 5]], [[7, 5], [8, 5], [9, 5]]], ["kanan", "kiri"])
    ev = g2.apply(s2, {0: None, 1: None})
    assert [e["pemain"] for e in ev if e["jenis"] == "tumbang"] == ["B"] and s2["ular"][0]["hidup"]


def test_ular_bangkit_dan_mode_habis():
    g, s = _ul()
    _set_snakes(s, [[[0, 5], [1, 5], [2, 5]], [[5, 15], [4, 15], [3, 15]]], ["kiri", "kanan"])
    g.apply(s, {0: None, 1: None})                  # A keluar tepi kiri
    assert not s["ular"][0]["hidup"] and s["ular"][0]["bangkit"] == s["t"] + 2 * s["cfg"]["kecepatan"]
    for _ in range(2 * s["cfg"]["kecepatan"]):
        g.apply(s, {0: None, 1: "bawah" if s["ular"][1]["arah"] == "kanan" else "kiri"})
    assert s["ular"][0]["hidup"] and len(s["ular"][0]["badan"]) == 3
    g2, s2 = _ul({"tabrakan": "habis"})
    _set_snakes(s2, [[[0, 5], [1, 5], [2, 5]], [[5, 15], [4, 15], [3, 15]]], ["kiri", "kanan"])
    ev = g2.apply(s2, {0: None, 1: None})
    akhir = next(e for e in ev if e["jenis"] == "ronde_selesai")
    assert akhir["hidup"] == ["B"] and akhir["bonus"]["B"] == 3 + 5 and s2["ronde"] == 2


def test_ular_tepi_tembus():
    g, s = _ul({"tembus_tepi": True})
    N = s["ukuran"]
    _set_snakes(s, [[[0, 5], [1, 5], [2, 5]], [[5, 15], [4, 15], [3, 15]]], ["kiri", "kanan"])
    g.apply(s, {0: None, 1: None})
    assert s["ular"][0]["hidup"] and s["ular"][0]["badan"][0] == [N - 1, 5]


def test_ular_template_bot_dan_replay_deterministik():
    out1 = _templates_ok("ular", {"durasi": 20, "ronde": 1}, ["A", "B", "C", "D"], seed=5)
    out2 = _templates_ok("ular", {"durasi": 20, "ronde": 1}, ["A", "B", "C", "D"], seed=5)
    assert out1["result"]["skor"] == out2["result"]["skor"] and max(out1["result"]["skor"]) > 5
    _templates_ok("ular", {"durasi": 15, "ronde": 1, "tabrakan": "habis", "rintangan": "banyak", "buah_busuk": True}, ["A", "B", "C"], seed=2)


# ------------------------------------------------------------------ Tembak Jitu
def test_tembak_nilai_tembakan_proporsional():
    from app.games.g_tembak import nilai_tembakan
    assert nilai_tembakan(0, 0, 0.06, 0, 1600) == (10, 1.0, 100)
    c, f, p = nilai_tembakan(0.03, 0, 0.06, 800, 1600)
    assert c == 5 and f == pytest.approx(0.65) and p == round(5 * 10 * 0.65)
    assert nilai_tembakan(0.07, 0, 0.06, 100, 1600)[2] == 0
    assert nilai_tembakan(0, 0, 0.06, 5000, 1600)[1] == 0.3


def test_tembak_hanya_target_aktif_terlihat_dan_tebakan_cepat_ditolak():
    g = GAMES["tembak"]
    assert not g.bot and g.mandiri
    s = g.init(g.clean_settings({"target": 5}), ["A", "B"], 4)
    o = g.observe(s, 0)
    assert len(o["aktif"]) == 1 and o["aktif"][0]["nomor"] == 0 and "sasaran" not in o
    g.apply(s, {0: g.validate(s, 0, {"target": 0, "dx": 0, "dy": 0, "ms": 40})})
    assert s["hasil"][0][0]["poin"] == 0 and "terlalu cepat" in s["hasil"][0][0]["catatan"]
    with pytest.raises(ActionError, match="sudah lewat"):
        g.validate(s, 0, {"target": 0, "dx": 0, "dy": 0, "ms": 300})
    g.apply(s, {0: g.validate(s, 0, {"target": 1, "dx": 0.0, "dy": 0.0, "ms": 300})})
    assert s["hasil"][0][1]["cincin"] == 10 and g.observe(s, 0)["aktif"][0]["nomor"] == 2
    assert g.observe(s, 1)["aktif"][0]["nomor"] == 0     # pemain lain jalan sendiri


def test_tembak_sandera_ganda_dan_akhir_ronde():
    g = GAMES["tembak"]
    s = g.init(g.clean_settings({"target": 30, "sandera": True, "ganda": True, "ronde": 1}), ["A"], 11)
    assert any(t["sandera"] for t in s["sasaran"]) and any(t["kembar"] for t in s["sasaran"])
    while not g.over(s):
        o = g.observe(s, 0)
        t = o["aktif"][0]
        if t["kembar"]:
            assert len(o["aktif"]) in (1, 2)
        a = {"target": t["nomor"], "lewat": True} if t["sandera"] else {"target": t["nomor"], "dx": 0.01, "dy": 0, "ms": 500}
        ev = g.apply(s, {0: g.validate(s, 0, a)})
    assert ev[-1]["jenis"] == "ronde_selesai" and s["skor"][0] > 0
    assert sum(1 for h in s["riwayat"][0]["hasil"]["A"] if h.get("tahan")) == sum(1 for t in s["riwayat"][0]["sasaran"] if t["sandera"])


# ------------------------------------------------------------------ Hitung Uang
def test_hitung_uang_total_mengabaikan_palsu_dan_kupon():
    from app.games.g_hitunguang import HitungUang
    items = [{"jenis": "kertas", "nilai": 50000}, {"jenis": "kertas", "nilai": 20000, "palsu": True},
             {"jenis": "koin", "nilai": 500}, {"jenis": "kupon", "nilai": 100000}, {"jenis": "mainan", "nilai": 10000}]
    assert HitungUang.total(items) == 50500


def test_hitung_uang_urutan_poin_salah_dan_hukuman():
    g = GAMES["hitunguang"]
    s = g.init(g.clean_settings({"ronde": 2, "koin": True, "palsu": True, "kupon": True, "terbalik": True}), ["A", "B", "C"], 3)
    tot = g.total(s["gepok"])
    assert "total" not in g.observe(s, 0) and g.observe(s, 0)["gepok"] and "gepok" not in g.public(s)
    assert g.validate(s, 0, f"Rp{tot:,}".replace(",", ".")) == tot
    ev = g.apply(s, {1: tot + 500})
    assert ev[0]["arah"] == "lebih" and s["skor"][1] == -3 and g.cooldown(s, 1, ev) == 4.0
    g.apply(s, {0: tot})
    g.apply(s, {1: g.validate(s, 1, {"jawab": tot})})
    assert s["skor"][0] == 15 and s["skor"][1] == -3 + 12
    g.apply(s, {2: tot - 1})
    g.apply(s, {2: tot - 2})
    ev = g.apply(s, {2: tot - 3})
    assert ev[0]["habis"] and g.cooldown(s, 2, ev) == 0.0
    end = next(e for e in ev if e["jenis"] == "ronde_selesai")
    assert end["total"] == tot and end["urut"] == ["A", "B"] and s["ronde"] == 2


# ------------------------------------------------------------------ Tebak Gambar
def test_tebak_gambar_parse_kustom_dan_buang():
    from app.games.g_tebakgambar import mirip, norm, parse_item
    assert parse_item("🦖 Dinosaurus | dino, t-rex") == {"emoji": "🦖", "nama": "Dinosaurus", "alias": ["dino", "t-rex"], "foto": None}
    assert parse_item("foto:abc123ef Pak RT | rt")["foto"] == "abc123ef"
    assert parse_item("Gunung Bromo")["nama"] == "Gunung Bromo" and parse_item("  ") is None
    assert mirip(norm("kura-kurx"), norm("Kura-kura")) and not mirip("kuda", "kura")
    g = GAMES["tebakgambar"]
    cfg = g.clean_settings({"kategori": "hewan", "kecualikan": "Gajah\nular", "tambahan": "🦖 Dinosaurus"})
    pool = [it["nama"] for it in g._pool(cfg)]
    assert "Dinosaurus" in pool and "Gajah" not in pool and "Ular" not in pool
    only = g._pool(g.clean_settings({"kategori": "kustom", "tambahan": "🦖 Dinosaurus\n🦄 Unicorn"}))
    assert [x["nama"] for x in only] == ["Dinosaurus", "Unicorn"]


def test_tebak_gambar_alur_tanya_jawab_tebak():
    g = GAMES["tebakgambar"]
    assert not g.bot
    s = g.init(g.clean_settings({"kesempatan": 2, "jawaban": "5"}), ["A", "B", "C"], 7)
    o = g.observe(s, 0)
    assert o["gambar"]["A"]["rahasia"] and not o["gambar"]["B"]["rahasia"] and o["gambar"]["B"]["nama"]
    assert all(not x["rahasia"] for x in g.public(s)["gambar"].values())
    g.apply(s, {0: g.validate(s, 0, {"tanya": ""})})
    assert s["pertanyaan"] == "(diucapkan)" and g.pending(s) == [1, 2]
    with pytest.raises(ActionError):
        g.validate(s, 1, {"jawab": "iya"})
    g.apply(s, {1: g.validate(s, 1, {"jawab": "mungkin ya"}), 2: g.default(s, 2)})
    assert s["catatan"][0][0]["rangkum"] == {"mungkin_ya": 1, "tidak_tahu": 1} and g.pending(s) == [0]
    with pytest.raises(ActionError, match="habis"):
        g.validate(s, 0, {"tanya": "lagi?"})
    g.apply(s, {0: g.validate(s, 0, {"tebak": "bukan ini"})})
    assert s["salah"][0] == 1 and s["giliran"] == 1
    g.apply(s, {1: g.validate(s, 1, {"tebak": s["gambar"][1]["nama"].upper()})})
    assert s["status"][1] == "menang" and s["skor"][1] >= 10
    g.apply(s, {2: "lewat"})
    ev = g.apply(s, {0: g.validate(s, 0, {"tebak": "salah lagi"})})
    assert s["status"][0] == "kalah" and ev[0]["kalah"] and ev[0]["gambar"]["nama"] == s["gambar"][0]["nama"]
    assert s["giliran"] == 2 and s["putaran"] == 2


def test_tebak_gambar_akhir_satu_pemenang_dan_putaran_habis():
    g = GAMES["tebakgambar"]
    s = g.init(g.clean_settings({"akhir": "satu"}), ["A", "B"], 1)
    g.apply(s, {0: g.validate(s, 0, {"tebak": s["gambar"][0]["nama"]})})
    assert g.over(s) and s["status"] == ["menang", "kalah"]
    s = g.init(g.clean_settings({"maks_putaran": 2}), ["A", "B"], 1)
    for _ in range(4):
        g.apply(s, {s["giliran"]: "lewat"})
    assert g.over(s) and s["status"] == ["kalah", "kalah"]


# ------------------------------------------------------------------ Room: detak, khusus manusia, foto
@pytest.fixture()
def client(tmp_path):
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        yield c


def test_game_khusus_manusia_menolak_bot(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "tembak", "nama": "Ani"})
        until(a, "masuk")
        a.send_json({"type": "tambah_bot", "nama": "B1", "kode": "def aksi():\n    return None\n"})
        assert "manusia" in until(a, "error")["message"]
    meta = {g["id"]: g for g in client.get("/api/main/games").json()}
    assert meta["tembak"]["bot"] is False and meta["domino"]["bot"] is True


def test_room_detak_ular_jalan_sendiri_dan_belok(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "ular", "nama": "Ani",
                     "settings": {"kecepatan": 12, "durasi": 20, "ronde": 1, "rintangan": "kosong"}, "jeda_hasil": 0})
        until(a, "masuk")
        a.send_json({"type": "mulai"})
        u = until(a, "update", pred=lambda m: m["view"]["mulai_dalam"] == 0, limit=200)
        assert u["detak"] == pytest.approx(1 / 12) and u["mandiri"]
        assert u["my_turn"] and u["pending"] == [0]          # tanpa ini browser mengabaikan panah/WASD
        arah = u["view"]["ular"]["Ani"]["arah"]
        belok = {"atas": "kiri", "bawah": "kanan", "kiri": "bawah", "kanan": "atas"}[arah]
        a.send_json({"type": "aksi", "aksi": belok})           # tanpa nomor langkah: masuk antrean detak
        u2 = until(a, "update", pred=lambda m: m["view"]["ular"]["Ani"]["arah"] == belok, limit=30)
        assert u2["step"] > u["step"]


def test_unggah_foto_host_dan_tampil(client):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 40
    data = "data:image/png;base64," + base64.b64encode(png).decode()
    with client.websocket_connect("/ws/main") as a, client.websocket_connect("/ws/main") as b:
        a.send_json({"type": "buat", "game": "tebakgambar", "nama": "Ani"})
        kode = until(a, "masuk")["kode"]
        b.send_json({"type": "gabung", "kode": kode, "nama": "Budi"})
        until(b, "masuk")
        a.send_json({"type": "foto", "data": data, "ref": "x1"})
        ok = until(a, "foto_ok")
        assert ok["ref"] == "x1"
        r = client.get(f"/api/main/foto/{kode}/{ok['id']}")
        assert r.status_code == 200 and r.content == png and r.headers["content-type"] == "image/png"
        b.send_json({"type": "foto", "data": data})
        assert "host" in until(b, "error")["message"]
        a.send_json({"type": "foto", "data": "data:image/png;base64," + base64.b64encode(b"bukan gambar").decode()})
        assert "bukan gambar" in until(a, "error")["message"]
    assert client.get("/api/main/foto/ZZZZZ/abc").status_code == 404
