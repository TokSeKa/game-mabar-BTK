"""Tes opsi kustomisasi per game (informasi/kabut, aturan, kejutan)."""

import pytest

from app.games.base import ActionError
from app.games.registry import GAMES
from app.games.runner import play_sync, sudut_sync


def _lelang(cfg, names=("A", "B", "C", "D"), seed=3):
    g = GAMES["lelang"]
    return g, g.init(g.clean_settings(cfg), list(names), seed)


# ------------------------------------------------------------------ Lelang
def test_lelang_jadwal_terlihat_n_barang_ke_depan():
    g, s = _lelang({"barang": 8, "lihat_depan": 2})
    v = g.observe(s, 0)
    assert v["jadwal"][:3] == s["jadwal"][:3] and v["jadwal"][3:] == [None] * 5
    assert v["nama_barang"][3] is None and v["nama_barang"][2] == s["nama_barang"][2]
    g.apply(s, {0: 0, 1: 0, 2: 0, 3: 0})
    v = g.observe(s, 0)
    assert v["jadwal"][3] == s["jadwal"][3] and v["jadwal"][4] is None   # jendela bergeser
    g0, s0 = _lelang({"barang": 8, "lihat_depan": 0})
    assert g0.observe(s0, 1)["jadwal"][1:] == [None] * 7
    assert g0.full_view(s0)["jadwal"] == s0["jadwal"]                       # replay: semua terbuka


def test_lelang_taksiran_pribadi_berbeda_dan_tetap():
    g, s = _lelang({"nilai_mode": "taksiran", "taksiran_selisih": 3}, names=("A", "B", "C", "D", "E", "F"))
    asli = s["jadwal"][0]
    lihat = [g.observe(s, p)["barang"]["nilai"] for p in range(6)]
    assert all(abs(x - asli) <= 3 for x in lihat) and len(set(lihat)) > 1
    assert lihat == [g.observe(s, p)["barang"]["nilai"] for p in range(6)]   # deterministik dari seed
    assert g.public(s)["barang"]["nilai"] is None                             # penonton tidak tahu
    g.apply(s, {p: 0 for p in range(6)})
    assert g.observe(s, 0)["jadwal"][0] == asli                               # nilai asli dibuka setelah lelang


def test_lelang_koin_rahasia_dan_tawaran_tertutup():
    g, s = _lelang({"koin_rahasia": True, "buka_tawaran": "pemenang"})
    g.apply(s, {0: 30, 1: 20, 2: 10, 3: 0})
    v = g.observe(s, 1)
    assert v["koin"]["B"] == 100 and v["koin"]["A"] is None and v["skor"]["A"] is None
    e = v["riwayat"][0]
    assert e["tawaran"] is None and e["tawaran_saya"] == 20 and e["pemenang"] == "A" and e["harga"] == 30
    _, s2 = _lelang({"buka_tawaran": "tidak"})
    g.apply(s2, {0: 30, 1: 20, 2: 10, 3: 0})
    assert g.observe(s2, 3)["riwayat"][0]["harga"] is None
    assert g.full_view(s2)["riwayat"][0]["tawaran"]["B"] == 20


def test_lelang_jenis_harga_kedua_dan_semua_bayar():
    g, s = _lelang({"jenis": "kedua"})
    g.apply(s, {0: 40, 1: 25, 2: 10, 3: 0})
    assert s["koin"] == [75, 100, 100, 100] and s["poin"][0] == s["jadwal"][0]
    g, s = _lelang({"jenis": "semua_bayar"})
    g.apply(s, {0: 40, 1: 25, 2: 10, 3: 0})
    assert s["koin"] == [60, 75, 90, 100] and s["poin"][0] == s["jadwal"][0] and s["poin"][1] == 0


def test_lelang_seri_hangus_ikut_membakar_koin():
    g, s = _lelang({"hangus_persen": 50})
    ev = g.apply(s, {0: 30, 1: 30, 2: 10, 3: 0})
    assert ev[0]["hangus"] and s["koin"] == [85, 85, 100, 100] and s["poin"] == [0, 0, 0, 0]
    assert ev[0]["hangus_koin"] == {"A": 15, "B": 15}
    g, s = _lelang({"hangus_persen": 0})
    g.apply(s, {0: 30, 1: 30, 2: 10, 3: 0})
    assert s["koin"] == [100] * 4


def _minus_state(names):
    g = GAMES["lelang"]
    s = g.init(g.clean_settings({"barang": 4}), list(names), 1)
    s["jadwal"][0] = -5
    return g, s


