"""Tes aturan setiap game Arena Mabar + semua template bot bisa main sampai selesai."""

import pytest

from app.games.base import ActionError
from app.games.g_poker import evaluate, hand_name, preflop_strength
from app.games.guide import guide_markdown
from app.games.registry import GAMES
from app.games.runner import play_sync, thin_frames
from app.games.runtime import compile_for


def run_defaults(game, cfg, names, seed=7, picker=None, limit=5000):
    """Mainkan game dengan aksi bawaan (atau ``picker``) sampai selesai."""
    s = game.init(game.clean_settings(cfg), names, seed)
    steps = 0
    while not game.over(s) and steps < limit:
        pend = game.pending(s)
        assert pend, "game belum selesai tapi tidak ada yang harus bertindak"
        if game.mandiri:
            for p in pend:
                a = picker(s, p) if picker else game.default(s, p)
                game.apply(s, {p: a})
        else:
            game.apply(s, {p: (picker(s, p) if picker else game.default(s, p)) for p in pend})
        steps += 1
    assert game.over(s)
    return s


# ---------------------------------------------------------------- semua game
@pytest.mark.parametrize("gid", list(GAMES))
def test_template_main_sampai_selesai(gid):
    g = GAMES[gid]
    for t in g.templates:
        compile_for(g, t["kode"])
    for n in sorted({g.min_pemain if g.min_pemain > 1 else 2, min(g.max_pemain, 5)}):
        names = [f"Bot{i}" for i in range(n)]
        codes = [g.templates[i % len(g.templates)]["kode"] for i in range(n)]
        a = play_sync(gid, {}, names, codes, 99)
        b = play_sync(gid, {}, names, codes, 99)
        assert a["result"] == b["result"], "hasil harus sama untuk seed yang sama"
        errors = [e for lg in a["logs"] for e in lg if "error" in e]
        assert errors == [], errors[:3]
        assert len(a["result"]["ranking"]) == n
        assert a["frames"][0]["step"] == 0
        assert len(a["frames"]) <= g.max_frames


@pytest.mark.parametrize("gid", list(GAMES))
def test_aksi_bawaan_selalu_bisa_menyelesaikan_game(gid):
    g = GAMES[gid]
    n = g.min_pemain if g.min_pemain > 1 else 2
    run_defaults(g, {}, [f"P{i}" for i in range(n)])


@pytest.mark.parametrize("gid", list(GAMES))
def test_meta_dan_panduan(gid):
    g = GAMES[gid]
    m = g.meta()
    assert m["id"] == gid and m["nama"] and m["aturan"] and m["templates"]
    md = guide_markdown(g)
    assert f"def {g.fungsi_bot}():" in md and "Contoh bot" in md


def test_bot_rusak_jatuh_ke_aksi_bawaan_lalu_dimatikan():
    out = play_sync("lelang", {}, ["Rusak", "Normal"], ["def aksi():\n    return 1 / 0\n", "def aksi():\n    return 1\n"], 5)
    log = out["logs"][0]
    assert sum(1 for e in log if "error" in e) == 3
    assert "dimatikan" in log[2]["catatan"]


def test_kode_tidak_valid_saat_kompilasi():
    out = play_sync("duapertiga", {}, ["A", "B"], ["import os", None], 1)
    assert "Kode bot tidak valid" in out["logs"][0][0]["catatan"]


def test_thin_frames_simpan_awal_dan_akhir():
    frames = [{"step": i} for i in range(1000)]
    t = thin_frames(frames, 100)
    assert len(t) <= 100 and t[0]["step"] == 0 and t[-1]["step"] == 999


# ---------------------------------------------------------------- poker
def test_evaluator_poker():
    def v(s):
        return evaluate(s.split())
    assert hand_name(v("As Ks Qs Js Ts 2d 3c")) == "Royal Flush"
    assert v("9h 8h 7h 6h 5h Ad Ac") > v("Ad Ac Ah As Kd 2c 3c")          # straight flush > quads
    assert v("Ad Ac Ah Kd Kc 2c 3s")[0] == 6                                 # full house
    assert v("Ad Ac Ah Kd Kc Kh 3s") == (6, 14, 13)                          # dua trips -> full house
    assert v("Ah 2d 3c 4s 5h 9d Jc") == (4, 5)                               # wheel A-2-3-4-5
    assert v("2h 7h 9h Jh Kh 3d 4c")[0] == 5 and v("2h 7h 9h Jh Kh 3d 4c") > v("Td Jc Qs Kd Ah 2c 3c")
    assert v("Ad Ac Kd Kc Qd Qc 2s") == (2, 14, 13, 12)                     # dua pasang terbaik + kicker
    assert v("Ad Ac 9d 8c 7d 4c 2s") > v("Kd Kc Ad 8c 7d 4c 2s")
    assert preflop_strength(["As", "Ah"]) == 1.0
    assert preflop_strength(["7d", "2c"]) < 0.1 < preflop_strength(["Ks", "Qs"])


