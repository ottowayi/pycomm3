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
import logging
from itertools import cycle


from .base import RequestPacket, ResponsePacket
from .util import get_service_status, get_extended_status, parse_reply_data_by_format

from ..const import(SUCCESS, INSUFFICIENT_PACKETS, MULTI_PACKET_SERVICES,
                    Services, DataItem, AddressItem, EncapsulationCommands)

from ..bytes_ import Pack, Unpack


class SendUnitDataResponsePacket(ResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'SendUnitDataRequestPacket', raw_data: bytes = None):
        super().__init__(request, raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.service = Services.get(Services.from_reply(self.raw[46:47]))
            self.service_status = Unpack.usint(self.raw[48:49])
            self.data = self.raw[50:]
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self) -> bool:
        valid = self.service_status == SUCCESS or (self.service_status == INSUFFICIENT_PACKETS and
                                                   self.service in MULTI_PACKET_SERVICES)
        return all((
            super().is_valid(),
            valid
        ))

    def command_extended_status(self) -> str:
        return f'{get_service_status(self.command_status)} - {get_extended_status(self.raw, 48)}'

    def service_extended_status(self) -> str:
        return f'{get_service_status(self.service_status)} - {get_extended_status(self.raw, 48)}'


class SendUnitDataRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = DataItem.connected
    _address_type = AddressItem.connection
    response_class = SendUnitDataResponsePacket
    _encap_command = EncapsulationCommands.send_unit_data

    def build_request(self, target_cid: bytes, session_id: int, context: bytes, option: int,
                      sequence: cycle = None, **kwargs):
        self._msg.insert(0, Pack.uint(next(sequence)))
        return super().build_request(target_cid, session_id, context, option, **kwargs)


class SendRRDataResponsePacket(ResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request, raw_data: bytes = None, *args, **kwargs):
        super().__init__(request, raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.service = Services.get(Services.from_reply(self.raw[40:41]))
            self.service_status = Unpack.usint(self.raw[42:43])
            self.data = self.raw[44:]
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self) -> bool:
        return all((
            super().is_valid(),
            self.service_status == SUCCESS
        ))

    def command_extended_status(self) -> str:
        return f'{get_service_status(self.command_status)} - {get_extended_status(self.raw, 42)}'

    def service_extended_status(self) -> str:
        return f'{get_service_status(self.service_status)} - {get_extended_status(self.raw, 42)}'


class SendRRDataRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = DataItem.unconnected
    _address_type = AddressItem.uccm
    _encap_command = EncapsulationCommands.send_rr_data
    response_class = SendRRDataResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return super()._build_common_packet_format(addr_data=None)


class RegisterSessionResponsePacket(ResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'RegisterSessionRequestPacket', raw_data: bytes = None):
        self.session = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.session = Unpack.udint(self.raw[4:8])
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self) -> bool:
        return all((
            super().is_valid(),
            self.session is not None
        ))

    def __repr__(self):
        return f'{self.__class__.__name__}(session={self.session!r}, error={self.error!r})'


class RegisterSessionRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommands.register_session
    response_class = RegisterSessionResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return self.message


class UnRegisterSessionResponsePacket(ResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __repr__(self):
        return 'UnRegisterSessionResponsePacket()'


class UnRegisterSessionRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommands.unregister_session
    response_class = UnRegisterSessionResponsePacket
    no_response = True

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''


class ListIdentityResponsePacket(ResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _data_format = (
        ('item_type_code', 'UINT'),
        ('item_length', 'UINT'),
        ('encap_protocol_version', 'UINT'),
        (None, 4),
        ('ip_address', 'IP'),
        (None, 8),
        ('vendor_id', 'UINT'),
        ('device_type', 'UINT'),
        ('product_code', 'UINT'),
        ('revision_major', 'USINT'),
        ('revision_minor', 'USINT'),
        ('status', 'WORD'),
        ('serial_number', 'UDINT'),
        ('product_name', 'SHORT_STRING'),
        ('state', 'USINT')
    )

    def __init__(self, request: 'ListIdentityRequestPacket', raw_data: bytes = None):
        self.identity = {}
        super().__init__(request, raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.data = self.raw[26:]
            self.identity = parse_reply_data_by_format(self.data, self._data_format)
        except Exception as err:
            self.__log.exception('Failed to parse response')
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self) -> bool:
        return all((
            super().is_valid(),
            self.identity is not None
        ))

    def __repr__(self):
        return f'{self.__class__.__name__}(identity={self.identity!r}, error={self.error!r})'


class ListIdentityRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommands.list_identity
    response_class = ListIdentityResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''