def test_lelang_barang_minus_kena_tertinggi_terendah_dan_tengah():
    g, s = _minus_state("ABCD")                                  # 4 pemain: hanya ujung
    ev = g.apply(s, {0: 30, 1: 20, 2: 10, 3: 5})
    assert ev[0]["kena_minus"] == ["A", "D"] and s["poin"] == [-5, 0, 0, -5] and s["koin"] == [100] * 4
    g, s = _minus_state("ABCDE")                                 # 5 pemain (ganjil > 3): ujung + tengah
    ev = g.apply(s, {0: 30, 1: 20, 2: 15, 3: 10, 4: 5})
    assert ev[0]["kena_minus"] == ["A", "C", "E"]
    g, s = _minus_state("ABC")                                   # 3 pemain: tengah tidak kena
    ev = g.apply(s, {0: 30, 1: 20, 2: 10})
    assert ev[0]["kena_minus"] == ["A", "C"]
    g, s = _minus_state("ABCD")                                  # seri di ujung: semua yang seri kena
    ev = g.apply(s, {0: 30, 1: 30, 2: 10, 3: 20})
    assert ev[0]["kena_minus"] == ["A", "B", "C"]
    g, s = _minus_state("ABCD")                                  # semua sama: semua kena
    ev = g.apply(s, {0: 0, 1: 0, 2: 0, 3: 0})
    assert ev[0]["kena_minus"] == ["A", "B", "C", "D"]


def test_lelang_jadwal_barang_minus_dan_bonus_set_dan_koin_ronde():
    g, s = _lelang({"barang": 10, "barang_minus": 3, "bonus_set": 8, "koin_ronde": 5})
    minus = [k for k, v in enumerate(s["jadwal"]) if v < 0]
    assert len(minus) == 3 and 0 not in minus and all(-8 <= s["jadwal"][k] <= -1 for k in minus)
    assert all(s["kategori"][k] is None for k in minus)
    s["koleksi"][0] = {"Seni": 3, "Kriya": 2}
    assert g._set_bonus(s, 0) == 8
    g.apply(s, {0: 0, 1: 0, 2: 0, 3: 0})
    assert s["koin"] == [105] * 4


@pytest.mark.parametrize("cfg", [
    {"lihat_depan": 0, "nilai_mode": "taksiran", "koin_rahasia": True, "buka_tawaran": "tidak"},
    {"barang_minus": 4, "hangus_persen": 100, "bonus_set": 10, "jenis": "semua_bayar", "koin_ronde": 3},
    {"nilai_mode": "rahasia", "jenis": "kedua"},
])
def test_lelang_template_tetap_jalan_dengan_kabut(cfg):
    g = GAMES["lelang"]
    codes = [t["kode"] for t in g.templates]
    out = play_sync("lelang", cfg, ["A", "B", "C", "D", "E"], codes + codes[:2], 5)
    errors = [x for lg in out["logs"] for x in lg if x.get("error")]
    assert not errors, errors[:2]
    assert out["frames"][-1]["view"]["jadwal"] == out["frames"][-1]["view"]["jadwal"]


def test_replay_sudut_pandang_berkabut():
    g = GAMES["lelang"]
    cfg = {"lihat_depan": 1, "koin_rahasia": True}
    codes = [t["kode"] for t in g.templates]
    out = play_sync("lelang", cfg, ["A", "B", "C"], codes, 11)
    frames_b = sudut_sync("lelang", cfg, ["A", "B", "C"], 11, out["langkah"], 1)
    assert len(frames_b) == len(out["frames"])
    akhir = frames_b[-1]["view"]
    assert akhir["koin"]["A"] is None and akhir["koin"]["B"] is not None      # B tidak melihat dompet A
    assert out["frames"][-1]["view"]["koin"]["A"] is not None                  # replay terbuka melihat semua
    assert frames_b[0]["view"]["jadwal"][2] is None


def _templates_ok(gid, cfg, names, seed=5):
    g = GAMES[gid]
    codes = [t["kode"] for t in g.templates]
    codes = (codes * len(names))[:len(names)]
    out = play_sync(gid, cfg, list(names), codes, seed)
    errors = [x for lg in out["logs"] for x in lg if x.get("error")]
    assert not errors, errors[:2]
    return out


# ------------------------------------------------------------------ Suit
def test_suit_hp_samar_dan_ronde_rahasia():
    g = GAMES["suit"]
    s = g.init(g.clean_settings({"hp_awal": 1000, "hp_kalah": 100, "ronde_maks": 40, "hp_samar": True, "ronde_rahasia": True}),
               ["A", "B", "C"], 7)
    g.apply(s, {0: "batu", 1: "gunting", 2: "gunting"})
    v = g.observe(s, 1)
    assert v["hp"]["B"] == s["hp"][1] and v["hp"]["A"] % 100 == 0                 # HP sendiri pasti, lawan dibulatkan
    assert v["terakhir"]["perubahan"]["A"] is None and v["terakhir"]["perubahan"]["B"] == -100
    assert v["ronde_maks"] == 40 and not v["ronde_pasti"] and 30 <= s["cfg"]["ronde_maks"] <= 50
    assert g.full_view(s)["hp"]["A"] == s["hp"][0]


