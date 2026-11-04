import pytest

from app.bot.errors import BotError
from app.bot.validator import compile_bot

OK = "def pilih():\n    return BATU\n"


def err(code: str) -> BotError:
    with pytest.raises(BotError) as e:
        compile_bot(code)
    return e.value


def test_kode_valid():
    assert compile_bot(OK).tree is not None


@pytest.mark.parametrize("code, kata", [
    ("import os\n" + OK, "import"),
    ("from os import path\n" + OK, "import"),
    ("class A:\n    pass\n" + OK, "class"),
    ("def pilih():\n    global x\n    return BATU\n", "global"),
    ("def pilih():\n    try:\n        pass\n    except:\n        pass\n    return BATU\n", "try"),
    ("def pilih():\n    x = {1, 2}\n    return BATU\n", "set"),
    ("def pilih():\n    with x:\n        pass\n    return BATU\n", "with"),
    ("def pilih():\n    del x\n    return BATU\n", "del"),
    ("def pilih():\n    return ().__class__\n", "__class__"),
    ("def pilih():\n    return [].append\n", "memanggil"),
    ("def pilih():\n    return 'a'.format(1)\n", "format"),
    ("def pilih():\n    return __import__('os')\n", "__import__"),
    ("def pilih():\n    BATU = 1\n    return BATU\n", "konstanta"),
    ("def pilih():\n    return 1 << 3\n", "<<"),
    ("def pilih():\n    yield BATU\n", "yield"),
    ("def pilih(x):\n    return BATU\n", "parameter wajib"),
    ("def lain():\n    return BATU\n", "def pilih"),
    ("@d\ndef pilih():\n    return BATU\n", "dekorator"),
    ("def pilih(*a):\n    return BATU\n", "*args"),
    ("def pilih():\n    return b'x'\n", "jenis nilai"),
])
def test_ditolak(code, kata):
    assert kata in err(code).pesan


def test_syntax_error_bahasa_indonesia_dan_baris():
    e = err("def pilih():\n    if True\n        return BATU\n")
    assert e.baris == 2
    assert "':'" in e.pesan


def test_return_di_luar_fungsi():
    assert "fungsi" in err("return 1\n" + OK).pesan


def test_kode_terlalu_panjang():
    assert "terlalu panjang" in err(OK + "#" * 10_001).pesan


def test_terlalu_bertingkat():
    code = "def pilih():\n    return " + "[" * 100 + "1" + "]" * 100 + "\n"
    pesan = err(code).pesan
    assert "bertingkat" in pesan or "rumit" in pesan
