"""Aturan inti Suit Bot Arena.

Setiap ronde semua bot memilih senjata bersamaan. Untuk setiap pasangan
(pemenang > yang kalah) yang muncul di ronde itu:

* setiap pemain di golongan yang kalah kehilangan ``hp_kalah`` HP
  (atau sisa HP-nya kalau kurang dari itu);
* semua HP itu dikumpulkan lalu dibagi rata ke golongan pemenang;
* sisa pembagian tidak dibuang: +1 ke pemenang ber-HP terendah dulu,
  kalau HP sama yang lebih dulu masuk room didahulukan.

Karena ada tiga senjata, aturannya sirkular: kalau ketiganya muncul,
setiap golongan sekaligus menang atas satu golongan dan kalah dari yang lain.
Total HP semua pemain selalu tetap (zero-sum).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Hashable, Mapping, Sequence

BATU = "batu"
GUNTING = "gunting"
KERTAS = "kertas"

#: Urutan baku senjata. Dipakai untuk semua tie-break supaya hasil selalu sama.
SENJATA: tuple[str, ...] = (BATU, GUNTING, KERTAS)

#: kunci mengalahkan nilai
MENGALAHKAN: dict[str, str] = {BATU: GUNTING, GUNTING: KERTAS, KERTAS: BATU}
#: kunci dikalahkan oleh nilai
DIKALAHKAN_OLEH: dict[str, str] = {v: k for k, v in MENGALAHKAN.items()}


@dataclass
class Loser:
    id: Hashable
    amt: int


@dataclass
class PairResult:
    win: str
    lose: str
    losers: list[Loser]
    pool: int
    winners: list[Hashable]
    share: int
    rem_ids: list[Hashable]


@dataclass
class RoundOutcome:
    delta: dict[Hashable, int]
    groups: dict[str, list[Hashable]]
    pairs: list[PairResult] = field(default_factory=list)


def resolve_round(
    pilihan: Mapping[Hashable, str],
    hp: Mapping[Hashable, int],
    hp_kalah: int,
    urutan_masuk: Mapping[Hashable, int],
) -> RoundOutcome:
    """Hitung perubahan HP satu ronde.

    ``pilihan`` dan ``hp`` memakai kunci yang sama (id atau nama pemain).
    ``hp`` adalah HP di awal ronde. Urutan iterasi ``pilihan`` menentukan
    urutan anggota tiap golongan.
    """
    groups: dict[str, list[Hashable]] = {s: [] for s in SENJATA}
    for pid, senjata in pilihan.items():
        groups[senjata].append(pid)
    for s in SENJATA:
        groups[s].sort(key=lambda p: urutan_masuk[p])

    delta: dict[Hashable, int] = {pid: 0 for pid in pilihan}
    pairs: list[PairResult] = []
    for menang in SENJATA:
        kalah = MENGALAHKAN[menang]
        pemenang, pecundang = groups[menang], groups[kalah]
        if not pemenang or not pecundang:
            continue
        losers = [Loser(pid, min(hp_kalah, hp[pid])) for pid in pecundang]
        pool = sum(l.amt for l in losers)
        share, sisa = divmod(pool, len(pemenang))
        rem_ids = sorted(pemenang, key=lambda p: (hp[p], urutan_masuk[p]))[:sisa]
        for l in losers:
            delta[l.id] -= l.amt
        for pid in pemenang:
            delta[pid] += share
        for pid in rem_ids:
            delta[pid] += 1
        pairs.append(PairResult(menang, kalah, losers, pool, list(pemenang), share, rem_ids))
    return RoundOutcome(delta=delta, groups=groups, pairs=pairs)
