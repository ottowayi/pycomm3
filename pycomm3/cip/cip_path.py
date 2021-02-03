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
from .object_library import ClassCode
from . import data_types as TYPES

__all__ = ['ELEMENT_TYPE', 'CLASS_TYPE', 'INSTANCE_TYPE', 'ATTRIBUTE_TYPE',
           'PATH_SEGMENTS', 'MSG_ROUTER_PATH', 'DataItem', 'AddressItem']


ELEMENT_TYPE = {
    "8-bit": b'\x28',
    "16-bit": b'\x29\x00',
    "32-bit": b'\x2a\x00\x00\x00',
    1: b'\x28',
    2: b'\x29\x00',
    3: b'\x2a\x00\x00\x00',
}

CLASS_TYPE = {
    "8-bit": b'\x20',
    "16-bit": b'\x21\x00',
    1: b'\x20',  # length of code
    2: b'\x21\x00'
}

INSTANCE_TYPE = {
    "8-bit": b'\x24',
    "16-bit": b'\x25\x00',
    1: b'\x24',  # length of code
    2: b'\x25\x00'
}

ATTRIBUTE_TYPE = {
    "8-bit": b'\x30',
    "16-bit": b'\x31\x00',
    1: b'\x30',
    2: b'\x31\x00',
}

PATH_SEGMENTS = {
    'backplane': 0x01,
    'bp': 0x01,
    'enet': 0x02,
    'dhrio-a': 0x02,
    'dhrio-b': 0x03,
    'dnet': 0x02,
    'cnet': 0x02,
    'dh485-a': 0x02,
    'dh485-b': 0x03,
}

# MSG_ROUTER_PATH = b''.join([CLASS_TYPE['8-bit'], ClassCode.message_router, INSTANCE_TYPE['8-bit'], b'\x01'])
MSG_ROUTER_PATH = TYPES.PACKED_EPATH.encode((
                    TYPES.LogicalSegment(ClassCode.message_router, 'class_id'),
                    TYPES.LogicalSegment(0x01, 'instance_id')
                  ))


class DataItem(EnumMap):
    connected = b'\xb1\x00'
    unconnected = b'\xb2\x00'


class AddressItem(EnumMap):
    connection = b'\xa1\x00'
    null = b'\x00\x00'
    uccm = b'\x00\x00'


