# -*- coding: utf-8 -*-
#
# const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
# Copyright (c) 2019 Ian Ottoway <ian@ottoway.dev>
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

from struct import pack, unpack
from .map import EnumMap


def _pack_epath(path, pad_len=False):
    if len(path) % 2:
        path += b'\x00'

    _len = Pack.usint(len(path)//2)
    if pad_len:
        _len += b'\x00'

    return _len + path


def _pack_char(char):
    unsigned = ord(char)
    return Pack.sint(unsigned - 256 if unsigned > 127 else unsigned)


def _short_string_encode(string):
    return Pack.usint(len(string)) + b''.join([_pack_char(x) for x in string])


def _short_string_decode(str_data):
    string_len = str_data[0]
    return ''.join(
        chr(v + 256) if v < 0 else chr(v) for v in str_data[1:string_len + 1]
    )


class Pack(EnumMap):

    sint = lambda n: pack('b', n)
    byte = sint
    usint = lambda n: pack('B', n)
    int = lambda n: pack('<h', n)
    uint = lambda n: pack('<H', n)
    word = uint
    dint = lambda n: pack('<i', n)
    udint = lambda n: pack('<I', n)
    dword = udint
    lint = lambda l: pack('<q', l)
    ulint = lambda l: pack('<Q', l)
    lword = ulint
    real = lambda r: pack('<f', r)
    long = lambda l: pack('<l', l)
    ulong = lambda l: pack('<L', l)
    epath = _pack_epath
    short_string = _short_string_encode
    char = _pack_char
    bool = lambda b: b'\xFF' if b else b'\x00'

    pccc_n = int
    pccc_b = int
    pccc_t = int
    pccc_c = int
    pccc_s = int
    pccc_o = int
    pccc_i = int
    pccc_f = real
    pccc_a = sint
    pccc_r = dint


class Unpack(EnumMap):
    bool = lambda st: st[0] != 0
    sint = lambda st: int(unpack('b', bytes([st[0]]))[0])
    byte = sint
    usint = lambda st: int(unpack('B', bytes([st[0]]))[0])
    int = lambda st: int(unpack('<h', st[0:2])[0])
    uint = lambda st: int(unpack('<H', st[0:2])[0])
    word = uint
    dint = lambda st: int(unpack('<i', st[0:4])[0])
    udint = lambda st: int(unpack('<I', st[0:4])[0])
    dword = udint
    lint = lambda st: int(unpack('<q', st[0:8])[0])
    ulint = lambda st: int(unpack('<Q', st[0:8])[0])
    lword = ulint
    real = lambda st: float(unpack('<f', st[0:4])[0])
    long = lambda st: int(unpack('<l', st[0:4])[0])
    ulong = lambda st: int(unpack('<L', st[0:4])[0])
    short_string = _short_string_decode

    pccc_n = int
    pccc_b = int
    pccc_t = int
    pccc_c = int
    pccc_s = int
    pccc_o = int
    pccc_i = int
    pccc_f = real
    pccc_a = sint
    pccc_r = dint


def print_bytes_line(msg):
    out = ''
    for ch in msg:
        out += f"{ch:0>2x}"
    return out


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


PCCC_DATA_FUNCTION = {
    'N': 'int',
    'B': 'int',
    'T': 'int',
    'C': 'int',
    'S': 'int',
    'F': 'real',
    'A': 'sint',
    'R': 'dint',
    'O': 'int',
    'I': 'int'
}