def test_suit_buruan_dan_kejutan_tetap_zero_sum():
    g = GAMES["suit"]
    s = g.init(g.clean_settings({"hp_awal": 1000, "hp_kalah": 100, "buruan": 100}), ["A", "B", "C"], 1)
    s["hp"] = [1200, 900, 900]
    g.apply(s, {0: "gunting", 1: "batu", 2: "kertas"})        # A (pemimpin) kalah dari B
    assert s["hp"][0] == 1200 - 100 - 100 + 100 and sum(s["hp"]) == 3000
    out = _templates_ok("suit", {"kejutan_ronde": 100, "buruan": 50}, "ABCDE")
    assert sum(out["frames"][-1]["view"]["hp"].values()) == 5000
    jenis = {e["kejutan"]["jenis"] for f in out["frames"] for e in f["events"] if e.get("kejutan")}
    assert jenis == {"ganda", "terbalik", "terlarang"}


def test_suit_ronde_terbalik_dan_senjata_terlarang():
    g = GAMES["suit"]
    s = g.init(g.clean_settings({"hp_awal": 1000, "hp_kalah": 100, "kejutan_ronde": 100}), ["A", "B", "C"], 1)
    r = s["ronde"]
    while g._kejutan(s, r)["jenis"] != "terbalik":
        r += 1
    s["ronde"] = r
    g.apply(s, {0: "batu", 1: "gunting", 2: "gunting"})       # terbalik: gunting mengalahkan batu
    assert s["hp"][0] == 900 and s["hp"][1] == 1050
    s = g.init(g.clean_settings({"hp_awal": 1000, "hp_kalah": 100, "kejutan_ronde": 100}), ["A", "B", "C"], 1)
    r = 1
    while g._kejutan(s, r)["jenis"] != "terlarang":
        r += 1
    s["ronde"] = r
    w = g._kejutan(s, r)["senjata"]
    other = next(x for x in ("batu", "gunting", "kertas") if x != w)
    g.apply(s, {0: w, 1: other, 2: other})
    assert s["hp"] == [900, 1050, 1050]


# ------------------------------------------------------------------ Poker
def test_poker_short_deck_ante_bounty_dan_chip_samar():
    from app.games.g_poker import evaluate, hand_name
    assert hand_name(evaluate(["As", "6d", "7c", "8h", "9s"], True), True) == "Straight"
    assert evaluate(["Ah", "Jh", "8h", "7h", "6h"], True) > evaluate(["Ks", "Kd", "Kc", "9h", "9s"], True)
    assert evaluate(["Ah", "Jh", "8h", "7h", "6h"]) < evaluate(["Ks", "Kd", "Kc", "9h", "9s"])
    g = GAMES["poker"]
    s = g.init(g.clean_settings({"chip": 1000, "sb": 10, "ante": 50, "short_deck": True, "chip_samar": True}), ["A", "B", "C"], 3)
    assert sum(s["h"]["total"]) == 3 * 10 + 10 + 20 and sum(s["chips"]) + sum(s["h"]["total"]) == 3000
    assert all(c[0] not in "2345" for c in s["h"]["deck"])
    v = g.observe(s, 0)
    assert v["chip"]["A"] == s["chips"][0] and v["chip"]["B"] % 100 == 0
    out = _templates_ok("poker", {"bounty": 300, "ante": 25, "short_deck": True}, "ABCD")
    v = out["frames"][-1]["view"]
    assert sum(v["chip"].values()) == 4000
    assert sorted(out["result"]["skor"], reverse=True)[0] == 4000 + 300 * max(v["bounty_dapat"].values())


# ------------------------------------------------------------------ Kapal
def _kapal_siap(cfg):
    g = GAMES["kapal"]
    s = g.init(g.clean_settings({"ukuran": 8, "armada": "kecil", **cfg}), ["A", "B"], 2)
    lay = [[0, 0, "H"], [2, 0, "H"], [4, 0, "H"], [6, 0, "H"]]
    g.apply(s, {0: g.validate(s, 0, lay), 1: g.validate(s, 1, lay)})
    s["giliran"] = 0
    s["sisa_tembak"] = g._shots_for(s, 0)
    return g, s


def test_kapal_kabar_tenggelam_disembunyikan():
    g, s = _kapal_siap({"info_tenggelam": "tidak"})
    for c in range(2):
        g.apply(s, {0: {"tembak": [6, c]}})
        s["giliran"], s["sisa_tembak"] = 0, 1
    v = g.observe(s, 0)
    assert v["riwayat"][-1]["hasil"] == "kena" and v["riwayat"][-1]["ukuran"] is None
    assert v["papan_tembak"][6][:2] == "oo" and v["kapal_lawan_sisa"] is None
    assert g.full_view(s)["riwayat"][-1]["hasil"] == "tenggelam"
    g2, s2 = _kapal_siap({"info_tenggelam": "tenggelam"})
    for c in range(2):
        g2.apply(s2, {0: {"tembak": [6, c]}})
        s2["giliran"], s2["sisa_tembak"] = 0, 1
    v2 = g2.observe(s2, 0)
    assert v2["papan_tembak"][6][:2] == "##" and v2["jumlah_kapal_lawan_sisa"] == 3 and v2["kapal_lawan_sisa"] is None


