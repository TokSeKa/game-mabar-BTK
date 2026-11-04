"""Spesifikasi pasar (mata uang, fee, lot) dan daftar aset yang diunduh."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketSpec:
    id: str
    nama: str
    currency: str
    capital: float               # modal awal default
    fee_buy: float               # proporsi, 0.001 = 0.1%
    fee_sell: float
    slippage: float              # untuk order market & stop
    lot: int                     # kelipatan jumlah (IDX: 100 lembar)
    qty_step: float              # langkah jumlah terkecil
    min_notional: float          # nilai transaksi minimal
    origin_ms: int               # awal bucket intraday relatif ke jam lokal (US: 09:30)
    tfs: tuple[str, ...]         # timeframe yang ditawarkan
    satuan: str                  # label satuan jumlah
    catatan_fee: str


CRYPTO_TFS = ("1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M")
STOCK_TFS = ("1m", "5m", "15m", "30m", "1h", "1d", "1w", "1M")

MARKETS: dict[str, MarketSpec] = {
    "crypto": MarketSpec(
        "crypto", "Kripto", "USDT", 10_000, 0.001, 0.001, 0.0002, 1, 1e-6, 5.0, 0, CRYPTO_TFS, "koin",
        "Fee spot standar exchange besar: 0,1% beli dan 0,1% jual.",
    ),
    "idx": MarketSpec(
        "idx", "Saham IDX", "IDR", 100_000_000, 0.0015, 0.0025, 0.0005, 100, 100, 0.0, 0, STOCK_TFS, "lembar",
        "Perkiraan fee broker Indonesia: beli 0,15%, jual 0,25% (sudah termasuk PPh final 0,1%). 1 lot = 100 lembar.",
    ),
    "us": MarketSpec(
        "us", "Saham US", "USD", 10_000, 0.0005, 0.0005, 0.0003, 1, 1, 0.0, 30 * 60_000, STOCK_TFS, "lembar",
        "Perkiraan biaya broker retail: 0,05% per transaksi.",
    ),
    "demo": MarketSpec(
        "demo", "Data contoh", "USD", 10_000, 0.001, 0.001, 0.0002, 1, 1e-6, 1.0, 0, CRYPTO_TFS, "unit",
        "Data buatan (bukan pasar nyata) untuk mencoba game tanpa mengunduh data.",
    ),
}

YAHOO_SUFFIX = {"idx": ".JK", "us": ""}
YAHOO_INTERVALS = ("1d", "1h", "30m", "15m", "5m", "1m")

CRYPTO_NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana", "XRP": "XRP", "DOGE": "Dogecoin",
    "ADA": "Cardano", "TRX": "TRON", "AVAX": "Avalanche", "LINK": "Chainlink", "DOT": "Polkadot",
    "LTC": "Litecoin", "BCH": "Bitcoin Cash", "SHIB": "Shiba Inu", "TON": "Toncoin", "UNI": "Uniswap",
    "NEAR": "NEAR Protocol", "XLM": "Stellar", "ATOM": "Cosmos", "ETC": "Ethereum Classic", "FIL": "Filecoin",
    "APT": "Aptos", "ARB": "Arbitrum", "OP": "Optimism", "SUI": "Sui", "INJ": "Injective", "AAVE": "Aave",
    "ICP": "Internet Computer", "HBAR": "Hedera", "VET": "VeChain", "ALGO": "Algorand", "GRT": "The Graph",
    "SAND": "The Sandbox", "MANA": "Decentraland", "AXS": "Axie Infinity", "THETA": "Theta Network",
    "EOS": "EOS", "XTZ": "Tezos", "EGLD": "MultiversX", "RUNE": "THORChain", "LDO": "Lido DAO",
    "IMX": "Immutable", "CRV": "Curve DAO", "SNX": "Synthetix", "MKR": "Maker", "PEPE": "Pepe",
    "FET": "Fetch.ai", "RENDER": "Render", "WLD": "Worldcoin", "SEI": "Sei", "TIA": "Celestia",
    "JUP": "Jupiter", "STX": "Stacks", "KAVA": "Kava", "ZEC": "Zcash", "DASH": "Dash", "NEO": "NEO",
    "CHZ": "Chiliz", "ENS": "Ethereum Name Service", "GALA": "Gala", "FLOKI": "Floki", "BONK": "Bonk",
    "ORDI": "ORDI", "PENDLE": "Pendle", "MATIC": "Polygon (lama)", "POL": "Polygon", "FTM": "Fantom",
}
CRYPTO_FULL = [f"{s}USDT" for s in CRYPTO_NAMES]
CRYPTO_QUICK = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
CRYPTO_QUICK_SINCE = "2024-07"

IDX_NAMES = {
    "BBCA": "Bank Central Asia", "BBRI": "Bank Rakyat Indonesia", "BMRI": "Bank Mandiri", "BBNI": "Bank Negara Indonesia",
    "BRIS": "Bank Syariah Indonesia", "BBTN": "Bank Tabungan Negara", "ARTO": "Bank Jago", "BTPS": "Bank BTPN Syariah",
    "BJBR": "Bank BJB", "BJTM": "Bank Jatim", "BNGA": "Bank CIMB Niaga", "NISP": "Bank OCBC NISP", "PNBN": "Bank Panin",
    "BDMN": "Bank Danamon", "MEGA": "Bank Mega", "AGRO": "Bank Raya", "BBHI": "Allo Bank", "BBYB": "Bank Neo Commerce",
    "TLKM": "Telkom Indonesia", "EXCL": "XL Axiata", "ISAT": "Indosat Ooredoo Hutchison", "TOWR": "Sarana Menara Nusantara",
    "TBIG": "Tower Bersama", "MTEL": "Dayamitra Telekomunikasi", "ASII": "Astra International", "UNTR": "United Tractors",
    "AUTO": "Astra Otoparts", "SMSM": "Selamat Sempurna", "GJTL": "Gajah Tunggal", "UNVR": "Unilever Indonesia",
    "ICBP": "Indofood CBP", "INDF": "Indofood Sukses Makmur", "MYOR": "Mayora Indah", "ULTJ": "Ultrajaya",
    "ROTI": "Nippon Indosari", "CPIN": "Charoen Pokphand", "JPFA": "Japfa Comfeed", "MAIN": "Malindo Feedmill",
    "KLBF": "Kalbe Farma", "SIDO": "Sido Muncul", "KAEF": "Kimia Farma", "HMSP": "HM Sampoerna", "GGRM": "Gudang Garam",
    "WIIM": "Wismilak", "AMRT": "Sumber Alfaria Trijaya", "MIDI": "Midi Utama", "MAPI": "Mitra Adiperkasa",
    "MAPA": "MAP Aktif", "ACES": "Aspirasi Hidup Indonesia", "ERAA": "Erajaya", "LPPF": "Matahari Department Store",
    "RALS": "Ramayana", "ANTM": "Aneka Tambang", "INCO": "Vale Indonesia", "TINS": "Timah", "MDKA": "Merdeka Copper Gold",
    "MBMA": "Merdeka Battery Materials", "NCKL": "Trimegah Bangun Persada", "AMMN": "Amman Mineral", "BRMS": "Bumi Resources Minerals",
    "PSAB": "J Resources Asia Pasifik", "ADRO": "Alamtri Resources (Adaro)", "ADMR": "Alamtri Minerals", "PTBA": "Bukit Asam",
    "ITMG": "Indo Tambangraya Megah", "HRUM": "Harum Energy", "INDY": "Indika Energy", "BUMI": "Bumi Resources",
    "DOID": "Delta Dunia", "GEMS": "Golden Energy Mines", "BYAN": "Bayan Resources", "MEDC": "Medco Energi",
    "PGAS": "Perusahaan Gas Negara", "ELSA": "Elnusa", "AKRA": "AKR Corporindo", "ENRG": "Energi Mega Persada",
    "RAJA": "Rukun Raharja", "BREN": "Barito Renewables Energy", "PGEO": "Pertamina Geothermal", "BRPT": "Barito Pacific",
    "TPIA": "Chandra Asri", "ESSA": "ESSA Industries", "INKP": "Indah Kiat Pulp & Paper", "TKIM": "Tjiwi Kimia",
    "SMGR": "Semen Indonesia", "INTP": "Indocement", "SMBR": "Semen Baturaja", "JSMR": "Jasa Marga", "WIKA": "Wijaya Karya",
    "PTPP": "PP (Persero)", "ADHI": "Adhi Karya", "WTON": "Wijaya Karya Beton", "BSDE": "Bumi Serpong Damai",
    "CTRA": "Ciputra Development", "PWON": "Pakuwon Jati", "SMRA": "Summarecon Agung", "ASRI": "Alam Sutera",
    "LPKR": "Lippo Karawaci", "PANI": "Pantai Indah Kapuk Dua", "DMAS": "Puradelta Lestari", "AALI": "Astra Agro Lestari",
    "LSIP": "PP London Sumatra", "SSMS": "Sawit Sumbermas", "DSNG": "Dharma Satya Nusantara", "TAPG": "Triputra Agro Persada",
    "TBLA": "Tunas Baru Lampung", "GOTO": "GoTo Gojek Tokopedia", "BUKA": "Bukalapak", "EMTK": "Elang Mahkota Teknologi",
    "SCMA": "Surya Citra Media", "MNCN": "Media Nusantara Citra", "BMTR": "Global Mediacom", "HEAL": "Medikaloka Hermina",
    "MIKA": "Mitra Keluarga", "SILO": "Siloam International", "PRDA": "Prodia", "SRTG": "Saratoga", "CUAN": "Petrindo Jaya Kreasi",
    "SMDR": "Samudera Indonesia", "TMAS": "Temas", "ASSA": "Adi Sarana Armada", "BIRD": "Blue Bird", "GIAA": "Garuda Indonesia",
    "WIFI": "Solusi Sinergi Digital", "DCII": "DCI Indonesia", "CLEO": "Sariguna Primatirta", "AVIA": "Avia Avian",
    "ARNA": "Arwana Citramulia", "MARK": "Mark Dynamics", "IMPC": "Impack Pratama", "ISSP": "Steel Pipe Industry",
    "KRAS": "Krakatau Steel", "MTDL": "Metrodata", "MLPT": "Multipolar Technology", "DNET": "Indoritel",
}
IDX_QUICK = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP", "INDF", "GOTO", "ANTM", "ADRO", "PTBA", "UNTR",
    "CPIN", "KLBF", "MDKA", "INCO", "PGAS", "MEDC", "AMRT", "BRIS", "SMGR", "BREN", "AMMN", "ISAT", "EXCL", "CTRA",
    "MAPI", "ACES",
]

US_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet", "META": "Meta Platforms",
    "TSLA": "Tesla", "BRK-B": "Berkshire Hathaway", "JPM": "JPMorgan Chase", "V": "Visa", "MA": "Mastercard",
    "UNH": "UnitedHealth", "XOM": "Exxon Mobil", "JNJ": "Johnson & Johnson", "PG": "Procter & Gamble", "HD": "Home Depot",
    "AVGO": "Broadcom", "LLY": "Eli Lilly", "COST": "Costco", "PEP": "PepsiCo", "KO": "Coca-Cola", "MRK": "Merck",
    "ABBV": "AbbVie", "CVX": "Chevron", "WMT": "Walmart", "BAC": "Bank of America", "ORCL": "Oracle", "CRM": "Salesforce",
    "ADBE": "Adobe", "NFLX": "Netflix", "AMD": "AMD", "INTC": "Intel", "CSCO": "Cisco", "QCOM": "Qualcomm",
    "TXN": "Texas Instruments", "IBM": "IBM", "MU": "Micron", "AMAT": "Applied Materials", "LRCX": "Lam Research",
    "ASML": "ASML", "TSM": "TSMC", "BABA": "Alibaba", "PDD": "PDD Holdings", "NKE": "Nike", "MCD": "McDonald's",
    "SBUX": "Starbucks", "DIS": "Disney", "BA": "Boeing", "CAT": "Caterpillar", "GE": "GE Aerospace", "HON": "Honeywell",
    "LMT": "Lockheed Martin", "RTX": "RTX", "UPS": "UPS", "F": "Ford", "GM": "General Motors", "T": "AT&T",
    "VZ": "Verizon", "TMUS": "T-Mobile US", "PFE": "Pfizer", "MRNA": "Moderna", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "C": "Citigroup", "WFC": "Wells Fargo", "AXP": "American Express", "PYPL": "PayPal",
    "SHOP": "Shopify", "UBER": "Uber", "ABNB": "Airbnb", "COIN": "Coinbase", "PLTR": "Palantir", "SNOW": "Snowflake",
    "NET": "Cloudflare", "CRWD": "CrowdStrike", "PANW": "Palo Alto Networks", "MSTR": "Strategy (MicroStrategy)",
    "SPY": "SPDR S&P 500 ETF", "QQQ": "Invesco QQQ (Nasdaq-100)", "IWM": "iShares Russell 2000", "DIA": "SPDR Dow Jones ETF",
    "GLD": "SPDR Gold Shares", "SLV": "iShares Silver Trust", "TLT": "iShares 20+ Year Treasury", "XLE": "Energy Select SPDR",
    "XLF": "Financial Select SPDR", "XLK": "Technology Select SPDR", "SMH": "VanEck Semiconductor ETF", "ARKK": "ARK Innovation ETF",
}
US_QUICK = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "XOM", "KO", "NFLX", "AMD", "SPY", "QQQ",
            "GLD", "COIN", "PLTR", "DIS", "BA", "INTC"]


def asset_name(market: str, symbol: str) -> str:
    if market == "crypto":
        base = symbol[:-4] if symbol.endswith("USDT") else symbol
        return CRYPTO_NAMES.get(base, base)
    if market == "idx":
        return IDX_NAMES.get(symbol, symbol)
    if market == "us":
        return US_NAMES.get(symbol, symbol)
    return symbol


@dataclass
class Preset:
    crypto: list[str] = field(default_factory=list)
    crypto_since: str | None = None
    idx: list[str] = field(default_factory=list)
    us: list[str] = field(default_factory=list)


PRESETS = {
    "cepat": Preset(CRYPTO_QUICK, CRYPTO_QUICK_SINCE, IDX_QUICK, US_QUICK),
    "penuh": Preset(CRYPTO_FULL, None, list(IDX_NAMES), list(US_NAMES)),
}
