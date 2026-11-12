"""Tes game baru: Wordle Mabar, Labirin, UNO, Evolusi Hex, Monopoli Nusantara."""

import pytest

from app.games.base import ActionError
from app.games.registry import GAMES
from app.games.runner import play_sync


def _templates_ok(gid, cfg, names, seed=3):
    g = GAMES[gid]
    codes = [g.templates[i % len(g.templates)]["kode"] for i in range(len(names))]
    out = play_sync(gid, cfg, list(names), codes, seed)
    errs = [e for lg in out["logs"] for e in lg if "error" in e]
    assert errs == [], errs[:2]
    return out


# ------------------------------------------------------------------ Wordle Mabar
from app.games.g_wordle import HIJAU, JAWABAN, KAMUS, warna  # noqa: E402


def _wd(cfg=None, names=("A", "B", "C"), seed=1, kata=None):
    g = GAMES["wordle"]
    s = g.init(g.clean_settings(cfg or {}), list(names), seed)
    if kata:
        s["kata"] = list(kata)
    return g, s


def test_wordle_warna_huruf_kembar_seperti_wordle_asli():
    assert warna("kakak", "bakar") == "AHHHA"          # tidak ada K lagi yang tersisa untuk kuning
    assert warna("taman", "antar") == "KKAHK"
    assert warna("rumah", "rumah") == HIJAU
    assert all(len(w) == 5 for w in JAWABAN) and set(JAWABAN) <= KAMUS and len(JAWABAN) > 500


def test_wordle_balapan_poin_bonus_tercepat_dan_hukuman():
    g, s = _wd(kata=["rumah", "tanah", "kabar"])
    assert g.is_mandiri(s["cfg"]) and g.jeda_bot(s["cfg"]) == 12
    ev = g.apply(s, {1: "tanah"})
    assert ev[0]["warna"] == warna("tanah", "rumah") and g.cooldown(s, 1, ev) == 3.0
    ev = g.apply(s, {0: "rumah"})
    assert g.cooldown(s, 0, ev) == 0.0
    benar = next(e for e in ev if e["jenis"] == "benar")
    assert benar["poin"] == 6 + 3 and s["skor"][0] == 9 and s["selesai"][0]   # baris 1: 7 − 1 = 6, tercepat +3
    g.apply(s, {1: "rumah"})
    assert s["skor"][1] == 5 + 2                                              # baris 2: 5, kedua +2
    assert g.pending(s) == [2]
    ev = []
    for _ in range(6):
        ev = g.apply(s, {2: "-"})                                            # lewat = baris hangus
    kata = next(e for e in ev if e["jenis"] == "kata")
    assert kata["jawaban"] == "rumah" and kata["hasil"]["C"] == {"tebakan": 6, "menang": False, "poin": 0}
    assert s["ronde"] == 2 and g.pending(s) == [0, 1, 2] and s["papan"] == [[], [], []]


def test_wordle_kamus_mode_sulit_dan_kata_asal():
    g, s = _wd(kata=["rumah"])
    with pytest.raises(ActionError):
        g.validate(s, 0, "qzxjv")                                            # tidak ada di kamus
    with pytest.raises(ActionError):
        g.validate(s, 0, "rum4h")
    assert g.validate(s, 0, None) == "-" and g.validate(s, 0, " RUMAH ") == "rumah"
    g2, s2 = _wd({"kata_asal": "hangus"}, kata=["rumah"])
    g2.apply(s2, {0: g2.validate(s2, 0, "qzxjv")})
    assert s2["papan"][0][-1]["warna"] == "?????" and s2["papan"][0][-1]["asal"]
    g3, s3 = _wd({"mode_sulit": True}, kata=["rumah"])
    g3.apply(s3, {0: "ramai"})                                               # R hijau, A kuning
    with pytest.raises(ActionError):
        g3.validate(s3, 0, "tanah")                                          # huruf pertama harus R
    with pytest.raises(ActionError):
        g3.validate(s3, 0, "rindu")                                          # A wajib dipakai lagi
    assert g3.validate(s3, 0, "rumah") == "rumah"


def test_wordle_bergiliran_papan_bersama():
    g, s = _wd({"mode": "gantian"}, kata=["rumah", "tanah", "kabar"])
    assert not g.is_mandiri(s["cfg"]) and g.pending(s) == [0]
    ev = g.apply(s, {0: "ramai"})
    assert ev[0]["bantu"] and s["skor"][0] == 1 and g.pending(s) == [1]      # huruf hijau baru: +1
    g.apply(s, {1: "-"})
    assert g.pending(s) == [2] and len(s["bersama"]) == 1                    # lewat tidak memakan baris
    ev = g.apply(s, {2: "rumah"})
    assert s["skor"][2] == 5 and any(e["jenis"] == "kata" for e in ev)
    assert s["ronde"] == 2 and g.pending(s) == [1]                           # kata berikutnya dimulai pemain berikutnya
    assert g.observe(s, 0)["riwayat"][0]["papan"]["bersama"][0]["kata"] == "ramai"


def test_wordle_kata_licik_selalu_menghindar_dan_konsisten():
    g, s = _wd({"licik": True}, names=("A",))
    rows = []
    for w in ["sinar", "kapal", "tebus"]:
        ev = g.apply(s, {0: w})
        rows.append({"kata": w, "warna": ev[0]["warna"]})
        assert ev[0]["warna"] != HIJAU
    jawab = s["kandidat"][0]
    assert jawab and all(warna(r["kata"], j) == r["warna"] for r in rows for j in jawab)