def test_kapal_salvo_sonar_dan_ranjau():
    g, s = _kapal_siap({"salvo": True, "sonar": 1, "ranjau": 2})
    assert s["sisa_tembak"] == 4 and len(s["ranjau"][1]) == 2
    ev = g.apply(s, {0: g.validate(s, 0, {"sonar": [1, 1]})})
    assert ev[0]["jumlah"] == 6 and s["sisa_tembak"] == 3 and s["sonar"][0] == 0
    with pytest.raises(ActionError):
        g.validate(s, 0, {"sonar": [1, 1]})
    mine = s["ranjau"][1][0]
    ev = g.apply(s, {0: {"tembak": list(mine)}})
    assert ev[0]["hasil"] == "ranjau" and s["giliran"] == 1 and s["lewati"][0]
    s["sisa_tembak"] = 1
    ev = g.apply(s, {1: {"tembak": [7, 7]}})                  # giliran A dilewati: B menembak lagi
    assert any(e["jenis"] == "lewati" for e in ev) and s["giliran"] == 1 and s["sisa_tembak"] == 4
    assert "*" in "".join(g.observe(s, 1)["papan_saya"])
    _templates_ok("kapal", {"salvo": True, "sonar": 2, "ranjau": 3, "info_tenggelam": "tidak"}, "AB")


# ------------------------------------------------------------------ Robot
def test_robot_kabut_perang_dan_library_tidak_bocor():
    from tests.test_games import _robot_flat
    g, s = _robot_flat(["A", "B"], {"pandang": 3})
    a, b = s["bots"]
    a["r"], a["c"], b["r"], b["c"] = 2, 2, 2, 9
    s["crystals"] = [[2, 4], [9, 9]]
    v = g.observe(s, 0)
    assert "B" not in v["robot"] and v["kristal"] == [[2, 4]] and v["skor"]["B"]["poin"] == 0
    lib = g.bot_library(s, 0, v)
    assert lib["bisa_kena"]() is None and lib["musuh_terdekat"]() is None and lib["posisi"]("B") is None
    assert lib["tebak_langkah"]("B") is None and lib["kristal_terdekat"]() == [2, 4]
    assert g.public(s)["robot"] == {} and g.full_view(s)["robot"]["B"]["kolom"] == 9
    b["c"] = 4
    v = g.observe(s, 0)
    assert "B" in v["robot"] and g.bot_library(s, 0, v)["bisa_kena"]() == "kanan"


def test_robot_powerup_perisai_dan_zona():
    from tests.test_games import _robot_flat
    g, s = _robot_flat(["A", "B"], {"hp": 3, "powerup": 1, "zona": 50, "tick": 20})
    a, b = s["bots"]
    a["r"], a["c"], b["r"], b["c"] = 3, 1, 3, 5
    s["powerups"] = [{"r": 3, "c": 6, "jenis": "perisai"}]
    g.apply(s, {0: "diam", 1: "kanan"})
    assert b["perisai"] and len(s["powerups"]) == 1
    ev = g.apply(s, {0: "tembak_kanan", 1: "diam"})
    assert b["hp"] == 3 and not b["perisai"] and a["poin"] == 0 and any(e["jenis"] == "perisai" for e in ev)
    s["t"] = 10
    s["zona"] = [0, s["cfg"]["ukuran"] - 1]
    b["r"], b["c"] = 0, 0
    ev = g.apply(s, {0: "diam", 1: "diam"})
    assert s["zona"] == [1, s["cfg"]["ukuran"] - 2] and any(e["jenis"] == "zona" for e in ev)
    ev = g.apply(s, {0: "diam", 1: "diam"})
    assert b["hp"] == 2 and any(e["jenis"] == "badai" for e in ev)
    _templates_ok("robot", {"pandang": 3, "powerup": 4, "zona": 40}, "ABCD")


# ------------------------------------------------------------------ Kartu
def test_kartu_niat_musuh_kabut_dan_kesulitan():
    g = GAMES["kartu"]
    base = g.init(g.clean_settings({}), ["A", "B"], 4)
    hp0 = base["runs"][0]["musuh"][0]["hp"]
    niat = g.observe(base, 0)["musuh"][0]["niat"]
    assert niat.get("serang")
    s = g.init(g.clean_settings({"niat_musuh": "jenis", "kesulitan": 3}), ["A", "B"], 4)
    m = g.observe(s, 0)["musuh"][0]
    assert m["niat"] == {"jenis": "serang"} and m["niat_teks"] == "akan menyerang"
    assert m["hp"] == round(hp0 * 1.45)                                        # +15% per tingkat
    s = g.init(g.clean_settings({"niat_musuh": "rahasia"}), ["A", "B"], 4)
    o = g.observe(s, 0)
    assert o["musuh"][0]["niat"] == {} and o["musuh"][0]["niat_teks"] == "?"
    perkiraan = g.bot_library(s, 0, o)["perkiraan_serangan"]()
    assert perkiraan >= niat["serang"] * niat.get("kali", 1)                   # bot menganggap serangan terburuk


