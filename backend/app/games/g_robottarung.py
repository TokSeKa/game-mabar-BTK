"""Robot Tarung: rakit robot dari komponen lalu adu di arena (gaya pertarungan robot TV, versi game sendiri).

Fisika 2D dilihat dari atas, 20 langkah per detik, dihitung server (adil, bisa diulang dari seed + aksi). Tampilan di
browser 2.5D: robot dirakit dari komponennya dan digambar 3D, terlempar/terbalik digambar sebagai animasi.

Alur: garasi (rakit robot dalam batas berat) → hitung mundur → tarung → (ronde berikut dengan robot yang sama) → selesai.
Kendali: manusia langsung (keyboard / joystick HP) atau bot berkode, boleh dicampur.

Koordinat: meter, x ke kanan, y ke bawah. Arah robot dalam radian dari sumbu x positif, searah jarum jam (karena y ke
bawah). "belok" positif = belok kanan.
"""

from __future__ import annotations

import math
from typing import Any

from .base import ActionError, Game, Setting, rng

DT = 0.05                 # detik per langkah (20 langkah per detik)
TPS = 20
SISI = ("depan", "kanan", "belakang", "kiri")
HITUNG_MUNDUR = 3.0
KO_DETIK = 10.0
LUBANG_BUKA = 45.0        # lubang baru terbuka setelah sekian detik tarung

KATALOG: dict[str, Any] = {
    "sasis": {
        "kotak": {"nama": "Kotak", "berat": 12, "rangka": 100, "r": 0.55,
                  "ket": "Seimbang, kuat, dan mudah dipasangi senjata apa saja."},
        "baji": {"nama": "Baji", "berat": 13, "rangka": 90, "r": 0.55,
                 "ket": "Ujung depan rendah: menyelip ke bawah lawan sehingga rodanya terangkat dan gampang didorong."},
        "kubah": {"nama": "Kubah", "berat": 15, "rangka": 110, "r": 0.6,
                  "ket": "Pukulan dari samping meleset sebagian (−30%) dan lebih sulit dibalik."},
    },
    "penggerak": {
        "ringan": {"nama": "Ringan", "berat": 8, "daya": 1.0, "vmaks": 3.4, "putar": 3.8, "ket": "Gesit dan hemat energi, tapi kalah adu dorong."},
        "sedang": {"nama": "Sedang", "berat": 14, "daya": 1.6, "vmaks": 3.9, "putar": 3.5, "ket": "Pilihan aman."},
        "kuat": {"nama": "Kuat", "berat": 22, "daya": 2.4, "vmaks": 4.3, "putar": 3.1, "ket": "Raja adu dorong, boros energi."},
    },
    "baterai": {
        "kecil": {"nama": "Kecil", "berat": 6, "energi": 100},
        "sedang": {"nama": "Sedang", "berat": 10, "energi": 170},
        "besar": {"nama": "Besar", "berat": 15, "energi": 250},
    },
    "senjata": {
        "tidak": {"nama": "Tanpa senjata (penyeruduk)", "berat": 0,
                  "ket": "Pelat penyeruduk di depan: tabrakan depan 2× lebih sakit untuk lawan, ½ untuk dirimu. Berat sisa untuk armor dan roda."},
        "spinner_h": {"nama": "Spinner horizontal", "berat": 26,
                      "ket": "Bilah berputar mendatar. Pukulan terkuat, tapi butuh waktu memutar dan boros energi."},
        "spinner_v": {"nama": "Drum vertikal", "berat": 22,
                      "ket": "Drum berputar tegak di depan. Melontarkan lawan ke atas, kadang sampai terbalik. Tetap bekerja (70%) saat robotmu terbalik."},
        "flipper": {"nama": "Flipper", "berat": 18,
                    "ket": "Pelontar di depan: lempar lawan dan balikkan badan. Bisa dipakai untuk membalikkan diri sendiri."},
        "palu": {"nama": "Palu / kapak", "berat": 16,
                 "ket": "Menghantam dari atas, menembus armor sebagian. Dua kali lebih sakit untuk lawan yang terbalik."},
        "gergaji": {"nama": "Gergaji", "berat": 12,
                    "ket": "Menggerus terus selama menempel. Ringan dan menembus armor sedikit demi sedikit."},
    },
    "tambahan": {"pembalik": {"nama": "Pembalik badan", "berat": 5, "ket": "Lengan untuk berdiri lagi kalau terbalik."}},
    "armor": {"berat_per_tingkat": 2, "hp_per_tingkat": 15, "maks": 8},
}

# Angka-angka senjata (disetel lewat simulasi turnamen bot; lihat tes keseimbangan).
SENJATA = {
    "spinner_h": {"dmg": 36, "busur": 70, "jangkau": 0.28, "naik": 2.8, "biaya_naik": 4.0, "biaya_tahan": 1.0,
                  "sisa": 0.45, "dorong": 3.6, "pantul": 1.8, "putar": 5.0, "jeda": 0.4},
    "spinner_v": {"dmg": 22, "busur": 45, "jangkau": 0.22, "naik": 2.5, "biaya_naik": 3.5, "biaya_tahan": 0.9,
                  "sisa": 0.35, "dorong": 2.4, "pantul": 1.0, "terbang": 0.55, "balik": 0.25, "jeda": 0.4},
    "flipper": {"dmg": 7, "busur": 38, "jangkau": 0.35, "jeda": 2.4, "biaya": 6.0, "terbang": 0.9, "laju": 2.9, "balik": 0.55},
    "palu": {"dmg": 16, "busur": 42, "jangkau": 0.5, "jeda": 2.2, "biaya": 4.0, "tembus": 0.5, "kali_terbalik": 2.0},
    "gergaji": {"dmg": 0.8, "busur": 42, "jangkau": 0.16, "biaya_tahan": 3.0, "tembus": 0.3},
}
KOMPONEN_HP = {"motor": 40, "senjata": 50, "baterai": 40}

CONTOH_RAKITAN: list[dict[str, Any]] = [
    {"nama": "Drum Merah", "sasis": "kotak", "penggerak": "sedang", "baterai": "sedang", "senjata": "spinner_v",
     "pembalik": False, "armor": {"depan": 4, "kanan": 2, "belakang": 2, "kiri": 2}},
    {"nama": "Gasing Maut", "sasis": "kubah", "penggerak": "sedang", "baterai": "besar", "senjata": "spinner_h",
     "pembalik": False, "armor": {"depan": 2, "kanan": 2, "belakang": 1, "kiri": 2}},
    {"nama": "Lempar Lembing", "sasis": "baji", "penggerak": "kuat", "baterai": "sedang", "senjata": "flipper",
     "pembalik": False, "armor": {"depan": 3, "kanan": 2, "belakang": 1, "kiri": 2}},
    {"nama": "Godam", "sasis": "kotak", "penggerak": "sedang", "baterai": "sedang", "senjata": "palu",
     "pembalik": True, "armor": {"depan": 4, "kanan": 3, "belakang": 2, "kiri": 3}},
    {"nama": "Buldoser", "sasis": "baji", "penggerak": "kuat", "baterai": "besar", "senjata": "tidak",
     "pembalik": True, "armor": {"depan": 7, "kanan": 4, "belakang": 3, "kiri": 4}},
    {"nama": "Parut Kelapa", "sasis": "baji", "penggerak": "kuat", "baterai": "sedang", "senjata": "gergaji",
     "pembalik": True, "armor": {"depan": 5, "kanan": 3, "belakang": 2, "kiri": 3}},
]


def berat(d: dict[str, Any]) -> int:
    k = KATALOG
    a = d["armor"]
    return (k["sasis"][d["sasis"]]["berat"] + k["penggerak"][d["penggerak"]]["berat"] + k["baterai"][d["baterai"]]["berat"]
            + k["senjata"][d["senjata"]]["berat"] + (k["tambahan"]["pembalik"]["berat"] if d["pembalik"] else 0)
            + sum(a[x] for x in SISI) * k["armor"]["berat_per_tingkat"])


