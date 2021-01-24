import logging
from typing import Union

from .ethernetip import (SendUnitDataResponsePacket, SendUnitDataRequestPacket,
                         SendRRDataRequestPacket, SendRRDataResponsePacket)
from .util import parse_reply_data_by_format, DataFormatType, request_path, wrap_unconnected_send


class GenericConnectedResponsePacket(SendUnitDataResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'GenericConnectedRequestPacket', raw_data: bytes = None):
        self.data_format = request.data_format
        self.value = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        super()._parse_reply()

        if self.data_format is None:
            self.value = self.data
        elif self.is_valid():
            try:
                self.value = parse_reply_data_by_format(self.data, self.data_format)
            except Exception as err:
                self._error = f'Failed to parse reply - {err}'
                self.value = None


class GenericConnectedRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    response_class = GenericConnectedResponsePacket

    def __init__(self,
                 service: Union[int, bytes],
                 class_code: Union[int, bytes],
                 instance: Union[int, bytes],
                 attribute: Union[int, bytes] = b'',
                 request_data: bytes = b'',
                 data_format: DataFormatType = None):
        super().__init__()
        self.data_format = data_format
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
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'GenericUnconnectedRequestPacket', raw_data: bytes = None):
        self.data_format = request.data_format
        self.value = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        super()._parse_reply()

        if self.data_format is None:
            self.value = self.data
        elif self.is_valid():
            try:
                self.value = parse_reply_data_by_format(self.data, self.data_format)
            except Exception as err:
                self._error = f'Failed to parse reply - {err}'
                self.value = None


class GenericUnconnectedRequestPacket(SendRRDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    response_class = GenericUnconnectedResponsePacket

    def __init__(self,
                 service: Union[int, bytes],
                 class_code: Union[int, bytes],
                 instance: Union[int, bytes],
                 attribute: Union[int, bytes] = b'',
                 request_data: bytes = b'',
                 route_path: bytes = b'',
                 unconnected_send: bool = False,
                 data_format: DataFormatType = None):
        super().__init__()
        self.data_format = data_format
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
            msg = [wrap_unconnected_send(b''.join((self.service, req_path, self.request_data)), self.route_path), ]
        else:
            msg = [self.service, req_path, self.request_data, self.route_path]

        self._msg += msg