@pytest.mark.parametrize("seed,berkah", [(1, "jimat"), (2, "kebal"), (3, "keris"), (6, "kantong")])
def test_kartu_berkah_awal(seed, berkah):
    g = GAMES["kartu"]
    cfg = g.clean_settings({"berkah": True})
    s = g.init(cfg, ["A"], seed)
    run = s["runs"][0]
    assert s["berkah"] == berkah and g.observe(s, 0)["berkah_teks"]
    if berkah == "jimat":
        assert run["hp_maks"] == cfg["hp"] + 15
    if berkah == "kebal":
        assert run["blok"] == 6
    if berkah == "keris":
        assert run["kuat"] == 1
    if berkah == "kantong":
        assert len(run["tangan"]) == 6


def test_kartu_kutukan_tidak_bisa_dimainkan():
    g = GAMES["kartu"]
    s = g.init(g.clean_settings({"kutukan": 2}), ["A"], 4)
    run = s["runs"][0]
    assert (run["tangan"] + run["tarik"]).count("kutukan") == 2
    run["tangan"] = ["kutukan", "tebas"]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"main": 0})
    assert g.validate(s, 0, {"main": 1}) == {"main": 1, "target": 0}
    _templates_ok("kartu", {"niat_musuh": "rahasia", "kutukan": 2, "berkah": True, "kesulitan": 2}, "AB")


# ------------------------------------------------------------------ Tycoon
def test_tycoon_pesaing_rahasia_dan_stok_awet():
    g = GAMES["tycoon"]
    s = g.init(g.clean_settings({"pesaing_rahasia": True, "stok_awet": True, "ramalan": 0}), ["A", "B", "C"], 3)
    assert g.observe(s, 0)["ramalan_besok"] is None                            # ramalan 0 = tanpa ramalan
    a0 = g.validate(s, 0, {"produk": "mainan", "jumlah": 25, "harga": 60000})  # terlalu mahal: tidak laku
    a1 = g.validate(s, 1, {"produk": "sate", "jumlah": 10, "harga": 15000})
    ev = g.apply(s, {0: a0, 1: a1, 2: "tutup"})
    e = g.observe(s, 1)["riwayat"][0]
    assert e["jual"]["A"] == {"rahasia": True} and e["jual"]["C"] == "tutup" and e["jual"]["B"]["produk"] == "sate"
    assert e["penjual"] == {"mainan": 1, "sate": 1}
    assert g.event_for(s, ev[0], 2)["jual"]["A"] == {"rahasia": True}
    assert g.full_view(s)["riwayat"][0]["jual"]["A"]["produk"] == "mainan"
    sisa = s["riwayat"][0]["jual"]["A"]["disimpan"]
    assert sisa == 25 and g.observe(s, 0)["stok_saya"] == {"produk": "mainan", "jumlah": 25, "hari": 2}
    a = g.validate(s, 0, {"produk": "mainan", "jumlah": 0, "harga": 20000})    # jual stok kemarin saja
    assert a != "tutup"
    g.apply(s, {0: a, 1: "tutup", 2: "tutup"})
    j = s["riwayat"][1]["jual"]["A"]
    assert j["stok"] == 25 and j["terjual"] > 0 and j["untung"] == j["terjual"] * 20000 and s["stok"][0] is None


def test_tycoon_kejadian_pasar():
    g = GAMES["tycoon"]
    s = g.init(g.clean_settings({"event_pasar": 100, "hari": 20}), ["A", "B"], 5)
    assert all(day["kejadian"] for day in s["plan"])
    biasa = g.init(g.clean_settings({"hari": 20}), ["A", "B"], 5)
    kj = s["plan"][0]["kejadian"]                                              # hari 1: viral es teh
    assert kj["jenis"] == "viral" and g.observe(s, 0)["kejadian"] == kj
    assert g.observe(s, 0)["produk"]["es_teh"]["pengaruh"] == pytest.approx(g.observe(biasa, 0)["produk"]["es_teh"]["pengaruh"] * 2.5, abs=1e-3)
    g.apply(s, {0: "tutup", 1: "tutup"})
    assert s["plan"][1]["kejadian"]["jenis"] == "razia" and g.observe(s, 0)["produk"]["bakso"]["dilarang"]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"produk": "bakso", "jumlah": 5, "harga": 13000})
    g.apply(s, {0: "tutup", 1: "tutup"})
    assert g.observe(s, 1)["produk"]["es_teh"]["modal"] == 3000                # hari 3: bahan naik ×1,5
    _templates_ok("tycoon", {"pesaing_rahasia": True, "ramalan": 0, "stok_awet": True, "event_pasar": 60}, "ABC")