def bersihkan_rakitan(d: Any, berat_maks: int) -> dict[str, Any]:
    if not isinstance(d, dict):
        raise ActionError("rakitan harus berupa dict (lihat contoh di panduan)")
    out: dict[str, Any] = {}
    for key in ("sasis", "penggerak", "baterai", "senjata"):
        v = str(d.get(key, "")).strip().lower()
        if v not in KATALOG[key]:
            raise ActionError(f"{key} harus salah satu dari: {', '.join(KATALOG[key])}")
        out[key] = v
    out["pembalik"] = bool(d.get("pembalik", False))
    arm = d.get("armor") or {}
    if not isinstance(arm, dict):
        raise ActionError('armor harus dict, misalnya {"depan": 3, "kanan": 2, "belakang": 1, "kiri": 2}')
    mx = KATALOG["armor"]["maks"]
    out["armor"] = {}
    for sd in SISI:
        try:
            n = int(arm.get(sd, 0))
        except (TypeError, ValueError):
            raise ActionError(f"armor {sd} harus angka 0–{mx}") from None
        if not 0 <= n <= mx:
            raise ActionError(f"armor {sd} harus 0–{mx}")
        out["armor"][sd] = n
    nama = str(d.get("nama") or "Robot").strip()[:16] or "Robot"
    out["nama"] = nama
    b = berat(out)
    if b > berat_maks:
        raise ActionError(f"robotmu {b} kg, melebihi batas {berat_maks} kg")
    return out


def pas_berat(d: dict[str, Any], berat_maks: int) -> dict[str, Any]:
    """Sesuaikan rakitan supaya muat di batas berat: kurangi armor (sisakan 1 tiap sisi), lalu baterai & penggerak,
    lalu armor sisa, pembalik, dan terakhir senjata."""
    d = {**d, "armor": dict(d["armor"])}
    turun = {"baterai": ["besar", "sedang", "kecil"], "penggerak": ["kuat", "sedang", "ringan"]}
    for _ in range(80):
        if berat(d) <= berat_maks:
            return d
        sd = max(SISI, key=lambda x: d["armor"][x])
        if d["armor"][sd] > 1:
            d["armor"][sd] -= 1
            continue
        for key in ("baterai", "penggerak"):
            urut = turun[key]
            k = urut.index(d[key])
            if k < len(urut) - 1:
                d[key] = urut[k + 1]
                break
        else:
            if d["armor"][sd] > 0:
                d["armor"][sd] -= 1
            elif d["pembalik"]:
                d["pembalik"] = False
            elif d["senjata"] != "tidak":
                d["senjata"] = "tidak"
            elif d["sasis"] != "kotak":
                d["sasis"] = "kotak"
            else:
                break
    return d


def rakitan_bawaan(berat_maks: int) -> dict[str, Any]:
    return pas_berat(CONTOH_RAKITAN[0], berat_maks)


def sudut_rel(dx: float, dy: float, a: float) -> float:
    """Sudut (radian, -pi..pi) arah (dx, dy) relatif terhadap arah hadap a. Positif = di kanan."""
    d = math.atan2(dy, dx) - a
    while d > math.pi:
        d -= 2 * math.pi
    while d < -math.pi:
        d += 2 * math.pi
    return d


def sisi_dari(sudut: float) -> str:
    deg = math.degrees(sudut)
    if -45 <= deg <= 45:
        return "depan"
    if 45 < deg <= 135:
        return "kanan"
    if -135 <= deg < -45:
        return "kiri"
    return "belakang"


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


