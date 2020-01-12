# -*- coding: utf-8 -*-
#
# const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
# Copyright (c) 2019 Ian Ottoway <ian@ottoway.dev>
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

from autologging import logged

from . import Packet
from . import (ResponsePacket, SendUnitDataResponsePacket, ReadTagServiceResponsePacket, RegisterSessionResponsePacket,
               UnRegisterSessionResponsePacket, ListIdentityResponsePacket, SendRRDataResponsePacket,
               MultiServiceResponsePacket, ReadTagFragmentedServiceResponsePacket)
from .. import CommError
from ..bytes_ import pack_uint, pack_dint, print_bytes_msg, pack_usint
from ..const import (ENCAPSULATION_COMMAND, INSUFFICIENT_PACKETS, DATA_ITEM, ADDRESS_ITEM,
                     TAG_SERVICES_REQUEST, CLASS_CODE, CLASS_ID, INSTANCE_ID)


@logged
class RequestPacket(Packet):
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10
    single = True

    def __init__(self, plc):
        super().__init__()
        self._msg = []  # message data
        self._plc = plc

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
        msg = self.message
        return b''.join([
            b'\x00\x00\x00\x00',  # Interface Handle: shall be 0 for CIP
            self._timeout,
            b'\x02\x00',  # Item count: should be at list 2 (Address and Data)
            self._address_type,
            addr_data,
            self._message_type,
            pack_uint(len(msg)),
            msg
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

    def __init__(self, plc):
        super().__init__(plc)
        self._msg = [pack_uint(plc._get_sequence()), ]

    def _build_request(self):
        msg = self._build_common_packet_format(addr_data=self._plc._target_cid)
        header = self._build_header(ENCAPSULATION_COMMAND['send_unit_data'], len(msg))
        return header + msg

    def send(self):
        self._send(self._build_request())
        reply = self._receive()
        return SendUnitDataResponsePacket(reply)


@logged
class ReadTagServiceRequestPacket(SendUnitDataRequestPacket):

    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.elements = None
        self.tag_info = None

    def add(self, tag, elements=1, tag_info=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        request_path = self._plc.create_tag_rp(self.tag)
        if request_path is None:
            self.error = 'Invalid Tag Request Path'

        super().add(
            bytes([TAG_SERVICES_REQUEST['Read Tag']]),
            request_path,
            pack_uint(self.elements),
        )

    def send(self):
        if not self.error:
            self._send(self._build_request())
            reply = self._receive()
            return ReadTagServiceResponsePacket(reply, elements=self.elements, tag_info=self.tag_info, tag=self.tag)
        else:
            response = ReadTagServiceResponsePacket(tag=self.tag)
            response._error = self.error

        return response


@logged
class ReadTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.request_path = None
        self.request_num = 0

    def add(self, tag, elements=1, tag_info=None, request_num=0):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_path = self._plc.create_tag_rp(self.tag)
        self.request_num = request_num
        if self.request_path is None:
            self.error = 'Invalid Tag Request Path'

    def send(self):
        if not self.error:
            offset = 0
            responses = []
            while offset is not None:
                self._msg.extend([bytes([TAG_SERVICES_REQUEST['Read Tag Fragmented']]),
                                 self.request_path,
                                 pack_uint(self.elements),
                                 pack_dint(offset)])
                self._send(self._build_request())
                reply = self._receive()
                response = ReadTagFragmentedServiceResponsePacket(reply, self.tag_info, self.elements)
                responses.append(response)
                if response.service_status == INSUFFICIENT_PACKETS:
                    offset += len(response.bytes_)
                    self._msg = [pack_uint(self._plc._get_sequence())]
                else:
                    offset = None
            if all(responses):
                final_response = responses[-1]
                final_response.bytes_ = b''.join(resp.bytes_ for resp in responses)
                final_response.parse_bytes()
                return final_response

        failed_response = ReadTagServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'


@logged
class MultiServiceRequestPacket(SendUnitDataRequestPacket):
    single = False

    def __init__(self, plc, sequence=1):
        super().__init__(plc)
        self.error = None
        self.tags = []
        self._msg.extend((
            bytes([TAG_SERVICES_REQUEST["Multiple Service Packet"]]),  # the Request Service
            pack_usint(2),  # the Request Path Size length in word
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            b'\x01',  # Instance 1
        ))
        self._message = None
        self._msg_errors = None

    @property
    def message(self) -> bytes:
        return self._message

    def build_message(self, tags):
        rp_list, errors = [], []
        for tag in tags:
            if tag['rp'] is None:
                errors.append(f'Unable to create request path {tag["tag"]}')
            else:
                rp_list.append(tag['rp'])

        offset = len(rp_list) * 2 + 2
        offsets = []
        for rp in rp_list:
            offsets.append(pack_uint(offset))
            offset += len(rp)

        msg = self._msg + [pack_uint(len(rp_list))] + offsets + rp_list
        return b''.join(msg)

    def add_read(self, tag, elements=1, tag_info=None, request_num=0):

        request_path = self._plc.create_tag_rp(tag)
        if request_path is not None:
            request_path = bytes([TAG_SERVICES_REQUEST['Read Tag']]) + request_path + pack_uint(elements)
            tag = {'tag': tag, 'elements': elements, 'tag_info': tag_info, 'rp': request_path, 'request_num': request_num}
            message = self.build_message(self.tags + [tag])
            if len(message) < self._plc.connection_size:
                self._message = message
                self.tags.append(tag)
                return True
            else:
                return False
        else:
            self.__log.error(f'Failed to create request path for {tag}')
            return False

    def add_write(self, tag, value, tag_info):
        ...

    def send(self):
        if not self._msg_errors:
            self._send(self._build_request())
            reply = self._receive()
            return MultiServiceResponsePacket(reply, tags=self.tags)
        else:
            self.error = f'Failed to create request path for: {", ".join(self._msg_errors)}'
            response = MultiServiceResponsePacket()
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
