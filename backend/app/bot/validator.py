"""Mengecek kode bot sebelum dijalankan.

Kode di-parse dengan parser Python, lalu setiap node dicek terhadap daftar
fitur yang diizinkan. Kode tidak pernah dijalankan dengan ``exec``; yang
menjalankannya adalah interpreter di ``interpreter.py``.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from .errors import BotError

MAX_KODE = 10_000
MAX_KEDALAMAN = 60

ALLOWED_NODES: tuple[type, ...] = (
    ast.Module,
    # statement
    ast.FunctionDef, ast.Return, ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.For, ast.While, ast.If, ast.Expr, ast.Pass, ast.Break, ast.Continue,
    # expression
    ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Lambda, ast.IfExp, ast.Dict,
    ast.ListComp, ast.DictComp, ast.GeneratorExp, ast.Compare, ast.Call,
    ast.FormattedValue, ast.JoinedStr, ast.Constant, ast.Attribute,
    ast.Subscript, ast.Name, ast.List, ast.Tuple, ast.Slice,
    # konteks & operator
    ast.Load, ast.Store,
    ast.And, ast.Or,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    ast.Not, ast.UAdd, ast.USub,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.comprehension, ast.arguments, ast.arg, ast.keyword,
)

_IMPORT = "'import' tidak diizinkan. Semua yang dibutuhkan bot sudah ada di library game."
_MEMORI = "'{0}' tidak didukung. Setiap ronde bot mulai dari nol, jadi tidak ada memori antar ronde."
REJECT_MESSAGES: dict[str, str] = {
    "Import": _IMPORT,
    "ImportFrom": _IMPORT,
    "ClassDef": "'class' tidak didukung. Pakai fungsi (def) saja.",
    "Try": "'try/except' tidak didukung.",
    "TryStar": "'try/except' tidak didukung.",
    "Raise": "'raise' tidak didukung.",
    "Assert": "'assert' tidak didukung.",
    "With": "'with' tidak didukung.",
    "AsyncWith": "'async' tidak didukung.",
    "AsyncFor": "'async' tidak didukung.",
    "AsyncFunctionDef": "'async' tidak didukung.",
    "Await": "'await' tidak didukung.",
    "Yield": "'yield' tidak didukung.",
    "YieldFrom": "'yield' tidak didukung.",
    "Global": _MEMORI.format("global"),
    "Nonlocal": _MEMORI.format("nonlocal"),
    "Delete": "'del' tidak didukung.",
    "Set": "set {...} tidak didukung. Pakai list [...] saja.",
    "SetComp": "set {...} tidak didukung. Pakai list [...] saja.",
    "NamedExpr": "operator ':=' tidak didukung.",
    "Starred": "tanda '*' untuk membongkar list tidak didukung.",
    "Match": "'match/case' tidak didukung. Pakai if/elif.",
    "MatMult": "operator '@' tidak didukung.",
    "BitAnd": "operator '&' tidak didukung. Untuk logika pakai 'and'.",
    "BitOr": "operator '|' tidak didukung. Untuk logika pakai 'or'.",
    "BitXor": "operator '^' tidak didukung. Untuk pangkat pakai '**'.",
    "LShift": "operator '<<' tidak didukung.",
    "RShift": "operator '>>' tidak didukung.",
    "Invert": "operator '~' tidak didukung.",
    "Del": "'del' tidak didukung.",
    "TypeAlias": "'type' alias tidak didukung.",
}

#: method yang boleh dipanggil, per tipe data
ALLOWED_METHODS: dict[type, frozenset[str]] = {
    list: frozenset({"append", "extend", "insert", "pop", "remove", "index", "count",
                     "copy", "reverse", "sort", "clear"}),
    dict: frozenset({"get", "keys", "values", "items", "copy", "pop", "setdefault",
                     "update", "clear"}),
    str: frozenset({"upper", "lower", "strip", "lstrip", "rstrip", "startswith", "endswith",
                    "split", "join", "replace", "find", "count", "capitalize", "title",
                    "isdigit"}),
    tuple: frozenset({"index", "count"}),
}
ALL_METHODS: frozenset[str] = frozenset().union(*ALLOWED_METHODS.values())

#: nama konstanta library yang tidak boleh ditimpa
PROTECTED_NAMES = frozenset({"BATU", "GUNTING", "KERTAS", "SENJATA"})

_SYNTAX_ID = [
    (re.compile(r"^invalid syntax"), "penulisan tidak valid"),
    (re.compile(r"^expected ':'"), "kurang tanda ':' di akhir baris"),
    (re.compile(r"^expected an indented block"), "baris setelah ':' harus menjorok ke dalam (indentasi)"),
    (re.compile(r"^unexpected indent"), "indentasi (spasi di awal baris) tidak terduga"),
    (re.compile(r"^unindent does not match"), "indentasi tidak sejajar dengan baris sebelumnya"),
    (re.compile(r"^unterminated string"), "teks belum ditutup dengan tanda kutip"),
    (re.compile(r"^unterminated triple-quoted string"), "teks belum ditutup dengan tanda kutip"),
    (re.compile(r"was never closed"), "ada kurung yang belum ditutup"),
    (re.compile(r"^unmatched"), "ada kurung tutup tanpa kurung buka"),
    (re.compile(r"'return' outside function"), "'return' hanya boleh di dalam fungsi"),
    (re.compile(r"'break' outside loop"), "'break' hanya boleh di dalam perulangan"),
    (re.compile(r"'continue' not properly in loop"), "'continue' hanya boleh di dalam perulangan"),
    (re.compile(r"^cannot assign to"), "tidak bisa memberi nilai ke sini"),
    (re.compile(r"inconsistent use of tabs and spaces"), "campuran tab dan spasi untuk indentasi"),
    (re.compile(r"^Did you mean '=='"), "untuk membandingkan pakai '==' bukan '='"),
]


def _translate_syntax(msg: str) -> str:
    for pattern, indo in _SYNTAX_ID:
        if pattern.search(msg):
            return indo
    return f"penulisan tidak valid ({msg})"


@dataclass(frozen=True)
class CompiledBot:
    source: str
    tree: ast.Module


def compile_bot(source: str, func: str = "pilih", hint: str = "BATU, GUNTING, atau KERTAS") -> CompiledBot:
    """Parse dan validasi kode bot. Lempar ``BotError`` kalau ada masalah.

    ``func`` = nama fungsi utama yang wajib ada (Suit: ``pilih``, game lain: ``aksi``).
    """
    if not isinstance(source, str):
        raise BotError("kode bot harus berupa teks")
    if len(source) > MAX_KODE:
        raise BotError(f"kode terlalu panjang ({len(source)} karakter, maksimal {MAX_KODE})")
    if "\x00" in source:
        raise BotError("kode berisi karakter yang tidak valid")
    try:
        tree = ast.parse(source, filename="<bot>", mode="exec")
        # compile hanya untuk menangkap error seperti 'return' di luar fungsi.
        # Hasilnya tidak pernah dijalankan.
        compile(tree, "<bot>", "exec", dont_inherit=True)
    except SyntaxError as e:
        raise BotError(_translate_syntax(e.msg or ""), e.lineno) from None
    except (RecursionError, MemoryError, ValueError):
        raise BotError("kode terlalu bertingkat atau terlalu rumit") from None

    _check_tree(tree)
    if not any(isinstance(n, ast.FunctionDef) and n.name == func for n in tree.body):
        raise BotError(f"bot harus punya fungsi 'def {func}():' yang mengembalikan {hint}")
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == func:
            required = len(n.args.args) - len(n.args.defaults)
            if required > 0:
                raise BotError(f"fungsi {func}() tidak boleh punya parameter wajib", n.lineno)
    return CompiledBot(source=source, tree=tree)


def _check_tree(tree: ast.Module) -> None:
    # iterative DFS supaya kode yang sangat bertingkat tidak membuat validator crash
    stack: list[tuple[ast.AST, ast.AST | None, int]] = [(tree, None, 0)]
    while stack:
        node, parent, depth = stack.pop()
        line = getattr(node, "lineno", None) or getattr(parent, "lineno", None)
        if depth > MAX_KEDALAMAN:
            raise BotError("kode terlalu bertingkat (terlalu banyak kurung atau blok di dalam blok)", line)
        name = type(node).__name__
        if not isinstance(node, ALLOWED_NODES):
            raise BotError(REJECT_MESSAGES.get(name, f"fitur Python '{name}' tidak didukung di bot"), line)
        _check_node(node, parent, line)
        for child in ast.iter_child_nodes(node):
            stack.append((child, node, depth + 1))


def _check_node(node: ast.AST, parent: ast.AST | None, line: int | None) -> None:
    if isinstance(node, ast.Name):
        if node.id.startswith("__"):
            raise BotError(f"nama '{node.id}' tidak diizinkan", line)
        if isinstance(node.ctx, ast.Store) and node.id in PROTECTED_NAMES:
            raise BotError(f"'{node.id}' adalah konstanta library dan tidak boleh diubah", line)
    elif isinstance(node, ast.Attribute):
        if node.attr.startswith("_"):
            raise BotError(f"atribut '{node.attr}' tidak diizinkan", line)
        if not (isinstance(parent, ast.Call) and parent.func is node):
            raise BotError(f"'.{node.attr}' hanya boleh dipakai untuk memanggil fungsi, misalnya daftar.append(x)", line)
        if node.attr not in ALL_METHODS:
            raise BotError(f"fungsi '.{node.attr}()' tidak tersedia", line)
    elif isinstance(node, ast.FunctionDef):
        if node.decorator_list:
            raise BotError("dekorator (@) tidak didukung", line)
        if getattr(node, "type_params", None):
            raise BotError("parameter tipe tidak didukung", line)
        if node.name.startswith("__"):
            raise BotError(f"nama fungsi '{node.name}' tidak diizinkan", line)
        if node.name in PROTECTED_NAMES:
            raise BotError(f"'{node.name}' adalah konstanta library dan tidak boleh diubah", line)
        _check_args(node.args, line)
    elif isinstance(node, ast.Lambda):
        _check_args(node.args, line)
    elif isinstance(node, ast.arg):
        if node.arg.startswith("__"):
            raise BotError(f"nama parameter '{node.arg}' tidak diizinkan", line)
    elif isinstance(node, ast.keyword):
        if node.arg is None:
            raise BotError("'**' untuk argumen tidak didukung", line)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, str, bool, type(None))) or isinstance(node.value, complex):
            raise BotError("jenis nilai ini tidak didukung (pakai angka, teks, True/False, atau None)", line)
    elif isinstance(node, ast.comprehension):
        if node.is_async:
            raise BotError("'async' tidak didukung", line)
    elif isinstance(node, (ast.For, ast.While)):
        pass
    elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
        pass


def _check_args(args: ast.arguments, line: int | None) -> None:
    if args.vararg or args.kwarg:
        raise BotError("'*args' dan '**kwargs' tidak didukung", line)
    if args.kwonlyargs or args.posonlyargs:
        raise BotError("jenis parameter ini tidak didukung; pakai parameter biasa", line)
