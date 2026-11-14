"""Tebak Gambar: setiap pemain mendapat gambar rahasia yang bisa dilihat semua orang KECUALI dirinya sendiri.

Bergiliran, pemain bertanya tentang gambarnya ("Apakah aku hewan?") dan pemain lain menjawab dengan tombol
(Ya / Tidak / Mungkin, atau 5 pilihan). Pertanyaan boleh diketik di chat game atau diucapkan lewat panggilan suara.
Kapan saja di gilirannya pemain boleh menebak. Khusus pemain manusia.

Gambar: emoji bawaan per kategori, isian tambahan host (emoji + nama), atau foto yang diunggah host ke room.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .base import ActionError, Game, Setting, rng

KATEGORI: dict[str, list[str]] = {
    "hewan": ["🐘 Gajah", "🦒 Jerapah", "🐯 Harimau", "🦁 Singa", "🐒 Monyet", "🐍 Ular", "🐊 Buaya", "🐢 Kura-kura",
              "🐧 Penguin", "🦉 Burung hantu", "🐓 Ayam | ayam jago", "🦆 Bebek", "🐄 Sapi", "🐐 Kambing", "🐈 Kucing",
              "🐕 Anjing", "🐇 Kelinci", "🐟 Ikan", "🦈 Hiu", "🐬 Lumba-lumba", "🐙 Gurita", "🦀 Kepiting", "🐝 Lebah",
              "🦋 Kupu-kupu", "🐜 Semut", "🦇 Kelelawar", "🐫 Unta", "🦓 Zebra", "🦏 Badak", "🦘 Kanguru", "🐼 Panda",
              "🐨 Koala", "🦜 Burung beo | beo", "🐸 Katak | kodok", "🦎 Kadal | cicak", "🐌 Siput | bekicot"],
    "makanan": ["🍜 Mi ayam | mie ayam", "🍚 Nasi", "🍳 Telur ceplok | telur mata sapi", "🍕 Pizza", "🍔 Burger",
                "🍟 Kentang goreng", "🍗 Ayam goreng", "🍢 Sate", "🍞 Roti", "🍰 Kue", "🍩 Donat", "🍦 Es krim",
                "🍫 Cokelat | coklat", "🍌 Pisang", "🍎 Apel", "🍉 Semangka", "🍇 Anggur", "🍍 Nanas", "🥭 Mangga",
                "🥥 Kelapa", "🌽 Jagung", "🥕 Wortel", "🌶️ Cabai | cabe", "🍄 Jamur", "🧀 Keju", "🍿 Popcorn | berondong",
                "🥟 Pangsit | dimsum", "🍣 Sushi", "🍤 Udang goreng", "☕ Kopi", "🍵 Teh", "🥛 Susu", "🧃 Jus"],
    "benda": ["📱 HP | handphone | ponsel", "💻 Laptop", "⌚ Jam tangan", "📷 Kamera", "🔑 Kunci", "✂️ Gunting",
              "🖊️ Pulpen | pena", "📚 Buku", "🎒 Tas ransel | tas", "👓 Kacamata", "☂️ Payung", "🕯️ Lilin",
              "💡 Lampu | bohlam", "🔨 Palu", "🧹 Sapu", "🪑 Kursi", "🛏️ Kasur | tempat tidur", "🚪 Pintu",
              "🪞 Cermin", "🧸 Boneka beruang | boneka", "🎸 Gitar", "🥁 Drum | gendang", "⚽ Bola", "🎈 Balon",
              "🧲 Magnet", "🔦 Senter", "📺 Televisi | tv", "🧺 Keranjang", "🪥 Sikat gigi", "🧦 Kaus kaki",
              "👟 Sepatu", "🎩 Topi"],
    "profesi": ["👮 Polisi", "👨‍🚒 Pemadam kebakaran | damkar", "👨‍⚕️ Dokter", "👩‍🏫 Guru", "👨‍🍳 Koki | chef",
                "👨‍🌾 Petani", "👷 Tukang bangunan | kuli bangunan", "👨‍✈️ Pilot", "👨‍🚀 Astronot",
                "🧑‍🎨 Pelukis", "🧑‍🎤 Penyanyi", "🧑‍🔧 Montir | mekanik", "🧑‍💻 Programmer", "💂 Tentara",
                "🕵️ Detektif", "🧑‍⚖️ Hakim", "💇 Tukang cukur | barber", "🧑‍🍼 Pengasuh bayi", "🤡 Badut",
                "🧙 Penyihir", "🥷 Ninja", "🤴 Raja", "🎣 Nelayan | pemancing", "📸 Fotografer"],
    "tempat": ["🏖️ Pantai", "⛰️ Gunung", "🏝️ Pulau", "🏜️ Gurun | padang pasir", "🌋 Gunung berapi",
               "🏫 Sekolah", "🏥 Rumah sakit", "🏦 Bank", "🕌 Masjid", "⛪ Gereja", "🏟️ Stadion", "🎡 Pasar malam",
               "🏰 Istana | kastil", "🗼 Menara", "🌉 Jembatan", "🏠 Rumah", "🏪 Warung | toko", "🚉 Stasiun",
               "✈️ Bandara", "⛺ Perkemahan | kemah", "🏊 Kolam renang", "🎪 Sirkus", "🌳 Hutan | taman"],
    "kendaraan": ["🚗 Mobil", "🚌 Bus | bis", "🚲 Sepeda", "🏍️ Motor | sepeda motor", "🛺 Bajaj", "🚂 Kereta api | kereta",
                  "✈️ Pesawat", "🚁 Helikopter", "🚀 Roket", "⛵ Perahu layar | perahu", "🚢 Kapal", "🚑 Ambulans",
                  "🚒 Mobil pemadam | damkar", "🚓 Mobil polisi", "🚜 Traktor", "🛴 Skuter | otopet", "🛶 Kano | sampan",
                  "🚠 Kereta gantung", "🛸 UFO | piring terbang", "🚛 Truk"],
    "olahraga": ["⚽ Sepak bola", "🏀 Basket | bola basket", "🏸 Bulu tangkis | badminton", "🏓 Tenis meja | pingpong",
                 "🎾 Tenis", "🏐 Voli | bola voli", "🏊 Renang", "🚴 Bersepeda", "🥊 Tinju", "🥋 Karate | silat",
                 "⛳ Golf", "🏹 Panahan", "🎳 Bowling", "🏄 Selancar | surfing", "⛷️ Ski", "🧗 Panjat tebing",
                 "🏇 Pacuan kuda", "🤸 Senam", "🏋️ Angkat besi", "♟️ Catur"],
}
JAWAB3 = [["ya", "Ya"], ["tidak", "Tidak"], ["mungkin", "Mungkin"]]
JAWAB5 = [["ya", "Ya"], ["mungkin_ya", "Mungkin ya"], ["tidak_tahu", "Tidak tahu"], ["mungkin_tidak", "Mungkin tidak"],
          ["tidak", "Tidak"]]
POIN_MENANG = [10, 7, 5, 4, 3, 2, 2, 1]


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def mirip(a: str, b: str) -> bool:
    """Sama, atau salah ketik satu huruf untuk kata yang cukup panjang."""
    if a == b:
        return True
    if min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 1:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= 1


def parse_item(line: str) -> dict[str, Any] | None:
    """'🐘 Gajah | gajah asia, liman' atau 'foto:abc123 Pak RT | rt'. Nama wajib; emoji/foto boleh kosong."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    main, _, alias = line.partition("|")
    main = main.strip()
    foto = None
    m = re.match(r"^foto:([0-9a-f]{6,16})\s+(.*)$", main)
    emoji = ""
    if m:
        foto, nama = m.group(1), m.group(2).strip()
    else:
        parts = main.split(maxsplit=1)
        if len(parts) == 2 and not any(ch.isalnum() for ch in parts[0]):
            emoji, nama = parts[0], parts[1].strip()
        else:
            nama = main
    nama = nama[:40]
    if not norm(nama):
        return None
    als = [a.strip()[:40] for a in re.split(r"[,|]", alias) if norm(a)]
    return {"emoji": emoji[:16], "nama": nama, "alias": als[:6], "foto": foto}