class RobotTarung(Game):
    id = "robottarung"
    nama = "Robot Tarung"
    ringkas = "Rakit robot tempurmu dari komponen (sasis, roda, baterai, armor, senjata) lalu adu di arena 3D. Kendalikan sendiri atau program botnya."
    kategori = "tick"
    min_pemain = 2
    max_pemain = 4
    hint_aksi = '{"rakit": {...}} di garasi; {"maju": -1..1, "belok": -1..1, "senjata": bool, "balik": bool} saat tarung'
    timer = 30
    jeda_pada, jeda_hasil = ("ronde_selesai",), 8
    label_skor = "Poin"
    max_frames = 1500
    bot_langkah = 3000
    settings = [
        Setting("durasi", "Lama satu ronde (detik)", "int", 120, 45, 300),
        Setting("ronde", "Jumlah ronde", "int", 1, 1, 5),
        Setting("berat_maks", "Batas berat robot (kg)", "int", 100, 60, 160, grup="aturan",
                ket="Kelas berat. Semua komponen + armor harus muat di batas ini."),
        Setting("waktu_garasi", "Waktu merakit di garasi (detik)", "int", 120, 20, 600,
                ket="Yang belum siap saat waktu habis memakai rakitan bawaan."),
        Setting("arena", "Ukuran arena", "pilihan", "otomatis",
                pilihan=[["otomatis", "Otomatis (14 m untuk 2 robot, 17 m untuk 3–4)"], ["kecil", "Kecil 12 m"],
                         ["sedang", "Sedang 15 m"], ["besar", "Besar 18 m"]], grup="aturan"),
        Setting("lubang", "Lubang di pojok arena", "bool", True, grup="kejutan",
                ket=f"Terbuka setelah {int(LUBANG_BUKA)} detik. Robot yang masuk lubang langsung kalah (KO)."),
        Setting("gergaji_lantai", "Gergaji lantai", "bool", True, grup="kejutan"),
        Setting("palu_arena", "Palu arena", "bool", True, grup="kejutan", ket="Menghantam setiap 5 detik di dekat dinding bawah."),
        Setting("dinding_duri", "Dinding berduri", "bool", False, grup="kejutan", ket="Menabrak dinding 2,5× lebih sakit."),
        Setting("kerusakan", "Tingkat kerusakan", "pilihan", "normal", grup="aturan",
                pilihan=[["ringan", "Ringan (×0,7, ronde lebih panjang)"], ["normal", "Normal"], ["brutal", "Brutal (×1,5)"]]),
    ]
    presets = [
        {"id": "brutal", "nama": "Brutal", "ket": "Kerusakan ×1,5 dan dinding berduri.",
         "nilai": {"kerusakan": "brutal", "dinding_duri": True}},
        {"id": "murni", "nama": "Arena Polos", "ket": "Tanpa jebakan sama sekali: murni adu robot.",
         "nilai": {"lubang": False, "gergaji_lantai": False, "palu_arena": False}},
        {"id": "ringan", "nama": "Kelas Ringan", "ket": "Batas berat 70 kg, arena kecil.", "nilai": {"berat_maks": 70, "arena": "kecil"}},
    ]
    aturan = """
- **Garasi**: rakit robotmu dalam batas berat (default 100 kg): sasis (kotak / baji / kubah), penggerak, baterai, armor
  per sisi (depan, kanan, belakang, kiri), senjata, dan pembalik badan. Semua ada tarik-ulurnya: armor tebal = berat,
  spinner besar = kuat tapi boros energi. Rakitan bisa disimpan di perangkatmu untuk dipakai lagi.
- **Kendali**: W/S atau ↑/↓ maju-mundur, A/D atau ←/→ belok, **Spasi** = senjata (spinner/gergaji: nyala-mati; flipper/palu:
  tekan untuk memukul), **E** = membalikkan badan. Di HP: joystick kiri + tombol di kanan. Atau pakai bot berkode.
- **Kerusakan per komponen**: pukulan mengenai armor di sisi yang terkena. Kalau armor sisi itu habis, yang rusak bagian
  dalamnya: depan → senjata, kanan/kiri → motor roda kanan/kiri (robot jadi berputar-putar), belakang → baterai. Rangka
  habis = hancur.
- **Senjata**: spinner horizontal (pukulan terkuat, perlu waktu memutar), drum vertikal (melontarkan lawan, kadang sampai
  terbalik), flipper (melempar dan membalikkan lawan), palu (menembus armor, 2× untuk lawan terbalik), gergaji (menggerus
  terus), atau tanpa senjata (baji pendorong). Sasis baji menyelip ke bawah lawan sehingga lawan mudah didorong.
- **Terbalik**: robot masih bisa jalan pelan, tapi senjatanya mati (kecuali drum vertikal, tetap 70%). Tekan E kalau punya
  pembalik badan atau flipper.
- **Jebakan**: lubang di pojok (terbuka setelah 45 detik; masuk = KO), gergaji lantai, palu arena, dinding berduri (opsi).
- **KO**: rangka hancur, masuk lubang, atau tidak bisa bergerak 10 detik (motor dua-duanya rusak / energi habis).
  Baterai rusak membuat robot pincang (tenaga tinggal 25%).
  Kalau waktu habis, **juri** menilai: kerusakan yang diberikan 50%, agresi 25%, kontrol (melempar, menyelip, mendorong ke
  jebakan) 25%.
- **Poin**: menang ronde +10, KO lawan +3, dan +1 untuk setiap 10 kerusakan yang diberikan.
"""
    format_aksi = """Di garasi: `{"rakit": {"nama": "Drum Merah", "sasis": "kotak", "penggerak": "sedang", "baterai": "sedang",
"senjata": "spinner_v", "pembalik": False, "armor": {"depan": 4, "kanan": 2, "belakang": 2, "kiri": 2}}}`.
Saat tarung: `{"maju": 1.0, "belok": -0.5, "senjata": True, "balik": False}` (semua opsional; yang tidak dikirim tetap
seperti sebelumnya). `None` = kendali tidak berubah. `maju`/`belok` antara -1 dan 1 (belok positif = ke kanan)."""
    format_info = """```
{ "fase": "garasi" | "hitung" | "tarung", "ronde": 1, "ronde_total": 1, "arena": 14.0, "sisa": 87.5 (detik),
  "berat_maks": 100, "siap": {"Budi": True, ...} (garasi), "desain_saya": {...} (garasi),
  "jebakan": [{"jenis": "lubang" | "gergaji" | "palu", "x": .., "y": .., "r": ..}, ...],
  "robot": {"Budi": {"x": 3.1, "y": 7.0, "a": 12.5 (derajat), "v": 2.1, "hidup": True, "ko": None,
                     "terbalik": False, "udara": 0.0, "energi": 140.2, "energi_maks": 170, "rpm": 0.8, "siap": True,
                     "rangka": 86, "armor": {"depan": 36, ...}, "motor": [40, 40], "senjata_hp": 50, "baterai_hp": 40,
                     "desain": {...}, ...}, ...} }
```"""
    lib_docs = [
        {"nama": "saya", "jenis": "fungsi", "tanda": "saya()", "ket": "Data robotmu (sama dengan info()['robot'][nama_saya()]) ditambah x, y, a (derajat)."},
        {"nama": "lawan", "jenis": "fungsi", "tanda": "lawan()", "ket": "Daftar robot lawan yang masih hidup (dict, dengan kunci 'nama')."},
        {"nama": "lawan_terdekat", "jenis": "fungsi", "tanda": "lawan_terdekat()", "ket": "Robot lawan terdekat yang masih hidup, atau None."},
        {"nama": "sudut_ke", "jenis": "fungsi", "tanda": "sudut_ke(x, y)", "ket": "Sudut (derajat, -180..180) titik itu relatif ke arah hadapmu. Positif = di kanan."},
        {"nama": "jarak_ke", "jenis": "fungsi", "tanda": "jarak_ke(x, y)", "ket": "Jarak (meter) dari pusat robotmu."},
        {"nama": "kejar", "jenis": "fungsi", "tanda": "kejar(x, y)", "ket": "Kendali {'maju', 'belok'} untuk menuju titik itu (belok dulu kalau sudutnya besar)."},
        {"nama": "kabur", "jenis": "fungsi", "tanda": "kabur(x, y)", "ket": "Kendali untuk mundur menjauhi titik itu sambil tetap menghadapnya (berhenti mundur kalau di belakang ada dinding/jebakan)."},
        {"nama": "kena_senjata", "jenis": "fungsi", "tanda": "kena_senjata(nama)", "ket": "True kalau robot itu sedang dalam jangkauan senjatamu (jarak dan sudutnya pas)."},
        {"nama": "bahaya_di", "jenis": "fungsi", "tanda": "bahaya_di(x, y)", "ket": "True kalau titik itu di dalam/dekat lubang atau gergaji lantai, atau terlalu dekat dinding."},
        {"nama": "jebakan", "jenis": "fungsi", "tanda": "jebakan()", "ket": "Daftar jebakan arena: [{'jenis', 'x', 'y', 'r'}]."},
        {"nama": "contoh_rakitan", "jenis": "fungsi", "tanda": "contoh_rakitan(i)", "ket": "Rakitan contoh nomor i (0–5), sudah disesuaikan dengan batas berat room. Boleh dimodifikasi."},
        {"nama": "pas_berat", "jenis": "fungsi", "tanda": "pas_berat(rakitan)", "ket": "Kurangi armor/baterai/roda (senjata paling akhir) sampai rakitan muat di batas berat room."},
        {"nama": "berat_rakitan", "jenis": "fungsi", "tanda": "berat_rakitan(rakitan)", "ket": "Berat (kg) sebuah rakitan."},
    ]
    templates = [
        {"id": "drum", "nama": "Drum Pemburu", "ket": "Drum vertikal: putar senjata, kejar lawan, hantam dari depan, mundur sebentar setelah memukul.", "kode": '''def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(0)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0, "senjata": False}
    k = kejar(l["x"], l["y"])
    if s["rpm"] < 0.6 and jarak_ke(l["x"], l["y"]) < 2.5:
        k = kabur(l["x"], l["y"])
    k["senjata"] = True
    k["balik"] = s["terbalik"]
    return k
'''},
        {"id": "gasing", "nama": "Gasing Sabar", "ket": "Spinner horizontal: putar sampai penuh dulu sambil menghindar, baru menyerang.", "kode": '''def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(1)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0, "senjata": True}
    d = jarak_ke(l["x"], l["y"])
    if s["rpm"] >= 0.85:
        k = kejar(l["x"], l["y"])
    elif d < 3.5:
        k = kabur(l["x"], l["y"])
    else:
        k = {"maju": 0.2, "belok": 0.6}
    k["senjata"] = s["energi"] > 8
    return k
'''},
        {"id": "pelempar", "nama": "Pelempar", "ket": "Flipper + baji: menyelip ke depan lawan, lempar saat dalam jangkauan, lalu dorong ke lubang.", "kode": '''def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(2)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    k = kejar(l["x"], l["y"])
    k["senjata"] = kena_senjata(l["nama"]) and s["siap"]
    k["balik"] = s["terbalik"]
    # lawan terbalik: dorong ke lubang kalau ada
    if l["terbalik"]:
        for j in jebakan():
            if j["jenis"] == "lubang" and jarak_ke(l["x"], l["y"]) < 1.5:
                k["maju"] = 1
    return k
'''},
        {"id": "godam", "nama": "Godam", "ket": "Palu: dekati lawan dengan armor tebal, pukul tiap kali siap, incar lawan yang terbalik.", "kode": '''def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(3)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    k = kejar(l["x"], l["y"])
    if jarak_ke(l["x"], l["y"]) < 1.6 and abs(sudut_ke(l["x"], l["y"])) < 30:
        k["maju"] = 0.15
    k["senjata"] = kena_senjata(l["nama"]) and s["siap"]
    k["balik"] = s["terbalik"]
    return k
'''},
        {"id": "buldoser", "nama": "Buldoser", "ket": "Tanpa senjata: armor tebal + roda kuat, mendorong lawan ke dinding, gergaji, dan lubang.", "kode": '''def aksi():
    if info()["fase"] == "garasi":
        return {"rakit": contoh_rakitan(4)}
    s = saya()
    l = lawan_terdekat()
    if l == None:
        return {"maju": 0, "belok": 0}
    tx = l["x"]
    ty = l["y"]
    # dekati dari sisi yang membuat lawan terdorong ke jebakan terdekat
    for j in jebakan():
        if j["jenis"] == "lubang":
            dx = l["x"] - j["x"]
            dy = l["y"] - j["y"]
            n = (dx * dx + dy * dy) ** 0.5
            if n > 0 and jarak_ke(l["x"], l["y"]) > 1.8:
                tx = l["x"] + dx / n * 0.8
                ty = l["y"] + dy / n * 0.8
    k = kejar(tx, ty)
    k["balik"] = s["terbalik"]
    return k
'''},
    ]

    # ------------------------------------------------------------ meta & util
    def meta(self) -> dict[str, Any]:
        m = super().meta()
        m["katalog"] = KATALOG
        m["contoh_rakitan"] = CONTOH_RAKITAN
        m["senjata_info"] = {k: {"busur": v["busur"], "jangkau": v["jangkau"]} for k, v in SENJATA.items()}
        return m

    def detak(self, cfg):
        return DT

    def _arena(self, cfg, n):
        a = cfg["arena"]
        if a == "otomatis":
            return 14.0 if n <= 2 else 17.0
        return {"kecil": 12.0, "sedang": 15.0, "besar": 18.0}[a]

    def _kali(self, s):
        return 0.55 * {"ringan": 0.7, "normal": 1.0, "brutal": 1.5}[s["cfg"]["kerusakan"]]

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "ronde": 1, "skor": [0] * n, "riwayat": [],
             "fase": "garasi", "t": 0, "fase_t": 0, "desain": [None] * n, "N": self._arena(cfg, n),
             "rusak_total": [0.0] * n, "robot": [], "jebakan": []}
        return s

    def _hazards(self, s):
        c, N = s["cfg"], s["N"]
        hz = []
        if c["lubang"]:
            k = rng(s, "lubang", s["ronde"]).randrange(4)
            off = 1.9
            px = off if k in (0, 3) else N - off
            py = off if k in (0, 1) else N - off
            hz.append({"jenis": "lubang", "x": px, "y": py, "r": 0.85, "buka": LUBANG_BUKA})
        if c["gergaji_lantai"]:
            hz.append({"jenis": "gergaji", "x": round(N * 0.38, 3), "y": 2.0, "r": 0.55})
            hz.append({"jenis": "gergaji", "x": round(N * 0.62, 3), "y": 2.0, "r": 0.55})
        if c["palu_arena"]:
            hz.append({"jenis": "palu", "x": N / 2, "y": N - 1.6, "r": 1.0})
        return hz

    def _make_robot(self, s, p, x, y, a):
        d = s["desain"][p]
        K = KATALOG
        sas = K["sasis"][d["sasis"]]
        hp_tk = K["armor"]["hp_per_tingkat"]
        return {"x": x, "y": y, "a": a, "vx": 0.0, "vy": 0.0, "w": 0.0,
                "massa": float(berat(d)), "r": sas["r"], "rangka": float(sas["rangka"]), "rangka_maks": sas["rangka"],
                "armor": {sd: float(d["armor"][sd] * hp_tk) for sd in SISI},
                "armor_maks": {sd: d["armor"][sd] * hp_tk for sd in SISI},
                "motor": [float(KOMPONEN_HP["motor"])] * 2, "senjata_hp": float(KOMPONEN_HP["senjata"]),
                "baterai_hp": float(KOMPONEN_HP["baterai"]),
                "energi": float(K["baterai"][d["baterai"]]["energi"]), "energi_maks": K["baterai"][d["baterai"]]["energi"],
                "rpm": 0.0, "cd": 0.0, "hit_cd": 0.0, "kontrol": [0.0, 0.0, False, False], "senjata_prev": False,
                "terbalik": False, "udara": 0.0, "udara_total": 0.0, "akan_balik": False, "angkat": 0.0,
                "membalik": 0.0, "diam": 0.0, "hidup": True, "ko": None, "pemukul": None, "pemukul_t": -999,
                "rusak": 0.0, "agresi": 0.0, "kontrol_poin": 0.0, "gergaji_lantai_cd": 0.0}

    def _start_round(self, s):
        n, N = len(s["names"]), s["N"]
        s["jebakan"] = self._hazards(s)
        s["robot"] = []
        jit = rng(s, "posisi", s["ronde"])
        for p in range(n):
            if n == 2:
                x, y, a = (N * 0.22, N / 2, 0.0) if p == 0 else (N * 0.78, N / 2, math.pi)
            else:
                ang = 2 * math.pi * p / n + math.pi
                x, y = N / 2 + N * 0.32 * math.cos(ang), N / 2 + N * 0.32 * math.sin(ang)
                a = math.atan2(N / 2 - y, N / 2 - x)
            # sedikit variasi posisi & arah awal (dari seed) supaya tiap ronde tidak sama persis
            x, y = x + jit.uniform(-0.6, 0.6), y + jit.uniform(-1.2, 1.2)
            a += math.radians(jit.uniform(-20, 20))
            s["robot"].append(self._make_robot(s, p, round(x, 4), round(y, 4), round(a, 5)))
        s["fase"], s["fase_t"] = "hitung", 0

    def pending(self, s):
        return [] if self.over(s) else list(range(len(s["names"])))

    # ------------------------------------------------------------ tampilan
    def _robot_view(self, s, p, r):
        d = s["desain"][p]
        return {"x": round(r["x"], 3), "y": round(r["y"], 3), "a": round(math.degrees(r["a"]), 1),
                "v": round(math.hypot(r["vx"], r["vy"]), 2), "hidup": r["hidup"], "ko": r["ko"],
                "terbalik": r["terbalik"], "udara": round(r["udara"], 2), "udara_total": round(r["udara_total"], 2),
                "membalik": round(r["membalik"], 2), "angkat": r["angkat"] > 0, "r": r["r"],
                "energi": round(r["energi"], 1), "energi_maks": r["energi_maks"], "rpm": round(r["rpm"], 2),
                "siap": r["cd"] <= 0, "cd": round(r["cd"], 2), "aktif": bool(r["kontrol"][2]),
                "rangka": round(r["rangka"], 1), "rangka_maks": r["rangka_maks"],
                "armor": {sd: round(v, 1) for sd, v in r["armor"].items()}, "armor_maks": r["armor_maks"],
                "motor": [round(m, 1) for m in r["motor"]], "senjata_hp": round(r["senjata_hp"], 1),
                "baterai_hp": round(r["baterai_hp"], 1), "diam": round(r["diam"], 1), "massa": r["massa"],
                "rusak": round(r["rusak"], 1), "desain": d}

    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        fase = s["fase"]
        v: dict[str, Any] = {"fase": fase if not self.over(s) else "selesai", "ronde": min(s["ronde"], c["ronde"]),
                             "ronde_total": c["ronde"], "arena": s["N"], "berat_maks": c["berat_maks"],
                             "skor": dict(zip(n, s["skor"])), "riwayat": [dict(e) for e in s["riwayat"]],
                             "jebakan": [dict(h) for h in s["jebakan"]], "t": s["t"],
                             "dinding_duri": c["dinding_duri"], "durasi": c["durasi"]}
        if fase == "garasi":
            v["sisa"] = round(max(0.0, c["waktu_garasi"] - s["fase_t"] * DT), 1)
            v["siap"] = {n[i]: s["desain"][i] is not None for i in range(len(n))}
            if viewer == "semua":
                v["desain"] = {n[i]: s["desain"][i] for i in range(len(n))}
        else:
            v["sisa"] = round(HITUNG_MUNDUR - s["fase_t"] * DT, 1) if fase == "hitung" else round(max(0.0, c["durasi"] - s["fase_t"] * DT), 1)
            v["robot"] = {n[i]: self._robot_view(s, i, r) for i, r in enumerate(s["robot"])}
            v["palu_dalam"] = round((100 - (s["fase_t"] % 100)) * DT, 2) if fase == "tarung" else None
            v["lubang_dalam"] = round(max(0.0, LUBANG_BUKA - s["fase_t"] * DT), 1) if fase == "tarung" else LUBANG_BUKA
        return v

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        v = self._view(s, p)
        if s["fase"] == "garasi":
            v["desain_saya"] = s["desain"][p]
        return {**v, "saya": p, "nama_saya": s["names"][p]}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if a is None:
            return None
        if not isinstance(a, dict):
            raise ActionError('kirim dict: {"rakit": {...}} di garasi, atau {"maju": .., "belok": .., "senjata": .., "balik": ..}')
        if "rakit" in a:
            if s["fase"] != "garasi":
                return None                    # rakitan di luar garasi diabaikan (bot boleh terus mengirim)
            return {"rakit": bersihkan_rakitan(a["rakit"], s["cfg"]["berat_maks"])}
        out: dict[str, Any] = {}
        for key in ("maju", "belok"):
            if key in a and a[key] is not None:
                try:
                    x = float(a[key])
                except (TypeError, ValueError):
                    raise ActionError(f"{key} harus angka -1 sampai 1") from None
                if not math.isfinite(x):
                    raise ActionError(f"{key} harus angka -1 sampai 1")
                out[key] = round(clamp(x, -1.0, 1.0), 2)
        for key in ("senjata", "balik"):
            if key in a and a[key] is not None:
                out[key] = bool(a[key])
        return out or None

    def default(self, s, p):
        return None

    # ------------------------------------------------------------ fisika
    def _damage(self, s, j, side, amount, attacker=None, bypass=0.0, sebab="pukul"):
        """Kerusakan masuk ke armor sisi itu; kelebihannya merusak rangka dan komponen di balik sisi tersebut."""
        r = s["robot"][j]
        if not r["hidup"] or amount <= 0:
            return 0.0
        amount *= self._kali(s)
        d = s["desain"][j]
        if d["sasis"] == "kubah" and side in ("kanan", "kiri"):
            amount *= 0.7
        if side in ("atas", "bawah"):
            # dari atas/bawah (mendarat, gergaji lantai, palu): tidak ada armor sisi, langsung ke rangka
            r["rangka"] -= amount * 0.8
            if attacker is not None and attacker != j:
                s["robot"][attacker]["rusak"] += amount
                s["rusak_total"][attacker] += amount
                r["pemukul"], r["pemukul_t"] = attacker, s["fase_t"]
            return amount
        direct = amount * bypass
        rest = amount - direct
        a = r["armor"][side]
        absorbed = min(a, rest)
        r["armor"][side] = a - absorbed
        over = rest - absorbed + direct
        if over > 0:
            r["rangka"] -= over * 0.6
            inner = over * 0.8
            if side == "depan":
                r["senjata_hp"] = max(0.0, r["senjata_hp"] - inner)
            elif side == "kanan":
                r["motor"][1] = max(0.0, r["motor"][1] - inner)
            elif side == "kiri":
                r["motor"][0] = max(0.0, r["motor"][0] - inner)
            else:
                r["baterai_hp"] = max(0.0, r["baterai_hp"] - inner)
                r["energi"] = max(0.0, r["energi"] - inner * 0.6)
        if attacker is not None and attacker != j:
            s["robot"][attacker]["rusak"] += amount
            s["rusak_total"][attacker] += amount
            r["pemukul"], r["pemukul_t"] = attacker, s["fase_t"]
        return amount

    def _side_toward(self, r, x, y):
        return sisi_dari(sudut_rel(x - r["x"], y - r["y"], r["a"]))

    def _in_reach(self, s, i, j, jangkau, busur):
        a, b = s["robot"][i], s["robot"][j]
        if not b["hidup"] or b["udara"] > 0:
            return False
        gap = math.hypot(b["x"] - a["x"], b["y"] - a["y"]) - a["r"] - b["r"]
        if gap > jangkau:
            return False
        return abs(math.degrees(sudut_rel(b["x"] - a["x"], b["y"] - a["y"], a["a"]))) <= busur

    def _launch(self, s, i, j, dur, speed, flip_chance, events):
        a, b = s["robot"][i], s["robot"][j]
        if s["desain"][j]["sasis"] == "kubah":
            flip_chance *= 0.6
        b["udara"] = b["udara_total"] = dur
        b["vx"] = math.cos(a["a"]) * speed + (b["x"] - a["x"]) * 0.4
        b["vy"] = math.sin(a["a"]) * speed + (b["y"] - a["y"]) * 0.4
        b["w"] = 0.0
        b["akan_balik"] = rng(s, "balik", s["ronde"], s["fase_t"], i, j).random() < flip_chance
        a["kontrol_poin"] += 2.0
        events.append({"jenis": "terbang", "pemain": s["names"][j], "oleh": s["names"][i], "durasi": dur, "balik": b["akan_balik"]})

    def _ko(self, s, j, sebab, events):
        r = s["robot"][j]
        if not r["hidup"]:
            return
        r["hidup"], r["ko"] = False, sebab
        r["vx"] = r["vy"] = r["w"] = 0.0
        oleh = r["pemukul"] if r["pemukul"] is not None and s["fase_t"] - r["pemukul_t"] <= 10 * TPS else None
        if oleh is not None:
            s["skor"][oleh] += 3
        events.append({"jenis": "ko", "pemain": s["names"][j], "sebab": sebab, "oleh": s["names"][oleh] if oleh is not None else None})

    def _step_robots(self, s, events):
        N = s["N"]
        K = KATALOG
        duri = 2.5 if s["cfg"]["dinding_duri"] else 1.0
        rs = s["robot"]
        alive = [i for i, r in enumerate(rs) if r["hidup"]]
        # gerak
        for i in alive:
            r = rs[i]
            d = s["desain"][i]
            pg = K["penggerak"][d["penggerak"]]
            maju, belok, aktif, balik = r["kontrol"]
            r["hit_cd"] = max(0.0, r["hit_cd"] - DT)
            r["cd"] = max(0.0, r["cd"] - DT)
            r["angkat"] = max(0.0, r["angkat"] - DT)
            r["gergaji_lantai_cd"] = max(0.0, r["gergaji_lantai_cd"] - DT)
            if r["udara"] > 0:
                r["udara"] = max(0.0, r["udara"] - DT)
                r["x"] += r["vx"] * DT
                r["y"] += r["vy"] * DT
                if r["udara"] <= 0:
                    if r["akan_balik"]:
                        r["terbalik"] = not r["terbalik"]
                        events.append({"jenis": "terbalik" if r["terbalik"] else "tegak", "pemain": s["names"][i]})
                    r["akan_balik"] = False
                    self._damage(s, i, "bawah", 3.0, sebab="mendarat")
                    r["vx"] *= 0.3
                    r["vy"] *= 0.3
                    r["udara_total"] = 0.0
                continue
            # membalikkan badan
            if r["terbalik"] and balik and r["membalik"] <= 0 and r["energi"] > 0:
                if d["senjata"] == "flipper" and r["senjata_hp"] > 0 and r["energi"] >= 4:
                    r["membalik"], r["energi"] = 0.5, r["energi"] - 4
                elif d["pembalik"]:
                    r["membalik"] = 1.2
            if r["membalik"] > 0:
                r["membalik"] = max(0.0, r["membalik"] - DT)
                if r["membalik"] <= 0 and r["terbalik"]:
                    r["terbalik"] = False
                    events.append({"jenis": "tegak", "pemain": s["names"][i], "sendiri": True})
            # penggerak tank: roda kiri & kanan
            ml = (0.4 + 0.6 * r["motor"][0] / KOMPONEN_HP["motor"]) if r["motor"][0] > 0 else 0.0
            mr = (0.4 + 0.6 * r["motor"][1] / KOMPONEN_HP["motor"]) if r["motor"][1] > 0 else 0.0
            power = (1.0 if r["baterai_hp"] > 0 else 0.25) if r["energi"] > 0 else 0.0   # baterai rusak = pincang
            if r["terbalik"]:
                power *= 0.55
            if r["membalik"] > 0:
                power = 0.0
            pl = clamp(maju + belok, -1, 1) * ml * power
            pr = clamp(maju - belok, -1, 1) * mr * power
            traksi = 0.2 if r["angkat"] > 0 else 1.0
            vf_t = (pl + pr) / 2 * pg["vmaks"]
            w_t = (pl - pr) / 2 * pg["putar"]
            hx, hy = math.cos(r["a"]), math.sin(r["a"])
            vf = r["vx"] * hx + r["vy"] * hy
            vl = -r["vx"] * hy + r["vy"] * hx
            acc = pg["daya"] * 450.0 / r["massa"] * traksi
            vf += clamp(vf_t - vf, -acc * DT, acc * DT)
            vl *= max(0.0, 1.0 - 9.0 * traksi * DT)
            r["vx"], r["vy"] = vf * hx - vl * hy, vf * hy + vl * hx
            r["w"] += clamp(w_t - r["w"], -14 * traksi * DT, 14 * traksi * DT)
            r["energi"] = max(0.0, r["energi"] - (abs(pl) + abs(pr)) / 2 * pg["daya"] * 0.16 * DT)
            r["x"] += r["vx"] * DT
            r["y"] += r["vy"] * DT
            r["a"] = (r["a"] + r["w"] * DT) % (2 * math.pi)
            # agresi: bergerak mendekati lawan terdekat
            opp = [rs[j] for j in alive if j != i]
            if opp:
                o = min(opp, key=lambda q: (q["x"] - r["x"]) ** 2 + (q["y"] - r["y"]) ** 2)
                dist = math.hypot(o["x"] - r["x"], o["y"] - r["y"])
                if dist < 4.5 and vf > 0.6 and abs(sudut_rel(o["x"] - r["x"], o["y"] - r["y"], r["a"])) < math.radians(50):
                    r["agresi"] += DT
            # mogok
            if (r["motor"][0] <= 0 and r["motor"][1] <= 0) or power <= 0 and r["membalik"] <= 0:
                r["diam"] += DT
            else:
                r["diam"] = 0.0
        # dinding
        for i in alive:
            r = rs[i]
            for axis, vk in (("x", "vx"), ("y", "vy")):
                lo, hi = r["r"], N - r["r"]
                hit = None
                if r[axis] < lo:
                    r[axis] = lo
                    if r[vk] < 0:
                        hit = (-r[vk], -1)
                elif r[axis] > hi:
                    r[axis] = hi
                    if r[vk] > 0:
                        hit = (r[vk], 1)
                if hit:
                    speed, sign = hit
                    r[vk] = -r[vk] * 0.35
                    if speed > 1.4 and r["udara"] <= 0:
                        wx, wy = (sign, 0) if axis == "x" else (0, sign)
                        side = sisi_dari(sudut_rel(wx, wy, r["a"]))
                        self._damage(s, i, side, (speed - 1.4) * 3.0 * duri, attacker=r["pemukul"] if s["fase_t"] - r["pemukul_t"] < TPS else None)
                        events.append({"jenis": "benturan", "pemain": s["names"][i], "x": round(r["x"] + wx * r["r"], 2),
                                       "y": round(r["y"] + wy * r["r"], 2), "kuat": round(speed, 1)})
        # tabrakan antar robot
        for ii, i in enumerate(alive):
            for j in alive[ii + 1:]:
                a, b = rs[i], rs[j]
                if a["udara"] > 0 or b["udara"] > 0:
                    continue
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dist = math.hypot(dx, dy) or 1e-6
                md = a["r"] + b["r"]
                if dist >= md:
                    continue
                nx, ny = dx / dist, dy / dist
                over = md - dist
                ma, mb = a["massa"], b["massa"]
                a["x"] -= nx * over * mb / (ma + mb)
                a["y"] -= ny * over * mb / (ma + mb)
                b["x"] += nx * over * ma / (ma + mb)
                b["y"] += ny * over * ma / (ma + mb)
                vn = (b["vx"] - a["vx"]) * nx + (b["vy"] - a["vy"]) * ny
                sa = sisi_dari(sudut_rel(nx, ny, a["a"]))
                sb = sisi_dari(sudut_rel(-nx, -ny, b["a"]))
                da, db = s["desain"][i], s["desain"][j]
                # baji menyelip ke bawah lawan
                if da["sasis"] == "baji" and sa == "depan" and not (db["sasis"] == "baji" and sb == "depan") and b["angkat"] <= 0:
                    b["angkat"] = 0.5
                    a["kontrol_poin"] += 0.5
                if db["sasis"] == "baji" and sb == "depan" and not (da["sasis"] == "baji" and sa == "depan") and a["angkat"] <= 0:
                    a["angkat"] = 0.5
                    b["kontrol_poin"] += 0.5
                if vn < 0:
                    jimp = -(1 + 0.25) * vn / (1 / ma + 1 / mb)
                    a["vx"] -= jimp / ma * nx
                    a["vy"] -= jimp / ma * ny
                    b["vx"] += jimp / mb * nx
                    b["vy"] += jimp / mb * ny
                    if -vn > 1.2:
                        base = (-vn - 1.2) * 3.5
                        kb = 1.2 if da["sasis"] == "baji" and sa == "depan" else 1.0
                        ka = 1.2 if db["sasis"] == "baji" and sb == "depan" else 1.0
                        # tanpa senjata = pelat penyeruduk di depan: tabrakan depan 2× lebih sakit untuk lawan, ½ untuk diri sendiri
                        if da["senjata"] == "tidak" and sa == "depan":
                            kb *= 2.0
                            ka *= 0.5
                        if db["senjata"] == "tidak" and sb == "depan":
                            ka *= 2.0
                            kb *= 0.5
                        self._damage(s, j, sb, base * 2 * ma / (ma + mb) * kb, attacker=i)
                        self._damage(s, i, sa, base * 2 * mb / (ma + mb) * ka * (0.6 if sa == "depan" else 1.0), attacker=j)
                        events.append({"jenis": "benturan", "pemain": s["names"][j], "oleh": s["names"][i],
                                       "x": round(a["x"] + nx * a["r"], 2), "y": round(a["y"] + ny * a["r"], 2), "kuat": round(-vn, 1)})
        # senjata
        for i in alive:
            r = rs[i]
            if r["udara"] > 0:
                continue
            self._weapon(s, i, alive, events)
        # jebakan
        self._hazard_tick(s, events)
        # KO
        for i in alive:
            r = rs[i]
            if not r["hidup"]:
                continue
            if r["rangka"] <= 0:
                r["rangka"] = 0.0
                self._ko(s, i, "hancur", events)
            elif r["diam"] >= KO_DETIK:
                self._ko(s, i, "mogok", events)
            r["x"], r["y"] = round(r["x"], 4), round(r["y"], 4)
            r["vx"], r["vy"], r["w"] = round(r["vx"], 4), round(r["vy"], 4), round(r["w"], 4)
            r["a"] = round(r["a"], 5)
            r["energi"] = round(r["energi"], 3)

    def _weapon(self, s, i, alive, events):
        r = s["robot"][i]
        d = s["desain"][i]
        w = d["senjata"]
        aktif = r["kontrol"][2]
        # drum vertikal simetris: tetap berfungsi saat terbalik (70%); senjata lain mati kalau terbalik
        bisa_terbalik = w == "spinner_v"
        usable = (not r["terbalik"] or bisa_terbalik) and r["senjata_hp"] > 0 and r["energi"] > 0 and r["membalik"] <= 0
        n = s["names"]
        if w in ("spinner_h", "spinner_v"):
            P = SENJATA[w]
            cap = 0.4 + 0.6 * r["senjata_hp"] / KOMPONEN_HP["senjata"] if r["senjata_hp"] > 0 else 0.0
            if r["terbalik"]:
                cap *= 0.7
            if aktif and usable:
                if r["rpm"] < cap:
                    r["rpm"] = min(cap, r["rpm"] + DT / P["naik"])
                    r["energi"] = max(0.0, r["energi"] - P["biaya_naik"] * DT)
                else:
                    r["energi"] = max(0.0, r["energi"] - P["biaya_tahan"] * DT)
            else:
                r["rpm"] = max(0.0, r["rpm"] - (0.15 if usable else 0.6) * DT)
            if r["rpm"] < 0.2 or r["hit_cd"] > 0 or (r["terbalik"] and not bisa_terbalik):
                return
            for j in alive:
                if j == i or not self._in_reach(s, i, j, P["jangkau"], P["busur"]):
                    continue
                b = s["robot"][j]
                side = self._side_toward(b, r["x"], r["y"])
                dmg = P["dmg"] * r["rpm"] ** 2           # harus berputar penuh dulu untuk pukulan besar
                self._damage(s, j, side, dmg, attacker=i)
                dx, dy = b["x"] - r["x"], b["y"] - r["y"]
                dist = math.hypot(dx, dy) or 1e-6
                nx, ny = dx / dist, dy / dist
                share = 2 * r["massa"] / (r["massa"] + b["massa"])
                b["vx"] += nx * P["dorong"] * r["rpm"] * share
                b["vy"] += ny * P["dorong"] * r["rpm"] * share
                r["vx"] -= nx * P["pantul"] * r["rpm"]
                r["vy"] -= ny * P["pantul"] * r["rpm"]
                if w == "spinner_h":
                    b["w"] += P["putar"] * r["rpm"] * (1 if sudut_rel(dx, dy, r["a"]) > 0 else -1)
                elif r["rpm"] > 0.6:
                    self._launch(s, i, j, P["terbang"] * r["rpm"], 1.2 * r["rpm"], P["balik"] * r["rpm"], events)
                events.append({"jenis": "hantam", "senjata": w, "pemain": n[j], "oleh": n[i], "sisi": side, "kuat": round(dmg, 1),
                               "x": round(r["x"] + nx * r["r"], 2), "y": round(r["y"] + ny * r["r"], 2)})
                r["rpm"] *= P["sisa"]
                r["hit_cd"] = P["jeda"]
                break
        elif w in ("flipper", "palu"):
            P = SENJATA[w]
            if not (aktif and usable and r["cd"] <= 0 and r["energi"] >= P["biaya"]):
                return
            r["cd"] = P["jeda"]
            r["energi"] -= P["biaya"]
            targets = [j for j in alive if j != i and self._in_reach(s, i, j, P["jangkau"], P["busur"])]
            events.append({"jenis": "ayun", "senjata": w, "pemain": n[i], "kena": bool(targets)})
            for j in targets[:1]:
                b = s["robot"][j]
                side = self._side_toward(b, r["x"], r["y"])
                if w == "flipper":
                    self._damage(s, j, side, P["dmg"], attacker=i)
                    self._launch(s, i, j, P["terbang"], P["laju"], P["balik"], events)
                else:
                    kali = P["kali_terbalik"] if b["terbalik"] else 1.0
                    self._damage(s, j, "bawah" if b["terbalik"] else side, P["dmg"] * kali, attacker=i, bypass=P["tembus"])
                events.append({"jenis": "hantam", "senjata": w, "pemain": n[j], "oleh": n[i], "sisi": side,
                               "kuat": P["dmg"], "x": round((r["x"] + b["x"]) / 2, 2), "y": round((r["y"] + b["y"]) / 2, 2)})
        elif w == "gergaji":
            P = SENJATA[w]
            if not (aktif and usable):
                return
            r["energi"] = max(0.0, r["energi"] - P["biaya_tahan"] * DT)
            for j in alive:
                if j == i or not self._in_reach(s, i, j, P["jangkau"], P["busur"]):
                    continue
                b = s["robot"][j]
                side = self._side_toward(b, r["x"], r["y"])
                self._damage(s, j, side, P["dmg"] * (0.4 + 0.6 * r["senjata_hp"] / KOMPONEN_HP["senjata"]), attacker=i, bypass=P["tembus"])
                if s["fase_t"] % 5 == 0:
                    events.append({"jenis": "gerus", "pemain": n[j], "oleh": n[i],
                                   "x": round((r["x"] + b["x"]) / 2, 2), "y": round((r["y"] + b["y"]) / 2, 2)})
                break

    def _hazard_tick(self, s, events):
        n = s["names"]
        for h in s["jebakan"]:
            for i, r in enumerate(s["robot"]):
                if not r["hidup"] or r["udara"] > 0:
                    continue
                dist = math.hypot(r["x"] - h["x"], r["y"] - h["y"])
                if h["jenis"] == "lubang" and dist < h["r"] and s["fase_t"] * DT >= h.get("buka", 0):
                    pem = r["pemukul"]
                    if pem is not None and s["fase_t"] - r["pemukul_t"] < 4 * TPS:
                        s["robot"][pem]["kontrol_poin"] += 4.0
                    self._ko(s, i, "lubang", events)
                elif h["jenis"] == "gergaji" and dist < h["r"] + r["r"] * 0.5:
                    self._damage(s, i, "bawah", 0.55, sebab="gergaji_lantai")
                    if r["pemukul"] is not None and s["fase_t"] - r["pemukul_t"] < 3 * TPS:
                        s["robot"][r["pemukul"]]["kontrol_poin"] += 0.05
                    if r["gergaji_lantai_cd"] <= 0:
                        r["gergaji_lantai_cd"] = 0.5
                        ang = rng(s, "gergaji", s["fase_t"], i).uniform(0, 2 * math.pi)
                        r["vx"] += math.cos(ang) * 1.2
                        r["vy"] += math.sin(ang) * 1.2
                        events.append({"jenis": "gerus", "pemain": n[i], "oleh": None, "x": round(h["x"], 2), "y": round(h["y"], 2)})
            if h["jenis"] == "palu" and s["fase_t"] > 0 and s["fase_t"] % 100 == 0:
                kena = []
                for i, r in enumerate(s["robot"]):
                    if r["hidup"] and r["udara"] <= 0 and math.hypot(r["x"] - h["x"], r["y"] - h["y"]) < h["r"] + r["r"] * 0.4:
                        self._damage(s, i, "atas", 20.0, sebab="palu_arena")
                        kena.append(n[i])
                        if r["pemukul"] is not None and s["fase_t"] - r["pemukul_t"] < 3 * TPS:
                            s["robot"][r["pemukul"]]["kontrol_poin"] += 2.0
                events.append({"jenis": "palu_arena", "kena": kena, "x": h["x"], "y": h["y"]})

    # ------------------------------------------------------------ alur
    def apply(self, s, actions):
        c, n = s["cfg"], s["names"]
        events: list[dict[str, Any]] = []
        s["t"] += 1
        s["fase_t"] += 1
        if s["fase"] == "garasi":
            for p, a in sorted(actions.items()):
                if isinstance(a, dict) and "rakit" in a and s["desain"][p] is None:
                    s["desain"][p] = a["rakit"]
                    events.append({"jenis": "siap", "pemain": n[p], "nama_robot": a["rakit"]["nama"], "berat": berat(a["rakit"])})
            habis = s["fase_t"] * DT >= c["waktu_garasi"]
            if all(d is not None for d in s["desain"]) or habis:
                for p in range(len(n)):
                    if s["desain"][p] is None:
                        s["desain"][p] = rakitan_bawaan(c["berat_maks"])
                        events.append({"jenis": "siap", "pemain": n[p], "nama_robot": s["desain"][p]["nama"], "bawaan": True})
                self._start_round(s)
                events.append({"jenis": "ke_arena", "ronde": s["ronde"]})
            return events
        # kendali (juga selama hitung mundur, supaya senjata bisa mulai diputar tepat saat mulai)
        for p, a in actions.items():
            if isinstance(a, dict) and "rakit" not in a and p < len(s["robot"]):
                k = s["robot"][p]["kontrol"]
                if "maju" in a:
                    k[0] = a["maju"]
                if "belok" in a:
                    k[1] = a["belok"]
                if "senjata" in a:
                    k[2] = a["senjata"]
                if "balik" in a:
                    k[3] = a["balik"]
        if s["fase"] == "hitung":
            if s["fase_t"] * DT >= HITUNG_MUNDUR:
                s["fase"], s["fase_t"] = "tarung", 0
                events.append({"jenis": "mulai", "ronde": s["ronde"]})
            return events
        self._step_robots(s, events)
        hidup = [i for i, r in enumerate(s["robot"]) if r["hidup"]]
        if len(hidup) <= 1 or s["fase_t"] * DT >= c["durasi"]:
            events += self._end_round(s, hidup)
        return events

    def _judges(self, s, cands):
        """Nilai juri (0..100) untuk robot yang masih hidup: kerusakan 50%, agresi 25%, kontrol 25%."""
        out = {}
        tot = {k: sum(max(0.0, s["robot"][i][k]) for i in cands) or 1.0 for k in ("rusak", "agresi", "kontrol_poin")}
        for i in cands:
            r = s["robot"][i]
            out[i] = round(50 * r["rusak"] / tot["rusak"] + 25 * r["agresi"] / tot["agresi"] + 25 * r["kontrol_poin"] / tot["kontrol_poin"], 1)
        return out

    def _end_round(self, s, hidup):
        n = s["names"]
        cara = "ko"
        juri = {}
        if len(hidup) == 1:
            winner = hidup[0]
        elif not hidup:
            winner = max(range(len(n)), key=lambda i: (s["robot"][i]["rusak"], -i))
            cara = "seri_ko"
        else:
            juri = self._judges(s, hidup)
            winner = max(hidup, key=lambda i: (juri[i], s["robot"][i]["rusak"], -i))
            cara = "juri"
        s["skor"][winner] += 10
        for i, r in enumerate(s["robot"]):
            s["skor"][i] += int(r["rusak"] // 10)
        entry = {"ronde": s["ronde"], "pemenang": n[winner], "cara": cara, "juri": {n[i]: v for i, v in juri.items()},
                 "rusak": {n[i]: round(r["rusak"], 1) for i, r in enumerate(s["robot"])},
                 "ko": {n[i]: r["ko"] for i, r in enumerate(s["robot"]) if r["ko"]},
                 "detik": round(s["fase_t"] * DT, 1), "skor": dict(zip(n, s["skor"]))}
        s["riwayat"].append(entry)
        s["ronde"] += 1
        if not self.over(s):
            self._start_round(s)
        return [{"jenis": "ronde_selesai", **entry}]

    def over(self, s):
        return s["ronde"] > s["cfg"]["ronde"]

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [float(x) for x in s["rusak_total"]]

    def reveal(self, s):
        return {"desain": {s["names"][i]: d for i, d in enumerate(s["desain"])}, "ronde": [dict(e) for e in s["riwayat"]]}

    # ------------------------------------------------------------ bot
    def bot_library(self, s, p, obs):
        n = s["names"]
        N = s["N"]

        def _me():
            return s["robot"][p] if s["robot"] else None

        def saya():
            r = _me()
            if r is None:
                return None
            return {**self._robot_view(s, p, r), "nama": n[p]}

        def lawan():
            return [{**self._robot_view(s, i, r), "nama": n[i]} for i, r in enumerate(s["robot"]) if i != p and r["hidup"]]

        def lawan_terdekat():
            r = _me()
            ls = lawan()
            if r is None or not ls:
                return None
            return min(ls, key=lambda o: (o["x"] - r["x"]) ** 2 + (o["y"] - r["y"]) ** 2)

        def sudut_ke(x, y):
            r = _me()
            if r is None:
                return 0.0
            return round(math.degrees(sudut_rel(float(x) - r["x"], float(y) - r["y"], r["a"])), 1)

        def jarak_ke(x, y):
            r = _me()
            if r is None:
                return 0.0
            return round(math.hypot(float(x) - r["x"], float(y) - r["y"]), 3)

        def kejar(x, y):
            deg = sudut_ke(x, y)
            belok = clamp(deg / 40.0, -1.0, 1.0)
            maju = clamp(math.cos(math.radians(deg)) * 1.2, -0.3, 1.0)
            if abs(deg) > 100:
                maju = -0.3
            return {"maju": round(maju, 2), "belok": round(belok, 2)}

        def kabur(x, y):
            """Mundur menjauh sambil tetap menghadap titik itu (armor depan yang menerima pukulan)."""
            deg = sudut_ke(x, y)
            belok = clamp(deg / 40.0, -1.0, 1.0)
            maju = -0.9 if abs(deg) < 60 else -0.3
            r = _me()
            if r is not None:
                bx, by = r["x"] - math.cos(r["a"]) * 1.2, r["y"] - math.sin(r["a"]) * 1.2
                if bahaya_di(bx, by):
                    maju = 0.0                     # di belakang ada dinding/jebakan: berhenti mundur, berputar saja
                    belok = 1.0 if belok >= 0 else -1.0
            return {"maju": round(maju, 2), "belok": round(belok, 2)}

        def kena_senjata(nama):
            if nama not in n:
                raise ActionError(f"tidak ada robot bernama {nama}")
            j = n.index(nama)
            w = s["desain"][p]["senjata"] if s["desain"][p] else "tidak"
            if w == "tidak" or not s["robot"]:
                return False
            P = SENJATA[w]
            return self._in_reach(s, p, j, P["jangkau"] + 0.05, P["busur"])

        def jebakan():
            return [dict(h) for h in s["jebakan"]]

        def bahaya_di(x, y):
            x, y = float(x), float(y)
            if x < 0.9 or y < 0.9 or x > N - 0.9 or y > N - 0.9:
                return True
            return any(math.hypot(x - h["x"], y - h["y"]) < h["r"] + 0.7 for h in s["jebakan"] if h["jenis"] in ("lubang", "gergaji"))

        def contoh_rakitan(i):
            try:
                k = int(i)
            except (TypeError, ValueError):
                raise ActionError("contoh_rakitan butuh nomor 0–5") from None
            if not 0 <= k < len(CONTOH_RAKITAN):
                raise ActionError("contoh_rakitan butuh nomor 0–5")
            return pas_berat(CONTOH_RAKITAN[k], s["cfg"]["berat_maks"])

        def berat_rakitan(d):
            try:
                return berat(bersihkan_rakitan(d, 10_000))
            except ActionError:
                raise
            except Exception:  # noqa: BLE001
                raise ActionError("rakitan tidak valid") from None

        def _pas(d):
            return pas_berat(bersihkan_rakitan(d, 10_000), s["cfg"]["berat_maks"])

        return {"pas_berat": _pas, "saya": saya, "lawan": lawan, "lawan_terdekat": lawan_terdekat, "sudut_ke": sudut_ke, "jarak_ke": jarak_ke,
                "kejar": kejar, "kabur": kabur, "kena_senjata": kena_senjata, "jebakan": jebakan, "bahaya_di": bahaya_di,
                "contoh_rakitan": contoh_rakitan, "berat_rakitan": berat_rakitan}