# ------------------------------------------------------------------ Rebutan Lahan
def test_blotto_alokasi_rahasia_dan_nilai_besok():
    g = GAMES["blotto"]
    s = g.init(g.clean_settings({"alokasi_rahasia": True, "nilai_besok": False, "medan": 3, "pasukan": 30, "menyusut": True}), ["A", "B"], 1)
    assert g.observe(s, 0)["nilai_berikut"] is None and g.full_view(s)["nilai_berikut"] is not None
    ev = g.apply(s, {0: [30, 0, 0], 1: [10, 10, 10]})
    o = g.observe(s, 0)
    e = o["riwayat"][0]
    assert e["alokasi"] == {"A": [30, 0, 0], "B": None} and e["hilang"]["B"] is None and e["pasukan"]["B"] is None
    assert e["penguasa"] == [["A"], ["B"], ["B"]] and o["pasukan_semua"] is None and o["pasukan_saya"] == 39
    assert g.event_for(s, ev[0], 1)["alokasi"]["A"] is None
    assert g.full_view(s)["riwayat"][0]["alokasi"]["B"] == [10, 10, 10]
    assert g.bot_library(s, 0, o)["rata_rata_lawan"]() is None


def test_blotto_benteng_menyusut_dan_bala_bantuan():
    g = GAMES["blotto"]
    s = g.init(g.clean_settings({"medan": 3, "pasukan": 30, "menyusut": True, "bala_bantuan": 30, "benteng": 50, "nilai_acak": False}), ["A", "B"], 1)
    g.apply(s, {0: [30, 0, 0], 1: [10, 10, 10]})
    assert s["pemilik"] == [0, 1, 1] and s["riwayat"][0]["hilang"] == {"A": 0, "B": 10}
    assert s["pool"] == [39, 29]                                               # yang kalah hilang, +9 bala bantuan
    with pytest.raises(ActionError):
        g.validate(s, 1, [30, 0, 0])                                           # pasukan B tinggal 29
    g.apply(s, {0: [20, 0, 0], 1: [25, 0, 0]})                                 # A bertahan: 20 × 1,5 = 30 > 25
    assert s["riwayat"][1]["penguasa"][0] == ["A"] and s["pool"] == [48, 13]


def test_blotto_medan_kejutan_ganda_dan_misteri():
    g = GAMES["blotto"]
    s = g.init(g.clean_settings({"medan": 4, "medan_kejutan": 100}), ["A", "B"], 2)
    o = g.observe(s, 0)
    asli = s["nilai"][0]
    for k, kh in enumerate(o["khusus"]):
        assert kh in ("ganda", "misteri")
        assert o["nilai"][k] == (None if kh == "misteri" else asli[k])
        if kh == "ganda":
            assert asli[k] % 2 == 0
    assert g.full_view(s)["nilai"] == asli
    g.apply(s, {0: [25, 25, 25, 25], 1: [0, 0, 0, 0]})
    assert s["riwayat"][0]["nilai"] == asli and s["skor"][0] == sum(asli)       # misteri dibuka setelah ronde
    _templates_ok("blotto", {"alokasi_rahasia": True, "nilai_besok": False, "benteng": 30, "menyusut": True, "medan_kejutan": 40}, "ABC")


# ------------------------------------------------------------------ Kas Desa
def test_kasdesa_sanksi_denda_usir_dan_bencana():
    g = GAMES["kasdesa"]
    cfg = g.clean_settings({"denda": 3, "usir": True, "bencana": 50, "target": 50, "bonus": 10, "ronde": 4, "akhir_rahasia": False})
    s = g.init(cfg, list("ABCD"), 2)
    g.apply(s, {0: 10, 1: 10, 2: 0, 3: 0})
    assert s["fase"] == "sanksi" and g.observe(s, 0)["fase"] == "sanksi" and g.pending(s) == [0, 1, 2, 3]
    assert s["skor"] == [18, 18, 28, 28]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"denda": {"C": 20}})                                 # lebih dari pendapatan
    with pytest.raises(ActionError):
        g.validate(s, 0, {"denda": {"A": 1}})                                  # tidak bisa mendenda diri sendiri
    assert g.validate(s, 2, None) == g.validate(s, 2, 0) == {"denda": {}, "usir": None}   # bot lama: tanpa sanksi
    acts = {0: {"denda": {"C": 2}, "usir": "C"}, 1: {"denda": {"C": 1, "D": 1}, "usir": "C"}, 2: None, 3: {"usir": "C"}}
    ev = g.apply(s, {p: g.validate(s, p, a) for p, a in acts.items()})
    assert ev[0]["diusir"] == ["C"] and s["skor"] == [16, 16, 19, 25]          # bayar 1 → orang itu −3
    assert g.pending(s) == [0, 1, 3]                                           # C diusir satu ronde
    g.apply(s, {0: 10, 1: 0, 3: 0})
    e = s["riwayat"][-1]
    assert e["dikucilkan"] == ["C"] and e["bagian"] == pytest.approx(16 / 3, abs=1e-3) and not e["tercapai"]
    assert s["skor"][2] == 19 + 10                                             # C tidak dapat bagian kas
    g.apply(s, {p: g.default(s, p) for p in range(4)})
    assert s["kucil"] == []
    skor = list(s["skor"])
    ev = g.apply(s, {p: 0 for p in range(4)})                                  # gagal 2× berturut-turut → banjir
    assert any(x["jenis"] == "bencana" for x in ev)
    assert s["skor"] == pytest.approx([(x + 10) / 2 for x in skor])
    _templates_ok("kasdesa", {"denda": 3, "usir": True, "bencana": 30}, "ABCD")


