"""Produk trading selain spot: futures perpetual dan akun margin (termasuk short).

Aturan "nyata" mengikuti cara kerja tempat aslinya (dicek November 2026):

* **Kripto – Futures USDⓈ-M perpetual** (meniru Binance): fee maker 0,02% / taker 0,05% untuk pengguna biasa,
  leverage bertingkat (makin besar posisi, makin kecil leverage maksimal dan makin besar maintenance margin),
  mode margin cross / isolated, funding tiap 8 jam (00:00, 08:00, 16:00 UTC), likuidasi saat margin balance
  turun ke maintenance margin; sisa margin posisi yang dilikuidasi masuk dana asuransi.
* **Saham US – akun margin Reg T** (meniru IBKR Pro Fixed): komisi USD 0,005/lembar (min USD 1, maks 1% nilai),
  SEC fee USD 20,60 per USD 1 juta penjualan (berlaku 4 April 2026), FINRA TAF USD 0,000195/lembar jual
  (maks USD 9,79). Initial margin 50% (daya beli 2×), maintenance 25% long / 30% short, posisi langsung
  dilikuidasi kalau di bawahnya. Bunga margin ±5,12%/tahun (benchmark + 1,5%), biaya pinjam saham mudah
  dipinjam ±0,25%/tahun, dihitung harian /360.
* **Saham IDX – transaksi margin & short selling BEI** (Peraturan II-H, short selling aktif lagi 1 Oktober 2026):
  short hanya untuk Daftar Efek Short Selling (ASII, BBCA, BRPT, BUMI, INDF), jaminan awal 50% atau minimal
  Rp50 juta, margin call di rasio jaminan 135% dan forced buy di 120%, order short wajib di harga ≥ harga
  terakhir (uptick). Margin long: daya beli 2×, margin call di ekuitas 35%, forced sell di 20%.
  Bunga margin 18%/tahun (tarif normal broker), dihitung harian /365. Fee beli 0,15%, jual 0,25%.

Aturan "bebas" membuka short dan futures untuk semua aset (untuk latihan, bukan kondisi nyata).
Angka di sini perkiraan dan bisa berubah sewaktu-waktu; semua bisa diubah lewat konfigurasi sesi.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

INF = float("inf")


@dataclass(frozen=True)
class Tier:
    cap: float      # batas atas nilai posisi (notional) di tier ini
    mmr: float      # maintenance margin rate
    max_lev: int    # leverage maksimal untuk posisi sebesar ini
    cum: float = 0  # "maintenance amount" supaya MM bersambung antar tier


def _tiers(rows: list[tuple[float, float, int]]) -> tuple[Tier, ...]:
    out: list[Tier] = []
    cum, prev_cap, prev_mmr = 0.0, 0.0, None
    for cap, mmr, lev in rows:
        if prev_mmr is not None:
            cum += prev_cap * (mmr - prev_mmr)
        out.append(Tier(cap, mmr, lev, cum))
        prev_cap, prev_mmr = cap, mmr
    return tuple(out)


# Tabel leverage & margin bertingkat (mendekati tabel Binance; angka persisnya sering diubah exchange).
TIERS_MAJOR = _tiers([(300_000, 0.004, 125), (800_000, 0.005, 100), (3_000_000, 0.0065, 75), (12_000_000, 0.01, 50),
                      (70_000_000, 0.02, 25), (100_000_000, 0.025, 20), (230_000_000, 0.05, 10),
                      (480_000_000, 0.1, 5), (600_000_000, 0.125, 4), (800_000_000, 0.25, 2), (INF, 0.5, 1)])
TIERS_LARGE = _tiers([(10_000, 0.005, 75), (100_000, 0.0065, 50), (500_000, 0.01, 25), (1_000_000, 0.02, 20),
                      (3_000_000, 0.025, 10), (10_000_000, 0.05, 5), (20_000_000, 0.1, 4), (50_000_000, 0.125, 2),
                      (INF, 0.5, 1)])
TIERS_ALT = _tiers([(5_000, 0.01, 50), (25_000, 0.015, 25), (100_000, 0.025, 20), (250_000, 0.05, 10),
                    (1_000_000, 0.1, 5), (2_500_000, 0.125, 4), (5_000_000, 0.25, 2), (INF, 0.5, 1)])
TIERS_FLAT = _tiers([(INF, 0.01, 50)])  # futures "bebas" untuk saham: satu tier saja

MAJOR = {"BTC", "ETH"}
LARGE = {"BNB", "SOL", "XRP", "DOGE", "ADA", "TRX", "AVAX", "LINK", "DOT", "LTC", "BCH", "TON", "SHIB", "UNI", "NEAR",
         "XLM", "ATOM", "ETC", "FIL", "APT", "ARB", "OP", "SUI", "AAVE", "PEPE", "POL", "MATIC"}

#: Daftar Efek Short Selling BEI yang berlaku sejak 1 Oktober 2026.
IDX_SHORT = frozenset({"ASII", "BBCA", "BRPT", "BUMI", "INDF"})


@dataclass(frozen=True)
class Product:
    id: str                         # "futures" | "margin"
    nama: str
    kind: str                       # "perp" | "margin"
    fee_buy: float                  # perp: fee taker; saham: fee beli (proporsi nilai)
    fee_sell: float                 # perp: fee taker; saham: fee jual
    maker: float | None = None      # perp: fee maker untuk limit yang menunggu
    max_lev: float = 1.0
    default_lev: float = 1.0
    tiers: tuple[Tier, ...] | None = None
    mmr_long: float = 0.0           # margin: maintenance (ekuitas / nilai posisi) sebelum likuidasi
    mmr_short: float = 0.0
    call_long: float = 0.0          # margin: batas peringatan margin call
    call_short: float = 0.0
    short: bool = True
    short_list: frozenset[str] | None = None   # kalau diisi: hanya simbol ini yang boleh short
    funding: float = 0.0            # perp: funding rate default per periode
    funding_hours: int = 8
    interest_apr: float = 0.0       # bunga dana pinjaman (posisi long dengan margin)
    borrow_apr: float = 0.0         # biaya pinjam saham (posisi short)
    day_count: int = 365
    insurance: bool = False         # perp: sisa margin posisi yang dilikuidasi hangus
    min_short_equity: float = 0.0   # IDX: jaminan awal minimal Rp50 juta
    uptick: bool = False            # IDX: order short di harga >= harga terakhir
    per_share: tuple[float, float, float] | None = None   # (per lembar, minimal, maks % nilai)
    sec_fee: float = 0.0            # proporsi nilai penjualan
    taf: tuple[float, float] | None = None                # (per lembar jual, maksimal per transaksi)
    modes: tuple[str, ...] = ("cross",)
    catatan: tuple[str, ...] = field(default_factory=tuple)

    def short_ok(self, symbol: str) -> bool:
        if not self.short:
            return False
        return self.short_list is None or symbol in self.short_list

    def public(self, symbol: str | None = None) -> dict[str, Any]:
        tiers = None
        if self.tiers:
            tiers = [{"cap": (None if t.cap == INF else t.cap), "mmr": t.mmr, "max_lev": t.max_lev} for t in self.tiers]
        return {
            "id": self.id, "nama": self.nama, "kind": self.kind, "fee_beli": self.fee_buy, "fee_jual": self.fee_sell,
            "maker": self.maker, "max_lev": self.max_lev, "default_lev": self.default_lev, "tiers": tiers,
            "mmr_long": self.mmr_long, "mmr_short": self.mmr_short, "call_long": self.call_long,
            "call_short": self.call_short, "short": self.short,
            "short_list": sorted(self.short_list) if self.short_list is not None else None,
            "short_ok": self.short_ok(symbol) if symbol else None,
            "funding": self.funding, "funding_hours": self.funding_hours, "interest_apr": self.interest_apr,
            "borrow_apr": self.borrow_apr, "day_count": self.day_count, "insurance": self.insurance,
            "min_short_equity": self.min_short_equity, "uptick": self.uptick, "per_share": self.per_share,
            "sec_fee": self.sec_fee, "taf": self.taf, "modes": list(self.modes), "catatan": list(self.catatan),
        }


CRYPTO_PERP = Product(
    "futures", "Futures USDⓈ-M (perpetual)", "perp", fee_buy=0.0005, fee_sell=0.0005, maker=0.0002,
    max_lev=125, default_lev=10, tiers=TIERS_ALT, funding=0.0001, funding_hours=8, insurance=True,
    modes=("cross", "isolated"),
    catatan=(
        "Fee pengguna biasa: maker 0,02% (limit yang menunggu), taker 0,05% (market, stop, limit yang langsung terisi).",
        "Funding tiap 8 jam (00:00, 08:00, 16:00 UTC): funding positif → long membayar short. Memakai data funding asli "
        "Binance kalau sudah diunduh, kalau belum 0,01% per 8 jam.",
        "Likuidasi saat margin balance ≤ maintenance margin. Sisa margin posisi itu hangus (dana asuransi), "
        "saldo tidak pernah minus.",
        "Harga acuan (mark) memakai harga candle spot; harga perpetual asli biasanya selisih tipis.",
    ),
)

US_MARGIN = Product(
    "margin", "Akun margin + short (Reg T)", "margin", fee_buy=0.0, fee_sell=0.0, max_lev=2, default_lev=2,
    mmr_long=0.25, mmr_short=0.30, call_long=0.30, call_short=0.35, short=True,
    interest_apr=0.0512, borrow_apr=0.0025, day_count=360, per_share=(0.005, 1.0, 0.01),
    sec_fee=20.60e-6, taf=(0.000195, 9.79),
    catatan=(
        "Komisi USD 0,005/lembar (min USD 1, maks 1% nilai) + SEC fee 0,00206% dan FINRA TAF USD 0,000195/lembar saat menjual.",
        "Daya beli 2× (initial margin 50%). Maintenance 25% untuk long, 30% untuk short; di bawahnya posisi dilikuidasi paksa.",
        "Bunga margin ±5,12%/tahun atas dana pinjaman; biaya pinjam saham ±0,25%/tahun atas nilai short. Dihitung harian /360.",
        "Ekuitas bisa minus kalau harga melompat jauh melewati batas likuidasi (utang ke broker).",
    ),
)

IDX_MARGIN = Product(
    "margin", "Margin + short selling (BEI)", "margin", fee_buy=0.0015, fee_sell=0.0025, max_lev=2, default_lev=2,
    mmr_long=0.20, mmr_short=0.20, call_long=0.35, call_short=0.35, short=True, short_list=IDX_SHORT,
    interest_apr=0.18, borrow_apr=0.18, day_count=365, min_short_equity=50_000_000, uptick=True,
    catatan=(
        "Short hanya untuk Daftar Efek Short Selling BEI (sejak 1 Okt 2026): ASII, BBCA, BRPT, BUMI, INDF.",
        "Jaminan awal short 50% nilai transaksi atau minimal Rp50 juta. Margin call di rasio jaminan 135%, "
        "forced buy di 120%.",
        "Order short wajib limit di harga ≥ harga terakhir (uptick rule). Short lewat market/stop ditolak.",
        "Margin long: daya beli 2×, margin call di ekuitas 35%, forced sell di 20% (perkiraan aturan umum broker).",
        "Bunga 18%/tahun (tarif normal) atas dana/saham pinjaman, dihitung harian termasuk akhir pekan.",
        "Fee beli 0,15%, jual 0,25% (termasuk PPh final 0,1%).",
    ),
)


def _stock_perp(currency_note: str) -> Product:
    return replace(CRYPTO_PERP, nama="Futures (aturan bebas)", tiers=TIERS_FLAT, max_lev=50, insurance=True,
                   catatan=("Saham tidak punya futures per emiten seperti ini; produk ini hanya untuk latihan.",
                            "Fee maker 0,02% / taker 0,05%, funding 0,01% per 8 jam, maintenance margin 1%, "
                            f"leverage maks 50×. {currency_note}"))


def products(market: str, aturan: str = "nyata") -> dict[str, Product]:
    """Produk selain spot yang tersedia untuk sebuah pasar."""
    bebas = aturan == "bebas"
    if market in ("crypto", "demo"):
        return {"futures": CRYPTO_PERP}
    if market == "us":
        out = {"margin": US_MARGIN}
        if bebas:
            out["futures"] = _stock_perp("")
        return out
    if market == "idx":
        if bebas:
            m = replace(IDX_MARGIN, nama="Margin + short (aturan bebas)", short_list=None, min_short_equity=0,
                        uptick=False, catatan=("Aturan bebas: short boleh untuk semua saham, tanpa uptick dan tanpa "
                                               "jaminan minimal Rp50 juta.",) + IDX_MARGIN.catatan[3:])
            return {"margin": m, "futures": _stock_perp("")}
        return {"margin": IDX_MARGIN}
    return {}


def product_for(market: str, pid: str, symbol: str, aturan: str = "nyata") -> Product | None:
    p = products(market, aturan).get(pid)
    if p is None:
        return None
    if p.kind == "perp" and market in ("crypto", "demo"):
        base = symbol[:-4] if symbol.endswith("USDT") else symbol
        tiers = TIERS_MAJOR if base in MAJOR else TIERS_LARGE if base in LARGE else TIERS_ALT
        p = replace(p, tiers=tiers, max_lev=tiers[0].max_lev)
    return p


def catalog(aturan: str = "nyata") -> dict[str, Any]:
    """Ringkasan produk per pasar untuk layar persiapan."""
    out: dict[str, Any] = {}
    for m in ("crypto", "idx", "us", "demo"):
        out[m] = {pid: p.public() for pid, p in products(m, aturan).items()}
    return out
