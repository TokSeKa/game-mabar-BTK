"""Tes keandalan room Arena Mabar: sambung ulang, submit otomatis, dan jeda lihat hasil.

Bug yang dilaporkan: kalau tombol kirim tidak sempat ditekan, layar pemain "beku" dan ronde-ronde berikutnya selalu
memakai aksi bawaan. Penyebabnya: setelah HP menyambung ulang, kegagalan kirim ke koneksi lama menimpa koneksi baru,
sehingga server menganggap pemain offline dan tidak mengirim update lagi.
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.games.registry import GAMES
from app.games.rooms import GameRoom
from app.main import create_app
from app.trading.accounts import AccountDB
from app.trading.api import create_trading
from app.trading.store import CandleStore

from .test_hub import until

BOT10 = "def aksi():\n    return 10\n"


class Pipe:
    """Pengganti websocket: menyimpan semua pesan, bisa dibuat gagal."""

    def __init__(self, gagal=False):
        self.msgs, self.gagal, self.kicked = [], gagal, False

    async def send(self, msg):
        if self.gagal:
            raise RuntimeError("koneksi lama sudah mati")
        self.msgs.append(msg)

    async def kick(self):
        self.kicked = True

    def of(self, typ):
        return [m for m in self.msgs if m["type"] == typ]


def run(coro):
    return asyncio.run(coro)


def test_gagal_kirim_menandai_offline_dan_memutus_koneksi():
    async def go():
        room = GameRoom("ABCDE", GAMES["duapertiga"], {}, 30, 0.0)
        pipe = Pipe(gagal=True)
        m = room.join("Ani", None, pipe.send, False, pipe.kick)
        await room._send(m, {"type": "x"})
        await asyncio.sleep(0)
        assert not m.online and m.send is None and pipe.kicked and m.offline_since > 0

    run(go())


def test_koneksi_lama_gagal_tidak_menimpa_koneksi_baru():
    """Gagal kirim ke koneksi lama setelah anggota tersambung lagi tidak boleh memutus koneksi barunya."""
    async def go():
        room = GameRoom("ABCDE", GAMES["duapertiga"], {}, 30, 0.0)
        lama, baru = Pipe(gagal=True), Pipe()
        m = room.join("Ani", None, lama.send, False, lama.kick)

        async def lambat(msg):
            await asyncio.sleep(0.05)      # sedang mengirim ke koneksi lama…
            raise RuntimeError("putus")

        m.send = lambat
        kirim = asyncio.create_task(room._send(m, {"type": "x"}))
        await asyncio.sleep(0.01)
        room.rejoin(m.id, m.token, baru.send, baru.kick)   # …sementara HP sudah tersambung lagi
        await kirim
        assert m.online and m.send == baru.send and not lama.kicked
        await room._send(m, {"type": "y"})
        assert baru.of("y")

    run(go())


def test_putus_sebentar_tidak_langsung_aksi_bawaan():
    async def go():
        room = GameRoom("ABCDE", GAMES["duapertiga"], {"ronde": 1}, 30, 0.0, jeda_hasil=0)
        pipe = Pipe()
        m = room.join("Ani", None, pipe.send, False, pipe.kick)
        room.state = room.game.init(room.settings, ["Ani"], 1)
        now = time.time()
        room.turn_start = now - 5
        m.online, m.offline_since = False, now - 3
        assert not room._gone(0, now)                 # baru putus 3 detik: masih ditunggu
        assert room._gone(0, now + 8)                 # 11 detik: tidak ditunggu lagi
        m.offline_since = 0.0                         # keluar dengan sengaja
        assert room._gone(0, now)

    run(go())


@pytest.fixture()
def client(tmp_path):
    svc = create_trading(CandleStore(tmp_path / "pasar"), AccountDB(tmp_path / "akun.db"))
    app = create_app(Config(match_workers=0), trading=svc)
    with TestClient(app) as c:
        yield c


def test_submit_otomatis_pilihan_terakhir(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "duapertiga", "nama": "Ani", "settings": {"ronde": 1}, "waktu": 3, "jeda_hasil": 0})
        until(a, "masuk")
        a.send_json({"type": "tambah_bot", "nama": "B1", "kode": BOT10})
        until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        a.send_json({"type": "mulai"})
        until(a, "update", pred=lambda m: m["my_turn"])
        a.send_json({"type": "draf", "aksi": 999})        # tidak valid: diabaikan
        a.send_json({"type": "draf", "aksi": 7})          # pilihan terakhir yang belum dikirim
        u = until(a, "update", pred=lambda m: any(e.get("jenis") == "waktu_habis" for e in m["events"]), limit=50)
        habis = u["events"][0]
        assert habis["otomatis"] == ["Ani"] and habis["pemain"] == []
        ronde = next(e for e in u["events"] if e.get("jenis") == "ronde")
        assert ronde["tebakan"]["Ani"] == 7


def test_jeda_lihat_hasil_dan_tombol_lanjut(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "blotto", "nama": "Ani", "settings": {"ronde": 2}, "waktu": 20, "jeda_hasil": 20})
        until(a, "masuk")
        room = until(a, "room")
        assert room["jeda_hasil"] == 20
        a.send_json({"type": "tambah_bot", "nama": "B1", "kode": "def aksi():\n    return bagi_rata()\n"})
        until(a, "room", pred=lambda m: len(m["kursi"]) == 2)
        a.send_json({"type": "mulai"})
        until(a, "update", pred=lambda m: m["my_turn"])
        a.send_json({"type": "aksi", "aksi": [100, 0, 0, 0, 0]})
        u = until(a, "update", pred=lambda m: m["jeda"] is not None, limit=50)
        assert u["pending"] == [] and not u["my_turn"]
        assert u["jeda"]["sampai"] - u["now"] > 15
        # selama jeda belum boleh beraksi untuk ronde berikutnya
        a.send_json({"type": "aksi", "aksi": [100, 0, 0, 0, 0]})
        assert "hasil ronde" in until(a, "error")["message"]
        t0 = time.time()
        a.send_json({"type": "lanjut"})
        until(a, "siap_lanjut")
        u2 = until(a, "update", pred=lambda m: m["my_turn"], limit=50)
        assert u2["view"]["ronde"] == 2 and time.time() - t0 < 5   # semua manusia siap → lanjut lebih cepat


def test_keluar_saat_main_tidak_ditunggu_dan_closed_menandai_offline(client):
    with client.websocket_connect("/ws/main") as a:
        a.send_json({"type": "buat", "game": "kasdesa", "nama": "Ani", "settings": {"ronde": 1}, "waktu": 60, "jeda_hasil": 0})
        m = until(a, "masuk")
        b = client.websocket_connect("/ws/main")
        b.__enter__()
        b.send_json({"type": "gabung", "kode": m["kode"], "nama": "Budi"})
        until(b, "masuk")
        until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
        b.__exit__(None, None, None)        # Budi menutup browser
        r = until(a, "room", pred=lambda r: not r["kursi"][1]["online"])
        assert r["kursi"][1]["name"] == "Budi"


def _room_dua(client, waktu=30, **extra):
    a = client.websocket_connect("/ws/main")
    a.__enter__()
    a.send_json({"type": "buat", "game": "duapertiga", "nama": "Ani", "settings": {"ronde": 3, "mode_faktor": "tetap"},
                 "waktu": waktu, "jeda_hasil": 0, **extra})
    masuk = until(a, "masuk")
    return a, masuk


def test_klik_telat_ditolak_dan_ronde_berikutnya_tetap_bisa_dipilih(client):
    """Bug yang dilaporkan: jawaban ronde 1 yang sampai terlambat dulu dipakai sebagai jawaban ronde 2."""
    a, masuk = _room_dua(client, waktu=3)
    b = client.websocket_connect("/ws/main")
    b.__enter__()
    b.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "Budi"})
    until(b, "masuk")
    until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
    a.send_json({"type": "mulai"})
    u1 = until(b, "update", pred=lambda m: m["my_turn"])
    ua = until(a, "update", pred=lambda m: m["my_turn"])
    a.send_json({"type": "aksi", "aksi": 40, "step": ua["step"]})
    # Budi tidak sempat kirim; ronde 1 ditutup, ronde 2 dimulai
    u2 = until(b, "update", pred=lambda m: m["my_turn"] and m["step"] > u1["step"], limit=60)
    b.send_json({"type": "aksi", "aksi": 99, "step": u1["step"]})        # klik untuk ronde 1 yang telat sampai
    err = until(b, "error")
    assert err["kode"] == "telat" and "Terlambat" in err["message"]
    b.send_json({"type": "aksi", "aksi": 25, "step": u2["step"]})        # ronde 2 masih bisa dipilih normal
    ok = until(b, "aksi_ok")
    assert ok["step"] == u2["step"] and ok["aksi"] == 25
    a.send_json({"type": "aksi", "aksi": 40, "step": u2["step"]})
    hasil = until(b, "update", pred=lambda m: any(e.get("jenis") == "ronde" and e["ronde"] == 2 for e in m["events"]), limit=60)
    r2 = next(e for e in hasil["events"] if e.get("jenis") == "ronde")
    assert r2["tebakan"]["Budi"] == 25
    for w in (a, b):
        w.__exit__(None, None, None)


def test_ubah_jawaban_sebelum_ronde_ditutup(client):
    a, masuk = _room_dua(client)
    b = client.websocket_connect("/ws/main")
    b.__enter__()
    b.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "Budi"})
    until(b, "masuk")
    until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
    a.send_json({"type": "mulai"})
    u = until(a, "update", pred=lambda m: m["my_turn"])
    a.send_json({"type": "aksi", "aksi": 10, "step": u["step"]})
    assert until(a, "aksi_ok")["aksi"] == 10
    a.send_json({"type": "aksi", "aksi": 12, "step": u["step"]})          # kirim ulang = ubah jawaban
    ok = until(a, "aksi_ok")
    assert ok["aksi"] == 12 and ok["ubah"]
    a.send_json({"type": "batal", "step": u["step"]})                     # tombol Ubah: tarik jawaban
    until(a, "batal_ok")
    a.send_json({"type": "aksi", "aksi": 15, "step": u["step"]})
    until(a, "aksi_ok")
    ub = until(b, "update", pred=lambda m: m["my_turn"])
    b.send_json({"type": "aksi", "aksi": 30, "step": ub["step"]})
    hasil = until(a, "update", pred=lambda m: any(e.get("jenis") == "ronde" for e in m["events"]), limit=60)
    assert next(e for e in hasil["events"] if e.get("jenis") == "ronde")["tebakan"]["Ani"] == 15
    for w in (a, b):
        w.__exit__(None, None, None)


def test_host_jeda_membekukan_waktu(client):
    a, masuk = _room_dua(client, waktu=4)
    a.send_json({"type": "tambah_bot", "nama": "B1", "kode": BOT10})
    until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
    a.send_json({"type": "mulai"})
    u = until(a, "update", pred=lambda m: m["my_turn"])
    sisa = u["deadline"] - u["now"]
    a.send_json({"type": "jeda_host"})
    assert until(a, "jeda_host")["dijeda"]
    p = until(a, "update", pred=lambda m: m["dijeda_sejak"] is not None)
    a.send_json({"type": "aksi", "aksi": 5, "step": u["step"]})
    assert "dijeda" in until(a, "error")["message"]
    time.sleep(4.5)                                                        # lebih lama dari waktu langkah
    a.send_json({"type": "jeda_host"})
    assert not until(a, "jeda_host")["dijeda"]
    lanjut = until(a, "update", pred=lambda m: m["dijeda_sejak"] is None)
    assert lanjut["my_turn"] and lanjut["deadline"] - lanjut["now"] > sisa - 1.5   # sisa waktu tidak termakan jeda
    a.send_json({"type": "aksi", "aksi": 5, "step": lanjut["step"]})
    assert until(a, "aksi_ok")["aksi"] == 5
    a.__exit__(None, None, None)


def test_masuk_lagi_dengan_nama_sama_kembali_ke_kursi(client):
    a, masuk = _room_dua(client)
    b = client.websocket_connect("/ws/main")
    b.__enter__()
    b.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "Budi"})
    mb = until(b, "masuk")
    until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
    a.send_json({"type": "mulai"})
    until(b, "update", pred=lambda m: m["my_turn"])
    # HP lain dengan nama yang sama, sementara koneksi lama masih tercatat tersambung
    c = client.websocket_connect("/ws/main")
    c.__enter__()
    c.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "budi"})
    e = until(c, "error")
    assert e["kode"] == "nama_dipakai"
    c.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "budi", "ambil_alih": True})
    mc = until(c, "masuk")
    assert mc["member_id"] == mb["member_id"]
    assert until(c, "mulai")["main_sendiri"] is True
    assert until(b, "pindah")["type"] == "pindah"                          # tab lama diberi tahu
    u = until(c, "update", pred=lambda m: m["my_turn"])
    c.send_json({"type": "aksi", "aksi": 20, "step": u["step"]})
    assert until(c, "aksi_ok")["aksi"] == 20
    for w in (a, b, c):
        w.__exit__(None, None, None)


def test_klasemen_sesi_dan_replay_sudut_pandang(client):
    a, masuk = _room_dua(client, jeda=0)
    a.send_json({"type": "tambah_bot", "nama": "B1", "kode": BOT10})
    a.send_json({"type": "tambah_bot", "nama": "B2", "kode": "def aksi():\n    return 60\n"})
    until(a, "room", pred=lambda r: len(r["kursi"]) == 3)
    for _ in range(2):
        a.send_json({"type": "mulai"})
        for _r in range(3):
            u = until(a, "update", pred=lambda m: m["my_turn"], limit=80)
            a.send_json({"type": "aksi", "aksi": 7, "step": u["step"]})
        fin = until(a, "selesai", limit=200)
    lobby = until(a, "room", pred=lambda r: r["status"] == "lobby" and r["match_no"] == 2)
    sesi = {r["nama"]: r for r in lobby["sesi"]}
    assert all(r["main"] == 2 for r in sesi.values()) and sum(r["juara"] for r in sesi.values()) == 2
    rid = fin["replay_id"]
    assert rid
    lengkap = client.get(f"/api/main/sudut/{rid}?kursi=0").json()["frames"]
    assert len(lengkap) == len(fin["frames"]) and lengkap[-1]["view"]["saya"] == 0
    assert client.get(f"/api/main/sudut/{rid}?kursi=9").status_code == 400
    assert client.get("/api/main/sudut/tidakada").status_code == 404
    a.send_json({"type": "reset_sesi"})
    assert until(a, "room", pred=lambda r: r["sesi"] == [])["sesi"] == []
    a.__exit__(None, None, None)


def test_penonton_ikut_kabut_kecuali_host_membuka_semua(client):
    a, masuk = _room_dua(client, jeda=0)
    a.send_json({"type": "atur", "settings": {"ronde": 1, "tebakan_rahasia": True}})
    until(a, "room", pred=lambda r: r["settings"]["tebakan_rahasia"] and r["settings"]["ronde"] == 1)
    a.send_json({"type": "tambah_bot", "nama": "B1", "kode": BOT10})
    until(a, "room", pred=lambda r: len(r["kursi"]) == 2)
    t = client.websocket_connect("/ws/main")
    t.__enter__()
    t.send_json({"type": "gabung", "kode": masuk["kode"], "nama": "Tono", "tonton": True})
    until(t, "masuk")
    for buka in (False, True):
        a.send_json({"type": "atur", "penonton_semua": buka})
        until(a, "room", pred=lambda r: r["penonton_semua"] is buka)
        a.send_json({"type": "mulai"})
        until(t, "mulai")
        u = until(a, "update", pred=lambda m: m["my_turn"], limit=80)
        a.send_json({"type": "aksi", "aksi": 40, "step": u["step"]})
        v = until(t, "update", pred=lambda m: m["view"]["riwayat"], limit=80)
        tebakan = v["view"]["riwayat"][-1]["tebakan"]
        live = next(e for e in v["events"] if e.get("jenis") == "ronde")["tebakan"]
        if buka:
            assert tebakan == {"Ani": 40, "B1": 10} and live == tebakan
        else:
            assert tebakan == {"Ani": None, "B1": None} and live == tebakan
        until(t, "selesai", limit=200)
        until(a, "selesai", limit=200)
    for w in (a, t):
        w.__exit__(None, None, None)
