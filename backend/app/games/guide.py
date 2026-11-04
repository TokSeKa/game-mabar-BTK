"""Panduan markdown per game (untuk pemain dan untuk ditempel ke AI)."""

from __future__ import annotations

from .base import BASE_DOCS, Game

BAHASA = """## Bahasa bot (sama untuk semua game)

- Bot ditulis dalam **subset Python** dan dijalankan interpreter khusus (bukan Python biasa).
- Boleh: variabel, `+ - * / // % **`, perbandingan, `and/or/not`, `if/elif/else`, `for`, `while`, `break`, `continue`,
  `def` (fungsi bantu), `lambda`, list, dict, tuple, comprehension, f-string, dan fungsi bawaan
  `len, range, min, max, sum, abs, round, int, float, str, bool, list, dict, tuple, sorted, reversed, enumerate, zip, any, all, print`.
- Method list: `append, extend, insert, pop, remove, index, count, copy, reverse, sort, clear`.
  Method dict: `get, keys, values, items, copy, pop, setdefault, update, clear`. Method teks: `upper, lower, strip, split, join, replace, find, count, startswith, endswith`.
- **Dilarang/tidak ada:** `import`, `random`, `class`, `try/except`, `global`, `with`, `yield`, set `{1,2}`, atribut berawalan `_`, `open/eval/exec/getattr/type`.
- **Tidak ada memori antar langkah.** Setiap kali bot dipanggil, seluruh kode dijalankan dari nol. Semua informasi diambil dari `info()`.
- **Tidak ada keacakan.** Bot yang sama dengan info yang sama selalu memberi aksi yang sama.
- Batas: 20.000 langkah per pemanggilan, list/teks maks 10.000 isi. Kalau bot error atau aksinya tidak valid, langkah itu memakai **aksi bawaan**.
  Error 3 kali berturut-turut → bot dimatikan dan selalu memakai aksi bawaan.
- `print(...)` ditulis ke log botmu (hanya kamu yang bisa melihat, muncul di layar hasil).
"""


def guide_markdown(g: Game) -> str:
    lines = [
        f"# Panduan Bot: {g.nama}",
        "",
        "> **Untuk AI yang membaca dokumen ini:** bantu pemain menulis bot untuk game ini. Tulis **satu blok kode Python lengkap** "
        f"yang berisi `def {g.fungsi_bot}():` dan hanya memakai fitur di bawah. Jangan memakai `import`, `random`, `class`, `try`, `global`, "
        "atau variabel yang diharapkan tersimpan antar langkah. Setelah kode, jelaskan strateginya singkat dalam bahasa Indonesia.",
        "",
        f"**{g.ringkas}**",
        "",
        f"Pemain: {g.min_pemain}–{g.max_pemain}. Fungsi wajib: `def {g.fungsi_bot}():`.",
        "",
        "## Aturan",
        "",
        g.aturan.strip(),
        "",
        "## Aksi yang dikembalikan",
        "",
        g.format_aksi.strip(),
        "",
        "## Isi `info()`",
        "",
        g.format_info.strip(),
        "",
        "## Fungsi yang tersedia",
        "",
        "| Fungsi | Keterangan |",
        "|---|---|",
    ]
    for d in BASE_DOCS + g.lib_docs:
        lines.append(f"| `{d['tanda']}` | {d['ket']} |")
    if g.settings:
        lines += ["", "## Pengaturan room (diatur host)", "", "| Pengaturan | Default | Keterangan |", "|---|---|---|"]
        for st in g.settings:
            lines.append(f"| {st.label} | {st.default} | {st.ket} |")
    lines += ["", BAHASA, "## Contoh bot", ""]
    for t in g.templates:
        lines += [f"### {t['nama']}", "", t["ket"], "", "```python", t["kode"].rstrip(), "```", ""]
    return "\n".join(lines)