def test_wordle_papan_lawan_berkabut():
    g, s = _wd({"info_lawan": "warna"}, kata=["rumah"])
    ev = g.apply(s, {1: "tanah"})
    o = g.observe(s, 0)
    assert o["papan"]["B"]["baris"][0]["kata"] is None and o["papan"]["B"]["baris"][0]["warna"] == warna("tanah", "rumah")
    assert g.observe(s, 1)["papan"]["B"]["baris"][0]["kata"] == "tanah" and o["jawaban"] is None
    assert g.event_for(s, ev[0], 0)["kata"] is None and g.event_for(s, ev[0], 1)["kata"] == "tanah"
    assert g.full_view(s)["jawaban"] == "rumah"
    g2, s2 = _wd({"info_lawan": "tidak"}, kata=["rumah"])
    ev = g2.apply(s2, {1: "tanah"})
    assert g2.observe(s2, 0)["papan"]["B"]["baris"][0]["warna"] is None and g2.event_for(s2, ev[0], 0)["warna"] is None


@pytest.mark.parametrize("cfg", [{}, {"mode": "serentak"}, {"mode": "gantian"}, {"licik": True}, {"mode_sulit": True, "kata_asal": "hangus"}])
def test_wordle_template_semua_mode(cfg):
    out = _templates_ok("wordle", cfg, "ABCD")
    assert len(out["frames"][-1]["view"]["riwayat"]) == 3


# ------------------------------------------------------------------ Labirin
from app.games.g_labirin import ARAH, BIT, buat_labirin, jarak_dari, terbuka  # noqa: E402
from app.games.base import rng  # noqa: E402


def _lb(cfg=None, names=("A", "B"), seed=1):
    g = GAMES["labirin"]
    return g, g.init(g.clean_settings(cfg or {}), list(names), seed)


def _open_dirs(s, p):
    r, c = s["pos"][p]
    return [a for a in ARAH if terbuka(s["lab"]["walls"], r, c, a)]


def test_labirin_sempurna_terhubung_dan_deterministik():
    s = {"seed": 5}
    w1 = buat_labirin(rng(s, "x"), 9, 0)
    w2 = buat_labirin(rng(s, "x"), 9, 0)
    assert w1 == w2
    opened = sum(1 for r in range(9) for c in range(9) for a in ("kanan", "bawah") if not w1[r][c] & BIT[a]
                 and ((a == "kanan" and c < 8) or (a == "bawah" and r < 8)))
    assert opened == 9 * 9 - 1 and len(jarak_dari(w1, (0, 0))) == 81                 # pohon: semua petak terhubung, satu jalan
    assert all(w1[0][c] & 1 for c in range(9)) and all(w1[r][8] & 2 for r in range(9))  # tembok luar utuh
    w3 = buat_labirin(rng(s, "x"), 9, 30)
    assert sum(bin(x).count("1") for row in w3 for x in row) < sum(bin(x).count("1") for row in w1 for x in row)


def test_labirin_tembok_lari_dan_jatah_langkah():
    g, s = _lb({"pandang": "terang", "koin": 0})
    blocked = [a for a in ARAH if a not in _open_dirs(s, 0)]
    with pytest.raises(ActionError):
        g.validate(s, 0, blocked[0])
    a = _open_dirs(s, 0)[0]
    ev = g.apply(s, {0: g.validate(s, 0, "lari_" + a)})
    gerak = ev[0]
    assert gerak["jenis"] == "gerak" and gerak["langkah"] >= 1 and s["langkah"][0] == gerak["langkah"]
    # lari berhenti di persimpangan / buntu: dari petak akhir tidak ada tepat satu jalan lanjutan
    back = {"atas": "bawah", "bawah": "atas", "kiri": "kanan", "kanan": "kiri"}[s["arah"][0]]
    assert len([x for x in _open_dirs(s, 0) if x != back]) != 1 or s["pos"][0] == s["lab"]["keluar"]
    assert g.validate(s, 0, None) == "diam"
    g.apply(s, {0: "diam"})
    assert s["langkah"][0] == gerak["langkah"] + 1


def test_labirin_finis_poin_dan_sisa_langkah_lawan():
    g, s = _lb({"pandang": "terang", "koin": 0, "sisa_finis": 5, "ronde": 1}, names=("A", "B", "C"))
    lib = g.bot_library(s, 0, g.observe(s, 0))
    path = lib["jalur_ke"](*s["lab"]["keluar"])
    assert len(path) == s["lab"]["jalur"]
    for a in path:
        ev = g.apply(s, {0: a})
    fin = next(e for e in ev if e["jenis"] == "finis")
    assert fin["urutan"] == 1 and fin["poin"] == 10 and s["skor"][0] == 10 and 0 not in g.pending(s)
    assert s["batas"][1] == 5 and s["batas"][2] == 5                      # yang lain tinggal 5 langkah
    for _ in range(5):
        g.apply(s, {1: "diam"})
    ev = []
    for _ in range(5):
        ev = g.apply(s, {2: "diam"})
    end = next(e for e in ev if e["jenis"] == "labirin")
    assert end["urutan"] == ["A"] and g.over(s) and s["riwayat"][0]["peta"] == s["lab"]["walls"]


def test_labirin_kabut_ingatan_dan_lawan_tersembunyi():
    g, s = _lb({"pandang": "kabut", "jarak_pandang": 1, "lawan_terlihat": "dekat"})
    o = g.observe(s, 0)
    known = [(r, c) for r, row in enumerate(o["peta"]) for c, x in enumerate(row) if x is not None]
    assert (0, 0) in known and len(known) <= 3 and o["pemain"]["B"]["posisi"] == [0, 0]   # B di petak yang sama: terlihat
    a = _open_dirs(s, 1)[0]
    ev = g.apply(s, {1: a})
    assert g.event_for(s, ev[0], 0) is None and g.event_for(s, ev[0], 1) == ev[0] and g.event_for(s, ev[0], "semua") == ev[0]
    assert g.public(s)["pemain"]["B"]["posisi"] is None and g.full_view(s)["pemain"]["B"]["posisi"] == s["pos"][1]
    g2, s2 = _lb({"pandang": "ingat", "jarak_pandang": 1})
    path = g2.bot_library(s2, 0, g2.full_view(s2) | {"posisi": [0, 0], "arah_terakhir": None})["jalur_ke"](*s2["lab"]["keluar"])
    for a in path[:4]:
        g2.apply(s2, {0: a})
    known2 = sum(1 for row in g2.observe(s2, 0)["peta"] for x in row if x is not None)
    assert known2 >= 5 and g2.observe(s2, 1)["peta"][s2["pos"][0][0]][s2["pos"][0][1]] is None   # ingatan milik sendiri


