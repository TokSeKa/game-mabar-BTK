import numpy as np
import pytest

from app.trading.session import Blind, SessionError, build_view
from app.trading.store import CandleStore
from app.trading.timeframes import aggregate, bucket

from .trading_fixtures import make_crypto, make_idx


@pytest.fixture()
def store(tmp_path):
    make_crypto(tmp_path, days=30)
    make_idx(tmp_path)
    return CandleStore(tmp_path)


def open_view(store, key, tf, blind=False, steps=None, seed=7):
    return build_view(store, key, tf, np.random.default_rng(seed), Blind.from_any(blind), steps=steps)


def revealed_base(view):
    return np.asarray(view.base[: view.cursor])


def check_no_future(view):
    """Setiap candle yang dikirim harus bisa dihitung dari candle dasar yang sudah terbuka."""
    base = revealed_base(view)
    last_lt = int(base["lt"][-1])
    for tf in view.tfs:
        candles, _ = view.candles(tf, limit=5000)
        times = [c[0] for c in candles]
        assert times == sorted(times) and len(set(times)) == len(times), tf
        assert max(times) * 1000 - view.shift <= last_lt, f"{tf} memuat candle masa depan"
        # candle terakhir (sedang terbentuk) = agregat candle dasar yang sudah terbuka di bucket itu
        b_last = bucket(last_lt, tf, view.origin)
        if b_last < bucket(int(view.base["lt"][view.start_idx]), tf, view.origin):
            continue  # masih candle riwayat dari sebelum sesi dimulai
        in_bucket = base[bucket(base["lt"], tf, view.origin) == b_last]
        agg = aggregate(in_bucket, tf, view.origin)[-1]
        o, h, l, c = candles[-1][1:5]
        k = view.k
        assert h == pytest.approx(agg["h"] * k, rel=1e-6), tf
        assert l == pytest.approx(agg["l"] * k, rel=1e-6), tf
        assert c == pytest.approx(agg["c"] * k, rel=1e-6), tf


def test_tidak_ada_kebocoran_masa_depan_kripto(store):
    v = open_view(store, "crypto:TESTUSDT", "1h")
    assert v.base_tf == "1m"
    check_no_future(v)
    for tf, n in [("1m", 7), ("15m", 3), ("1h", 2), ("4h", 1), ("1d", 1)]:
        v.advance(tf, n)
        check_no_future(v)


def test_step_berhenti_di_batas_candle(store):
    v = open_view(store, "crypto:TESTUSDT", "1h")
    v.advance("1m", 7)
    v.advance("1h", 1)
    nxt = int(v.base["lt"][v.cursor])
    assert nxt % 3_600_000 == 0  # candle dasar berikutnya = awal jam baru
    last = int(v.base["lt"][v.cursor - 1])
    assert bucket(last, "1h") == bucket(nxt, "1h") - 1


def test_updates_sama_dengan_candles(store):
    v = open_view(store, "crypto:TESTUSDT", "15m")
    before, _ = v.candles("1h", limit=5000)
    old, _new = v.advance("15m", 5)
    upd = v.updates("1h", old)
    after, _ = v.candles("1h", limit=5000)
    merged = {c[0]: c for c in before}
    for c in upd:
        merged[c[0]] = c
    assert [merged[t] for t in sorted(merged)] == after


def test_paginasi_sebelum(store):
    v = open_view(store, "crypto:TESTUSDT", "5m")
    last, more = v.candles("5m", limit=100)
    assert more and len(last) == 100
    older, _ = v.candles("5m", before=last[0][0], limit=100)
    assert older[-1][0] < last[0][0]


def test_mode_buta(store):
    v = open_view(store, "crypto:TESTUSDT", "1h", blind=True)
    assert v.label() == "Aset rahasia"
    real = float(v.base["c"][v.cursor - 1])
    assert v.last_price() == pytest.approx(real * v.k)
    assert 10 <= v.first_price() <= 1000
    # tanggal disamarkan ke sekitar 2001, hari dalam minggu & jam tetap
    t = v.now() * 1000 - v.shift
    assert int(v.base["lt"][v.cursor - 1]) == t
    assert 2000 <= 1970 + v.now() / (365.25 * 86400) <= 2002
    assert v.shift % (7 * 86_400_000) == 0
    r = v.reveal()
    assert r["symbol"] == "TESTUSDT" and r["harga_awal_asli"] == pytest.approx(v.first_price() / v.k)


def test_langkah_tetap(store):
    v = open_view(store, "crypto:TESTUSDT", "15m", steps=40)
    n = 0
    while not v.done:
        v.advance("15m", 1)
        n += 1
    assert n == 40


def test_saham_idx_memilih_data_dasar_terkecil(store):
    v = open_view(store, "idx:TEST", "1d", seed=1)
    assert v.base_tf in ("1d", "1h", "5m")
    check_no_future(v)
    v.advance("1d", 3)
    check_no_future(v)
    # paksa titik awal di masa 5m tersedia
    i = store.asset("idx:TEST")["series"]["5m"]
    v2 = build_view(store, "idx:TEST", "1h", np.random.default_rng(2), Blind.from_any(False),
                    start=(i["t0"] + 3 * 86_400_000) // 1000)
    assert v2.base_tf == "5m"
    assert "1h" in v2.tfs and "1m" not in v2.tfs
    check_no_future(v2)
    v2.advance("1h", 4)
    check_no_future(v2)


def test_data_kurang(store):
    with pytest.raises(SessionError):
        open_view(store, "idx:TEST", "1M", steps=500)
