"""Interpreter mini-Python untuk bot.

Menjalankan AST yang sudah lolos ``validator.compile_bot``. Setiap node yang
dievaluasi dihitung sebagai satu "langkah"; kalau melewati batas, bot
dihentikan. Semua operasi yang bisa membuat data sangat besar (perkalian list,
pangkat, penggabungan teks, dsb.) dicek ukurannya dulu.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .errors import BotError, StepLimitExceeded
from .validator import ALLOWED_METHODS, CompiledBot


@dataclass
class Limits:
    max_steps: int = 20_000
    max_len: int = 10_000          # panjang maksimal list / dict / teks
    max_int: int = 10**18
    max_depth: int = 40            # kedalaman pemanggilan fungsi
    max_prints: int = 20
    max_print_len: int = 200


# ---------------------------------------------------------------- nilai fungsi
class LibFunction:
    """Fungsi bawaan (library game atau builtin aman)."""

    __slots__ = ("name", "fn", "cost")

    def __init__(self, name: str, fn: Callable[..., Any], cost: int = 1):
        self.name, self.fn, self.cost = name, fn, cost

    def __call__(self, *args, **kwargs):  # dipakai sebagai key= di sorted/min/max
        return self.fn(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<fungsi {self.name}>"


class UserFunction:
    """Fungsi yang ditulis pemain (def atau lambda)."""

    __slots__ = ("node", "env", "interp", "name", "defaults")

    def __init__(self, node, env, interp, name, defaults):
        self.node, self.env, self.interp, self.name, self.defaults = node, env, interp, name, defaults

    def __call__(self, *args, **kwargs):
        return self.interp.call_user(self, list(args), kwargs)

    def __repr__(self) -> str:
        return f"<fungsi {self.name}>"


class Env:
    __slots__ = ("vars", "parent", "fname")

    def __init__(self, parent: "Env | None" = None, fname: str = ""):
        self.vars: dict[str, Any] = {}
        self.parent = parent
        self.fname = fname


class _Return(BaseException):
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


class _Break(BaseException):
    pass


class _Continue(BaseException):
    pass


# ---------------------------------------------------------------- helper teks
TYPE_NAMES = {
    bool: "True/False", int: "angka", float: "angka desimal", str: "teks",
    type(None): "None", list: "list", dict: "dict", tuple: "tuple", range: "range",
    UserFunction: "fungsi", LibFunction: "fungsi",
}


def tn(v: Any) -> str:
    return TYPE_NAMES.get(type(v), type(v).__name__)


OP_SYMBOL = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%",
    ast.Pow: "**", ast.FloorDiv: "//",
}

_SPEC_DIGITS = re.compile(r"\d+")


def to_text(v: Any, limit: int, top: bool = True) -> str:
    """str()/repr() aman: dibatasi panjangnya dan kedalamannya."""
    out: list[str] = []
    budget = [limit]

    def emit(s: str) -> None:
        if budget[0] <= 0:
            return
        if len(s) > budget[0]:
            s = s[: budget[0]] + "…"
        budget[0] -= len(s)
        out.append(s)

    def rec(x: Any, depth: int, top_level: bool) -> None:
        if budget[0] <= 0:
            return
        if depth > 20:
            emit("…")
            return
        t = type(x)
        if t is str:
            emit(x if top_level else repr(x))
        elif t in (int, bool, float, type(None)):
            emit(repr(x))
        elif t in (list, tuple):
            emit("[" if t is list else "(")
            for i, item in enumerate(x):
                if i:
                    emit(", ")
                rec(item, depth + 1, False)
                if budget[0] <= 0:
                    return
            if t is tuple and len(x) == 1:
                emit(",")
            emit("]" if t is list else ")")
        elif t is dict:
            emit("{")
            for i, (k, val) in enumerate(x.items()):
                if i:
                    emit(", ")
                rec(k, depth + 1, False)
                emit(": ")
                rec(val, depth + 1, False)
                if budget[0] <= 0:
                    return
            emit("}")
        elif t is range:
            emit(repr(x))
        else:
            emit(repr(x))

    rec(v, 0, top)
    return "".join(out)


def _convert_exception(e: Exception) -> BotError:
    if isinstance(e, BotError):
        return e
    if isinstance(e, ZeroDivisionError):
        return BotError("pembagian dengan nol")
    if isinstance(e, IndexError):
        return BotError("indeks di luar jangkauan (list/teks tidak sepanjang itu)")
    if isinstance(e, KeyError):
        key = e.args[0] if e.args else "?"
        return BotError(f"kunci {key!r} tidak ada di dict. Pakai .get(kunci, nilai_awal) kalau belum tentu ada")
    if isinstance(e, TypeError):
        msg = str(e)
        if "unhashable" in msg:
            return BotError("list/dict tidak bisa dijadikan kunci dict")
        if "not supported between" in msg:
            return BotError("dua nilai ini tidak bisa dibandingkan dengan <, >, <=, >=")
        return BotError(f"tipe data tidak cocok ({msg})")
    if isinstance(e, ValueError):
        return BotError(f"nilai tidak valid ({e})")
    if isinstance(e, OverflowError):
        return BotError("angka terlalu besar")
    if isinstance(e, RecursionError):
        return BotError("terlalu dalam (fungsi memanggil dirinya sendiri terlalu banyak?)")
    if isinstance(e, MemoryError):
        return BotError("memori habis")
    if isinstance(e, RuntimeError) and "changed size" in str(e):
        return BotError("list/dict diubah saat sedang diulang dengan for")
    return BotError(f"terjadi kesalahan ({type(e).__name__})")


# ---------------------------------------------------------------- interpreter
class Interpreter:
    def __init__(self, compiled: CompiledBot, library: dict[str, Any], limits: Limits | None = None,
                 trace: list[dict[str, Any]] | None = None):
        self.trace = trace  # kalau diisi: catat baris & variabel setiap statement (untuk debugger)
        self.tree = compiled.tree
        self.limits = limits or Limits()
        self.steps = 0
        self.depth = 0
        self.prints: list[str] = []
        self.library = library
        self.builtins = self._make_builtins()
        self.genv = Env()
        self._stmt = {
            ast.FunctionDef: self.s_def, ast.Return: self.s_return, ast.Assign: self.s_assign,
            ast.AugAssign: self.s_augassign, ast.AnnAssign: self.s_annassign, ast.For: self.s_for,
            ast.While: self.s_while, ast.If: self.s_if, ast.Expr: self.s_expr, ast.Pass: self.s_pass,
            ast.Break: self.s_break, ast.Continue: self.s_continue,
        }
        self._expr = {
            ast.Constant: self.e_const, ast.Name: self.e_name, ast.BinOp: self.e_binop,
            ast.UnaryOp: self.e_unary, ast.BoolOp: self.e_boolop, ast.Compare: self.e_compare,
            ast.IfExp: self.e_ifexp, ast.Call: self.e_call, ast.Subscript: self.e_subscript,
            ast.List: self.e_list, ast.Tuple: self.e_tuple, ast.Dict: self.e_dict,
            ast.ListComp: self.e_listcomp, ast.GeneratorExp: self.e_listcomp,
            ast.DictComp: self.e_dictcomp, ast.Lambda: self.e_lambda,
            ast.JoinedStr: self.e_joinedstr, ast.FormattedValue: self.e_formatted,
        }

    # ------------------------------------------------------------ entry
    def run_module(self) -> None:
        self.exec_block(self.tree.body, self.genv)

    def call_function(self, name: str, args: list | None = None) -> Any:
        f = self.genv.vars.get(name)
        if not isinstance(f, UserFunction):
            raise BotError(f"fungsi {name}() tidak ditemukan")
        return self.call_user(f, args or [], {})

    # ------------------------------------------------------------ helper
    def charge(self, n: int = 1) -> None:
        self.steps += n
        if self.steps > self.limits.max_steps:
            raise StepLimitExceeded(
                f"bot kehabisan langkah (maksimal {self.limits.max_steps} per ronde). "
                "Mungkin ada perulangan yang tidak pernah berhenti?"
            )

    def check_len(self, n: int, what: str = "list/teks") -> None:
        if n > self.limits.max_len:
            raise BotError(f"{what} terlalu panjang (maksimal {self.limits.max_len})")

    def check_num(self, v: Any) -> Any:
        t = type(v)
        if t is int and (v > self.limits.max_int or v < -self.limits.max_int):
            raise BotError(f"angka terlalu besar (maksimal {self.limits.max_int:.0e})")
        if t is complex:
            raise BotError("hasil hitungan bukan angka biasa (bilangan kompleks)")
        return v

    def materialize(self, obj: Any) -> list:
        if isinstance(obj, range):
            self.check_len(len(obj))
            self.charge(len(obj) // 10 + 1)
            return list(obj)
        if isinstance(obj, (list, tuple, str)):
            self.charge(len(obj) // 10 + 1)
            return list(obj)
        if isinstance(obj, dict):
            self.charge(len(obj) // 10 + 1)
            return list(obj.keys())
        raise BotError(f"{tn(obj)} tidak bisa diulang (bukan list/teks/dict/range)")

    def iterate(self, obj: Any) -> Iterable:
        if not isinstance(obj, (list, tuple, str, dict, range)):
            raise BotError(f"{tn(obj)} tidak bisa diulang dengan for")
        for x in obj:
            self.charge()
            yield x

    def lookup(self, name: str, env: Env) -> Any:
        e: Env | None = env
        while e is not None:
            if name in e.vars:
                return e.vars[name]
            e = e.parent
        if name in self.library:
            return self.library[name]
        if name in self.builtins:
            return self.builtins[name]
        raise BotError(f"nama '{name}' belum dibuat atau salah ketik")

    # ------------------------------------------------------------ statement
    def exec_block(self, stmts: list[ast.stmt], env: Env) -> None:
        for st in stmts:
            try:
                self.charge()
                if self.trace is not None and isinstance(st, ast.If):
                    self._record(st, env)          # if: catat sebelum kondisinya diperiksa
                self._stmt[type(st)](st, env)
                if self.trace is not None and not isinstance(st, (ast.FunctionDef, ast.If, ast.For, ast.While)):
                    self._record(st, env)          # statement biasa: catat setelah dijalankan
            except (_Return, _Break, _Continue):
                raise
            except BotError as e:
                if e.baris is None:
                    e.baris = st.lineno
                raise
            except Exception as e:  # noqa: BLE001 - semua error diubah jadi pesan untuk pemain
                err = _convert_exception(e)
                err.baris = st.lineno
                raise err from None

    def _record(self, st: ast.stmt, env: Env) -> None:
        if self.trace is None or len(self.trace) >= 600:
            return
        vars_ = {}
        for k, v in env.vars.items():
            if isinstance(v, (UserFunction, LibFunction)):
                continue
            vars_[k] = to_text(v, 120, top=False)
        self.trace.append({"baris": st.lineno, "fungsi": getattr(env, "fname", ""), "vars": vars_, "langkah": self.steps})

    def s_def(self, node: ast.FunctionDef, env: Env) -> None:
        defaults = [self.eval(d, env) for d in node.args.defaults]
        env.vars[node.name] = UserFunction(node, env, self, node.name, defaults)

    def s_return(self, node: ast.Return, env: Env) -> None:
        value = self.eval(node.value, env) if node.value is not None else None
        if self.trace is not None and len(self.trace) < 600:
            self._record(node, env)
            self.trace[-1]["kembali"] = to_text(value, 120, top=False)
            self.trace[-1]["fungsi"] = env.fname or self.trace[-1]["fungsi"]
        raise _Return(value)

    def s_assign(self, node: ast.Assign, env: Env) -> None:
        value = self.eval(node.value, env)
        for target in node.targets:
            self.assign(target, value, env)

    def s_annassign(self, node: ast.AnnAssign, env: Env) -> None:
        if node.value is not None:
            self.assign(node.target, self.eval(node.value, env), env)

    def s_augassign(self, node: ast.AugAssign, env: Env) -> None:
        t = node.target
        if isinstance(t, ast.Name):
            cur = self.lookup(t.id, env)
            env.vars[t.id] = self.binop(node.op, cur, self.eval(node.value, env))
        elif isinstance(t, ast.Subscript):
            container = self.eval(t.value, env)
            key = self.eval(t.slice, env)
            cur = self.get_item(container, key)
            self.set_item(container, key, self.binop(node.op, cur, self.eval(node.value, env)))
        else:
            raise BotError("tidak bisa memberi nilai ke sini")

    def s_for(self, node: ast.For, env: Env) -> None:
        broke = False
        for item in self.iterate(self.eval(node.iter, env)):
            self.assign(node.target, item, env)
            if self.trace is not None:
                self._record(node, env)            # setiap putaran, setelah variabel loop diisi
            try:
                self.exec_block(node.body, env)
            except _Break:
                broke = True
                break
            except _Continue:
                continue
        if not broke and node.orelse:
            self.exec_block(node.orelse, env)

    def s_while(self, node: ast.While, env: Env) -> None:
        broke = False
        while self.eval(node.test, env):
            self.charge()
            if self.trace is not None:
                self._record(node, env)
            try:
                self.exec_block(node.body, env)
            except _Break:
                broke = True
                break
            except _Continue:
                continue
        if not broke and node.orelse:
            self.exec_block(node.orelse, env)

    def s_if(self, node: ast.If, env: Env) -> None:
        if self.eval(node.test, env):
            self.exec_block(node.body, env)
        elif node.orelse:
            self.exec_block(node.orelse, env)

    def s_expr(self, node: ast.Expr, env: Env) -> None:
        self.eval(node.value, env)

    def s_pass(self, node, env) -> None:
        pass

    def s_break(self, node, env) -> None:
        raise _Break()

    def s_continue(self, node, env) -> None:
        raise _Continue()

    # ------------------------------------------------------------ assignment
    def assign(self, target: ast.expr, value: Any, env: Env) -> None:
        if isinstance(target, ast.Name):
            env.vars[target.id] = value
        elif isinstance(target, ast.Subscript):
            container = self.eval(target.value, env)
            key = self.eval(target.slice, env)
            self.set_item(container, key, value)
        elif isinstance(target, (ast.Tuple, ast.List)):
            items = self.materialize(value)
            if len(items) != len(target.elts):
                raise BotError(f"jumlah nilai ({len(items)}) tidak sama dengan jumlah variabel ({len(target.elts)})")
            for t, v in zip(target.elts, items):
                self.assign(t, v, env)
        else:
            raise BotError("tidak bisa memberi nilai ke sini")

    def get_item(self, container: Any, key: Any) -> Any:
        if isinstance(key, slice):
            if not isinstance(container, (list, tuple, str)):
                raise BotError(f"{tn(container)} tidak bisa dipotong dengan [a:b]")
            res = container[key]
            self.charge(len(res) // 10)
            return res
        if isinstance(container, dict):
            return container[key]
        if isinstance(container, (list, tuple, str, range)):
            if type(key) is not int and type(key) is not bool:
                raise BotError(f"indeks {tn(container)} harus angka bulat, bukan {tn(key)}")
            return container[key]
        raise BotError(f"{tn(container)} tidak bisa diambil isinya dengan [ ]")

    def set_item(self, container: Any, key: Any, value: Any) -> None:
        if isinstance(container, dict):
            if key not in container:
                self.check_len(len(container) + 1, "dict")
            container[key] = value
        elif isinstance(container, list):
            if isinstance(key, slice):
                raise BotError("mengganti potongan list [a:b] tidak didukung")
            if type(key) is not int:
                raise BotError(f"indeks list harus angka bulat, bukan {tn(key)}")
            container[key] = value
        else:
            raise BotError(f"isi {tn(container)} tidak bisa diubah")

    # ------------------------------------------------------------ expression
    def eval(self, node: ast.expr, env: Env) -> Any:
        self.charge()
        return self._expr[type(node)](node, env)

    def e_const(self, node: ast.Constant, env: Env) -> Any:
        return node.value

    def e_name(self, node: ast.Name, env: Env) -> Any:
        return self.lookup(node.id, env)

    def e_binop(self, node: ast.BinOp, env: Env) -> Any:
        return self.binop(node.op, self.eval(node.left, env), self.eval(node.right, env))

    def binop(self, op: ast.operator, a: Any, b: Any) -> Any:
        t = type(op)
        seq = (str, list, tuple)
        try:
            if t is ast.Add:
                if isinstance(a, seq) and type(a) is type(b):
                    self.check_len(len(a) + len(b))
                    self.charge((len(a) + len(b)) // 50)
                r = a + b
            elif t is ast.Mult:
                if isinstance(a, seq) and type(b) in (int, bool):
                    self.check_len(len(a) * max(int(b), 0))
                    self.charge(len(a) * max(int(b), 0) // 50)
                elif isinstance(b, seq) and type(a) in (int, bool):
                    self.check_len(len(b) * max(int(a), 0))
                    self.charge(len(b) * max(int(a), 0) // 50)
                r = a * b
            elif t is ast.Sub:
                r = a - b
            elif t is ast.Div:
                r = a / b
            elif t is ast.FloorDiv:
                r = a // b
            elif t is ast.Mod:
                if isinstance(a, str):
                    raise BotError("format teks dengan '%' tidak didukung. Pakai f\"...{nilai}...\"")
                r = a % b
            elif t is ast.Pow:
                if type(a) in (int, bool) and type(b) in (int, bool) and b > 0 and abs(a) > 1:
                    if b * math.log2(abs(a)) > 62:
                        raise BotError("hasil pangkat terlalu besar")
                r = a**b
            else:  # pragma: no cover - ditolak validator
                raise BotError("operator tidak didukung")
        except TypeError:
            raise BotError(f"tidak bisa memakai '{OP_SYMBOL.get(t, '?')}' antara {tn(a)} dan {tn(b)}") from None
        return self.check_num(r)

    def e_unary(self, node: ast.UnaryOp, env: Env) -> Any:
        v = self.eval(node.operand, env)
        t = type(node.op)
        if t is ast.Not:
            return not v
        if not isinstance(v, (int, float)):
            raise BotError(f"tanda '-' atau '+' hanya untuk angka, bukan {tn(v)}")
        return -v if t is ast.USub else +v

    def e_boolop(self, node: ast.BoolOp, env: Env) -> Any:
        if isinstance(node.op, ast.And):
            v = True
            for x in node.values:
                v = self.eval(x, env)
                if not v:
                    return v
            return v
        v = False
        for x in node.values:
            v = self.eval(x, env)
            if v:
                return v
        return v

    def e_compare(self, node: ast.Compare, env: Env) -> bool:
        left = self.eval(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = self.eval(comp, env)
            t = type(op)
            if t in (ast.In, ast.NotIn):
                if not isinstance(right, (list, tuple, str, dict, range)):
                    raise BotError(f"'in' butuh list/teks/dict di sebelah kanan, bukan {tn(right)}")
                if isinstance(right, str) and not isinstance(left, str):
                    raise BotError("'in' pada teks butuh teks juga di sebelah kiri")
                self.charge(len(right) // 20 if not isinstance(right, dict) else 0)
                ok = left in right
                if t is ast.NotIn:
                    ok = not ok
            elif t in (ast.Eq, ast.NotEq):
                if isinstance(left, (list, tuple, dict, str)):
                    self.charge(len(left) // 20)
                ok = (left == right) if t is ast.Eq else (left != right)
            elif t is ast.Is:
                ok = left is right
            elif t is ast.IsNot:
                ok = left is not right
            else:
                try:
                    if t is ast.Lt:
                        ok = left < right
                    elif t is ast.LtE:
                        ok = left <= right
                    elif t is ast.Gt:
                        ok = left > right
                    else:
                        ok = left >= right
                except TypeError:
                    raise BotError(f"tidak bisa membandingkan {tn(left)} dengan {tn(right)}") from None
            if not ok:
                return False
            left = right
        return True

    def e_ifexp(self, node: ast.IfExp, env: Env) -> Any:
        return self.eval(node.body, env) if self.eval(node.test, env) else self.eval(node.orelse, env)

    def e_list(self, node: ast.List, env: Env) -> list:
        return [self.eval(e, env) for e in node.elts]

    def e_tuple(self, node: ast.Tuple, env: Env) -> tuple:
        return tuple(self.eval(e, env) for e in node.elts)

    def e_dict(self, node: ast.Dict, env: Env) -> dict:
        out = {}
        for k, v in zip(node.keys, node.values):
            if k is None:
                raise BotError("'**' di dalam dict tidak didukung")
            key = self.eval(k, env)
            try:
                out[key] = self.eval(v, env)
            except TypeError:
                raise BotError("list/dict tidak bisa dijadikan kunci dict") from None
        return out

    def _comp(self, gens: list[ast.comprehension], i: int, env: Env, emit: Callable[[], None]) -> None:
        g = gens[i]
        for item in self.iterate(self.eval(g.iter, env)):
            self.assign(g.target, item, env)
            if all(self.eval(c, env) for c in g.ifs):
                if i + 1 == len(gens):
                    emit()
                else:
                    self._comp(gens, i + 1, env, emit)

    def e_listcomp(self, node, env: Env) -> list:
        out: list = []
        cenv = Env(env)

        def emit() -> None:
            out.append(self.eval(node.elt, cenv))
            self.check_len(len(out))

        self._comp(node.generators, 0, cenv, emit)
        return out

    def e_dictcomp(self, node: ast.DictComp, env: Env) -> dict:
        out: dict = {}
        cenv = Env(env)

        def emit() -> None:
            k = self.eval(node.key, cenv)
            out[k] = self.eval(node.value, cenv)
            self.check_len(len(out), "dict")

        self._comp(node.generators, 0, cenv, emit)
        return out

    def e_lambda(self, node: ast.Lambda, env: Env) -> UserFunction:
        defaults = [self.eval(d, env) for d in node.args.defaults]
        return UserFunction(node, env, self, "lambda", defaults)

    def e_joinedstr(self, node: ast.JoinedStr, env: Env) -> str:
        parts = []
        total = 0
        for v in node.values:
            s = v.value if isinstance(v, ast.Constant) else self.eval(v, env)
            total += len(s)
            self.check_len(total, "teks")
            parts.append(s)
        return "".join(parts)

    def e_formatted(self, node: ast.FormattedValue, env: Env) -> str:
        v = self.eval(node.value, env)
        if node.conversion == ord("r"):
            v = to_text(v, self.limits.max_len, top=False)
        elif node.conversion in (ord("s"), ord("a")):
            v = to_text(v, self.limits.max_len)
        if node.format_spec is not None:
            spec = self.eval(node.format_spec, env)
            if any(len(m) > 3 for m in _SPEC_DIGITS.findall(spec)):
                raise BotError("format f-string terlalu lebar")
            if isinstance(v, (int, float, str)):
                try:
                    return format(v, spec)
                except ValueError:
                    raise BotError(f"format '{spec}' tidak cocok untuk {tn(v)}") from None
        return v if isinstance(v, str) else to_text(v, self.limits.max_len)

    def e_subscript(self, node: ast.Subscript, env: Env) -> Any:
        container = self.eval(node.value, env)
        if isinstance(node.slice, ast.Slice):
            s = node.slice
            parts = []
            for p in (s.lower, s.upper, s.step):
                val = self.eval(p, env) if p is not None else None
                if val is not None and type(val) not in (int, bool):
                    raise BotError("batas potongan [a:b] harus angka bulat")
                parts.append(val)
            return self.get_item(container, slice(*parts))
        return self.get_item(container, self.eval(node.slice, env))

    # ------------------------------------------------------------ calls
    def e_call(self, node: ast.Call, env: Env) -> Any:
        if isinstance(node.func, ast.Attribute):
            obj = self.eval(node.func.value, env)
            args = [self.eval(a, env) for a in node.args]
            kwargs = {k.arg: self.eval(k.value, env) for k in node.keywords}
            return self.call_method(obj, node.func.attr, args, kwargs)
        f = self.eval(node.func, env)
        args = [self.eval(a, env) for a in node.args]
        kwargs = {k.arg: self.eval(k.value, env) for k in node.keywords}
        return self.call(f, args, kwargs)

    def call(self, f: Any, args: list, kwargs: dict) -> Any:
        if type(f) is UserFunction:
            return self.call_user(f, args, kwargs)
        if type(f) is LibFunction:
            self.charge(f.cost)
            try:
                return f.fn(*args, **kwargs)
            except TypeError as e:
                if "argument" in str(e):
                    raise BotError(f"jumlah atau nama argumen untuk {f.name}() tidak sesuai") from None
                raise
        raise BotError(f"{tn(f)} bukan fungsi, jadi tidak bisa dipanggil dengan ( )")

    def call_user(self, f: UserFunction, args: list, kwargs: dict) -> Any:
        node = f.node
        params = [a.arg for a in node.args.args]
        if len(args) > len(params):
            raise BotError(f"{f.name}() menerima paling banyak {len(params)} argumen, tapi diberi {len(args)}")
        self.depth += 1
        try:
            if self.depth > self.limits.max_depth:
                raise BotError(f"terlalu banyak fungsi bertumpuk (maksimal {self.limits.max_depth}). Ada rekursi tanpa akhir?")
            env = Env(f.env, f.name)
            for p, v in zip(params, args):
                env.vars[p] = v
            for k, v in kwargs.items():
                if k not in params:
                    raise BotError(f"{f.name}() tidak punya parameter '{k}'")
                if k in env.vars:
                    raise BotError(f"parameter '{k}' untuk {f.name}() diisi dua kali")
                env.vars[k] = v
            first_default = len(params) - len(f.defaults)
            for idx, p in enumerate(params):
                if p not in env.vars:
                    if idx >= first_default:
                        env.vars[p] = f.defaults[idx - first_default]
                    else:
                        raise BotError(f"argumen '{p}' untuk {f.name}() belum diisi")
            if isinstance(node, ast.Lambda):
                return self.eval(node.body, env)
            try:
                self.exec_block(node.body, env)
            except _Return as r:
                return r.value
            except (_Break, _Continue):  # pragma: no cover - dicegah compile()
                raise BotError("'break/continue' di luar perulangan")
            return None
        finally:
            self.depth -= 1

    def _key(self, key: Any) -> Any:
        if key is None:
            return None
        if type(key) not in (UserFunction, LibFunction):
            raise BotError("key= harus berupa fungsi")
        return key

    def call_method(self, obj: Any, name: str, args: list, kwargs: dict) -> Any:
        allowed = ALLOWED_METHODS.get(type(obj))
        if allowed is None or name not in allowed:
            raise BotError(f"{tn(obj)} tidak punya fungsi .{name}()")
        self.charge()
        if isinstance(obj, list):
            if name in ("append", "insert"):
                self.check_len(len(obj) + 1)
            elif name == "extend":
                if len(args) != 1:
                    raise BotError(".extend() butuh tepat satu list")
                items = self.materialize(args[0])
                self.check_len(len(obj) + len(items))
                obj.extend(items)
                return None
            elif name == "sort":
                self.charge(len(obj) // 5)
                key = self._key(kwargs.get("key"))
                rev = bool(kwargs.get("reverse", False))
                if set(kwargs) - {"key", "reverse"} or args:
                    raise BotError(".sort() hanya menerima key= dan reverse=")
                obj.sort(key=key, reverse=rev)
                return None
            elif name in ("index", "count", "remove", "copy"):
                self.charge(len(obj) // 20)
        elif isinstance(obj, dict):
            if name in ("keys", "values", "items"):
                self.charge(len(obj) // 20)
                return list(getattr(obj, name)())
            if name == "update":
                if len(args) != 1 or not isinstance(args[0], dict) or kwargs:
                    raise BotError(".update() butuh tepat satu dict")
                self.check_len(len(obj) + len(args[0]), "dict")
            if name == "setdefault":
                self.check_len(len(obj) + 1, "dict")
        elif isinstance(obj, str):
            self.charge(len(obj) // 50)
            if name == "join":
                if len(args) != 1:
                    raise BotError(".join() butuh tepat satu list")
                items = self.materialize(args[0])
                if not all(isinstance(x, str) for x in items):
                    raise BotError(".join() hanya bisa menggabungkan list berisi teks")
                self.check_len(sum(len(x) for x in items) + len(obj) * max(len(items) - 1, 0), "teks")
                return obj.join(items)
            if name == "replace" and len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
                old, new = args[0], args[1]
                grow = len(new) - len(old)
                n = (len(obj) + 1) if old == "" else obj.count(old)
                self.check_len(len(obj) + max(grow, 0) * n, "teks")
        method = getattr(obj, name)
        result = method(*args, **kwargs)
        return result

    # ------------------------------------------------------------ builtins
    def _make_builtins(self) -> dict[str, LibFunction]:
        L = self.limits

        def _len(x):
            if not isinstance(x, (list, tuple, str, dict, range)):
                raise BotError(f"len() tidak bisa dipakai untuk {tn(x)}")
            return len(x)

        def _range(*a):
            if not 1 <= len(a) <= 3 or not all(type(x) in (int, bool) for x in a):
                raise BotError("range() butuh 1 sampai 3 angka bulat")
            return range(*a)

        def _minmax(fn, name):
            def inner(*a, key=None, default=None):
                key = self._key(key)
                items = self.materialize(a[0]) if len(a) == 1 else list(a)
                if not items:
                    if default is not None:
                        return default
                    raise BotError(f"{name}() dari list kosong")
                try:
                    return fn(items, key=key) if key else fn(items)
                except TypeError:
                    raise BotError(f"isi list untuk {name}() tidak bisa dibandingkan") from None
            return inner

        def _sum(x, start=0):
            items = self.materialize(x)
            total = start
            for it in items:
                if type(it) not in (int, float, bool):
                    raise BotError(f"sum() hanya untuk angka, ada {tn(it)} di dalamnya")
                total = self.check_num(total + it)
            return total

        def _abs(x):
            if type(x) not in (int, float, bool):
                raise BotError(f"abs() hanya untuk angka, bukan {tn(x)}")
            return abs(x)

        def _round(x, n=None):
            if type(x) not in (int, float, bool) or (n is not None and type(n) is not int):
                raise BotError("round() butuh angka")
            return round(x) if n is None else round(x, max(min(n, 15), -15))

        def _int(x=0):
            if isinstance(x, str):
                if len(x.strip()) > 19:
                    raise BotError("angka terlalu besar")
                try:
                    return int(x)
                except ValueError:
                    raise BotError(f"teks {x!r} bukan angka bulat") from None
            if type(x) not in (int, float, bool):
                raise BotError(f"int() tidak bisa mengubah {tn(x)}")
            if isinstance(x, float) and (math.isinf(x) or math.isnan(x)):
                raise BotError("angka tidak terhingga tidak bisa diubah jadi int")
            return self.check_num(int(x))

        def _float(x=0.0):
            if isinstance(x, str):
                if len(x) > 50:
                    raise BotError("teks terlalu panjang untuk float()")
                try:
                    return float(x)
                except ValueError:
                    raise BotError(f"teks {x!r} bukan angka") from None
            if type(x) not in (int, float, bool):
                raise BotError(f"float() tidak bisa mengubah {tn(x)}")
            return float(x)

        def _str(x=""):
            s = to_text(x, L.max_len)
            return s

        def _list(x=None):
            return [] if x is None else self.materialize(x)

        def _tuple(x=None):
            return () if x is None else tuple(self.materialize(x))

        def _dict(x=None):
            if x is None:
                return {}
            if isinstance(x, dict):
                return dict(x)
            items = self.materialize(x)
            out = {}
            for it in items:
                if not isinstance(it, (list, tuple)) or len(it) != 2:
                    raise BotError("dict() butuh list berisi pasangan (kunci, nilai)")
                out[it[0]] = it[1]
            return out

        def _sorted(x, key=None, reverse=False):
            items = self.materialize(x)
            self.charge(len(items) // 5)
            try:
                return sorted(items, key=self._key(key), reverse=bool(reverse))
            except TypeError:
                raise BotError("isi list untuk sorted() tidak bisa dibandingkan") from None

        def _reversed(x):
            return list(reversed(self.materialize(x)))

        def _enumerate(x, start=0):
            return [(i + start, v) for i, v in enumerate(self.materialize(x))]

        def _zip(*xs):
            lists = [self.materialize(x) for x in xs]
            return [tuple(t) for t in zip(*lists)]

        def _any(x):
            return any(self.materialize(x))

        def _all(x):
            return all(self.materialize(x))

        def _bool(x=False):
            return bool(x)

        def _print(*a, sep=" "):
            if len(self.prints) >= L.max_prints:
                return None
            s = str(sep).join(to_text(x, L.max_print_len) for x in a)
            if len(s) > L.max_print_len:
                s = s[: L.max_print_len] + "…"
            self.prints.append(s)
            return None

        fns = {
            "len": _len, "range": _range, "min": _minmax(min, "min"), "max": _minmax(max, "max"),
            "sum": _sum, "abs": _abs, "round": _round, "int": _int, "float": _float, "str": _str,
            "list": _list, "tuple": _tuple, "dict": _dict, "sorted": _sorted, "reversed": _reversed,
            "enumerate": _enumerate, "zip": _zip, "any": _any, "all": _all, "bool": _bool,
            "print": _print,
        }
        return {name: LibFunction(name, fn) for name, fn in fns.items()}