def test_labirin_tanda_tali_suar_terlihat_semua():
    g, s = _lb({"pandang": "kabut", "tanda": 1, "tali": 3, "suar": 1})
    g.apply(s, {0: g.validate(s, 0, {"tanda": "✖"})})
    assert g.observe(s, 1)["tanda"] == [{"posisi": [0, 0], "simbol": "✖", "oleh": "A"}]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"tanda": "⭐"})                                 # jatah habis
    with pytest.raises(ActionError):
        g.validate(s, 0, {"tanda": "🍕"})
    g.apply(s, {0: g.validate(s, 0, "tali")})
    assert s["tali_aktif"][0]
    lib = g.bot_library(s, 0, g.full_view(s) | {"posisi": s["pos"][0], "arah_terakhir": None})
    ev = []
    for a in lib["jalur_ke"](*s["lab"]["keluar"])[:4]:
        ev += g.apply(s, {0: a})
    assert len(s["tali"][0]) == 4 and not s["tali_aktif"][0] and any(e.get("habis") for e in ev)   # 3 langkah tali + titik awal
    assert g.observe(s, 1)["tali"]["A"] == s["tali"][0]
    r0 = len([x for row in g.observe(s, 0)["peta"] for x in row if x is not None])
    g.apply(s, {0: "suar"})
    assert s["suar_aktif"][0] == 6 and len([x for row in g.observe(s, 0)["peta"] for x in row if x is not None]) > r0


def test_labirin_koin_jebakan_portal():
    g, s = _lb({"pandang": "terang", "koin": 0, "jebakan": 0, "portal": 0})
    a = _open_dirs(s, 0)[0]
    dr, dc = ARAH[a]
    target = [dr, dc]
    s["lab"]["koin"] = [target]
    ev = g.apply(s, {0: a})
    assert any(e["jenis"] == "koin" for e in ev) and s["skor"][0] == 1 and s["lab"]["koin"] == []
    g2, s2 = _lb({"pandang": "kabut", "koin": 0})
    a = _open_dirs(s2, 0)[0]
    dr, dc = ARAH[a]
    s2["lab"]["jebakan"] = [[dr, dc]]
    ev = g2.apply(s2, {0: a})
    assert s2["langkah"][0] == 6 and g2.cooldown(s2, 0, ev) == 3.0 and g2.observe(s2, 1)["jebakan"] == [[dr, dc]]
    g3, s3 = _lb({"pandang": "terang", "koin": 0})
    a = _open_dirs(s3, 0)[0]
    dr, dc = ARAH[a]
    s3["lab"]["portal"] = [[[dr, dc], list(s3["lab"]["keluar"])]]
    ev = g3.apply(s3, {0: a})
    assert any(e["jenis"] == "portal" for e in ev) and any(e["jenis"] == "finis" for e in ev)


@pytest.mark.parametrize("cfg", [{}, {"pandang": "terang"}, {"pandang": "kabut", "jarak_pandang": 1, "kompas": False},
                                 {"koin": 8, "jebakan": 4, "portal": 2}, {"ukuran": 14, "pintas": 0}])
def test_labirin_template_semua_mode(cfg):
    out = _templates_ok("labirin", cfg, "ABCD")
    assert len(out["frames"][-1]["view"]["riwayat"]) == 2


# ------------------------------------------------------------------ Satu! (gaya UNO)
from app.games.g_satu import CONTOH_KARTU, bersihkan_kartu  # noqa: E402


def _st(cfg=None, names=("A", "B", "C"), seed=1):
    g = GAMES["satu"]
    return g, g.init(g.clean_settings(cfg or {}), list(names), seed)


def K(warna, jenis="angka", angka=None, kustom=None, cid=None):
    K.n = getattr(K, "n", 1000) + 1
    return {"id": cid or K.n, "warna": warna, "jenis": jenis, "angka": angka, "kustom": kustom}


def _set_table(s, top, warna=None, giliran=0):
    s["buang"] = [top]
    s["warna"] = warna or top["warna"]
    s["giliran"] = giliran
    s["fase"], s["baru"], s["tumpukan"] = "main", None, 0


def test_satu_dek_108_dan_kartu_kustom():
    g, s = _st()
    assert len(g._deck(s)) == 108
    g2, s2 = _st({"kartu_kustom": [CONTOH_KARTU[0], CONTOH_KARTU[1]]})   # liar ×2 + semua warna ×1
    deck = g2._deck(s2)
    assert len(deck) == 108 + 2 + 4 and sum(1 for c in deck if c["jenis"] == "kustom") == 6
    assert all(len(h) == 7 for h in s["tangan"]) and s["buang"][-1]["jenis"] == "angka"
    rusak = [{"nama": "X", "warna": "liar", "kode": "def efek(:\n"}, {"nama": "", "kode": "def efek():\n    pass\n"}, CONTOH_KARTU[2]]
    assert [k["nama"] for k in bersihkan_kartu(rusak)] == ["Putar Tangan"]          # kode rusak & tanpa nama dibuang


