from .bytes_ import pack_uint, pack_dint, print_bytes_msg, unpack_uint, unpack_usint, unpack_dint
from . import CommError
from autologging import logged
from .const import (ENCAPSULATION_COMMAND, REPLY_INFO, SUCCESS, INSUFFICIENT_PACKETS, TAG_SERVICES_REPLY,
                    get_service_status, get_extended_status, MULTI_PACKET_SERVICES, DATA_ITEM, ADDRESS_ITEM)


@logged
class Packet:
    def __init__(self):
        self._msg = []  # message data

    def add(self, *value: bytes):
        self._msg.extend(value)

    @property
    def message(self) -> bytes:
        return b''.join(self._msg)


@logged
class RequestPacket(Packet):
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00' # 10

    def __init__(self, plc):
        super().__init__()
        self._plc = plc

    def _build_header(self, command, length) -> bytes:
        """ Build the encapsulate message header

        The header is 24 bytes fixed length, and includes the command and the length of the optional data portion.

         :return: the header
        """
        try:
            return b''.join([
                command,
                pack_uint(length),  # Length UINT
                pack_dint(self._plc._session),  # Session Handle UDINT
                b'\x00\x00\x00\x00',  # Status UDINT
                self._plc.attribs['context'],  # Sender Context 8 bytes
                pack_dint(self._plc.attribs['option']),  # Option UDINT
            ])

        except Exception as e:
            raise CommError(e)

    def _build_common_packet_format(self, addr_data=None):
        addr_data = b'\x00\x00' if addr_data is None else pack_uint(len(addr_data)) + addr_data
        return b''.join([
            b'\x00\x00\x00\x00',  # Interface Handle: shall be 0 for CIP
            self._timeout,  # Item count: should be at list 2 (Address and Data)
            b'\x02\x00',
            self._address_type,
            addr_data,
            self._message_type,
            pack_uint(len(self.message)),
            self.message
        ])

    def _send(self, message):
        """
                socket send
                :return: true if no error otherwise false
                """
        try:
            if self._plc._debug:
                self.__log.debug(print_bytes_msg(message, '-------------- SEND --------------'))
            self._plc._sock.send(message)
        except Exception as e:
            raise CommError(e)

    def _receive(self):
        """
        socket receive
        :return: reply data
        """
        try:
            reply = self._plc._sock.receive()
        except Exception as e:
            raise CommError(e)
        else:
            if self._plc._debug:
                self.__log.debug(print_bytes_msg(reply, '----------- RECEIVE -----------'))
            return reply


@logged
class SendUnitDataRequestPacket(RequestPacket):
    _message_type = DATA_ITEM['Connected']
    _address_type = ADDRESS_ITEM['Connection Based']

    def __init__(self, plc):
        super().__init__(plc)

    def send(self):
        msg = self._build_common_packet_format(addr_data=self._plc._target_cid)
        header = self._build_header(ENCAPSULATION_COMMAND['send_rr_data'], len(msg))
        self._send(header + msg)
        reply = self._receive()
        return SendUnitDataResponsePacket(reply)


@logged
class SendRRDataRequestPacket(RequestPacket):
    _message_type = DATA_ITEM['Unconnected']
    _address_type = ADDRESS_ITEM['UCMM']

    def __init__(self, plc):
        super().__init__(plc)

    def send(self):
        msg = self._build_common_packet_format()
        header = self._build_header(ENCAPSULATION_COMMAND['send_rr_data'], len(msg))
        self._send(header + msg)
        reply = self._receive()
        return SendRRDataResponsePacket(reply)


@logged
class ResponsePacket(Packet):

    def __init__(self, raw_data: bytes = None):
        super().__init__()
        self.raw = raw_data
        self._error = None
        self.service = None
        self.service_status = None
        self.data = None
        self.command = None
        self.command_status = None

        self._is_valid = False

        self._parse_reply()

    def __bool__(self):
        return self.is_valid()

    @property
    def error(self):
        if self.is_valid():
            return None
        else:
            if self._error is None:
                if self.command_status not in (None, SUCCESS):
                    return f'{get_service_status(self.command_status)} - {get_extended_status(self.raw, 42)}'
                if self.service_status not in (None, SUCCESS):
                    return f'{get_service_status(self.service_status)} - {get_extended_status(self.raw, 42)}'
                return 'Unknown Error'
            else:
                return self._error

    def is_valid(self):
        return all((
            self._error is None,
            self.command is not None,
            self.command_status == SUCCESS,
        ))

    def _parse_reply(self):
        try:
            if self.raw is None:
                self._error = 'No Reply From PLC'
            else:
                self.command = self.raw[:2]
                self.command_status = unpack_dint(self.raw[8:12])  # encapsulation status check
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'


class SendUnitDataResponsePacket(ResponsePacket):
    def __init__(self, raw_data: bytes = None):
        super().__init__(raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.service = self.raw[46]
            self.service_status = unpack_usint(self.raw[48:49])
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self):
        valid = self.service_status == SUCCESS or (self.service_status == INSUFFICIENT_PACKETS and
                                                   self.service in MULTI_PACKET_SERVICES)
        return all((
            super().is_valid(),
            valid
        ))


class SendRRDataResponsePacket(ResponsePacket):

    def __init__(self, raw_data: bytes = None):
        super().__init__(raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.service = self.raw[40]
            self.service_status = unpack_usint(self.raw[42:43])
            self.data = self.raw[44:]
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self):
        return all((
            super().is_valid(),
            self.service_status == SUCCESS
        ))
