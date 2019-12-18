from . import Packet
from autologging import logged
from . import (ResponsePacket, SendUnitDataResponsePacket, ReadTagServiceResponsePacket, RegisterSessionResponsePacket,
               UnRegisterSessionResponsePacket, ListIdentityResponsePacket, SendRRDataResponsePacket)

from ..bytes_ import pack_uint, pack_dint, print_bytes_msg, unpack_uint, unpack_usint, unpack_dint
from ..const import (ENCAPSULATION_COMMAND, REPLY_INFO, SUCCESS, INSUFFICIENT_PACKETS, TAG_SERVICES_REPLY,
                    get_service_status, get_extended_status, MULTI_PACKET_SERVICES, DATA_ITEM, ADDRESS_ITEM,
                    REPLY_START, TAG_SERVICES_REQUEST)
from .. import CommError, Tag


@logged
class RequestPacket(Packet):
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10

    def __init__(self, plc: 'LogixDriver'):
        super().__init__()
        self._msg = []  # message data
        self._plc: 'LogixDriver' = plc

    def add(self, *value: bytes):
        self._msg.extend(value)
        return self

    @property
    def message(self) -> bytes:
        return b''.join(self._msg)

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

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        addr_data = b'\x00\x00' if addr_data is None else pack_uint(len(addr_data)) + addr_data
        return b''.join([
            b'\x00\x00\x00\x00',  # Interface Handle: shall be 0 for CIP
            self._timeout,
            b'\x02\x00',  # Item count: should be at list 2 (Address and Data)
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

    def send(self) -> ResponsePacket:
        ...


@logged
class SendUnitDataRequestPacket(RequestPacket):
    _message_type = DATA_ITEM['Connected']
    _address_type = ADDRESS_ITEM['Connection Based']
    _ResponseClass = SendUnitDataResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self._msg = [pack_uint(plc._get_sequence()), ]

    def send(self):
        msg = self._build_common_packet_format(addr_data=self._plc._target_cid)
        header = self._build_header(ENCAPSULATION_COMMAND['send_unit_data'], len(msg))
        print(f'header: {header}')
        print(f'msg: {msg}')
        self._send(header + msg)
        reply = self._receive()
        return self._ResponseClass(reply)


@logged
class ReadTagServiceRequestPacket(SendUnitDataRequestPacket):
    _ResponseClass = ReadTagServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.elements = None

    def add(self, tag, elements=1):
        self.tag = tag
        self.elements = elements
        request_path = self._plc.create_tag_rp(self.tag)
        if request_path is None:
            self.error = 'Invalid Tag Request Path'

        super().add(
            bytes([TAG_SERVICES_REQUEST['Read Tag']]),
            request_path,
            pack_uint(self.elements),
        )

    def send(self):
        print('send')
        if not self.error:
            response = super().send()
        else:
            response = ReadTagServiceResponsePacket()
            response._error = self.error

        return response


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
class RegisterSessionRequestPacket(RequestPacket):
    def __init__(self, plc):
        super().__init__(plc)

    def send(self):
        msg = self.message
        header = self._build_header(ENCAPSULATION_COMMAND['register_session'], len(msg))
        self._send(header + msg)
        reply = self._receive()
        return RegisterSessionResponsePacket(reply)


@logged
class UnRegisterSessionRequestPacket(RequestPacket):
    def __init__(self, plc):
        super().__init__(plc)

    def send(self):
        header = self._build_header(ENCAPSULATION_COMMAND['unregister_session'], 0)
        self._send(header)
        return UnRegisterSessionResponsePacket(b'')


@logged
class ListIdentityRequestPacket(RequestPacket):
    def __init__(self, plc):
        super().__init__(plc)

    def send(self):
        msg = self._build_header(ENCAPSULATION_COMMAND['list_identity'], 0)
        self._send(msg)
        reply = self._receive()
        return ListIdentityResponsePacket(reply)
