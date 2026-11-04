"""Library game yang bisa dipakai bot.

Setiap ronde library dibuat ulang dari ``RoundView``, yaitu potret keadaan
game di awal ronde. Semua nilai yang dikembalikan adalah salinan, jadi bot
tidak bisa mengubah data game.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from ..engine.rules import BATU, DIKALAHKAN_OLEH, GUNTING, KERTAS, MENGALAHKAN, SENJATA, resolve_round
from .errors import BotError
from .interpreter import LibFunction


@dataclass
class RoundView:
    me: str
    ronde: int
    hp_awal: int
    hp_kalah: int
    ronde_maks: int
    ingatan: int
    names: list[str]                       # semua peserta, urutan masuk room
    hp: dict[str, int]                     # HP di awal ronde (0 = sudah gugur)
    history: list[dict] = field(default_factory=list)  # hanya N ronde terakhir

    @property
    def alive(self) -> list[str]:
        return [n for n in self.names if self.hp[n] > 0]


def _senjata(s: Any, fname: str) -> str:
    if isinstance(s, str) and s.strip().lower() in SENJATA:
        return s.strip().lower()
    raise BotError(f"{fname}(): {s!r} bukan senjata. Pakai BATU, GUNTING, atau KERTAS")


def _urut_kunci(keys: list) -> list:
    """Kalau semua kunci adalah senjata, urutkan batu, gunting, kertas."""
    if keys and all(k in SENJATA for k in keys):
        return [s for s in SENJATA if s in keys]
    return keys


def _ekstrem(data: Any, fname: str, terbesar: bool) -> Any:
    if isinstance(data, dict):
        if not data:
            raise BotError(f"{fname}(): dict kosong")
        counts = data
        keys = _urut_kunci(list(data.keys()))
    elif isinstance(data, (list, tuple)):
        items = [x for x in data if x is not None]
        if not items:
            return None
        counts: dict = {}
        if all(isinstance(x, str) and x in SENJATA for x in items):
            counts = {s: 0 for s in SENJATA}
        for x in items:
            try:
                counts[x] = counts.get(x, 0) + 1
            except TypeError:
                raise BotError(f"{fname}(): isi list tidak bisa dihitung") from None
        keys = list(counts.keys())
    else:
        raise BotError(f"{fname}() butuh dict (misalnya jumlah_terakhir()) atau list")
    best = keys[0]
    for k in keys[1:]:
        v, bv = counts[k], counts[best]
        if not isinstance(v, (int, float)) or not isinstance(bv, (int, float)):
            raise BotError(f"{fname}(): nilai di dalam dict harus angka")
        if (v > bv) if terbesar else (v < bv):
            best = k
    return best


def make_library(view: RoundView) -> dict[str, Any]:
    names = list(view.names)
    order = {n: i for i, n in enumerate(names)}
    hist = view.history

    def _nama(n: Any, fname: str) -> str:
        if n not in order:
            raise BotError(f"{fname}(): tidak ada pemain bernama {n!r}. Lihat semua_pemain()")
        return n

    def nama_saya():
        return view.me

    def hp_saya():
        return view.hp[view.me]

    def ronde():
        return view.ronde

    def ronde_maks():
        return view.ronde_maks

    def hp_awal():
        return view.hp_awal

    def hp_kalah():
        return view.hp_kalah

    def ingatan():
        return view.ingatan

    def semua_pemain():
        return list(names)

    def pemain_hidup():
        return view.alive

    def lawan():
        return [n for n in view.alive if n != view.me]

    def hp(nama):
        return view.hp[_nama(nama, "hp")]

    def terkuat():
        lw = lawan()
        if not lw:
            return None
        best = lw[0]
        for n in lw[1:]:
            if view.hp[n] > view.hp[best]:
                best = n
        return best

    def terlemah():
        lw = lawan()
        if not lw:
            return None
        best = lw[0]
        for n in lw[1:]:
            if view.hp[n] < view.hp[best]:
                best = n
        return best

    def jumlah_terakhir():
        if not hist:
            return {s: 0 for s in SENJATA}
        return dict(hist[-1]["jumlah"])

    def riwayat_jumlah():
        return [dict(h["jumlah"]) for h in hist]

    def pilihan_terakhir(nama):
        _nama(nama, "pilihan_terakhir")
        return hist[-1]["pilihan"].get(nama) if hist else None

    def riwayat_pilihan(nama):
        _nama(nama, "riwayat_pilihan")
        return [h["pilihan"].get(nama) for h in hist]

    def perubahan_terakhir(nama):
        _nama(nama, "perubahan_terakhir")
        return hist[-1]["perubahan"].get(nama, 0) if hist else 0

    def riwayat_perubahan(nama):
        _nama(nama, "riwayat_perubahan")
        return [h["perubahan"].get(nama, 0) for h in hist]

    def riwayat():
        return copy.deepcopy(hist)

    def pengalah(s):
        return DIKALAHKAN_OLEH[_senjata(s, "pengalah")]

    def korban(s):
        return MENGALAHKAN[_senjata(s, "korban")]

    def terbanyak(data):
        return _ekstrem(data, "terbanyak", True)

    def tersedikit(data):
        return _ekstrem(data, "tersedikit", False)

    def hitung(daftar, x):
        if not isinstance(daftar, (list, tuple)):
            raise BotError("hitung() butuh list sebagai argumen pertama")
        return sum(1 for v in daftar if v == x)

    def total_jumlah(daftar):
        if not isinstance(daftar, (list, tuple)):
            raise BotError("total_jumlah() butuh list berisi dict, misalnya riwayat_jumlah()")
        total = {s: 0 for s in SENJATA}
        for d in daftar:
            if not isinstance(d, dict):
                raise BotError("total_jumlah() butuh list berisi dict")
            for k, v in d.items():
                if not isinstance(v, (int, float)):
                    raise BotError("total_jumlah(): nilai di dalam dict harus angka")
                total[k] = total.get(k, 0) + v
        return total

    def hitung_hasil(pilihan):
        if not isinstance(pilihan, dict):
            raise BotError("hitung_hasil() butuh dict {nama_pemain: senjata}")
        clean: dict[str, str] = {}
        for n in sorted(pilihan, key=lambda k: order.get(k, 1 << 30)):
            _nama(n, "hitung_hasil")
            if view.hp[n] <= 0:
                raise BotError(f"hitung_hasil(): {n} sudah gugur")
            clean[n] = _senjata(pilihan[n], "hitung_hasil")
        out = resolve_round(clean, view.hp, view.hp_kalah, order)
        return dict(out.delta)

    def senjata_terbaik():
        if not hist:
            return BATU
        tebakan = {}
        for n in lawan():
            p = hist[-1]["pilihan"].get(n)
            if p is not None:
                tebakan[n] = p
        best, best_score = BATU, None
        for s in SENJATA:
            tebakan[view.me] = s
            score = hitung_hasil(dict(tebakan))[view.me]
            if best_score is None or score > best_score:
                best, best_score = s, score
        return best

    fns = {
        "nama_saya": (nama_saya, 1), "hp_saya": (hp_saya, 1), "ronde": (ronde, 1),
        "ronde_maks": (ronde_maks, 1), "hp_awal": (hp_awal, 1), "hp_kalah": (hp_kalah, 1),
        "ingatan": (ingatan, 1), "semua_pemain": (semua_pemain, 2), "pemain_hidup": (pemain_hidup, 2),
        "lawan": (lawan, 2), "hp": (hp, 1), "terkuat": (terkuat, 3), "terlemah": (terlemah, 3),
        "jumlah_terakhir": (jumlah_terakhir, 2), "riwayat_jumlah": (riwayat_jumlah, 5),
        "pilihan_terakhir": (pilihan_terakhir, 1), "riwayat_pilihan": (riwayat_pilihan, 5),
        "perubahan_terakhir": (perubahan_terakhir, 1), "riwayat_perubahan": (riwayat_perubahan, 5),
        "riwayat": (riwayat, 20), "pengalah": (pengalah, 1), "korban": (korban, 1),
        "terbanyak": (terbanyak, 3), "tersedikit": (tersedikit, 3), "hitung": (hitung, 3),
        "total_jumlah": (total_jumlah, 5), "hitung_hasil": (hitung_hasil, 20),
        "senjata_terbaik": (senjata_terbaik, 60),
    }
    lib: dict[str, Any] = {name: LibFunction(name, fn, cost) for name, (fn, cost) in fns.items()}
    lib.update({"BATU": BATU, "GUNTING": GUNTING, "KERTAS": KERTAS, "SENJATA": list(SENJATA)})
    return lib


#: dokumentasi singkat tiap fungsi, dipakai untuk autocomplete di editor
LIBRARY_DOCS: list[dict[str, str]] = [
    {"nama": "BATU", "jenis": "konstanta", "tanda": "BATU", "ket": "Senjata batu. Mengalahkan gunting."},
    {"nama": "GUNTING", "jenis": "konstanta", "tanda": "GUNTING", "ket": "Senjata gunting. Mengalahkan kertas."},
    {"nama": "KERTAS", "jenis": "konstanta", "tanda": "KERTAS", "ket": "Senjata kertas. Mengalahkan batu."},
    {"nama": "SENJATA", "jenis": "konstanta", "tanda": "SENJATA", "ket": "List [BATU, GUNTING, KERTAS]."},
    {"nama": "nama_saya", "jenis": "fungsi", "tanda": "nama_saya()", "ket": "Nama botmu."},
    {"nama": "hp_saya", "jenis": "fungsi", "tanda": "hp_saya()", "ket": "HP botmu di awal ronde ini."},
    {"nama": "ronde", "jenis": "fungsi", "tanda": "ronde()", "ket": "Nomor ronde sekarang, mulai dari 1."},
    {"nama": "ronde_maks", "jenis": "fungsi", "tanda": "ronde_maks()", "ket": "Batas ronde match ini."},
    {"nama": "hp_awal", "jenis": "fungsi", "tanda": "hp_awal()", "ket": "HP setiap pemain saat match dimulai."},
    {"nama": "hp_kalah", "jenis": "fungsi", "tanda": "hp_kalah()", "ket": "HP yang hilang setiap kali kalah."},
    {"nama": "ingatan", "jenis": "fungsi", "tanda": "ingatan()", "ket": "Berapa ronde terakhir yang bisa dilihat di riwayat."},
    {"nama": "semua_pemain", "jenis": "fungsi", "tanda": "semua_pemain()", "ket": "Nama semua peserta (termasuk yang sudah gugur dan dirimu)."},
    {"nama": "pemain_hidup", "jenis": "fungsi", "tanda": "pemain_hidup()", "ket": "Nama peserta yang masih hidup, termasuk dirimu."},
    {"nama": "lawan", "jenis": "fungsi", "tanda": "lawan()", "ket": "Nama lawan yang masih hidup."},
    {"nama": "hp", "jenis": "fungsi", "tanda": "hp(nama)", "ket": "HP pemain itu di awal ronde (0 kalau sudah gugur)."},
    {"nama": "terkuat", "jenis": "fungsi", "tanda": "terkuat()", "ket": "Nama lawan dengan HP tertinggi."},
    {"nama": "terlemah", "jenis": "fungsi", "tanda": "terlemah()", "ket": "Nama lawan dengan HP terendah."},
    {"nama": "jumlah_terakhir", "jenis": "fungsi", "tanda": "jumlah_terakhir()", "ket": "Jumlah pemilih tiap senjata di ronde lalu, misalnya {\"batu\": 3, \"gunting\": 2, \"kertas\": 3}."},
    {"nama": "riwayat_jumlah", "jenis": "fungsi", "tanda": "riwayat_jumlah()", "ket": "List jumlah tiap senjata per ronde (sebanyak ingatan, terbaru di akhir)."},
    {"nama": "pilihan_terakhir", "jenis": "fungsi", "tanda": "pilihan_terakhir(nama)", "ket": "Senjata pemain itu di ronde lalu (None kalau belum ada)."},
    {"nama": "riwayat_pilihan", "jenis": "fungsi", "tanda": "riwayat_pilihan(nama)", "ket": "List senjata pemain itu per ronde dalam ingatan."},
    {"nama": "perubahan_terakhir", "jenis": "fungsi", "tanda": "perubahan_terakhir(nama)", "ket": "Perubahan HP pemain itu di ronde lalu (+ untung, - rugi)."},
    {"nama": "riwayat_perubahan", "jenis": "fungsi", "tanda": "riwayat_perubahan(nama)", "ket": "List perubahan HP pemain itu per ronde dalam ingatan."},
    {"nama": "riwayat", "jenis": "fungsi", "tanda": "riwayat()", "ket": "List lengkap per ronde: {\"ronde\", \"jumlah\", \"pilihan\", \"perubahan\", \"hp\"}."},
    {"nama": "pengalah", "jenis": "fungsi", "tanda": "pengalah(senjata)", "ket": "Senjata yang MENGALAHKAN senjata itu. pengalah(BATU) = KERTAS."},
    {"nama": "korban", "jenis": "fungsi", "tanda": "korban(senjata)", "ket": "Senjata yang DIKALAHKAN senjata itu. korban(BATU) = GUNTING."},
    {"nama": "terbanyak", "jenis": "fungsi", "tanda": "terbanyak(dict_atau_list)", "ket": "Kunci dengan nilai terbesar, atau isi list yang paling sering muncul. Seri: batu, gunting, kertas."},
    {"nama": "tersedikit", "jenis": "fungsi", "tanda": "tersedikit(dict_atau_list)", "ket": "Kebalikan terbanyak()."},
    {"nama": "hitung", "jenis": "fungsi", "tanda": "hitung(list, nilai)", "ket": "Berapa kali nilai muncul di list."},
    {"nama": "total_jumlah", "jenis": "fungsi", "tanda": "total_jumlah(list_dict)", "ket": "Menjumlahkan list dict, misalnya total_jumlah(riwayat_jumlah())."},
    {"nama": "hitung_hasil", "jenis": "fungsi", "tanda": "hitung_hasil(pilihan)", "ket": "Simulasi satu ronde: masukkan {nama: senjata}, keluar {nama: perubahan HP}."},
    {"nama": "senjata_terbaik", "jenis": "fungsi", "tanda": "senjata_terbaik()", "ket": "Senjata paling untung untukmu kalau semua lawan mengulang pilihan ronde lalu."},
]
