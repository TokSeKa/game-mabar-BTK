import io
import zipfile

import numpy as np
import pandas as pd

from app.trading.ingest_binance import parse_zip
from app.trading.ingest_yahoo import df_to_rec
from app.trading.store import CandleStore, read_series, series_path, write_series
from app.trading.timeframes import REC, aggregate, bucket, bucket_start, dedupe_sorted

from .trading_fixtures import T0, make_crypto, make_idx


def _rec(ts, lt=None, base=100.0):
    n = len(ts)
    r = np.empty(n, REC)
    r["t"] = ts
    r["lt"] = ts if lt is None else lt
    r["o"] = base + np.arange(n)
    r["h"] = r["o"] + 2
    r["l"] = r["o"] - 1
    r["c"] = r["o"] + 1
    r["v"] = 1.0
    return r


def test_aggregate_5m_dan_harian():
    ts = T0 + np.arange(0, 60 * 24 * 2) * 60_000  # 2 hari 1m
    r = _rec(ts)
    a5 = aggregate(r, "5m")
    assert len(a5) == 2 * 24 * 12
    assert a5["o"][0] == r["o"][0] and a5["c"][0] == r["c"][4]
    assert a5["h"][0] == r["h"][:5].max() and a5["l"][0] == r["l"][:5].min()
    assert a5["v"][0] == 5
    d = aggregate(r, "1d")
    assert len(d) == 2 and d["t"][1] - d["t"][0] == 86_400_000


def test_minggu_mulai_senin_dan_bulan_kalender():
    days = T0 + np.arange(0, 70) * 86_400_000  # mulai Senin 2024-01-01
    r = _rec(days)
    w = aggregate(r, "1w")
    weekday = (w["lt"] // 86_400_000 + 3) % 7
    assert set(weekday.tolist()) == {0}
    m = aggregate(r, "1M")
    assert [str(np.datetime64(int(x), "ms").astype("datetime64[D]")) for x in m["lt"]] == ["2024-01-01", "2024-02-01", "2024-03-01"]


def test_bucket_origin_saham_us():
    lt = np.array([9 * 3600_000 + 30 * 60_000, 10 * 3600_000 + 25 * 60_000, 10 * 3600_000 + 30 * 60_000])
    b = bucket(lt, "1h", origin=30 * 60_000)
    assert b[0] == b[1] != b[2]
    assert bucket_start(b[0], "1h", 30 * 60_000) % 3600_000 == 30 * 60_000


def test_dedupe_terakhir_menang():
    r = _rec(np.array([3, 1, 2, 1]))
    r["c"] = [30, 10, 20, 99]
    d = dedupe_sorted(r)
    assert d["t"].tolist() == [1, 2, 3] and d["c"].tolist() == [99, 20, 30]


def test_parse_zip_mikrodetik_dan_header(tmp_path):
    lines = ["open_time,open,high,low,close,volume,close_time,qv,n,tb,tq,ig",
             "1740787200000000,84349.95,84390.05,84324.42,84338.54,14.42,1740787259999999,1,2,3,4,0",
             "1740787260000000,84337.70,84337.70,84269.50,84274.88,9.99,1740787319999999,1,2,3,4,0"]
    p = tmp_path / "x.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("x.csv", "\n".join(lines))
    r = parse_zip(p)
    assert r["t"].tolist() == [1740787200000, 1740787260000]
    assert r["c"][1] == 84274.88


def test_df_to_rec_zona_waktu():
    idx = pd.DatetimeIndex(["2024-03-08 09:30", "2024-03-11 09:30"]).tz_localize("America/New_York")  # sebelum/sesudah DST
    df = pd.DataFrame({"Open": [1, 2], "High": [2, 3], "Low": [0.5, 1.5], "Close": [1.5, 2.5], "Volume": [10, np.nan]}, index=idx)
    r = df_to_rec(df)
    assert (r["lt"] % 86_400_000).tolist() == [9.5 * 3600_000, 9.5 * 3600_000]
    assert (r["lt"] - r["t"]).tolist() == [-5 * 3600_000, -4 * 3600_000]
    assert r["v"].tolist() == [10, 0]
    jk = pd.DataFrame({"Open": [1], "High": [1], "Low": [1], "Close": [1], "Volume": [1]},
                      index=pd.DatetimeIndex(["2024-01-02"]).tz_localize("Asia/Jakarta"))
    rj = df_to_rec(jk)
    assert rj["lt"][0] % 86_400_000 == 0 and rj["lt"][0] - rj["t"][0] == 7 * 3600_000


def test_store_katalog_dan_segmen(tmp_path):
    make_crypto(tmp_path, days=3)
    make_idx(tmp_path)
    s = CandleStore(tmp_path)
    a = s.asset("crypto:TESTUSDT")
    assert set(a["series"]) >= {"1m", "5m", "1h", "1d", "1w", "1M"}
    assert a["series"]["1m"]["native"] and not a["series"]["1h"]["native"]
    i = s.asset("idx:TEST")
    assert set(i["series"]) == {"1d", "1h", "5m", "1w", "1M"}
    assert len(i["series"]["5m"]["segments"]) == 1
    summ = s.summary()
    assert {"crypto", "idx"} <= set(summ)
    # tulis ulang → cache memmap ikut diperbarui
    p = series_path(tmp_path, "crypto", "TESTUSDT", "1d")
    old = read_series(p, mmap=False)
    write_series(p, old[:1])
    import os, time
    os.utime(p, (time.time() + 5, time.time() + 5))
    assert len(s.series("crypto:TESTUSDT", "1d")) == 1