def _poker_state(chips, dealer=0):
    g = GAMES["poker"]
    names = [f"P{i}" for i in range(len(chips))]
    s = g.init(g.clean_settings({"chip": 1000, "sb": 10, "naik_tiap": 0, "tangan_maks": 50}), names, 3)
    # set ulang tangan pertama dengan chip yang diinginkan
    s["chips"] = list(chips)
    s["tangan"] = 0
    s["dealer"] = dealer
    s["riwayat"], s["arsip"] = [], []
    g._start_hand(s, first=True)
    g._progress(s, s["h"]["bb_p"])
    return g, s


def test_poker_heads_up_dealer_small_blind_dan_bertindak_dulu():
    g, s = _poker_state([1000, 1000], dealer=0)
    h = s["h"]
    assert h["sb_p"] == 0 and h["bb_p"] == 1
    assert h["bet"] == [10, 20]
    assert g.pending(s) == [0]


def test_poker_side_pot_dan_konservasi_chip():
    g, s = _poker_state([100, 300, 1000], dealer=0)
    total_awal = sum(s["chips"]) + sum(s["h"]["total"])
    # atur kartu: P0 (AA) > P1 (KK) > P2 (sepasang 2). Papan 4s 8c 9d Js 2h: tanpa straight/flush.
    h = s["h"]
    h["hole"] = [["As", "Ah"], ["Ks", "Kh"], ["2c", "7d"]]
    urut_ambil = ["5c", "4s", "8c", "9d", "6c", "Js", "Tc", "2h"]   # bakar, flop×3, bakar, turn, bakar, river
    pakai = {c for hole in h["hole"] for c in hole} | set(urut_ambil)
    h["deck"] = [c for c in h["deck"] if c not in pakai] + list(reversed(urut_ambil))
    while not g.over(s) and s["tangan"] == 1:
        p = g.pending(s)[0]
        g.apply(s, {p: g.validate(s, p, "allin")})
    assert sum(s["chips"]) + sum(s["h"]["total"]) == total_awal
    last = s["riwayat"][-1]
    assert last["meja"] == ["4s", "8c", "9d", "Js", "2h"]
    # pot utama 3×100 untuk P0, side pot 2×200 untuk P1, kelebihan 700 milik P2 dikembalikan
    assert last["menang"] == {"P0": 300, "P1": 400}
    assert s["chips"][2] + s["h"]["total"][2] == 700


def test_poker_check_tidak_boleh_saat_ada_taruhan_dan_raise_dirapikan():
    g, s = _poker_state([1000, 1000], dealer=0)
    with pytest.raises(ActionError):
        g.validate(s, 0, "check")
    assert g.validate(s, 0, {"aksi": "raise", "ke": 5}) == {"aksi": "raise", "ke": 40}   # minimal
    assert g.validate(s, 0, {"aksi": "raise", "ke": 99999}) == {"aksi": "raise", "ke": 1000}
    assert g.validate(s, 0, "ikut") == {"aksi": "call"}
    assert g.default(s, 0) == {"aksi": "fold"}


def test_poker_short_allin_tidak_membuka_raise_lagi():
    g, s = _poker_state([1000, 1000, 45], dealer=0)
    # 3 pemain: dealer P0, SB P1, BB P2 (all-in 20 dari 45? tidak: P2 punya 45, pasang 20)
    order = []
    p = g.pending(s)[0]
    order.append(p)
    g.apply(s, {p: g.validate(s, p, {"aksi": "raise", "ke": 40})})   # P0 raise ke 40
    p = g.pending(s)[0]
    g.apply(s, {p: g.validate(s, p, "call")})                         # P1 call 40
    p = g.pending(s)[0]
    assert p == 2
    g.apply(s, {p: g.validate(s, p, "allin")})                        # P2 all-in 45 (naik 5 saja)
    p = g.pending(s)[0]
    assert p == 0
    assert "raise" not in g._valid(s, 0)                              # tidak dibuka ulang
    assert g.validate(s, 0, {"aksi": "raise", "ke": 500}) == {"aksi": "call"}


