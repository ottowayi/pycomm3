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
from typing import Union, Any

from ..util import cycle
from .ethernetip import (
    SendUnitDataResponsePacket,
    SendUnitDataRequestPacket,
    SendRRDataRequestPacket,
    SendRRDataResponsePacket,
)
from .util import request_path, wrap_unconnected_send
from ..cip import DataType


class GenericConnectedResponsePacket(SendUnitDataResponsePacket):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")

    def __init__(
        self, request: "GenericConnectedRequestPacket", raw_data: bytes = None
    ):
        self.data_type = request.data_type
        self.value = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        super()._parse_reply()

        if self.data_type is None:
            self.value = self.data
        elif self.is_valid():
            try:
                self.value = self.data_type.decode(self.data)
            except Exception as err:
                self.__log.exception("Failed to parse reply")
                self._error = f"Failed to parse reply - {err}"
                self.value = None


class GenericConnectedRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    response_class = GenericConnectedResponsePacket

    def __init__(
        self,
        sequence: cycle,
        service: Union[int, bytes],
        class_code: Union[int, bytes],
        instance: Union[int, bytes],
        attribute: Union[int, bytes] = b"",
        request_data: Any = b"",
        data_type: DataType = None,
    ):
        super().__init__(sequence)
        self.data_type = data_type
        self.class_code = class_code
        self.instance = instance
        self.attribute = attribute
        self.service = service if isinstance(service, bytes) else bytes([service])
        self.request_data = request_data

    def _setup_message(self):
        super()._setup_message()
        req_path = request_path(self.class_code, self.instance, self.attribute)
        self._msg += [self.service, req_path, self.request_data]


class GenericUnconnectedResponsePacket(SendRRDataResponsePacket):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")

    def __init__(
        self, request: "GenericUnconnectedRequestPacket", raw_data: bytes = None
    ):
        self.data_type = request.data_type
        self.value = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        super()._parse_reply()

        if self.data_type is None:
            self.value = self.data
        elif self.is_valid():
            try:
                self.value = self.data_type.decode(self.data)
            except Exception as err:
                self.__log.exception("Failed to parse reply")
                self._error = f"Failed to parse reply - {err}"
                self.value = None


class GenericUnconnectedRequestPacket(SendRRDataRequestPacket):
    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    response_class = GenericUnconnectedResponsePacket

    def __init__(
        self,
        service: Union[int, bytes],
        class_code: Union[int, bytes],
        instance: Union[int, bytes],
        attribute: Union[int, bytes] = b"",
        request_data: bytes = b"",
        route_path: bytes = b"",
        unconnected_send: bool = False,
        data_type: DataType = None,
    ):
        super().__init__()
        self.data_type = data_type
        self.class_code = class_code
        self.instance = instance
        self.attribute = attribute
        self.service = service if isinstance(service, bytes) else bytes([service])
        self.request_data = request_data
        self.route_path = route_path
        self.unconnected_send = unconnected_send

    def _setup_message(self):
        super()._setup_message()
        req_path = request_path(self.class_code, self.instance, self.attribute)

        if self.unconnected_send:
            msg = [
                wrap_unconnected_send(
                    b"".join((self.service, req_path, self.request_data)),
                    self.route_path,
                ),
            ]
        else:
            msg = [self.service, req_path, self.request_data, self.route_path]

        self._msg += msg