def test_kasdesa_kabut_sumbangan_dan_pengali_rahasia():
    g = GAMES["kasdesa"]
    s = g.init(g.clean_settings({"pengali_rahasia": True, "terbuka": False}), list("ABC"), 5)
    o = g.observe(s, 0)
    assert o["pengali"] is None and o["pengali_kisaran"] == [0.8, 2.4]
    p1 = g.full_view(s)["pengali"]
    assert p1 is not None and p1 == g._pengali(s, 1)
    ev = g.apply(s, {0: 10, 1: 5, 2: 0})
    assert ev[0]["sumbangan"] == {"A": None, "B": None, "C": None} and ev[0]["pengali"] == p1
    assert g.observe(s, 0)["riwayat"][0]["sumbangan"] == {"A": 10, "B": None, "C": None}
    assert g.public(s)["riwayat"][0]["sumbangan"]["A"] is None
    assert g.full_view(s)["riwayat"][0]["sumbangan"] == {"A": 10, "B": 5, "C": 0}
    _templates_ok("kasdesa", {"terbuka": False, "pengali_rahasia": True}, "ABCD")


# ------------------------------------------------------------------ Dua Pertiga
def _dp(cfg, names, seed=1):
    g = GAMES["duapertiga"]
    return g, g.init(g.clean_settings(cfg), list(names), seed)


def test_duapertiga_median_dan_poin_bertingkat():
    g, s = _dp({"mode_faktor": "tetap", "faktor": 1.0, "kembar_gugur": False, "acuan": "median", "poin_mode": "bertingkat"}, "ABCDE")
    g.apply(s, {0: 10, 1: 20, 2: 30, 3: 90, 4: 100})                          # rata-rata 50, median 30
    e = s["riwayat"][0]
    assert e["median"] == 30 and e["target"] == 30 and e["acuan"] == "median"
    assert e["poin"] == {"C": 3, "B": 2, "A": 1} and e["pemenang"] == ["C"]
    assert s["skor"] == [1, 2, 3, 0, 0]


def test_duapertiga_angka_terlarang_gugur():
    g, s = _dp({"mode_faktor": "tetap", "faktor": 1.0, "kembar_gugur": False, "terlarang": 3, "poin_mode": "bertingkat"}, "ABC", 4)
    ban = g.observe(s, 0)["terlarang"]
    assert len(ban) == 3 and ban == g.public(s)["terlarang"] and ban == _dp({"terlarang": 3}, "ABC", 4)[0].observe(_dp({"terlarang": 3}, "ABC", 4)[1], 1)["terlarang"]
    bebas = [x for x in range(101) if x not in ban]
    g.apply(s, {0: ban[0], 1: bebas[0], 2: bebas[1]})
    e = s["riwayat"][0]
    assert "A" in e["gugur"] and "A" not in e["poin"] and e["terlarang"] == ban and set(e["poin"]) == {"B", "C"}


def test_duapertiga_tebakan_rahasia():
    g, s = _dp({"tebakan_rahasia": True, "kembar_gugur": True}, "ABC", 2)
    ev = g.apply(s, {0: 10, 1: 10, 2: 50})
    e = g.observe(s, 0)["riwayat"][0]
    assert e["tebakan"] == {"A": 10, "B": None, "C": None} and e["gugur"] == ["A"]
    assert g.observe(s, 2)["riwayat"][0]["gugur"] == [] and g.observe(s, 2)["riwayat"][0]["pemenang"] == ["C"]
    assert g.public(s)["riwayat"][0]["tebakan"] == {"A": None, "B": None, "C": None}
    assert g.full_view(s)["riwayat"][0]["tebakan"]["B"] == 10
    live = g.event_for(s, ev[0], 1)
    assert live["tebakan"]["A"] is None and live["tebakan"]["B"] == 10
    _templates_ok("duapertiga", {"tebakan_rahasia": True, "terlarang": 5, "acuan": "median", "poin_mode": "bertingkat"}, "ABCD")


