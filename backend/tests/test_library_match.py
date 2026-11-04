import pytest

from app.bot.interpreter import Interpreter, Limits
from app.bot.library import RoundView, make_library
from app.bot.templates import TEMPLATE_BY_ID, TEMPLATES
from app.bot.validator import compile_bot
from app.engine.match import BotEntry, MatchSettings, run_match


def view(**kw) -> RoundView:
    base = dict(
        me="Budi", ronde=3, hp_awal=1000, hp_kalah=100, ronde_maks=100, ingatan=10,
        names=["Budi", "Ani", "Citra"], hp={"Budi": 900, "Ani": 1200, "Citra": 900},
        history=[
            {"ronde": 1, "jumlah": {"batu": 2, "gunting": 1, "kertas": 0},
             "pilihan": {"Budi": "batu", "Ani": "batu", "Citra": "gunting"},
             "perubahan": {"Budi": 50, "Ani": 50, "Citra": -100}, "hp": {"Budi": 1050, "Ani": 1050, "Citra": 900}},
            {"ronde": 2, "jumlah": {"batu": 1, "gunting": 1, "kertas": 1},
             "pilihan": {"Budi": "gunting", "Ani": "kertas", "Citra": "batu"},
             "perubahan": {"Budi": -150, "Ani": 150, "Citra": 0}, "hp": {"Budi": 900, "Ani": 1200, "Citra": 900}},
        ],
    )
    base.update(kw)
    return RoundView(**base)


def ev(expr: str, v: RoundView | None = None):
    it = Interpreter(compile_bot(f"def pilih():\n    return {expr}\n"), make_library(v or view()))
    it.run_module()
    return it.call_function("pilih")


def test_info_dasar():
    assert ev("[nama_saya(), hp_saya(), ronde(), hp_awal(), hp_kalah(), ingatan()]") == ["Budi", 900, 3, 1000, 100, 10]
    assert ev("lawan()") == ["Ani", "Citra"]
    assert ev("terkuat()") == "Ani"
    assert ev("terlemah()") == "Citra"
    assert ev("hp('Ani')") == 1200


def test_riwayat():
    assert ev("jumlah_terakhir()") == {"batu": 1, "gunting": 1, "kertas": 1}
    assert ev("pilihan_terakhir('Ani')") == "kertas"
    assert ev("riwayat_pilihan('Budi')") == ["batu", "gunting"]
    assert ev("perubahan_terakhir('Budi')") == -150
    assert ev("total_jumlah(riwayat_jumlah())") == {"batu": 3, "gunting": 2, "kertas": 1}
    assert ev("len(riwayat())") == 2


def test_riwayat_kosong_di_ronde_1():
    v = view(ronde=1, history=[])
    assert ev("jumlah_terakhir()", v) == {"batu": 0, "gunting": 0, "kertas": 0}
    assert ev("pilihan_terakhir('Ani')", v) is None
    assert ev("senjata_terbaik()", v) == "batu"


def test_helper_senjata():
    assert ev("[pengalah(BATU), korban(BATU), pengalah('Kertas')]") == ["kertas", "gunting", "gunting"]
    assert ev("terbanyak({'batu': 2, 'gunting': 2, 'kertas': 1})") == "batu"
    assert ev("tersedikit({'kertas': 0, 'batu': 0, 'gunting': 5})") == "batu"
    assert ev("tersedikit(['batu', 'batu', 'gunting'])") == "kertas"
    assert ev("hitung(['a', 'b', 'a'], 'a')") == 2


def test_hitung_hasil_dan_senjata_terbaik():
    assert ev("hitung_hasil({'Budi': BATU, 'Ani': GUNTING})") == {"Budi": 100, "Ani": -100}
    # lawan mengulang: Ani kertas, Citra batu -> gunting: kalahkan kertas, kalah dari batu
    assert ev("senjata_terbaik()") in ("batu", "gunting", "kertas")


def test_data_library_tidak_bisa_merusak_game():
    v = view()
    ev("riwayat()[0].clear()", v)
    assert v.history[0]["ronde"] == 1


def test_error_nama_tidak_ada():
    with pytest.raises(Exception) as e:
        ev("hp('Zaki')")
    assert "tidak ada pemain" in str(e.value)


def test_semua_template_valid_dan_jalan():
    entries = [BotEntry(f"P{i}", t["kode"]) for i, t in enumerate(TEMPLATES[:8])]
    res = run_match(entries, MatchSettings())
    for log in res["logs"]:
        assert not any("error" in e for e in log)
    assert sum(res["final_hp"]) == 8 * 1000


def test_match_deterministik_dan_zero_sum():
    ids = ["pemutar", "anti_mayoritas", "pembalas", "ahli_hitung", "pembaca_pola"]
    entries = [BotEntry(f"B{i}", TEMPLATE_BY_ID[t]["kode"]) for i, t in enumerate(ids)]
    a = run_match(entries, MatchSettings(ronde_maks=60))
    b = run_match(entries, MatchSettings(ronde_maks=60))
    assert a["rounds"] == b["rounds"]
    for r in a["rounds"]:
        assert sum(r["after"]) == 5 * 1000
        assert sum(r["delta"]) == 0


def test_tidak_ada_memori_antar_ronde():
    code = "x = []\n\ndef pilih():\n    x.append(1)\n    print(len(x))\n    return BATU\n"
    res = run_match([BotEntry("A", code), BotEntry("B", "def pilih():\n    return GUNTING\n")],
                    MatchSettings(ronde_maks=3, hp_kalah=1))
    assert [e["cetak"] for e in res["logs"][0]] == [["1"], ["1"], ["1"]]


def test_ingatan_dibatasi():
    code = "def pilih():\n    print(len(riwayat()))\n    return BATU\n"
    res = run_match([BotEntry("A", code), BotEntry("B", code)], MatchSettings(ronde_maks=8, ingatan=3))
    assert [e["cetak"][0] for e in res["logs"][0]] == ["0", "1", "2", "3", "3", "3", "3", "3"]


def test_bot_error_dimatikan_setelah_3_kali():
    bad = "def pilih():\n    return 1 / 0\n"
    res = run_match([BotEntry("A", bad), BotEntry("B", "def pilih():\n    return KERTAS\n")],
                    MatchSettings(ronde_maks=6, hp_kalah=10))
    log = res["logs"][0]
    assert len(log) == 3 and "catatan" in log[2]
    assert all(c == "batu" for c in (r["choices"][0] for r in res["rounds"]))


def test_eliminasi_dan_pemenang():
    res = run_match([BotEntry("A", "def pilih():\n    return KERTAS\n"),
                     BotEntry("B", "def pilih():\n    return BATU\n")],
                    MatchSettings(hp_awal=300, hp_kalah=100))
    assert res["reason"] == "last_standing"
    assert res["winners"] == [0]
    assert len(res["rounds"]) == 3
    assert res["elim_round"] == {"1": 3}


def test_settings_dibatasi():
    s = MatchSettings.from_dict({"hp_awal": 50, "hp_kalah": 999999, "ronde_maks": "abc", "ingatan": 0})
    assert s.hp_awal == 100 and s.hp_kalah == 100 and s.ronde_maks == 100 and s.ingatan == 1


def test_bot_langkah_habis_tidak_menghentikan_match():
    res = run_match([BotEntry("A", "def pilih():\n    while True:\n        pass\n"),
                     BotEntry("B", "def pilih():\n    return KERTAS\n")],
                    MatchSettings(ronde_maks=20), Limits(max_steps=5000))
    assert len(res["rounds"]) == 10  # A selalu BATU, kalah 100 per ronde
