# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Ian Ottoway <ian@ottoway.dev>
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

from ..map import EnumMap

__all__ = ['StringTypeLenSize', 'DataTypeSize', 'DataType', 'PCCC_DATA_TYPE',
           'PCCC_DATA_SIZE', 'PCCC_CT']


class StringTypeLenSize(EnumMap):
    short_string = 1
    string = 2
    logix_string = 4


class DataTypeSize(EnumMap):
    bool = 1
    sint = 1
    usint = 1
    byte = 1
    int = 2
    uint = 2
    word = 2
    dint = 4
    udint = 4
    real = 4
    dword = 4
    lint = 8
    ulint = 8
    lword = 8


class DataType(EnumMap):
    _return_caps_only_ = True  # datatype strings always in CAPS

    bool = 0xc1
    sint = 0xc2  # signed 8-bit integer
    int = 0xc3  # signed 16-bit integer
    dint = 0xc4  # signed 32-bit integer
    lint = 0xc5  # signed 64-bit integer
    usint = 0xc6  # unsigned 8-bit integer
    uint = 0xc7  # unsigned 16-bit integer
    udint = 0xc8  # unsigned 32-bit integer
    ulint = 0xc9  # unsigned 64-bit integer
    real = 0xca  # 32-bit floating point
    lreal = 0xcb  # 64-bit floating point
    stime = 0xcc  # synchronous time
    date = 0xcd
    time_of_day = 0xce
    date_and_time = 0xcf
    string = 0xd0  # character string (1 byte per character)
    byte = 0xd1  # byte string 8-bits
    word = 0xd2  # byte string 16-bits
    dword = 0xd3  # byte string 32-bits
    lword = 0xd4  # byte string 64-bits
    string2 = 0xd5  # character string (2 byte per character)
    ftime = 0xd6  # duration high resolution
    ltime = 0xd7  # duration long
    itime = 0xd8  # duration short
    stringn = 0xd9  # character string (n byte per character)
    short_string = 0xda  # character string (1 byte per character 1 byte length indicator)
    time = 0xdb  # duration in milliseconds
    epath = 0xdc  # cip path segment
    engunit = 0xdd  # engineering units
    stringi = 0xde  # international character string


_PCCC_DATA_TYPE = {
    'N': b'\x89',
    'B': b'\x85',
    'T': b'\x86',
    'C': b'\x87',
    'S': b'\x84',
    'F': b'\x8a',
    'ST': b'\x8d',
    'A': b'\x8e',
    'R': b'\x88',
    'O': b'\x82',  # or b'\x8b'?
    'I': b'\x83',  # or b'\x8c'?
    'L': b'\x91',
    'MG': b'\x92',
    'PD': b'\x93',
    'PLS': b'\x94',
}


PCCC_DATA_TYPE = {
    **_PCCC_DATA_TYPE,
    **{v: k for k, v in _PCCC_DATA_TYPE.items()},
}


PCCC_DATA_SIZE = {
    'N': 2,
    'L': 4,
    'B': 2,
    'T': 6,
    'C': 6,
    'S': 2,
    'F': 4,
    'ST': 84,
    'A': 2,
    'R': 6,
    'O': 2,
    'I': 2,
    'MG': 50,
    'PD': 46,
    'PLS': 12,
}


PCCC_CT = {
    'PRE': 1,
    'ACC': 2,
    'EN': 15,
    'TT': 14,
    'DN': 13,
    'CU': 15,
    'CD': 14,
    'OV': 12,
    'UN': 11,
    'UA': 10
}
