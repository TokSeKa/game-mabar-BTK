from itertools import product

from app.engine.rules import BATU, GUNTING, KERTAS, SENJATA, resolve_round


def _run(pilihan, hp=None, kalah=100):
    names = list(pilihan)
    hp = hp or {n: 1000 for n in names}
    return resolve_round(pilihan, hp, kalah, {n: i for i, n in enumerate(names)})


def test_contoh_delapan_pemain():
    nama = ["Budi", "Ani", "Citra", "Dodi", "Eka", "Fajar", "Gita", "Hana"]
    senjata = [BATU, KERTAS, GUNTING, BATU, BATU, KERTAS, GUNTING, KERTAS]
    out = _run(dict(zip(nama, senjata)))
    assert out.delta == {"Budi": -33, "Ani": 0, "Citra": 50, "Dodi": -33, "Eka": -34,
                         "Fajar": 0, "Gita": 50, "Hana": 0}
    batu_pair = next(p for p in out.pairs if p.win == BATU)
    assert batu_pair.pool == 200 and batu_pair.share == 66
    # sisa 2 HP ke pemenang ber-HP terendah; semua 1000 jadi urutan masuk
    assert batu_pair.rem_ids == ["Budi", "Dodi"]


def test_semua_sama_tidak_ada_perubahan():
    out = _run({"a": BATU, "b": BATU, "c": BATU})
    assert out.delta == {"a": 0, "b": 0, "c": 0}
    assert out.pairs == []


def test_dua_senjata_biasa():
    out = _run({"a": BATU, "b": GUNTING, "c": GUNTING})
    assert out.delta == {"a": 200, "b": -100, "c": -100}


def test_hp_kurang_dari_hp_kalah():
    out = _run({"a": KERTAS, "b": BATU}, hp={"a": 1000, "b": 40})
    assert out.delta == {"a": 40, "b": -40}


def test_sisa_ke_hp_terendah():
    out = _run({"a": KERTAS, "b": KERTAS, "c": KERTAS, "d": BATU},
               hp={"a": 500, "b": 200, "c": 300, "d": 1000})
    # 100 dibagi 3 = 33 sisa 1 -> b (HP terendah)
    assert out.delta == {"a": 33, "b": 34, "c": 33, "d": -100}


def test_zero_sum_semua_kombinasi():
    names = ["a", "b", "c", "d", "e"]
    for combo in product(SENJATA, repeat=len(names)):
        for kalah in (1, 7, 100, 333):
            hp = {n: 50 + 37 * i for i, n in enumerate(names)}
            out = _run(dict(zip(names, combo)), hp=hp, kalah=kalah)
            assert sum(out.delta.values()) == 0
            for n in names:
                assert hp[n] + out.delta[n] >= 0
