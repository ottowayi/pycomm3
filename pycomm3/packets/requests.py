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
               MultiServiceResponsePacket, ReadTagFragmentedServiceResponsePacket, WriteTagServiceResponsePacket,
               WriteTagFragmentedServiceResponsePacket)
from .. import CommError, RequestError
from ..bytes_ import pack_uint, pack_udint, pack_dint, print_bytes_msg, pack_usint, PACK_DATA_FUNCTION
from ..const import (ENCAPSULATION_COMMAND, INSUFFICIENT_PACKETS, DATA_ITEM, ADDRESS_ITEM,
                     TAG_SERVICES_REQUEST, CLASS_CODE, CLASS_ID, INSTANCE_ID, DATA_TYPE, DATA_TYPE_SIZE)


@logged
class RequestPacket(Packet):
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10
    type_ = None

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
    type_ = 'read'

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
    type_ = 'read'

    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.request_path = None

    def add(self, tag, elements=1, tag_info=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_path = self._plc.create_tag_rp(self.tag)
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
        return failed_response


@logged
class WriteTagServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'write'

    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.value = None
        self.data_type = None

    def add(self, tag, value, elements=1, tag_info=None, bits_write=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.value = value
        request_path = self._plc.create_tag_rp(self.tag)
        if request_path is None:
            self.error = 'Invalid Tag Request Path'
            
        else:
            if bits_write:
                request_path = _make_write_data_bit(tag_info, value, request_path)
                data_type = 'BOOL'
            else:
                request_path, data_type = _make_write_data_tag(tag_info, value, elements, request_path)

            super().add(
                bytes([TAG_SERVICES_REQUEST['Write Tag']]),
                request_path,
            )
            self.data_type = data_type

    def send(self):
        if not self.error:
            self._send(self._build_request())
            reply = self._receive()
            return WriteTagServiceResponsePacket(reply)
        else:
            response = WriteTagServiceResponsePacket()
            response._error = self.error

        return response


@logged
class WriteTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'write'

    def __init__(self, plc):
        super().__init__(plc)
        self.error = None
        self.tag = None
        self.value = None
        self.elements = None
        self.tag_info = None
        self.request_path = None
        self.data_type = None

    def add(self, tag, value, elements=1, tag_info=None):
        if tag_info['tag_type'] != 'atomic':
            raise RequestError('Fragmented write of structures is not supported')

        self.tag = tag
        self.value = value
        self.elements = elements
        self.data_type = tag_info['data_type']
        self.tag_info = tag_info
        self.request_path = self._plc.create_tag_rp(self.tag)
        if self.request_path is None:
            self.error = 'Invalid Tag Request Path'

    def send(self):
        if not self.error:
            responses = []
            segment_size = self._plc.connection_size // (DATA_TYPE_SIZE[self.data_type] + 4)
            pack_func = PACK_DATA_FUNCTION[self.data_type]
            segments = (self.value[i:i+segment_size]
                        for i in range(0, len(self.value), segment_size))

            offset = 0
            elements_packed = pack_uint(self.elements)
            data_type_packed = pack_uint(DATA_TYPE[self.data_type])
            for segment in segments:
                segment_bytes = b''.join(pack_func(s) for s in segment)
                self._msg.extend((
                    bytes([TAG_SERVICES_REQUEST["Write Tag Fragmented"]]),
                    self.request_path,
                    data_type_packed,
                    elements_packed,
                    pack_dint(offset),
                    segment_bytes
                ))

                self._send(self._build_request())
                reply = self._receive()
                response = WriteTagFragmentedServiceResponsePacket(reply)
                responses.append(response)
                offset += len(segment_bytes)
                self._msg = [pack_uint(self._plc._get_sequence()), ]

            if all(responses):
                final_response = responses[-1]
                return final_response

        failed_response = ReadTagServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        return failed_response


@logged
class MultiServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'multi'

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

    def add_read(self, tag, elements=1, tag_info=None):

        request_path = self._plc.create_tag_rp(tag)
        if request_path is not None:

            request_path = bytes([TAG_SERVICES_REQUEST['Read Tag']]) + request_path + pack_uint(elements)
            _tag = {'tag': tag, 'elements': elements, 'tag_info': tag_info, 'rp': request_path, 'service': 'read'}
            message = self.build_message(self.tags + [_tag])
            if len(message) < self._plc.connection_size:
                self._message = message
                self.tags.append(_tag)
                return True
            else:
                return False
        else:
            self.__log.error(f'Failed to create request path for {tag}')
            raise RequestError('Failed to create request path')

    def add_write(self, tag, value, elements=1, tag_info=None, bits_write=None):
        request_path = self._plc.create_tag_rp(tag)
        if request_path is not None:
            if bits_write:
                data_type = tag_info['data_type']
                request_path = _make_write_data_bit(tag_info, value, request_path)
            else:
                request_path, data_type = _make_write_data_tag(tag_info, value, elements, request_path)

            _tag = {'tag': tag, 'elements': elements, 'tag_info': tag_info, 'rp': request_path, 'service': 'write',
                    'value': value, 'data_type': data_type}

            message = self.build_message(self.tags + [_tag])
            if len(message) < self._plc.connection_size:
                self._message = message
                self.tags.append(_tag)
                return True
            else:
                return False

        else:
            self.__log.error(f'Failed to create request path for {tag}')
            raise RequestError('Failed to create request path')

    def send(self):
        if not self._msg_errors:
            request = self._build_request()
            self._send(request)
            reply = self._receive()
            return MultiServiceResponsePacket(reply, tags=self.tags)
        else:
            self.error = f'Failed to create request path for: {", ".join(self._msg_errors)}'
            response = MultiServiceResponsePacket()
            response._error = self.error
            return response


def _make_write_data_tag(tag_info, value, elements, request_path, fragmented=False):
    data_type = tag_info['data_type']
    if tag_info['tag_type'] == 'struct':
        if not isinstance(value, bytes):
            raise RequestError('Writing UDTs only supports bytes for value')
        _dt_value = b'\xA0\x02' + pack_uint(tag_info['data_type']['template']['structure_handle'])
        data_type = tag_info['data_type']['name']

    elif data_type not in DATA_TYPE:
        raise RequestError("Unsupported data type")
    else:
        _dt_value = pack_uint(DATA_TYPE[data_type])

    service = bytes([TAG_SERVICES_REQUEST['Write Tag Fragmented' if fragmented else 'Write Tag']])

    request_path = b''.join((service,
                             request_path,
                             _dt_value,
                             pack_uint(elements),
                             value))
    return request_path, data_type


def _make_write_data_bit(tag_info, value, request_path):
    mask_size = DATA_TYPE_SIZE.get(tag_info['data_type'])
    if mask_size is None:
        raise RequestError(f'Invalid data type {tag_info["data_type"]} for writing bits')

    or_mask, and_mask = value
    request_path = b''.join((
        bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]]),
        request_path,
        pack_uint(mask_size),
        pack_udint(or_mask)[:mask_size],
        pack_udint(and_mask)[:mask_size]
    ))

    return request_path


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