def test_satu_kartu_cocok_dan_setelah_ambil():
    g, s = _st()
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [K("merah", angka=1), K("biru", angka=5), K("biru", angka=7), K("liar", "ganti"), K("hijau", "lewati")]
    assert g._playable_idx(s, 0) == [0, 1, 3]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"main": 2})
    with pytest.raises(ActionError):
        g.validate(s, 0, "lewat")                                          # lewat hanya setelah ambil
    assert g.validate(s, 0, {"main": 3})["warna"] in ("merah", "kuning", "hijau", "biru")   # warna liar dipilih otomatis
    s["dek"].append(K("merah", angka=9, cid=777))
    g.apply(s, {0: "ambil"})
    assert s["fase"] == "setelah_ambil" and g.pending(s) == [0] and g._playable_idx(s, 0) == [5]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"main": 0})                                      # hanya kartu baru
    g.apply(s, {0: "lewat"})
    assert s["giliran"] == 1 and s["fase"] == "main"


def test_satu_lewati_balik_tambah2_dan_tumpuk():
    g, s = _st()
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [K("merah", "lewati"), K("merah", angka=2), K("merah", angka=3)]
    g.apply(s, {0: {"main": 0, "warna": None, "satu": False, "target": None}})
    assert s["giliran"] == 2                                               # B dilewati
    s["tangan"][2] = [K("merah", "balik"), K("biru", angka=1), K("biru", angka=2)]
    g.apply(s, {2: {"main": 0, "warna": None, "satu": False, "target": None}})
    assert s["arah"] == -1 and s["giliran"] == 1
    before = len(s["tangan"][0])
    s["tangan"][1] = [K("merah", "tambah2"), K("hijau", angka=4), K("hijau", angka=6)]
    g.apply(s, {1: {"main": 0, "warna": None, "satu": False, "target": None}})
    assert len(s["tangan"][0]) == before + 2 and s["giliran"] == 2         # A menarik 2 lalu dilewati (arah terbalik)
    g2, s2 = _st({"tumpuk": True})
    _set_table(s2, K("merah", angka=5))
    s2["tangan"][0] = [K("merah", "tambah2"), K("biru", angka=1), K("biru", angka=2)]
    s2["tangan"][1] = [K("hijau", "tambah2"), K("biru", angka=3), K("biru", angka=4)]
    g2.apply(s2, {0: {"main": 0, "warna": None, "satu": False, "target": None}})
    assert s2["tumpukan"] == 2 and g2._playable_idx(s2, 1) == [0]
    g2.apply(s2, {1: {"main": 0, "warna": None, "satu": False, "target": None}})
    n2 = len(s2["tangan"][2])
    g2.apply(s2, {2: "ambil"})
    assert len(s2["tangan"][2]) == n2 + 4 and s2["tumpukan"] == 0 and s2["giliran"] == 0
    g3, s3 = _st(names=("A", "B"))
    _set_table(s3, K("merah", angka=5))
    s3["tangan"][0] = [K("merah", "balik"), K("biru", angka=1), K("biru", angka=2)]
    g3.apply(s3, {0: {"main": 0, "warna": None, "satu": False, "target": None}})
    assert s3["giliran"] == 0                                              # berdua: balik = lewati


def test_satu_teriak_dan_lupa_satu():
    g, s = _st()
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [K("merah", angka=1), K("biru", angka=8)]
    ev = g.apply(s, {0: g.validate(s, 0, {"main": 0})})
    assert any(e["jenis"] == "lupa_satu" for e in ev) and len(s["tangan"][0]) == 3
    _set_table(s, K("biru", angka=5), giliran=1)
    s["tangan"][1] = [K("biru", angka=1), K("kuning", angka=8)]
    ev = g.apply(s, {1: g.validate(s, 1, {"main": 0, "satu": True})})
    assert any(e["jenis"] == "teriak" for e in ev) and g.observe(s, 0)["teriak"] == ["B"]


def test_satu_menang_ronde_menghitung_sisa_kartu():
    g, s = _st({"ronde": 2})
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [K("merah", angka=1)]
    s["tangan"][1] = [K("biru", angka=7), K("liar", "tambah4")]            # 7 + 50
    s["tangan"][2] = [K("hijau", "lewati")]                                 # 20
    ev = g.apply(s, {0: {"main": 0, "warna": None, "satu": False, "target": None}})
    win = next(e for e in ev if e["jenis"] == "menang_ronde")
    assert win["pemenang"] == "A" and win["poin"] == 77 and s["skor"][0] == 77
    assert s["ronde"] == 2 and all(len(h) == 7 for h in s["tangan"]) and s["giliran"] == 2   # dealer bergeser


def test_satu_kartu_kustom_tukar_lompat_dan_error():
    cards = [CONTOH_KARTU[0], CONTOH_KARTU[4], {"nama": "Rusak", "simbol": "💣", "warna": "semua", "kode": "def efek():\n    tarik('Siapa', 1)\n"}]
    g, s = _st({"kartu_kustom": cards})
    tukar = K("liar", "kustom", kustom=0)
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [tukar, K("biru", angka=1), K("biru", angka=2)]
    s["tangan"][2] = [K("hijau", angka=3)]
    a = g.validate(s, 0, {"main": 0, "warna": "hijau", "target": "C"})
    ev = g.apply(s, {0: a})
    assert any(e["jenis"] == "tukar" for e in ev) and len(s["tangan"][0]) == 1 and len(s["tangan"][2]) == 2
    assert s["warna"] == "hijau"
    _set_table(s, K("merah", angka=5), giliran=1)
    s["tangan"][1] = [K("merah", "kustom", kustom=1), K("biru", angka=1)]
    g.apply(s, {1: g.validate(s, 1, {"main": 0, "satu": True})})
    assert s["giliran"] == 1                                               # lompat dua dari B (3 pemain) = kembali ke B
    s["tangan"][1] = [K("merah", "kustom", kustom=2), K("biru", angka=1), K("biru", angka=4)]
    ev = g.apply(s, {1: g.validate(s, 1, {"main": 0})})
    assert any(e["jenis"] == "efek_gagal" for e in ev) and s["giliran"] == 2   # error: tanpa efek, permainan jalan terus
    s["tangan"][2] = [tukar, K("biru", angka=9)]
    with pytest.raises(ActionError):
        g.validate(s, 2, {"main": 0, "warna": "biru", "target": "C"})      # target harus pemain lain


