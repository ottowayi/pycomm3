from __future__ import annotations
import pytest

from pycomm3 import USINT, UINT
from pycomm3.data_types import STRING, STRING2, STRINGI, STRINGN, SHORT_STRING
from pycomm3.exceptions import DataError


str_maxes = [
    (SHORT_STRING, 'x' * 255, b'\xFF' + b'x' * 255),
    (STRING, 'x' * 65_535, b'\xFF\xFF' + b'x' * 65_535),
    (STRING2, 'x' * 65_535, b'\xFF\xFF' + b'x\x00' * 65_535),
    (STRINGN, 'x' * 65_535, b'\x01\x00\xFF\xFF' + b'x' * 65_535),
]
string_tests = [
    (SHORT_STRING, '', b'\x00'),
    (STRING, '', b'\x00\x00'),
    (STRING2, '', b'\x00\x00'),
    (SHORT_STRING, 'hello', b'\x05hello'),
    (STRING, 'hello', b'\x05\x00hello'),
    (STRING2, 'hello', b'\x05\x00' + 'hello'.encode('utf-16-le')),
    *str_maxes,
]


@pytest.mark.parametrize(
    'typ, val, bites',
    string_tests,
    ids=[
        f'string_{i}' for i in range(len(string_tests))
    ],  # fix error with env var size limits on windows
)
def test_strings(typ, val, bites):
    assert typ(val) == val
    assert bytes(typ(val)) == bites
    assert typ(val).__encoded_value__ == bites


@pytest.mark.parametrize(
    'typ, val, bites',
    str_maxes,
    ids=[
        f'string_{i}' for i in range(len(str_maxes))
    ],  # fix error with env var size limits on windows
)
def test_limits(typ, val, bites):
    with pytest.raises(DataError):
        typ(val + 'z')


def test_stringn_default():
    val = 'hello world'
    utf8 = b''.join(
        (b'\x01\x00', b'\x0a\x00', val.encode('utf-8'))  # encoding: 1  # char count: 10
    )

    _str = STRINGN(val)
    assert _str == val
    assert _str.encoding == STRINGN.Encoding.utf_8
    assert _str == STRINGN.decode(bytes(_str))


stringn_tests = [
    # string val, [char size][char count][string], encoding
    ('hello there', b'\x01\x00' b'\x0b\x00' b'hello there', STRINGN.Encoding.utf_8),
    (
        'general kenobi',
        b'\x02\x00\x0e\x00'
        b'g\x00e\x00n\x00e\x00r\x00a\x00l\x00 \x00k\x00e\x00n\x00o\x00b\x00i\x00',
        STRINGN.Encoding.utf_16,
    ),
    (
        'more lightsabers for my collection',
        b'\x04\x00\x22\x00'
        b'm\x00\x00\x00o\x00\x00\x00r\x00\x00\x00e\x00\x00\x00 \x00\x00\x00l\x00\x00\x00i'
        b'\x00\x00\x00g\x00\x00\x00h\x00\x00\x00t\x00\x00\x00s\x00\x00\x00a\x00\x00\x00b'
        b'\x00\x00\x00e\x00\x00\x00r\x00\x00\x00s\x00\x00\x00 \x00\x00\x00f\x00\x00\x00o'
        b'\x00\x00\x00r\x00\x00\x00 \x00\x00\x00m\x00\x00\x00y\x00\x00\x00 \x00\x00\x00c'
        b'\x00\x00\x00o\x00\x00\x00l\x00\x00\x00l\x00\x00\x00e\x00\x00\x00c\x00\x00\x00t'
        b'\x00\x00\x00i\x00\x00\x00o\x00\x00\x00n\x00\x00\x00',
        STRINGN.Encoding.utf_32,
    ),
]


@pytest.mark.parametrize('val, bites, encoding', stringn_tests)
def test_stringn(val, bites, encoding):
    _str = STRINGN(val, encoding=encoding)
    assert _str == val
    assert bytes(_str) == bites
    assert _str.__encoded_value__ == bites
    assert len(_str.__encoded_value__) == (encoding * len(val)) + 4  # 4 = len & char size

    assert _str.encoding == encoding  # instance var set for encoding
    assert STRINGN.encoding == STRINGN.Encoding.utf_8  # don't override class var

    assert STRINGN.encode(val, encoding=encoding) == bites
    assert STRINGN.decode(bites) == _str


stringi_tests = [
    (
        [
            (
                str0 := 'what about',
                STRING,
                STRINGI.Language.english,
                STRINGI.CharSet.iso_8859_1,
            ),
            (
                str1 := "l'attaque des droïdes",
                STRING,
                STRINGI.Language.french,
                STRINGI.CharSet.iso_8859_1,
            ),
            (
                str2 := 'on the wookies',
                SHORT_STRING,
                STRINGI.Language.english,
                STRINGI.CharSet.iso_8859_6,
            )
        ],
        b''.join(
            (
                b'\x03',  # num strings
                b'eng',
                USINT.encode(STRING.code),
                UINT.encode(4),
                UINT.encode(len(str0)),
                str0.encode('iso-8859-1'),
                b'fra',
                USINT.encode(STRING.code),
                UINT.encode(4),
                UINT.encode(len(str1)),
                str1.encode('iso-8859-1'),
                b'eng',
                USINT.encode(SHORT_STRING.code),
                UINT.encode(9),
                USINT.encode(len(str2)),
                str2.encode('iso-8859-6'),
            )
        ),
    ),
]


@pytest.mark.parametrize('strings, bites', stringi_tests)
def test_stringi(
    strings: list[
        tuple[
            str, type[STRING | STRING2 | STRINGN | SHORT_STRING], STRINGI.Language, STRINGI.CharSet
        ]
    ],
    bites: bytes,
):
    _str = STRINGI(*(STRINGI.istr(*s) for s in strings))
    assert bytes(_str) == bites
    assert _str.__encoded_value__ == bites
    assert _str.get() == strings[0][0]
    assert _str.get(STRINGI.Language.french) == strings[1][0]

    decoded = STRINGI.decode(bytes(_str))
    assert decoded == _str
    assert decoded._strs[0] == STRINGI.istr(*strings[0])
