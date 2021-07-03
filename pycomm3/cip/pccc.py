# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from itertools import chain
from io import BytesIO

from .data_types import INT, DINT, REAL, StringDataType, UINT

from ..map import EnumMap


class PCCCStringType(StringDataType):
    @classmethod
    def _slc_string_swap(cls, data):
        pairs = [
            (x2, x1) for x1, x2 in (data[i : i + 2] for i in range(0, len(data), 2))
        ]
        return bytes(chain.from_iterable(pairs))


class PCCC_ASCII(PCCCStringType):
    @classmethod
    def _encode(cls, value: str, *args, **kwargs) -> bytes:
        char1, char2 = value[:2]
        return (char2 or " ").encode(cls.encoding) + (char1 or " ").encode(cls.encoding)

    @classmethod
    def _decode(cls, stream: BytesIO) -> str:
        return cls._slc_string_swap(stream.read(2)).decode(cls.encoding)


class PCCC_STRING(PCCCStringType):
    @classmethod
    def _encode(cls, value: str) -> bytes:
        _len = UINT.encode(len(value))
        _data = cls._slc_string_swap(value.encode(cls.encoding))
        return _len + _data

    @classmethod
    def _decode(cls, stream: BytesIO) -> str:
        _len = UINT.decode(stream)
        return cls._slc_string_swap(stream.read(82)).decode(cls.encoding)


class PCCCDataTypes(EnumMap):
    _return_caps_only_ = True
    n = INT
    b = INT
    t = INT
    c = INT
    s = INT
    o = INT
    i = INT
    f = REAL
    a = PCCC_ASCII
    r = DINT
    st = PCCC_STRING
    l = DINT


PCCC_CT = {
    "PRE": 1,
    "ACC": 2,
    "EN": 15,
    "TT": 14,
    "DN": 13,
    "CU": 15,
    "CD": 14,
    "OV": 12,
    "UN": 11,
    "UA": 10,
}

_PCCC_DATA_TYPE = {
    "N": b"\x89",
    "B": b"\x85",
    "T": b"\x86",
    "C": b"\x87",
    "S": b"\x84",
    "F": b"\x8a",
    "ST": b"\x8d",
    "A": b"\x8e",
    "R": b"\x88",
    "O": b"\x82",  # or b'\x8b'?
    "I": b"\x83",  # or b'\x8c'?
    "L": b"\x91",
    "MG": b"\x92",
    "PD": b"\x93",
    "PLS": b"\x94",
}


PCCC_DATA_TYPE = {
    **_PCCC_DATA_TYPE,
    **{v: k for k, v in _PCCC_DATA_TYPE.items()},
}


PCCC_DATA_SIZE = {
    "N": 2,
    "L": 4,
    "B": 2,
    "T": 6,
    "C": 6,
    "S": 2,
    "F": 4,
    "ST": 84,
    "A": 2,
    "R": 6,
    "O": 2,
    "I": 2,
    "MG": 50,
    "PD": 46,
    "PLS": 12,
}
