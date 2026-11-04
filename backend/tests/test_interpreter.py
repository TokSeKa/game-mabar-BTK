import pytest

from app.bot.errors import BotError, StepLimitExceeded
from app.bot.interpreter import Interpreter, Limits
from app.bot.validator import compile_bot


def run(body: str, limits: Limits | None = None, lib=None):
    code = "def pilih():\n" + "".join("    " + line + "\n" for line in body.strip("\n").split("\n"))
    it = Interpreter(compile_bot(code), lib or {}, limits)
    it.run_module()
    return it.call_function("pilih"), it


def val(body: str):
    return run(body)[0]


def bot_err(body: str, limits: Limits | None = None) -> BotError:
    with pytest.raises(BotError) as e:
        run(body, limits)
    return e.value


def test_aritmetika_dan_variabel():
    assert val("x = 7\ny = 3\nreturn [x + y, x - y, x * y, x // y, x % y, x ** 2, x / 2]") == [10, 4, 21, 2, 1, 49, 3.5]


def test_if_elif_else():
    assert val("x = 5\nif x > 10:\n    return 'a'\nelif x > 3:\n    return 'b'\nelse:\n    return 'c'") == "b"


def test_for_while_break_continue():
    assert val("t = 0\nfor i in range(10):\n    if i == 7:\n        break\n    if i % 2:\n        continue\n    t += i\nreturn t") == 0 + 2 + 4 + 6
    assert val("i = 0\nwhile i < 5:\n    i += 1\nelse:\n    i = 100\nreturn i") == 100


def test_list_dict_method():
    assert val("a = [3, 1, 2]\na.append(5)\na.sort()\nreturn a") == [1, 2, 3, 5]
    assert val("d = {'batu': 1}\nd['kertas'] = d.get('kertas', 0) + 2\nreturn sorted(d.items())") == [("batu", 1), ("kertas", 2)]
    assert val("return ' '.join(['a', 'b']).upper()") == "A B"


def test_comprehension_lambda_sorted():
    assert val("return [x * x for x in range(5) if x % 2 == 0]") == [0, 4, 16]
    assert val("return {k: v for k, v in [('a', 1), ('b', 2)]}") == {"a": 1, "b": 2}
    assert val("return sorted(['ccc', 'a', 'bb'], key=lambda s: len(s), reverse=True)") == ["ccc", "bb", "a"]
    assert val("return sum(x for x in [1, 2, 3])") == 6
    assert val("return max([3, 9, 2], key=lambda x: -x)") == 2


def test_fungsi_bantu_dan_default():
    code = (
        "def dobel(x, kali=2):\n    return x * kali\n\n"
        "def pilih():\n    return [dobel(3), dobel(3, 3), dobel(x=1, kali=5)]\n"
    )
    it = Interpreter(compile_bot(code), {})
    it.run_module()
    assert it.call_function("pilih") == [6, 9, 5]


def test_closure_dan_rekursi():
    code = (
        "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n\n"
        "def pilih():\n    return fib(10)\n"
    )
    it = Interpreter(compile_bot(code), {})
    it.run_module()
    assert it.call_function("pilih") == 55


def test_fstring_dan_print():
    v, it = run("x = 3.14159\nprint('nilai', x)\nprint(f'{x:.2f}|{[1, 2]}|{\"a\"!r}')\nreturn 1")
    assert it.prints == ["nilai 3.14159", "3.14|[1, 2]|'a'"]


def test_unpacking():
    assert val("a, b = [1, 2]\nreturn b, a") == (2, 1)
    assert "jumlah nilai" in bot_err("a, b = [1, 2, 3]\nreturn a").pesan


def test_error_bahasa_indonesia_dengan_baris():
    e = bot_err("x = 1\ny = x / 0\nreturn y")
    assert e.baris == 3 and "nol" in e.pesan
    e = bot_err("return belum_ada")
    assert "belum dibuat" in e.pesan and e.baris == 2
    assert "kunci" in bot_err("d = {}\nreturn d['x']").pesan
    assert "indeks" in bot_err("return [1][5]").pesan
    assert "antara angka dan teks" in bot_err("return 1 + 'a'").pesan
    assert "bukan fungsi" in bot_err("x = 3\nreturn x()").pesan


def test_batas_langkah():
    with pytest.raises(StepLimitExceeded):
        run("while True:\n    pass", Limits(max_steps=1000))


def test_batas_rekursi():
    code = "def f(n):\n    return f(n + 1)\n\ndef pilih():\n    return f(0)\n"
    it = Interpreter(compile_bot(code), {}, Limits(max_steps=10**6))
    it.run_module()
    with pytest.raises(BotError) as e:
        it.call_function("pilih")
    assert "bertumpuk" in e.value.pesan


@pytest.mark.parametrize("body", [
    "return [0] * 100000",
    "return 'a' * 100000",
    "s = 'ab'\nfor i in range(30):\n    s = s + s\nreturn s",
    "a = [1]\nfor i in range(30):\n    a.extend(a)\nreturn a",
    "return 10 ** 100",
    "x = 2\nfor i in range(100):\n    x = x * x\nreturn x",
    "return list(range(10 ** 9))",
    "return 'x'.replace('', 'y' * 5000) * 3",
    "return f'{1:99999}'",
])
def test_data_raksasa_ditolak(body):
    e = bot_err(body, Limits(max_steps=10**6))
    assert any(k in e.pesan for k in ("terlalu", "besar", "panjang", "lebar"))


@pytest.mark.parametrize("body", [
    "return open('x')",
    "return eval('1')",
    "return exec('1')",
    "return getattr(1, 'real')",
    "return globals()",
    "return type(1)",
    "return vars()",
    "return compile('1', 'x', 'exec')",
])
def test_fungsi_berbahaya_tidak_ada(body):
    assert "belum dibuat" in bot_err(body).pesan


def test_method_tidak_diizinkan_per_tipe():
    assert "tidak punya" in bot_err("return (1).upper()").pesan


def test_str_aman_untuk_struktur_raksasa():
    v = val("a = [1] * 9000\nb = [a] * 9000\nreturn len(str(b))")
    assert v <= 10_001
