import logging
from reprlib import repr as _r
from typing import Optional

from ..const import SUCCESS
from ..bytes_ import Pack, Unpack, print_bytes_msg
from ..exceptions import CommError

__all__ = ['Packet', 'ResponsePacket', 'RequestPacket']


class Packet:
    __log = logging.getLogger(__qualname__)


class ResponsePacket(Packet):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'RequestPacket', raw_data: bytes = None):
        super().__init__()
        self._request = request
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

    def __bool__(self):
        return self.is_valid()

    @property
    def error(self) -> Optional[str]:
        if self.is_valid():
            return None
        else:
            if self._error is None:
                if self.command_status not in (None, SUCCESS):
                    return self.command_extended_status()
                if self.service_status not in (None, SUCCESS):
                    return self.service_extended_status()
                return 'Unknown Error'
            else:
                return self._error

    def is_valid(self) -> bool:
        return all((
            self._error is None,
            self.command is not None,
            self.command_status == SUCCESS,
        ))

    def _parse_reply(self):
        try:
            self.command = self.raw[:2]
            self.command_status = Unpack.dint(self.raw[8:12])  # encapsulation status check
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def command_extended_status(self) -> str:
        return 'Unknown Error'

    def service_extended_status(self) -> str:
        return 'Unknown Error'

    def __repr__(self):
        return f'{self.__class__.__name__}(service={self.service if self.service else None!r}, command={self.command!r}, error={self.error!r})'

    __str__ = __repr__


class RequestPacket(Packet):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10
    _encap_command = None
    response_class = ResponsePacket
    type_ = None
    VERBOSE_DEBUG = False
    no_response = False

    def __init__(self):
        super().__init__()
        self._msg = []  # message data
        # self._driver = driver  # TODO: Remove
        self.error = None

    def add(self, *value: bytes):
        self._msg.extend(value)
        return self

    @property
    def message(self) -> bytes:
        return b''.join(self._msg)

    def build_request(self, target_cid: bytes, session_id: int, context: bytes, option: int, **kwargs) -> bytes:
        # TODO: should have args for any driver provided data
        msg = self._build_common_packet_format(addr_data=target_cid)
        header = self._build_header(self._encap_command, len(msg), session_id, context, option)
        return header + msg

    @staticmethod
    def _build_header(command, length, session_id, context, option) -> bytes:
        """ Build the encapsulate message header

        The header is 24 bytes fixed length, and includes the command and the length of the optional data portion.

         :return: the header
        """
        try:
            return b''.join([
                command,
                Pack.uint(length),  # Length UINT
                Pack.udint(session_id),  # Session Handle UDINT
                b'\x00\x00\x00\x00',  # Status UDINT
                context,  # Sender Context 8 bytes
                Pack.udint(option)  # Option UDINT
            ])

        except Exception as err:
            raise CommError('Failed to build request header') from err

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        addr_data = b'\x00\x00' if addr_data is None else Pack.uint(len(addr_data)) + addr_data
        msg = self.message
        return b''.join([
            b'\x00\x00\x00\x00',  # Interface Handle: shall be 0 for CIP
            self._timeout,
            b'\x02\x00',  # Item count: should be at list 2 (Address and Data)
            self._address_type,
            addr_data,
            self._message_type,
            Pack.uint(len(msg)),
            msg
        ])

    def __repr__(self):
        return f'{self.__class__.__name__}(message={_r(self._msg)})'

    __str__ = __repr__


