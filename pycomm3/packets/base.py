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

import logging
from reprlib import repr as _r
from typing import Optional

from ..cip import DINT, UINT, UDINT
from ..const import SUCCESS
from ..exceptions import CommError

__all__ = ["Packet", "ResponsePacket", "RequestPacket"]


class Packet:
    __log = logging.getLogger(f"{__module__}.{__qualname__}")


class ResponsePacket(Packet):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")

    def __init__(self, request: "RequestPacket", raw_data: bytes = None):
        super().__init__()
        self.request = request
        self.raw = raw_data
        self._error = None
        self.service = None
        self.service_status = None
        self.data = None
        self.command = None
        self.command_status = None

        self._is_valid = False

        if raw_data is not None:
            self._parse_reply()
        else:
            self._error = "No response data received"

    def __bool__(self):
        return self.is_valid()

    @property
    def error(self) -> Optional[str]:
        if self.is_valid():
            return None
        if self._error is not None:
            return self._error
        if self.command_status not in (None, SUCCESS):
            return self.command_extended_status()
        if self.service_status not in (None, SUCCESS):
            return self.service_extended_status()
        return "Unknown Error"

    def is_valid(self) -> bool:
        return all(
            (
                self._error is None,
                self.command is not None,
                self.command_status == SUCCESS,
            )
        )

    def _parse_reply(self):
        try:
            self.command = self.raw[:2]
            self.command_status = DINT.decode(
                self.raw[8:12]
            )  # encapsulation status check
        except Exception as err:
            self.__log.exception("Failed to parse reply")
            self._error = f"Failed to parse reply - {err}"

    def command_extended_status(self) -> str:
        return "Unknown Error"

    def service_extended_status(self) -> str:
        return "Unknown Error"

    def __repr__(self):
        service = self.service or None
        return f"{self.__class__.__name__}(service={service!r}, command={self.command!r}, error={self.error!r})"

    __str__ = __repr__


class RequestPacket(Packet):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    _message_type = None
    _address_type = None
    _timeout = b"\x0a\x00"  # 10
    _encap_command = None
    response_class = ResponsePacket
    type_ = None
    VERBOSE_DEBUG = False
    no_response = False

    def __init__(self):
        super().__init__()
        self.message = b""
        self._msg_setup = False
        self._msg = []  # message data
        self._added = []
        self.error = None

    def add(self, *value: bytes):
        self._added.extend(value)
        return self

    def _setup_message(self):
        self._msg_setup = True

    def build_message(self):
        if not self._msg_setup:
            self._setup_message()
            self._msg += self._added
        self.message = b"".join(self._msg)
        return self.message

    def build_request(
        self, target_cid: bytes, session_id: int, context: bytes, option: int, **kwargs
    ) -> bytes:
        msg = self.build_message()
        common = self._build_common_packet_format(msg, addr_data=target_cid)
        header = self._build_header(
            self._encap_command, len(common), session_id, context, option
        )
        return header + common

    @staticmethod
    def _build_header(command, length, session_id, context, option) -> bytes:
        """Build the encapsulate message header

        The header is 24 bytes fixed length, and includes the command and the length of the optional data portion.

         :return: the header
        """
        try:
            return b"".join(
                [
                    command,
                    UINT.encode(length),  # Length UINT
                    UDINT.encode(session_id),  # Session Handle UDINT
                    b"\x00\x00\x00\x00",  # Status UDINT
                    context,  # Sender Context 8 bytes
                    UDINT.encode(option),  # Option UDINT
                ]
            )

        except Exception as err:
            raise CommError("Failed to build request header") from err

    def _build_common_packet_format(self, message, addr_data=None) -> bytes:
        addr_data = (
            b"\x00\x00"
            if addr_data is None
            else UINT.encode(len(addr_data)) + addr_data
        )

        return b"".join(
            [
                b"\x00\x00\x00\x00",  # Interface Handle: shall be 0 for CIP
                self._timeout,
                b"\x02\x00",  # Item count: should be at list 2 (Address and Data)
                self._address_type,
                addr_data,
                self._message_type,
                UINT.encode(len(message)),
                message,
            ]
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(message={_r(self._msg)})"

    __str__ = __repr__