def bersihkan_daftar(v: Any) -> str:
    """Isian teks: maksimal 200 baris dan 8000 karakter."""
    if v is None:
        return ""
    text = str(v).replace("\r", "")
    lines = [ln[:120] for ln in text.split("\n")][:200]
    return "\n".join(lines)[:8000]


class TebakGambar(Game):
    id = "tebakgambar"
    nama = "Tebak Gambar"
    ringkas = "Semua bisa melihat gambarmu kecuali kamu sendiri! Bertanya bergiliran (jawab Ya / Tidak / Mungkin) lalu tebak gambar apa dirimu."
    kategori = "giliran"
    min_pemain = 2
    max_pemain = 10
    bot = False
    hint_aksi = '{"tanya": "Apakah aku hewan?"}, {"tebak": "gajah"}, {"jawab": "ya"}, atau "lewat"'
    timer = 60
    jeda_pada, jeda_hasil = (), 0
    label_skor = "Poin"
    settings = [
        Setting("kategori", "Kategori", "pilihan", "campur",
                pilihan=[["campur", "Campur semua kategori"], ["hewan", "Hewan"], ["makanan", "Makanan & minuman"],
                         ["benda", "Benda"], ["profesi", "Profesi"], ["tempat", "Tempat"], ["kendaraan", "Kendaraan"],
                         ["olahraga", "Olahraga"], ["kustom", "Hanya isian tambahan di bawah"]]),
        Setting("tambahan", "Isian tambahan (satu per baris)", "teks", "", grup="dasar", foto=True,
                cleaner=bersihkan_daftar,
                ket="Format: emoji lalu nama, alias setelah garis tegak. Contoh: \"🦖 Dinosaurus | dino\". Foto yang "
                    "diunggah otomatis ditambahkan sebagai \"foto:kode Nama\" (ganti Nama-nya)."),
        Setting("kecualikan", "Buang dari kategori bawaan (satu nama per baris)", "teks", "", grup="dasar",
                cleaner=bersihkan_daftar, ket="Nama yang ditulis di sini tidak akan muncul. Contoh: Ular"),
        Setting("jawaban", "Tombol jawaban", "pilihan", "3",
                pilihan=[["3", "3 pilihan: Ya / Tidak / Mungkin"], ["5", "5 pilihan: Ya / Mungkin ya / Tidak tahu / Mungkin tidak / Tidak"]]),
        Setting("akhir", "Game selesai kalau", "pilihan", "semua",
                pilihan=[["semua", "Semua pemain sudah menebak benar atau kalah"], ["satu", "Ada satu pemain yang menebak benar"]]),
        Setting("kesempatan", "Kesempatan menebak", "int", 3, 1, 10, grup="aturan",
                ket="Tebakan salah sebanyak ini = kalah (gambarmu dibuka untukmu)."),
        Setting("maks_putaran", "Maksimal putaran", "int", 12, 2, 40, grup="aturan",
                ket="Satu putaran = semua pemain mendapat satu giliran. Setelah ini, yang belum menebak benar kalah."),
        Setting("tanya_per_giliran", "Pertanyaan per giliran", "int", 1, 1, 5, grup="aturan"),
        Setting("penjawab", "Yang menjawab pertanyaan", "pilihan", "semua", grup="aturan",
                pilihan=[["semua", "Semua pemain lain (hasilnya dirangkum)"], ["satu", "Satu pemain (bergiliran: pemain berikutnya)"]]),
        Setting("gambar_beda", "Setiap pemain beda kategori", "bool", False, grup="kejutan", jika={"kategori": "campur"},
                ket="Kategori tiap pemain diacak terpisah, dan kategorimu tidak diberitahukan."),
        Setting("kasih_kategori", "Beri tahu kategori gambarmu", "bool", True, grup="informasi"),
    ]
    presets = [
        {"id": "cepat", "nama": "Kilat", "ket": "Yang pertama menebak benar langsung menang, 2 pertanyaan per giliran.",
         "nilai": {"akhir": "satu", "tanya_per_giliran": 2}},
        {"id": "detail", "nama": "Detektif", "ket": "5 tombol jawaban, kesempatan menebak cuma 1, kategori dirahasiakan.",
         "nilai": {"jawaban": "5", "kesempatan": 1, "kasih_kategori": False}},
    ]
    aturan = """
- Setiap pemain mendapat **gambar rahasia**. Semua orang bisa melihat gambarmu, **kecuali kamu sendiri**.
- Bergiliran: di giliranmu **ajukan pertanyaan ya/tidak** tentang gambarmu ("Apakah aku hewan?", "Apakah aku bisa dimakan?").
  Ketik di kolom pertanyaan, atau ucapkan saja lewat panggilan suara lalu tekan **Tanya (lewat suara)**.
- Pemain lain menjawab dengan tombol **Ya / Tidak / Mungkin** (atau 5 pilihan, sesuai pengaturan). Semua tanya-jawab
  tercatat di papan, jadi kamu bisa membaca ulang petunjuknya.
- Kapan saja di giliranmu kamu boleh **menebak** (ketik namanya; salah ketik satu huruf masih diterima). Benar = menang,
  dengan poin lebih besar untuk yang lebih dulu. Salah = kesempatan berkurang; kalau habis, kamu kalah.
- Gambar bisa dari kategori bawaan (emoji), **isian tambahan** host, atau **foto yang diunggah host** di pengaturan room.
"""
    format_aksi = """Saat giliranmu: `{"tanya": "teks pertanyaan"}` (teks boleh kosong kalau diucapkan), `{"tebak": "nama"}`, atau
`"lewat"` (akhiri giliran). Saat diminta menjawab: `{"jawab": "ya" | "tidak" | "mungkin"}` (5 pilihan: ya, mungkin_ya, tidak_tahu,
mungkin_tidak, tidak)."""

    # ------------------------------------------------------------ util
    def _pool(self, cfg, kategori: str | None = None) -> list[dict[str, Any]]:
        buang = {norm(x) for x in str(cfg.get("kecualikan", "")).split("\n") if norm(x)}
        kat = kategori or cfg["kategori"]
        items: list[dict[str, Any]] = []
        if kat != "kustom":
            cats = list(KATEGORI) if kat == "campur" else [kat]
            for ck in cats:
                for line in KATEGORI[ck]:
                    it = parse_item(line)
                    if it and norm(it["nama"]) not in buang:
                        items.append({**it, "kategori": ck})
        for line in str(cfg.get("tambahan", "")).split("\n"):
            it = parse_item(line)
            if it and norm(it["nama"]) not in buang:
                items.append({**it, "kategori": "tambahan"})
        seen, out = set(), []
        for it in items:
            k = norm(it["nama"])
            if k not in seen:
                seen.add(k)
                out.append(it)
        return out

    def _options(self, s):
        return JAWAB5 if s["cfg"]["jawaban"] == "5" else JAWAB3

    def init(self, cfg, names, seed):
        n = len(names)
        s = {"seed": seed, "names": names, "cfg": cfg, "skor": [0] * n, "putaran": 1, "giliran": 0,
             "status": ["main"] * n, "salah": [0] * n, "urut_menang": [], "catatan": [[] for _ in range(n)],
             "fase": "tanya", "tanya_sisa": cfg["tanya_per_giliran"], "pertanyaan": None, "jawaban": {},
             "tanya_total": [0] * n}
        r = rng(s, "gambar")
        if cfg["kategori"] == "campur" and cfg["gambar_beda"]:
            gambar = []
            used: set[str] = set()
            for i in range(n):
                cats = list(KATEGORI)
                kat = r.choice(cats)
                pool = [it for it in self._pool(cfg, kat) if norm(it["nama"]) not in used] or self._pool(cfg)
                it = r.choice(pool)
                used.add(norm(it["nama"]))
                gambar.append(it)
        else:
            pool = self._pool(cfg)
            if len(pool) < n:
                pool = pool + [it for it in self._pool({**cfg, "kategori": "campur"}) if it not in pool]
            gambar = r.sample(pool, n) if len(pool) >= n else [pool[i % len(pool)] for i in range(n)]
        s["gambar"] = gambar
        return s

    def _active(self, s):
        return [i for i, st in enumerate(s["status"]) if st == "main"]

    def _answerers(self, s):
        p, n = s["giliran"], len(s["names"])
        if s["cfg"]["penjawab"] == "satu":
            return [(p + 1) % n]
        return [q for q in range(n) if q != p]

    def pending(self, s):
        if self.over(s):
            return []
        if s["fase"] == "jawab":
            return [q for q in self._answerers(s) if q not in s["jawaban"]]
        return [s["giliran"]]

    # ------------------------------------------------------------ tampilan
    def _item_view(self, s, i, show: bool) -> dict[str, Any]:
        it = s["gambar"][i]
        kat = it.get("kategori")
        if not show:
            return {"rahasia": True, "kategori": kat if s["cfg"]["kasih_kategori"] and not s["cfg"]["gambar_beda"] else None}
        return {"rahasia": False, "emoji": it["emoji"], "nama": it["nama"], "foto": it["foto"], "kategori": kat}

    def _view(self, s, viewer):
        c, n = s["cfg"], s["names"]
        over = self.over(s)
        gambar = {}
        for i in range(len(n)):
            show = viewer == "semua" or over or viewer != i or s["status"][i] != "main"
            if viewer is None and not over:
                show = True     # penonton biasa: boleh melihat semua gambar (tidak ikut menebak)
            gambar[n[i]] = self._item_view(s, i, show)
        return {"putaran": min(s["putaran"], c["maks_putaran"]), "maks_putaran": c["maks_putaran"],
                "giliran": n[s["giliran"]] if not over else None, "fase": s["fase"] if not over else "selesai",
                "pertanyaan": s["pertanyaan"], "tanya_sisa": s["tanya_sisa"],
                "sudah_jawab": [n[q] for q in s["jawaban"]], "penjawab": [n[q] for q in self._answerers(s)] if not over else [],
                "pilihan_jawaban": self._options(s), "gambar": gambar,
                "status": {n[i]: s["status"][i] for i in range(len(n))},
                "salah": {n[i]: s["salah"][i] for i in range(len(n))}, "kesempatan": c["kesempatan"],
                "catatan": {n[i]: [dict(x) for x in s["catatan"][i]] for i in range(len(n))},
                "skor": dict(zip(n, s["skor"])), "urut_menang": [n[i] for i in s["urut_menang"]],
                "akhir": c["akhir"]}

    def public(self, s):
        return self._view(s, None)

    def full_view(self, s):
        return self._view(s, "semua")

    def observe(self, s, p):
        return {**self._view(s, p), "saya": p, "nama_saya": s["names"][p]}

    # ------------------------------------------------------------ aksi
    def validate(self, s, p, a):
        if s["fase"] == "jawab":
            if isinstance(a, dict):
                a = a.get("jawab")
            ok = [o[0] for o in self._options(s)]
            w = str(a or "").strip().lower().replace(" ", "_")
            if w not in ok:
                raise ActionError("jawab dengan salah satu: " + ", ".join(ok))
            return {"jawab": w}
        if isinstance(a, str) and a.strip().lower() in ("lewat", "selesai"):
            return "lewat"
        if not isinstance(a, dict):
            raise ActionError('kirim {"tanya": "..."}, {"tebak": "..."}, atau "lewat"')
        if "tebak" in a:
            t = str(a.get("tebak") or "").strip()[:60]
            if not norm(t):
                raise ActionError("tebakan masih kosong")
            return {"tebak": t}
        if "tanya" in a:
            if s["tanya_sisa"] <= 0:
                raise ActionError("jatah pertanyaan giliran ini sudah habis: tebak atau lewat")
            return {"tanya": str(a.get("tanya") or "").strip()[:160]}
        raise ActionError('kirim {"tanya": "..."}, {"tebak": "..."}, atau "lewat"')

    def default(self, s, p):
        if s["fase"] == "jawab":
            return {"jawab": "tidak_tahu" if s["cfg"]["jawaban"] == "5" else "mungkin"}
        return "lewat"

    def _benar(self, s, p, tebakan: str) -> bool:
        it = s["gambar"][p]
        t = norm(tebakan)
        return any(mirip(t, norm(x)) for x in [it["nama"], *it.get("alias", [])])

    def apply(self, s, actions):
        n, c = s["names"], s["cfg"]
        events: list[dict[str, Any]] = []
        if s["fase"] == "jawab":
            for q, a in actions.items():
                s["jawaban"][q] = a["jawab"]
            if all(q in s["jawaban"] for q in self._answerers(s)):
                p = s["giliran"]
                hitung: dict[str, int] = {}
                for q, w in s["jawaban"].items():
                    hitung[w] = hitung.get(w, 0) + 1
                entry = {"tanya": s["pertanyaan"], "jawaban": {n[q]: w for q, w in s["jawaban"].items()},
                         "rangkum": hitung, "putaran": s["putaran"]}
                s["catatan"][p].append(entry)
                events.append({"jenis": "dijawab", "pemain": n[p], **entry})
                s["pertanyaan"], s["jawaban"] = None, {}
                s["fase"] = "tanya"
                # sisa pertanyaan habis: tetap di fase tanya, tapi hanya boleh tebak / lewat
            return events
        (p, a), = actions.items()
        if a == "lewat":
            events.append({"jenis": "lewat", "pemain": n[p]})
            self._next_turn(s, events)
            return events
        if "tanya" in a:
            s["tanya_sisa"] -= 1
            s["tanya_total"][p] += 1
            s["pertanyaan"] = a["tanya"] or "(diucapkan)"
            s["fase"] = "jawab"
            s["jawaban"] = {}
            events.append({"jenis": "tanya", "pemain": n[p], "tanya": s["pertanyaan"]})
            return events
        tebak = a["tebak"]
        if self._benar(s, p, tebak):
            s["status"][p] = "menang"
            s["urut_menang"].append(p)
            k = len(s["urut_menang"]) - 1
            pts = POIN_MENANG[min(k, len(POIN_MENANG) - 1)] + max(0, 5 - s["tanya_total"][p] // 2)
            s["skor"][p] += pts
            it = s["gambar"][p]
            events.append({"jenis": "tebak", "pemain": n[p], "tebakan": tebak, "benar": True, "poin": pts,
                           "gambar": {"emoji": it["emoji"], "nama": it["nama"], "foto": it["foto"]}})
        else:
            s["salah"][p] += 1
            habis = s["salah"][p] >= c["kesempatan"]
            ev = {"jenis": "tebak", "pemain": n[p], "tebakan": tebak, "benar": False, "sisa": c["kesempatan"] - s["salah"][p]}
            if habis:
                s["status"][p] = "kalah"
                it = s["gambar"][p]
                ev["kalah"] = True
                ev["gambar"] = {"emoji": it["emoji"], "nama": it["nama"], "foto": it["foto"]}
            events.append(ev)
        self._next_turn(s, events)
        return events

    def _next_turn(self, s, events):
        n = len(s["names"])
        c = s["cfg"]
        if c["akhir"] == "satu" and s["urut_menang"]:
            s["selesai"] = True
            self._finish_losers(s, events)
            return
        if not self._active(s):
            s["selesai"] = True
            return
        p = s["giliran"]
        for d in range(1, n + 1):
            q = (p + d) % n
            if s["status"][q] == "main":
                if q <= p:
                    s["putaran"] += 1          # melewati kursi terakhir = putaran baru
                s["giliran"] = q
                break
        s["fase"], s["tanya_sisa"], s["pertanyaan"], s["jawaban"] = "tanya", c["tanya_per_giliran"], None, {}
        if s["putaran"] > c["maks_putaran"]:
            s["selesai"] = True
            self._finish_losers(s, events)

    def _finish_losers(self, s, events):
        n = s["names"]
        for i, st in enumerate(s["status"]):
            if st == "main":
                s["status"][i] = "kalah"
                it = s["gambar"][i]
                events.append({"jenis": "habis_waktu", "pemain": n[i], "gambar": {"emoji": it["emoji"], "nama": it["nama"], "foto": it["foto"]}})

    def over(self, s):
        return bool(s.get("selesai"))

    def scores(self, s):
        return [float(x) for x in s["skor"]]

    def tiebreak(self, s):
        return [-float(x) for x in s["tanya_total"]]

    def reveal(self, s):
        return {"gambar": {s["names"][i]: {"emoji": it["emoji"], "nama": it["nama"], "foto": it["foto"]}
                           for i, it in enumerate(s["gambar"])}}