def test_satu_aturan_70_dan_kabut():
    g, s = _st({"aturan_70": True, "kartu_lawan": "rahasia"})
    _set_table(s, K("merah", angka=5))
    s["tangan"][0] = [K("merah", angka=7), K("biru", angka=1), K("biru", angka=2)]
    s["tangan"][1] = [K("hijau", angka=4)]
    g.apply(s, {0: g.validate(s, 0, {"main": 0, "target": "B"})})
    assert len(s["tangan"][0]) == 1 and len(s["tangan"][1]) == 2
    _set_table(s, K("kuning", angka=5), giliran=1)
    s["tangan"][1] = [K("kuning", angka=0), K("biru", angka=1)]
    sizes = [len(h) for h in s["tangan"]]
    g.apply(s, {1: g.validate(s, 1, {"main": 0, "satu": True})})
    assert [len(h) for h in s["tangan"]] == [sizes[2], sizes[0], sizes[1] - 1]   # semua tangan pindah ke pemain berikutnya
    o = g.observe(s, 2)
    assert o["jumlah_kartu"]["C"] is not None and o["jumlah_kartu"]["A"] in (None, 1)
    ev = {"jenis": "ambil", "pemain": "A", "jumlah": 3}
    assert "jumlah" not in g.event_for(s, ev, 2) and g.event_for(s, ev, 0)["jumlah"] == 3


def test_satu_cek_kartu_kustom_untuk_editor():
    ok = GAMES["satu"].cek_kustom(CONTOH_KARTU[3])
    assert ok["ok"] and ok["contoh"][0]["jenis"] == "efek_beri" and ok["sesudah"]["Lawan1"] == 7
    bad = GAMES["satu"].cek_kustom({"nama": "X", "warna": "liar", "kode": "def efek():\n    lewati(\n"})
    assert not bad["ok"] and bad["error"]["pesan"]


@pytest.mark.parametrize("cfg", [{}, {"tumpuk": True, "aturan_70": True}, {"kartu_lawan": "rahasia", "ambil_sampai": True},
                                 {"kartu_kustom": CONTOH_KARTU}, {"kartu_kustom": CONTOH_KARTU, "tumpuk": True}])
def test_satu_template_semua_mode(cfg):
    out = _templates_ok("satu", cfg, "ABCD")
    assert len(out["frames"][-1]["view"]["riwayat"]) == 3


# ------------------------------------------------------------------ Evolusi Hex
from app.games.g_evolusi import ARAH as HEX, biaya_langkah, energi_maks, hex_dist, key as hk  # noqa: E402


def _ev(cfg=None, names=("A", "B"), seed=1, design=None):
    g = GAMES["evolusi"]
    base = {"semak": 0, "batu": 0, "jebakan": 0, "makanan": 1, "populasi_awal": 1}
    s = g.init(g.clean_settings({**base, **(cfg or {})}), list(names), seed)
    acts = {p: g.validate(s, p, {"desain": design} if design else {}) for p in range(len(names))}
    g.apply(s, acts)
    s["makanan"] = {}
    return g, s


def _crit(s, p):
    return [m for m in s["makhluk"].values() if m["pemilik"] == p]


def test_evolusi_peta_sarang_dan_desain():
    g = GAMES["evolusi"]
    s = g.init(g.clean_settings({}), ["A", "B", "C"], 4)
    assert s["fase"] == "desain" and g.pending(s) == [0, 1, 2]
    assert len({hk(x) for x in s["sarang"]}) == 3 and all(hex_dist(x, [0, 0]) == s["cfg"]["radius"] - 1 for x in s["sarang"])
    with pytest.raises(ActionError):
        g.validate(s, 0, {"desain": {"pandangan": 9, "kelincahan": 9, "ukuran": 9}})   # 27 > 15 poin
    with pytest.raises(ActionError):
        g.validate(s, 0, {"desain": {"pandangan": 0, "kelincahan": 5, "ukuran": 5}})
    g.apply(s, {0: g.validate(s, 0, {"desain": {"pandangan": 2, "kelincahan": 3, "ukuran": 9}}), 1: {}, 2: {}})
    assert s["fase"] == "main" and s["giliran"] == 1 and len(_crit(s, 0)) == 2
    assert all(m["ukuran"] == 9 and m["hp"] == 55 for m in _crit(s, 0)) and _crit(s, 1)[0]["ukuran"] == 5
    # peta tetap tersambung walaupun banyak batu
    s2 = g.init(g.clean_settings({"batu": 25}), ["A", "B"], 9)
    from collections import deque
    start = "0,0"
    seen = {start}
    q = deque([start])
    while q:
        c = [int(x) for x in q.popleft().split(",")]
        for d in HEX.values():
            k2 = hk([c[0] + d[0], c[1] + d[1]])
            if k2 in s2["peta"] and s2["peta"][k2] != "#" and k2 not in seen:
                seen.add(k2)
                q.append(k2)
    assert seen == {k2 for k2, t in s2["peta"].items() if t != "#"}


def test_evolusi_biaya_energi_langkah_dan_hidup():
    g, s = _ev(design={"pandangan": 4, "kelincahan": 5, "ukuran": 6})
    m = _crit(s, 0)[0]
    e0 = m["energi"]
    m["posisi"] = [0, 0]
    _crit(s, 1)[0]["posisi"] = [-3, 3]
    a = g.validate(s, 0, {"perintah": {m["id"]: {"mode": "manual", "jalan": ["timur", "timur", "tenggara"]}}})
    g.apply(s, {0: a, 1: {"perintah": {_crit(s, 1)[0]["id"]: {"mode": "diam"}}}})
    assert m["posisi"] == [2, 1]
    expect = e0 - 3 * biaya_langkah(6, 5) - 0.5 - 0.25 * 4
    assert m["energi"] == pytest.approx(expect, abs=0.01) and biaya_langkah(6, 5) == pytest.approx(1.728)
    assert m["mode"] == "manual"                                           # manual tanpa langkah baru = diam
    g.apply(s, {0: {}, 1: {}})
    assert m["posisi"] == [2, 1]