def test_poker_seed_dan_hash_bisa_dicek():
    import hashlib
    out = play_sync("poker", {"tangan_maks": 3}, ["A", "B"], [None, None], 4242)
    rv = out["reveal"]
    assert hashlib.sha256(f"poker|{rv['seed']}".encode()).hexdigest()[:16] == rv["hash_dek"]
    assert rv["kartu_semua"] and set(rv["kartu_semua"][0]["kartu"]) == {"A", "B"}


def test_poker_kartu_lawan_tersembunyi():
    g = GAMES["poker"]
    s = g.init(g.clean_settings({}), ["A", "B"], 1)
    import json
    obs = g.observe(s, 0)
    assert obs["kartu_saya"] == s["h"]["hole"][0]
    pub, mine = json.dumps(g.public(s)), json.dumps(obs)
    for c in s["h"]["hole"][1]:
        assert f'"{c}"' not in pub and f'"{c}"' not in mine
    for c in s["h"]["hole"][0]:
        assert f'"{c}"' not in pub


# ---------------------------------------------------------------- kapal
def test_kapal_susun_dan_tembak():
    g = GAMES["kapal"]
    s = g.init(g.clean_settings({"armada": "kecil", "ukuran": 6}), ["A", "B"], 2)
    with pytest.raises(ActionError):
        g.validate(s, 0, [[0, 0, "H"], [0, 0, "V"], [3, 0, "H"], [5, 0, "H"]])   # bertumpuk
    with pytest.raises(ActionError):
        g.validate(s, 0, [[0, 4, "H"], [1, 0, "H"], [2, 0, "H"], [3, 0, "H"]])   # keluar papan
    lay = [[0, 0, "H"], [1, 0, "H"], [2, 0, "H"], [3, 0, "H"]]
    g.apply(s, {0: g.validate(s, 0, lay), 1: g.validate(s, 1, lay)})
    assert s["fase"] == "tembak"
    p = s["giliran"]
    ev = g.apply(s, {p: g.validate(s, p, [5, 5])})
    assert ev[0]["hasil"] == "meleset" and s["giliran"] == 1 - p
    q = s["giliran"]
    ev = g.apply(s, {q: g.validate(s, q, [3, 0])})
    assert ev[0]["hasil"] == "kena"
    with pytest.raises(ActionError):
        g.validate(s, p, [5, 5])                                                   # sudah pernah
    obs = g.observe(s, p)
    assert obs["papan_saya"][3][0] == "o" and "K" not in "".join(obs["papan_tembak"])


def test_kapal_menang_saat_semua_tenggelam():
    g = GAMES["kapal"]
    s = g.init(g.clean_settings({"armada": "kecil", "ukuran": 6, "tembak_lagi": True}), ["A", "B"], 2)
    lay = [[0, 0, "H"], [1, 0, "H"], [2, 0, "H"], [3, 0, "H"]]
    g.apply(s, {0: g.validate(s, 0, lay), 1: g.validate(s, 1, lay)})
    s["giliran"] = 0
    targets = [[0, c] for c in range(4)] + [[1, c] for c in range(3)] + [[2, 0], [2, 1], [3, 0], [3, 1]]
    for t in targets:
        assert s["giliran"] == 0
        g.apply(s, {0: g.validate(s, 0, t)})
    assert g.over(s) and g.result(s)["pemenang"] == 0
    assert set(g.reveal(s)["papan"]) == {"A", "B"}


# ---------------------------------------------------------------- lelang, blotto, angka
def test_lelang_seri_hangus_dan_bayar():
    g = GAMES["lelang"]
    s = g.init(g.clean_settings({"barang": 3, "modal": 50}), ["A", "B"], 1)
    ev = g.apply(s, {0: 10, 1: 10})
    assert ev[0]["hangus"] and s["koin"] == [50, 50]
    nilai = s["jadwal"][1]
    g.apply(s, {0: 20, 1: 5})
    assert s["koin"] == [30, 50] and s["poin"][0] == nilai
    with pytest.raises(ActionError):
        g.validate(s, 0, 31)


def test_blotto_seri_dibagi():
    g = GAMES["blotto"]
    s = g.init(g.clean_settings({"medan": 2, "pasukan": 10, "ronde": 1, "nilai_acak": False}), ["A", "B"], 1)
    g.apply(s, {0: [5, 5], 1: [5, 5]})
    assert s["skor"] == [1.0, 1.0]
    with pytest.raises(ActionError):
        g.validate(s, 0, [6, 6])