# ------------------------------------------------------------------ Pasar Malam Sepi
def test_farol_beberapa_tempat_hadiah_dan_hukuman():
    g = GAMES["farol"]
    s = g.init(g.clean_settings({"tempat": 3, "kapasitas": 50, "hadiah": 2, "hukuman": 3}), list("ABCDEFGH"), 1)
    v = g.observe(s, 0)
    assert {t["id"]: t["kapasitas"] for t in v["tempat"]} == {"pasar": 4, "konser": 2, "bazar": 1}
    assert [t["hadiah"] for t in v["tempat"]] == [2, 4, 6]
    assert g.validate(s, 0, "datang") == "pasar" and g.validate(s, 0, "BAZAR") == "bazar" and g.validate(s, 0, False) == "rumah"
    with pytest.raises(ActionError):
        g.validate(s, 0, "mall")
    g.apply(s, {0: "pasar", 1: "pasar", 2: "konser", 3: "konser", 4: "konser", 5: "bazar", 6: "rumah", 7: "rumah"})
    assert s["skor"] == [2, 2, -3, -3, -3, 6, 0, 0]                            # konser 3 > 2: sumpek
    e = s["riwayat"][0]
    assert [t["ramai"] for t in e["tempat"]] == [False, True, False] and sorted(e["datang"]) == list("ABCDEF")
    g1 = g.init(g.clean_settings({}), list("ABCD"), 1)
    with pytest.raises(ActionError):
        g.validate(g1, 0, "konser")                                            # hanya satu tempat
    _templates_ok("farol", {"tempat": 3, "kapasitas_mode": "berubah", "malam_spesial": 40}, "ABCDEF")


def test_farol_jumlah_dan_kapasitas_rahasia():
    g = GAMES["farol"]
    s = g.init(g.clean_settings({"jumlah_rahasia": True, "kapasitas_mode": "rahasia"}), list("ABCDE"), 3)
    assert g.observe(s, 0)["kapasitas"] is None and g.full_view(s)["kapasitas"] is not None
    ev = g.apply(s, {0: "pasar", 1: "pasar", 2: "rumah", 3: "rumah", 4: "pasar"})
    e = g.observe(s, 0)["riwayat"][0]
    assert e["jumlah"] is None and e["datang"] == ["A"] and e["kapasitas"] is not None   # kapasitas dibuka setelah malam
    assert e["tempat"][0]["jumlah"] is None and e["tempat"][0]["datang"] == ["A"]
    assert g.observe(s, 2)["riwayat"][0]["datang"] == [] and g.public(s)["riwayat"][0]["datang"] == []
    assert g.full_view(s)["riwayat"][0]["jumlah"] == 3
    live = g.event_for(s, ev[0], 4)
    assert live["jumlah"] is None and live["datang"] == ["E"]
    _templates_ok("farol", {"jumlah_rahasia": True, "kapasitas_mode": "rahasia"}, "ABCDEF")


def test_farol_malam_spesial():
    g = GAMES["farol"]
    s = g.init(g.clean_settings({"malam_spesial": 100, "kapasitas": 60, "malam": 10}), list("ABCDEFGHIJ"), 9)
    seen = set()
    for _ in range(10):
        v = g.observe(s, 0)
        sp = v["spesial"]["jenis"]
        seen.add(sp)
        assert v["tempat"][0]["kapasitas"] == (9 if sp == "festival" else 3)   # 6 × 1,5 atau 6 × ½
        assert v["tempat"][0]["hadiah"] == (2 if sp == "festival" else 1)
        g.apply(s, {i: "rumah" for i in range(10)})
        assert s["riwayat"][-1]["spesial"] == sp
    assert seen == {"festival", "hujan"}


# ------------------------------------------------------------------ kejadian live ikut berkabut
@pytest.mark.parametrize("gid,cfg", [
    ("duapertiga", {"tebakan_rahasia": True}),
    ("farol", {"jumlah_rahasia": True}),
    ("blotto", {"alokasi_rahasia": True}),
    ("tycoon", {"pesaing_rahasia": True}),
    ("lelang", {"buka_tawaran": "tidak"}),
])
def test_kejadian_live_tidak_membocorkan_info_rahasia(gid, cfg):
    """Kejadian live yang dikirim ke tiap pemain tidak boleh lebih terbuka dari riwayat di observe() pemain itu."""
    g = GAMES[gid]
    names = ["A", "B", "C"]
    codes = [t["kode"] for t in g.templates]
    out = play_sync(gid, cfg, names, (codes * 3)[:3], 7)
    s = g.init(g.clean_settings(cfg), names, 7)
    dicek = 0
    for step in out["langkah"]:
        for e in g.apply(s, {int(k): v for k, v in step.items()}):
            if e.get("jenis") not in ("ronde", "malam", "hari", "lelang"):
                continue
            for viewer in range(3):
                live = g.event_for(s, e, viewer)
                hist = g.observe(s, viewer)["riwayat"][-1]
                for k, v in hist.items():
                    if k in live:
                        assert live[k] == v, (gid, viewer, k)
                        dicek += 1
            assert g.event_for(s, e, "semua") == e
        if g.over(s):
            break
    assert dicek > 0