def test_evolusi_memangsa_dan_seimbang_terhalang():
    g, s = _ev()
    a, b = _crit(s, 0)[0], _crit(s, 1)[0]
    a["posisi"], b["posisi"] = [0, 0], [1, 0]
    a["ukuran"], b["ukuran"] = 6, 5                                         # 6 ≥ 1,2 × 5 → bisa memangsa
    b["mode"] = "diam"
    g.apply(s, {0: g.validate(s, 0, {"perintah": {a["id"]: {"mode": "manual", "jalan": ["timur"]}}}), 1: {}})
    assert b["id"] not in s["makhluk"] and a["posisi"] == [1, 0] and s["poin"][0] == 5 and s["stat"][0]["mangsa"] == 1
    g2, s2 = _ev()
    a, b = _crit(s2, 0)[0], _crit(s2, 1)[0]
    a["posisi"], b["posisi"] = [0, 0], [1, 0]
    b["mode"] = "diam"
    g2.apply(s2, {0: g2.validate(s2, 0, {"perintah": {a["id"]: {"mode": "manual", "jalan": ["timur"]}}}), 1: {}})
    assert a["posisi"] == [0, 0] and b["id"] in s2["makhluk"]                # ukuran sama: terhalang
    b["ukuran"] = 7                                                          # masuk ke mulut pemangsa
    g2.apply(s2, {0: g2.validate(s2, 0, {"perintah": {a["id"]: {"mode": "manual", "jalan": ["timur"]}}}), 1: {}})
    assert a["id"] not in s2["makhluk"] and s2["poin"][1] == 5


def test_evolusi_makan_beranak_mutasi_dan_kelaparan():
    g, s = _ev({"mutasi": 0, "maks_populasi": 3})
    m = _crit(s, 0)[0]
    _crit(s, 1)[0]["mode"] = "diam"
    m["posisi"] = [0, 0]
    s["makanan"] = {"1,0": "rumput"}
    e0 = m["energi"]
    g.apply(s, {0: g.validate(s, 0, {"perintah": {m["id"]: {"mode": "manual", "jalan": ["timur"]}}}), 1: {}})
    assert m["energi"] == pytest.approx(min(energi_maks(5), e0 + 12) - biaya_langkah(5, 5) - 0.5 - 0.25 * 5, abs=0.01)
    assert s["poin"][0] == 1 and "1,0" not in s["makanan"]
    m["energi"] = energi_maks(5)
    g.apply(s, {0: g.validate(s, 0, {"beranak": {m["id"]: True}, "perintah": {m["id"]: {"mode": "diam"}}}), 1: {}})
    kids = [x for x in _crit(s, 0) if x["induk"] == m["id"]]
    assert len(kids) == 1 and hex_dist(kids[0]["posisi"], m["posisi"]) == 1 and s["poin"][0] == 1 + 3
    assert kids[0]["nama"] == "#2" and kids[0]["beranak"]
    for _ in range(3):
        for x in _crit(s, 0):
            x["energi"] = energi_maks(5)
        g.apply(s, {0: {}, 1: {}})
    assert len(_crit(s, 0)) == 3                                             # populasi maksimal 3
    k = kids[0]
    k["energi"] = 0.1
    k["hp"] = 2
    k["mode"] = "diam"
    ev = g.apply(s, {0: {}, 1: {}})
    assert k["id"] not in s["makhluk"] and any(e["jenis"] == "mati" and e["sebab"] == "lapar" for e in ev)
    assert s["makanan"].get(hk(k["posisi"])) == "daging"


def test_evolusi_kabut_semak_dan_kejadian():
    g, s = _ev({"kabut": True})
    a, b = _crit(s, 0)[0], _crit(s, 1)[0]
    a["posisi"], b["posisi"] = [0, 0], [4, 0]
    a["pandangan"] = 2
    assert all(o["id"] != b["id"] for o in g.observe(s, 0)["makhluk_lain"])   # terlalu jauh
    a["pandangan"] = 5
    assert any(o["id"] == b["id"] for o in g.observe(s, 0)["makhluk_lain"])
    assert "energi" not in g.observe(s, 0)["makhluk_lain"][0]                 # info lawan terbatas
    s["peta"]["4,0"] = "s"                                                   # B bersembunyi di semak
    assert all(o["id"] != b["id"] for o in g.observe(s, 0)["makhluk_lain"])
    a["posisi"] = [3, 0]
    assert any(o["id"] == b["id"] for o in g.observe(s, 0)["makhluk_lain"])   # dari sebelahnya terlihat
    ev = {"jenis": "lahir", "pemilik": "B", "id": "9", "nama": "#2"}
    assert g.event_for(s, ev, 0) is None and g.event_for(s, ev, 1) == ev and g.event_for(s, ev, "semua") == ev
    assert len(g.full_view(s)["makhluk_lain"]) == 2 and g.public(s)["makhluk_lain"] == []


def test_evolusi_rintangan_batu_dan_duri():
    g, s = _ev({"rintangan": 2})
    a, b = _crit(s, 0)[0], _crit(s, 1)[0]
    a["posisi"], b["posisi"] = [0, 0], [3, -1]
    b["mode"] = "diam"
    a["mode"] = "diam"
    g.apply(s, {0: g.validate(s, 0, {"pasang": {"makhluk": a["id"], "arah": "barat", "jenis": "batu"}}), 1: {}})
    assert s["peta"]["-1,0"] == "#" and s["rintangan_sisa"][0] == 1
    g.apply(s, {0: g.validate(s, 0, {"pasang": {"makhluk": a["id"], "arah": "timur", "jenis": "duri"}}), 1: {}})
    assert s["jebakan"]["1,0"]["oleh"] == 0
    assert g.observe(s, 1)["jebakan"] == [] and g.observe(s, 0)["jebakan"] == [[1, 0, "duri", True]]
    with pytest.raises(ActionError):
        g.validate(s, 0, {"pasang": {"makhluk": a["id"], "arah": "timur", "jenis": "duri"}})   # jatah habis
    hp = b["hp"]
    b["posisi"] = [2, 0]
    g.apply(s, {0: {}, 1: g.validate(s, 1, {"perintah": {b["id"]: {"mode": "manual", "jalan": ["barat"]}}})})
    assert b["hp"] <= hp - 10 + 1 and "1,0" not in s["jebakan"]