def test_dua_pertiga_kasdesa_farol():
    g = GAMES["duapertiga"]
    s = g.init(g.clean_settings({"ronde": 1}), ["A", "B", "C"], 1)
    g.apply(s, {0: 0, 1: 30, 2: 60})          # rata 30 -> target 20
    assert s["skor"] == [0, 1, 0]
    k = GAMES["kasdesa"]
    s = k.init(k.clean_settings({"ronde": 1, "pendapatan": 10, "pengali": 2.0}), ["A", "B"], 1)
    k.apply(s, {0: 10, 1: 0})
    assert k.scores(s) == [10.0, 20.0]
    f = GAMES["farol"]
    s = f.init(f.clean_settings({"malam": 1, "kapasitas": 50}), ["A", "B", "C", "D"], 1)
    f.apply(s, {0: "datang", 1: "datang", 2: "rumah", 3: "rumah"})
    assert s["skor"] == [1, 1, 0, 0]


def test_suit_live_konservasi_hp():
    g = GAMES["suit"]
    s = g.init(g.clean_settings({"hp_awal": 1000, "hp_kalah": 100}), ["A", "B", "C"], 1)
    g.apply(s, {0: "batu", 1: "gunting", 2: "kertas"})
    assert sum(s["hp"]) == 3000
    g.apply(s, {0: "batu", 1: "gunting", 2: "gunting"})
    assert s["hp"][0] > 1000 and sum(s["hp"]) == 3000
    with pytest.raises(ActionError):
        g.validate(s, 0, "pistol")


# ---------------------------------------------------------------- robot
def _robot_flat(names, cfg=None):
    g = GAMES["robot"]
    s = g.init(g.clean_settings({"tembok": 0, "kristal": 1, **(cfg or {})}), names, 1)
    s["walls"] = []
    s["crystals"] = [[0, 0]]
    return g, s


def test_robot_tabrakan_dan_bertukar_batal():
    g, s = _robot_flat(["A", "B"])
    a, b = s["bots"]
    a["r"], a["c"], b["r"], b["c"] = 5, 5, 5, 7
    g.apply(s, {0: "kanan", 1: "kiri"})            # sama-sama ke (5,6)
    assert (a["c"], b["c"]) == (5, 7)
    b["c"] = 6
    g.apply(s, {0: "kanan", 1: "kiri"})            # bertukar tempat
    assert (a["c"], b["c"]) == (5, 6)
    g.apply(s, {0: "atas", 1: "kiri"})             # B mengikuti A yang pergi: boleh
    assert (a["r"], a["c"], b["c"]) == (4, 5, 5)


def test_robot_tembak_cooldown_dan_kristal():
    g, s = _robot_flat(["A", "B", "C"], {"hp": 2})
    a, b, c = s["bots"]
    a["r"], a["c"], b["r"], b["c"], c["r"], c["c"] = 3, 1, 3, 5, 3, 9
    g.apply(s, {0: "tembak_kanan", 1: "diam", 2: "diam"})
    assert b["hp"] == 1 and c["hp"] == 2 and a["poin"] == 1          # kena robot pertama saja
    with pytest.raises(ActionError):
        g.validate(s, 0, "tembak_kanan")                              # belum siap
    for _ in range(3):
        g.apply(s, {0: "diam", 1: "diam", 2: "diam"})
    assert g.validate(s, 0, "tembak_kanan") == "tembak_kanan"
    g.apply(s, {0: "tembak_kanan", 1: "diam", 2: "diam"})
    assert not b["hidup"] and a["poin"] == 1 + 1 + 3
    s["crystals"] = [[2, 1]]
    g.apply(s, {0: "atas", 2: "diam"})
    assert a["poin"] == 7 and len(s["crystals"]) == 1 and s["crystals"][0] != [2, 1]


def test_robot_bangkit_lagi():
    g, s = _robot_flat(["A", "B"], {"hp": 1, "bangkit": 3})
    a, b = s["bots"]
    a["r"], a["c"], b["r"], b["c"] = 3, 1, 3, 5
    g.apply(s, {0: "tembak_kanan", 1: "diam"})
    assert not b["hidup"] and not g.over(s)
    for _ in range(3):
        g.apply(s, {0: "diam"})
    assert b["hidup"] and [b["r"], b["c"]] == b["awal"]


def test_peta_robot_simetris_dan_terhubung():
    g = GAMES["robot"]
    s = g.init(g.clean_settings({"tembok": 25}), ["A", "B", "C", "D"], 77)
    n = s["cfg"]["ukuran"]
    walls = {tuple(w) for w in s["walls"]}
    assert all((n - 1 - r, k) in walls and (r, n - 1 - k) in walls for r, k in walls)
    ok, _ = g._connected(n, walls, [(b["r"], b["c"]) for b in s["bots"]])
    assert ok


