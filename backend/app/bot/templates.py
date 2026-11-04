"""Bot siap pakai: contoh untuk pemain dan lawan di arena latihan."""

from __future__ import annotations

TEMPLATES: list[dict[str, str]] = [
    {
        "id": "si_batu",
        "nama": "Si Batu",
        "level": "pemula",
        "ket": "Selalu memilih batu. Bot paling sederhana.",
        "kode": '''def pilih():
    return BATU
''',
    },
    {
        "id": "pemutar",
        "nama": "Pemutar",
        "level": "pemula",
        "ket": "Berputar batu, kertas, gunting, lalu kembali ke batu.",
        "kode": '''def pilih():
    urutan = [BATU, KERTAS, GUNTING]
    # ronde 1 -> indeks 0, ronde 2 -> indeks 1, dst.
    return urutan[(ronde() - 1) % 3]
''',
    },
    {
        "id": "anti_mayoritas",
        "nama": "Anti Mayoritas",
        "level": "pemula",
        "ket": "Melawan senjata yang paling banyak dipilih di ronde lalu.",
        "kode": '''def pilih():
    if ronde() == 1:
        return KERTAS
    favorit = terbanyak(jumlah_terakhir())
    return pengalah(favorit)
''',
    },
    {
        "id": "minoritas",
        "nama": "Minoritas",
        "level": "pemula",
        "ket": "Memilih senjata yang paling sepi di ronde lalu, supaya kalau menang bagiannya besar.",
        "kode": '''def pilih():
    if ronde() == 1:
        return GUNTING
    return tersedikit(jumlah_terakhir())
''',
    },
    {
        "id": "peniru_juara",
        "nama": "Peniru Juara",
        "level": "menengah",
        "ket": "Meniru pilihan terakhir lawan yang HP-nya paling tinggi.",
        "kode": '''def pilih():
    if ronde() == 1:
        return BATU
    juara = terkuat()
    tiruan = pilihan_terakhir(juara)
    if tiruan is None:
        return BATU
    return tiruan
''',
    },
    {
        "id": "pemburu_juara",
        "nama": "Pemburu Juara",
        "level": "menengah",
        "ket": "Menyerang lawan ber-HP tertinggi dengan senjata yang mengalahkan pilihan terakhirnya.",
        "kode": '''def pilih():
    if ronde() == 1:
        return KERTAS
    target = terkuat()
    tebakan = pilihan_terakhir(target)
    if tebakan is None:
        return KERTAS
    return pengalah(tebakan)
''',
    },
    {
        "id": "pengamat",
        "nama": "Pengamat",
        "level": "menengah",
        "ket": "Menjumlahkan semua ronde dalam ingatan, lalu melawan senjata yang paling sering muncul.",
        "kode": '''def pilih():
    if ronde() == 1:
        return BATU
    total = total_jumlah(riwayat_jumlah())
    return pengalah(terbanyak(total))
''',
    },
    {
        "id": "pembalas",
        "nama": "Pembalas",
        "level": "menengah",
        "ket": "Kalau ronde lalu untung, ulangi. Kalau rugi, pakai senjata yang mengalahkan penakluknya.",
        "kode": '''def pilih():
    if ronde() == 1:
        return GUNTING
    saya = nama_saya()
    terakhir = pilihan_terakhir(saya)
    if perubahan_terakhir(saya) >= 0:
        return terakhir
    penakluk = pengalah(terakhir)
    return pengalah(penakluk)
''',
    },
    {
        "id": "hati_hati",
        "nama": "Hati-hati",
        "level": "menengah",
        "ket": "Melawan mayoritas. Kalau HP tinggal sepertiga, sembunyi di senjata paling sepi.",
        "kode": '''def pilih():
    if ronde() == 1:
        return BATU
    jumlah = jumlah_terakhir()
    if hp_saya() < hp_awal() / 3:
        return tersedikit(jumlah)
    return pengalah(terbanyak(jumlah))
''',
    },
    {
        "id": "ahli_hitung",
        "nama": "Ahli Hitung",
        "level": "lanjut",
        "ket": "Menganggap semua lawan mengulang pilihannya, lalu menghitung senjata yang paling untung.",
        "kode": '''def pilih():
    if ronde() == 1:
        return GUNTING
    tebakan = {}
    for nama in lawan():
        tebakan[nama] = pilihan_terakhir(nama)
    terbaik = BATU
    skor_terbaik = -999999
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor = hitung_hasil(tebakan)[nama_saya()]
        if skor > skor_terbaik:
            terbaik = s
            skor_terbaik = skor
    return terbaik
''',
    },
    {
        "id": "pembaca_pola",
        "nama": "Pembaca Pola",
        "level": "lanjut",
        "ket": "Menebak pilihan tiap lawan dari senjata favoritnya dalam ingatan, lalu memilih senjata yang paling untung.",
        "kode": '''def tebak(nama):
    favorit = terbanyak(riwayat_pilihan(nama))
    if favorit is None:
        return BATU
    return favorit

def pilih():
    if ronde() <= 2:
        return [KERTAS, BATU][ronde() - 1]
    tebakan = {}
    for nama in lawan():
        tebakan[nama] = tebak(nama)
    skor = {}
    for s in SENJATA:
        tebakan[nama_saya()] = s
        skor[s] = hitung_hasil(tebakan)[nama_saya()]
    return terbanyak(skor)
''',
    },
]

TEMPLATE_BY_ID = {t["id"]: t for t in TEMPLATES}