def test_evolusi_tujuan_lalu_kembali_ke_naluri():
    g, s = _ev()
    a = _crit(s, 0)[0]
    _crit(s, 1)[0]["mode"] = "diam"
    a["posisi"] = [0, 0]
    g.apply(s, {0: g.validate(s, 0, {"perintah": {a["id"]: {"mode": "tujuan", "tujuan": [2, 0]}}}), 1: {}})
    assert a["posisi"] == [2, 0] and a["mode"] == "naluri" and a["tujuan"] is None
    with pytest.raises(ActionError):
        g.validate(s, 0, {"perintah": {a["id"]: {"mode": "terbang"}}})
    assert g.validate(s, 0, {"perintah": {"999": {"mode": "diam"}}}) == {"perintah": {}}   # makhluk lain/mati diabaikan


@pytest.mark.parametrize("cfg", [{}, {"kabut": False}, {"semak": 35, "jebakan": 8}, {"mutasi": 70, "bangkit": 0}, {"radius": 8, "giliran": 40}])
def test_evolusi_template_semua_mode(cfg):
    out = _templates_ok("evolusi", cfg, "ABCD")
    assert out["frames"][-1]["view"]["giliran"] >= 2


def test_evolusi_jalur_disimpan_dan_dibatasi_supaya_server_tidak_tersendat():
    from app.games.g_evolusi import MAKS_ASAL_JALUR, key, unkey
    g, s = _ev({"radius": 9, "jebakan": 6, "batu": 15}, seed=4)
    obs = g.observe(s, 0)
    lib = g.bot_library(s, 0, obs)
    cells = [unkey(k) for k in obs["peta"] if obs["peta"][k] != "#"]
    a = cells[0]
    first = lib["jalur"](a, cells[-1])
    assert all(lib["jalur"](a, cells[-1]) == first for _ in range(500))     # petak awal sama: dari simpanan
    for c in cells[1:MAKS_ASAL_JALUR]:
        lib["jalur"](c, a)
    with pytest.raises(ActionError):
        lib["jalur"](cells[MAKS_ASAL_JALUR], a)
    assert lib["jalur"](a, a) == [] and key(a) in obs["peta"]


# ------------------------------------------------------------------ Juragan Nusantara (gaya Monopoli)
from app.games.g_monopoli import KELOMPOK, PAPAN  # noqa: E402


def _mp(cfg=None, names=("A", "B", "C"), seed=1):
    g = GAMES["monopoli"]
    return g, g.init(g.clean_settings(cfg or {}), list(names), seed)


def _roll_to(s, cond):
    """Atur nomor lemparan supaya lemparan berikutnya memenuhi cond(d1, d2) (dadu tetap dari seed)."""
    for k in range(500):
        g = rng(s, "dadu", k + 1)
        d = (g.randint(1, 6), g.randint(1, 6))
        if cond(*d):
            s["lempar_no"] = k
            return d
    raise AssertionError("tidak ketemu")


def test_monopoli_papan_dan_sewa():
    g, s = _mp()
    assert len(PAPAN) == 40 and len(KELOMPOK["transport"]) == 4 and len(KELOMPOK["biru_tua"]) == 2
    s["milik"]["1"] = 0
    assert g._rent(s, 1) == 5                                               # 8% dari 60
    s["milik"]["3"] = 0
    assert g._rent(s, 1) == 10                                              # kelompok lengkap: ×2
    s["rumah"]["1"] = 3
    assert g._rent(s, 1) == 5 * 38
    for k, i in enumerate(KELOMPOK["transport"]):
        s["milik"][str(i)] = 1
        assert g._rent(s, i) == 25 * 2 ** k
    s["milik"]["12"] = 2
    assert g._rent(s, 12, dice=8) == 32
    s["milik"]["28"] = 2
    assert g._rent(s, 12, dice=8) == 80
    s["gadai"]["12"] = True
    assert g._rent(s, 12, dice=8) == 0


def test_monopoli_beli_tolak_dan_lelang_tertutup():
    g, s = _mp()
    s["posisi"][0] = 5
    s["fase"] = "beli"
    g.apply(s, {0: g.validate(s, 0, "tolak")})
    assert s["fase"] == "lelang" and g.pending(s) == [0, 1, 2]
    with pytest.raises(ActionError):
        g.validate(s, 1, {"lelang": 99999})
    ev = g.apply(s, {0: {"lelang": 0}, 1: {"lelang": 150}, 2: {"lelang": 150}})
    res = next(e for e in ev if e["jenis"] == "lelang_hasil")
    assert res["pemenang"] == "B" and s["milik"]["5"] == 1 and s["uang"][1] == 1350   # seri: B lebih dekat dari A
    assert s["fase"] in ("akhir", "awal")
    g2, s2 = _mp()
    s2["posisi"][0] = 39
    s2["fase"] = "beli"
    g2.apply(s2, {0: g2.validate(s2, 0, "beli")})
    assert s2["milik"]["39"] == 0 and s2["uang"][0] == 1100


