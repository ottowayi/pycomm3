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

import string

from io import BytesIO
from typing import Union, Optional

from ..cip import (
    ClassCode,
    ConnectionManagerServices,
    SERVICE_STATUS,
    EXTEND_CODES,
    StringDataType,
    ArrayType,
    UDINT,
    BitArrayType,
    LogicalSegment,
    PADDED_EPATH,
    DataSegment,
    UINT,
    USINT,
)
from ..const import PRIORITY, TIMEOUT_TICKS, STRUCTURE_READ_REPLY

__all__ = [
    "wrap_unconnected_send",
    "request_path",
    "tag_request_path",
    "get_service_status",
    "get_extended_status",
    "parse_read_reply",
    "dword_to_bool_array",
    "print_bytes_msg",
    "PacketLazyFormatter",
]


def wrap_unconnected_send(message: bytes, route_path: bytes) -> bytes:
    rp = request_path(class_code=ClassCode.connection_manager, instance=b"\x01")
    msg_len = len(message)
    return b"".join(
        [
            ConnectionManagerServices.unconnected_send,
            rp,
            PRIORITY,
            TIMEOUT_TICKS,
            UINT.encode(msg_len),
            message,
            b"\x00" if msg_len % 2 else b"",
            route_path,
        ]
    )


def request_path(
    class_code: Union[int, bytes],
    instance: Union[int, bytes],
    attribute: Union[int, bytes] = b"",
) -> bytes:
    segments = [
        LogicalSegment(class_code, "class_id"),
        LogicalSegment(instance, "instance_id"),
    ]

    if attribute:
        segments.append(LogicalSegment(attribute, "attribute_id"))

    return PADDED_EPATH.encode(segments, length=True)


def tag_request_path(tag, tag_info, use_instance_ids):
    """
    Returns the tag request path encoded as a packed EPATH, returns None on error.
    """

    tags = tag.split(".")
    if tags:
        base, *attrs = tags
        base_tag, index = _find_tag_index(base)
        if (
            use_instance_ids
            and not base.startswith("Program:")
            and tag_info.get("instance_id")
        ):
            segments = [
                LogicalSegment(ClassCode.symbol_object, "class_id"),
                LogicalSegment(tag_info["instance_id"], "instance_id"),
            ]
        else:
            segments = [
                DataSegment(base_tag),
            ]
        if index is None:
            return None

        segments += [LogicalSegment(int(idx), "member_id") for idx in index]

        for attr in attrs:
            attr, index = _find_tag_index(attr)

            attr_segments = [DataSegment(attr)]
            attr_segments += [LogicalSegment(int(idx), "member_id") for idx in index]

            segments += attr_segments

        return PADDED_EPATH.encode(segments, length=True)

    return None


def _find_tag_index(tag):
    if "[" in tag:  # Check if is an array tag
        t = tag[: len(tag) - 1]  # Remove the last square bracket
        inside_value = t[t.find("[") + 1 :]  # Isolate the value inside bracket
        index = inside_value.split(
            ","
        )  # Now split the inside value in case part of multidimensional array
        tag = t[: t.find("[")]  # Get only the tag part
    else:
        index = []
    return tag, index


def get_service_status(status) -> str:
    return SERVICE_STATUS.get(status, f"Unknown Error ({status:0>2x})")


def get_extended_status(msg, start) -> Optional[str]:
    stream = BytesIO(msg[start:])
    status = USINT.decode(stream)
    # send_rr_data
    # 42 General Status
    # 43 Size of additional status
    # 44..n additional status

    # send_unit_data
    # 48 General Status
    # 49 Size of additional status
    # 50..n additional status
    extended_status_size = USINT.decode(stream) * 2
    extended_status = 0
    if extended_status_size != 0:
        # There is an additional status
        if extended_status_size == 1:
            extended_status = USINT.decode(stream)
        elif extended_status_size == 2:
            extended_status = UINT.decode(stream)
        elif extended_status_size == 4:
            extended_status = UDINT.decode(stream)
        else:
            return "[ERROR] Extended Status Size Unknown"
    try:
        return f"{EXTEND_CODES[status][extended_status]}  ({status:0>2x}, {extended_status:0>2x})"
    except Exception:
        return None


def parse_read_reply(data, data_type, elements):
    dt_name = data_type["data_type_name"]
    _type = data_type["type_class"]
    is_struct = data[:2] == STRUCTURE_READ_REPLY
    stream = BytesIO(data[4:] if is_struct else data[2:])
    if issubclass(_type, ArrayType):
        _value = _type.decode(stream, length=elements)

        if elements == 1 and not issubclass(_type.element_type, BitArrayType):
            _value = _value[0]
    else:
        _value = _type.decode(stream)
        if is_struct and not issubclass(_type, StringDataType):
            _value = {
                attr: _value[attr] for attr in data_type["data_type"]["attributes"]
            }

    if dt_name == "DWORD":
        dt_name = f"BOOL[{elements * 32}]"

    elif elements > 1:
        dt_name = f"{dt_name}[{elements}]"

    return _value, dt_name


def dword_to_bool_array(dword: Union[bytes, int]):
    dword = UDINT.decode(dword) if isinstance(dword, bytes) else dword
    bits = [x == "1" for x in bin(dword)[2:]]
    bools = [False for _ in range(32 - len(bits))] + bits
    bools.reverse()
    return bools


def _to_hex(bites):
    return " ".join((f"{b:0>2x}" for b in bites))


PRINTABLE = set(
    b"".join(
        bytes(x, "ascii")
        for x in (string.ascii_letters, string.digits, string.punctuation, " ")
    )
)


def _to_ascii(bites):
    return "".join(f"{chr(b)}" if b in PRINTABLE else "•" for b in bites)


def print_bytes_msg(msg):
    line_len = 16
    lines = (msg[i : i + line_len] for i in range(0, len(msg), line_len))

    formatted_lines = (
        f"({i * line_len:0>4x}) {_to_hex(line): <48}    {_to_ascii(line)}"
        for i, line in enumerate(lines)
    )

    return "\n".join(formatted_lines)


class PacketLazyFormatter:
    def __init__(self, data):
        self._data = data

    def __str__(self):
        return print_bytes_msg(self._data)

    def __len__(self):
        return len(self._data)
