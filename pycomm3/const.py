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

from .cip import LogicalSegment, ClassCode


HEADER_SIZE = 24


MSG_ROUTER_PATH = [
    LogicalSegment(ClassCode.message_router, "class_id"),
    LogicalSegment(0x01, "instance_id"),
]

# used to estimate packet size  and determine when to start a new packet
MULTISERVICE_READ_OVERHEAD = 10

MIN_VER_INSTANCE_IDS = 21  # using Symbol Instance Addressing not supported below version 21
MIN_VER_LARGE_CONNECTIONS = 20  # >500 byte connections not supported below logix v20
MIN_VER_EXTERNAL_ACCESS = 18  # ExternalAccess attributed added in v18

MICRO800_PREFIX = "2080"  # catalog number prefix for Micro800 PLCs

EXTENDED_SYMBOL = b"\x91"

SUCCESS = 0
INSUFFICIENT_PACKETS = 6
OFFSET_MESSAGE_REQUEST = 40
PAD = b"\x00"
PRIORITY = b"\x0a"
TIMEOUT_TICKS = b"\x05"
TIMEOUT_MULTIPLIER = b"\x07"
TRANSPORT_CLASS = b"\xa3"
BASE_TAG_BIT = 1 << 26

SEC_TO_US = 1_000_000  # seconds to microseconds

TEMPLATE_MEMBER_INFO_LEN = 8  # 2B bit/array len, 2B datatype, 4B offset
STRUCTURE_READ_REPLY = b"\xa0\x02"

SLC_CMD_CODE = b"\x0F"
SLC_CMD_REPLY_CODE = b"\x4F"
SLC_FNC_READ = b"\xa2"  # protected typed logical read w/ 3 address fields
SLC_FNC_WRITE = b"\xab"  # protected typed logical masked write w/ 3 address fields
SLC_REPLY_START = 61
PCCC_PATH = b"\x67\x24\x01"