def test_monopoli_kembar_lempar_lagi_dan_tiga_kali_penjara():
    g, s = _mp()
    _roll_to(s, lambda a, b: a == b and PAPAN[(a + b) % 40][1] in ("kota",))
    g.apply(s, {0: "lempar"})
    assert s["fase"] in ("beli", "awal") and s["kembar"] == 1
    if s["fase"] == "beli":
        g.apply(s, {0: "beli"})
    assert s["fase"] == "awal" and s["giliran"] == 0                        # kembar: lempar lagi
    s["kembar"] = 2
    _roll_to(s, lambda a, b: a == b)
    g.apply(s, {0: "lempar"})
    assert s["penjara"][0] and s["posisi"][0] == 10 and s["fase"] == "akhir"
    g.apply(s, {0: "selesai"})
    assert s["giliran"] == 1


def test_monopoli_penjara_bayar_kembar_dan_wajib_keluar():
    g, s = _mp()
    s["penjara"][0], s["posisi"][0] = True, 10
    _roll_to(s, lambda a, b: a != b)
    g.apply(s, {0: "lempar"})
    assert s["penjara"][0] and s["giliran_penjara"][0] == 1 and s["fase"] == "akhir"
    s["fase"] = "awal"
    g.apply(s, {0: g.validate(s, 0, "bayar_penjara")})
    assert not s["penjara"][0] and s["uang"][0] == 1450
    s["penjara"][0], s["giliran_penjara"][0], s["posisi"][0] = True, 2, 10
    _roll_to(s, lambda a, b: a != b and PAPAN[10 + a + b][1] not in ("kesempatan", "dana"))
    g.apply(s, {0: "lempar"})
    assert not s["penjara"][0] and s["uang"][0] <= 1400                     # giliran ke-3 gagal: wajib bayar lalu jalan


def test_monopoli_bangun_merata_gadai_dan_jual():
    g, s = _mp()
    for i in KELOMPOK["coklat"]:
        s["milik"][str(i)] = 0
    s["fase"] = "awal"
    assert g._buildable(s, 0) == [1, 3]
    g.apply(s, {0: g.validate(s, 0, {"bangun": 1})})
    assert g._buildable(s, 0) == [3]                                        # harus merata
    with pytest.raises(ActionError):
        g.validate(s, 0, {"bangun": 1})
    with pytest.raises(ActionError):
        g.validate(s, 0, {"gadai": 3})                                      # kelompok masih punya rumah
    g.apply(s, {0: g.validate(s, 0, {"jual_rumah": 1})})
    assert s["rumah"]["1"] == 0 and s["uang"][0] == 1500 - 50 + 25
    g.apply(s, {0: g.validate(s, 0, {"gadai": 3})})
    assert s["gadai"]["3"] and g._buildable(s, 0) == [] and s["uang"][0] == 1475 + 30
    g.apply(s, {0: g.validate(s, 0, {"tebus": 3})})
    assert not s["gadai"]["3"] and s["uang"][0] == 1505 - 33


def test_monopoli_tukar_menukar():
    g, s = _mp()
    s["milik"]["6"], s["milik"]["8"] = 0, 1
    s["fase"] = "awal"
    a = g.validate(s, 0, {"tawar": {"ke": "B", "beri": {"uang": 100, "properti": [6]}, "minta": {"properti": [8]}}})
    g.apply(s, {0: a})
    assert s["fase"] == "tawaran" and g.pending(s) == [1] and g.observe(s, 1)["tawaran"]["dari"] == "A"
    g.apply(s, {1: g.validate(s, 1, "terima")})
    assert s["milik"]["6"] == 1 and s["milik"]["8"] == 0 and s["uang"] == [1400, 1600, 1500] and s["fase"] == "awal"
    with pytest.raises(ActionError):
        g.validate(s, 0, {"tawar": {"ke": "C", "minta": {"properti": [6]}}})   # 6 bukan milik C
    s["milik"]["9"], s["milik"]["6"] = 0, 0
    s["rumah"]["9"] = 1
    with pytest.raises(ActionError):
        g.validate(s, 0, {"tawar": {"ke": "B", "beri": {"properti": [8]}}})   # kelompok biru muda punya rumah
    s["tawar_count"] = 3
    with pytest.raises(ActionError):
        g.validate(s, 0, {"tawar": {"ke": "B", "beri": {"uang": 1}}})


def test_monopoli_likuidasi_bangkrut_dan_selesai():
    g, s = _mp(names=("A", "B"))
    s["milik"]["39"], s["milik"]["37"] = 1, 1
    s["rumah"]["39"] = 5
    s["milik"]["1"] = 0
    s["uang"][0] = 30
    s["posisi"][0] = 39
    ev = []
    g._resolve(s, 0, ev, 7)
    kinds = [e["jenis"] for e in ev]
    assert "likuidasi" in kinds and "bangkrut" in kinds and s["bangkrut"][0]
    assert s["milik"]["1"] == 1 and g.over(s)
    sc = g.scores(s)
    assert sc[1] > 0 > sc[0]


def test_monopoli_kartu_dan_uang_rahasia():
    g, s = _mp({"uang_rahasia": True})
    o = g.observe(s, 0)
    assert o["pemain"]["B"]["uang"] is None and o["pemain"]["A"]["uang"] == 1500 and g.full_view(s)["pemain"]["B"]["uang"] == 1500
    s["dek"]["kesempatan"] = [0] + [x for x in s["dek"]["kesempatan"] if x != 0]
    s["dek"]["ik"] = 0
    s["posisi"][0] = 36
    ev = []
    g._resolve(s, 0, ev, 7)
    assert s["posisi"][0] == 0 and s["uang"][0] == 1700 and any(e["jenis"] == "kartu" for e in ev)


@pytest.mark.parametrize("cfg", [{}, {"lelang_properti": False}, {"parkir_jackpot": True, "uang_rahasia": True}, {"tukar": False, "batas_putaran": 40}])
def test_monopoli_template_semua_mode(cfg):
    out = _templates_ok("monopoli", cfg, "ABCD")
    assert out["result"]["ranking"]
