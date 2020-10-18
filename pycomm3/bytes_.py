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

from typing import Callable
from struct import pack, unpack
from .map import EnumMap
from itertools import chain


def _pack_epath(path, pad_len=False):
    if len(path) % 2:
        path += b'\x00'

    _len = Pack.usint(len(path) // 2)
    if pad_len:
        _len += b'\x00'

    return _len + path


def _pack_char(char):
    unsigned = ord(char)
    return Pack.sint(unsigned - 256 if unsigned > 127 else unsigned)


def _logix_string_encode(string):
    return Pack.udint(len(string)) + b''.join([_pack_char(x) for x in string])


def _string_encode(string):
    return Pack.uint(len(string)) + b''.join([_pack_char(x) for x in string])


def _short_string_encode(string):
    return Pack.usint(len(string)) + b''.join([_pack_char(x) for x in string])


def _logix_string_decode(str_data):
    string_len = Unpack.udint(str_data)
    return _decode_string(str_data[4: string_len + 4])


def _string_decode(str_data):
    string_len = Unpack.uint(str_data)
    return _decode_string(str_data[2: string_len + 2])


def _short_string_decode(str_data):
    string_len = str_data[0]
    return _decode_string(str_data[1: string_len + 1])


def _decode_string(str_bytes):
    return ''.join(
        chr(v + 256) if v < 0 else chr(v) for v in str_bytes
    )


def _decode_pccc_ascii(data):
    return _decode_string(_slc_string_swap(data))


def _decode_pccc_string(str_bytes):
    str_len = Unpack.uint(str_bytes)
    str_data = str_bytes[2:2+str_len+(str_len % 2)]
    _str = _slc_string_swap(str_data)[:str_len]
    return _decode_string(_str)


def _encode_pccc_string(string):
    str_len = Pack.uint(len(string))
    str_data = str_len + b''.join(_pack_char(x) for x in _slc_string_swap(string))
    return str_data


def _encode_pccc_ascii(string):
    _len = len(string)
    if _len > 2:
        raise ValueError('ASCII strings cannot be greater than 2 characters')
    elif _len < 2:
        string += ' ' * (2 - _len)

    return b''.join(_pack_char(x) for x in _slc_string_swap(string))


def _slc_string_swap(data):
    return [
        x for x in
        chain.from_iterable(
                (x2, x1) for x1, x2 in (data[i:i + 2] for i in range(0, len(data), 2))
            )
    ]


class Pack(EnumMap):

    sint: Callable[[int], bytes] = lambda n: pack('b', n)
    byte: Callable[[int], bytes] = sint
    usint: Callable[[int], bytes] = lambda n: pack('B', n)
    int: Callable[[int], bytes] = lambda n: pack('<h', n)
    uint: Callable[[int], bytes] = lambda n: pack('<H', n)
    word: Callable[[int], bytes] = uint
    dint: Callable[[int], bytes] = lambda n: pack('<i', n)
    udint: Callable[[int], bytes] = lambda n: pack('<I', n)
    dword: Callable[[int], bytes] = udint
    lint: Callable[[int], bytes] = lambda l: pack('<q', l)
    ulint: Callable[[int], bytes] = lambda l: pack('<Q', l)
    lword: Callable[[int], bytes] = ulint
    real: Callable[[float], bytes] = lambda r: pack('<f', r)
    long: Callable[[float], bytes] = lambda l: pack('<l', l)
    ulong: Callable[[float], bytes] = lambda l: pack('<L', l)
    epath: Callable[[bytes, bool], bytes] = _pack_epath
    short_string: Callable[[str], bytes] = _short_string_encode
    string: Callable[[str], bytes] = _string_encode
    logix_string: Callable[[str], bytes] = _logix_string_encode
    char: Callable[[str], bytes] = _pack_char
    bool: Callable[[bool], bytes] = lambda b: b'\xFF' if b else b'\x00'

    pccc_n: Callable[[int], bytes] = int
    pccc_b: Callable[[int], bytes] = int
    pccc_t: Callable[[int], bytes] = int
    pccc_c: Callable[[int], bytes] = int
    pccc_s: Callable[[int], bytes] = int
    pccc_o: Callable[[int], bytes] = int
    pccc_i: Callable[[int], bytes] = int
    pccc_f: Callable[[float], bytes] = real
    pccc_a: Callable[[int], bytes] = _encode_pccc_ascii
    pccc_r: Callable[[int], bytes] = dint
    pccc_st: Callable[[str], bytes] = _encode_pccc_string
    pccc_l: Callable[[bytes], int] = dint


class Unpack(EnumMap):
    bool: Callable[[bytes], bool] = lambda st: st[0] != 0
    sint: Callable[[bytes], int] = lambda st: int(unpack('b', bytes([st[0]]))[0])
    char: Callable[[bytes], str] = sint
    byte: Callable[[bytes], int] = sint
    usint: Callable[[bytes], int] = lambda st: int(unpack('B', bytes([st[0]]))[0])
    int: Callable[[bytes], int] = lambda st: int(unpack('<h', st[0:2])[0])
    uint: Callable[[bytes], int] = lambda st: int(unpack('<H', st[0:2])[0])
    word: Callable[[bytes], int] = uint
    dint: Callable[[bytes], int] = lambda st: int(unpack('<i', st[0:4])[0])
    udint: Callable[[bytes], int] = lambda st: int(unpack('<I', st[0:4])[0])
    dword: Callable[[bytes], int] = udint
    lint: Callable[[bytes], int] = lambda st: int(unpack('<q', st[0:8])[0])
    ulint: Callable[[bytes], int] = lambda st: int(unpack('<Q', st[0:8])[0])
    lword: Callable[[bytes], int] = ulint
    real: Callable[[bytes], float] = lambda st: float(unpack('<f', st[0:4])[0])
    long: Callable[[bytes], float] = lambda st: int(unpack('<l', st[0:4])[0])
    ulong: Callable[[bytes], float] = lambda st: int(unpack('<L', st[0:4])[0])
    short_string: Callable[[bytes], str] = _short_string_decode
    string: Callable[[bytes], str] = _string_decode
    logix_string: Callable[[str], bytes] = _logix_string_decode

    pccc_n: Callable[[bytes], int] = int
    pccc_b: Callable[[bytes], int] = int
    pccc_t: Callable[[bytes], int] = int
    pccc_c: Callable[[bytes], int] = int
    pccc_s: Callable[[bytes], int] = int
    pccc_o: Callable[[bytes], int] = int
    pccc_i: Callable[[bytes], int] = int
    pccc_f: Callable[[bytes], float] = real
    pccc_a: Callable[[bytes], int] = _decode_pccc_ascii
    pccc_r: Callable[[bytes], int] = dint
    pccc_st: Callable[[bytes], str] = _decode_pccc_string
    pccc_l: Callable[[bytes], int] = dint


def print_bytes_msg(msg, info=''):
    out = info
    new_line = True
    line = 0
    column = 0
    for idx, ch in enumerate(msg):
        if new_line:
            out += "\n({:0>4d}) ".format(line * 10)
            new_line = False
        out += "{:0>2x} ".format(ch)
        if column == 9:
            new_line = True
            column = 0
            line += 1
        else:
            column += 1
    return out