# ---------------------------------------------------------------- tycoon
def test_tycoon_pembeli_dibagi_dan_modal_dicek():
    g = GAMES["tycoon"]
    s = g.init(g.clean_settings({"hari": 2, "modal": 200000}), ["A", "B", "C"], 1)
    with pytest.raises(ActionError):
        g.validate(s, 0, {"produk": "sate", "jumlah": 40, "harga": 15000})        # 240.000 > 200.000
    a = g.validate(s, 0, {"produk": "sate", "jumlah": 30, "harga": 15000})
    b = g.validate(s, 1, {"produk": "sate", "jumlah": 30, "harga": 15000})
    ev = g.apply(s, {0: a, 1: b, 2: "tutup"})
    jual = ev[0]["jual"]
    assert jual["A"]["terjual"] == jual["B"]["terjual"] and jual["C"] == "tutup"
    assert s["uang"][2] == 200000
    sold = jual["A"]["terjual"]
    assert s["uang"][0] == 200000 - 30 * 6000 + sold * 15000


def test_tycoon_harga_dua_kali_wajar_tidak_laku():
    g = GAMES["tycoon"]
    s = g.init(g.clean_settings({"hari": 1}), ["A", "B"], 1)
    ev = g.apply(s, {0: g.validate(s, 0, {"produk": "bakso", "jumlah": 10, "harga": 26000}), 1: "tutup"})
    assert ev[0]["jual"]["A"]["terjual"] == 0 and s["uang"][0] == 200000 - 50000


# ---------------------------------------------------------------- kartu
def test_kartu_seed_sama_musuh_sama_untuk_semua():
    g = GAMES["kartu"]
    s = g.init(g.clean_settings({}), ["A", "B", "C"], 5)
    musuh = [[(m["id"], m["hp"]) for m in r["musuh"]] for r in s["runs"]]
    assert musuh[0] == musuh[1] == musuh[2]
    assert s["runs"][0]["tangan"] == s["runs"][1]["tangan"]


def test_kartu_energi_blok_dan_racun():
    g = GAMES["kartu"]
    s = g.init(g.clean_settings({}), ["A"], 5)
    run = s["runs"][0]
    run["tangan"] = ["tangkis", "racun_upas", "amukan", "tebas"]
    run["energi"] = 3
    m = run["musuh"][0]
    m["hp"] = m["hp_maks"] = 100
    g.apply(s, {0: g.validate(s, 0, {"main": 0})})               # tangkis
    assert run["blok"] == 5 and run["energi"] == 2
    g.apply(s, {0: g.validate(s, 0, {"main": 0, "target": 0})})  # racun upas
    assert m["racun"] == 5
    assert run["tangan"] == ["amukan", "tebas"] and run["energi"] == 1
    with pytest.raises(ActionError):
        g.validate(s, 0, {"main": 2})                             # tidak ada kartu ke-2
    with pytest.raises(ActionError):
        g.validate(s, 0, {"main": 0})                             # amukan butuh 2 energi
    hp_before = m["hp"]
    g.apply(s, {0: g.validate(s, 0, "akhiri")})
    assert m["hp"] == hp_before - 5 and m["racun"] == 4          # racun bekerja di awal giliran musuh
    assert run["giliran"] == 2 and len(run["tangan"]) == 5 and run["energi"] == 3


def test_kartu_hadiah_dan_istirahat():
    g = GAMES["kartu"]
    s = g.init(g.clean_settings({}), ["A"], 5)
    run = s["runs"][0]
    for m in run["musuh"]:
        m["hp"] = 1
    run["tangan"] = ["tebas", "tebas", "tebas"]
    run["energi"] = 3
    while run["fase"] == "tarung":
        alive = [k for k, m in enumerate(run["musuh"]) if m["hidup"]]
        g.apply(s, {0: g.validate(s, 0, {"main": 0, "target": alive[0]})})
    assert run["fase"] == "hadiah" and len(run["pilihan"]) == 3
    pick = run["pilihan"][1]
    g.apply(s, {0: g.validate(s, 0, {"pilih": 1})})
    assert run["dek"][-1] == pick and run["lantai"] == 2
    run["lantai"] = 3
    run["hp"] = 10
    g._next_floor(s, run)
    assert run["fase"] == "istirahat"
    g.apply(s, {0: g.validate(s, 0, "pulihkan")})
    assert run["hp"] == 10 + run["hp_maks"] * 35 // 100 and run["lantai"] == 5 and run["fase"] == "tarung"
