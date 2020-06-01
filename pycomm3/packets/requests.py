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
from reprlib import repr as _r

from . import Packet, DataFormatType
from . import (ResponsePacket, SendUnitDataResponsePacket, ReadTagServiceResponsePacket, RegisterSessionResponsePacket,
               UnRegisterSessionResponsePacket, ListIdentityResponsePacket, SendRRDataResponsePacket,
               MultiServiceResponsePacket, ReadTagFragmentedServiceResponsePacket, WriteTagServiceResponsePacket,
               WriteTagFragmentedServiceResponsePacket, generic_read_response, generic_write_response)
from .. import CommError, RequestError
from ..bytes_ import pack_uint, pack_udint, pack_dint, print_bytes_msg, pack_usint, PACK_DATA_FUNCTION
from ..const import (ENCAPSULATION_COMMAND, INSUFFICIENT_PACKETS, DATA_ITEM, ADDRESS_ITEM, EXTENDED_SYMBOL, ELEMENT_TYPE,
                     TAG_SERVICES_REQUEST, CLASS_CODE, CLASS_TYPE, INSTANCE_TYPE, DATA_TYPE, DATA_TYPE_SIZE, UNCONNECTED_SEND)


@logged
class RequestPacket(Packet):
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10
    _encap_command = None
    _response_class = ResponsePacket
    type_ = None
    VERBOSE_DEBUG = False

    def __init__(self, plc):
        super().__init__()
        self._msg = []  # message data
        self._plc = plc
        self.error = None

    def add(self, *value: bytes):
        self._msg.extend(value)
        return self

    @property
    def message(self) -> bytes:
        return b''.join(self._msg)

    def _build_request(self):
        msg = self._build_common_packet_format(addr_data=self._plc._target_cid)
        header = self._build_header(self._encap_command, len(msg))
        return header + msg

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
            if self.VERBOSE_DEBUG:
                self.__log.debug(print_bytes_msg(message, '>>> SEND >>>'))
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
            if self.VERBOSE_DEBUG:
                self.__log.debug(print_bytes_msg(reply, '<<< RECEIVE <<<'))
            return reply

    def send(self) -> ResponsePacket:
        if not self.error:
            self._send(self._build_request())
            self.__log.debug(f'Sent: {self!r}')
            reply = self._receive()
            response = self._response_class(reply)
        else:
            response = self._response_class()
            response._error = self.error
        self.__log.debug(f'Received: {response!r}')
        return response

    def __repr__(self):
        return f'{self.__class__.__name__}(message={_r(self._msg)})'

    __str__ = __repr__


@logged
class SendUnitDataRequestPacket(RequestPacket):
    _message_type = DATA_ITEM['Connected']
    _address_type = ADDRESS_ITEM['Connection Based']
    _response_class = SendUnitDataResponsePacket
    _encap_command = ENCAPSULATION_COMMAND['send_unit_data']

    def __init__(self, plc):
        super().__init__(plc)
        self._msg = [pack_uint(plc._sequence), ]


@logged
class ReadTagServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'read'
    _response_class = ReadTagServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.elements = None
        self.tag_info = None

    def add(self, tag, elements=1, tag_info=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        request_path = _create_tag_rp(self.tag, self._plc.tags, self._plc.use_instance_ids)
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
            self.__log.debug(f'Sent: {self!r}')
            reply = self._receive()
            response = ReadTagServiceResponsePacket(reply, elements=self.elements, tag_info=self.tag_info, tag=self.tag)
        else:
            response = ReadTagServiceResponsePacket(tag=self.tag)
            response._error = self.error
        self.__log.debug(f'Received: {response!r}')
        return response

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self.tag!r}, elements={self.elements!r})'


@logged
class ReadTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'read'
    _response_class = ReadTagFragmentedServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.request_path = None

    def add(self, tag, elements=1, tag_info=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_path = _create_tag_rp(self.tag, self._plc.tags, self._plc.use_instance_ids)
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
                self.__log.debug(f'Sent: {self!r} (offset={offset})')
                reply = self._receive()
                response = ReadTagFragmentedServiceResponsePacket(reply, self.tag_info, self.elements)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                if response.service_status == INSUFFICIENT_PACKETS:
                    offset += len(response.bytes_)
                    self._msg = [pack_uint(self._plc._sequence)]
                else:
                    offset = None
            if all(responses):
                final_response = responses[-1]
                final_response.bytes_ = b''.join(resp.bytes_ for resp in responses)
                final_response.parse_bytes()
                self.__log.debug(f'Reassembled Response: {final_response!r}')
                return final_response

        failed_response = ReadTagServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        self.__log.debug(f'Reassembled Response: {failed_response!r}')
        return failed_response

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self.tag!r}, elements={self.elements!r})'


@logged
class WriteTagServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'write'
    _response_class = WriteTagServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
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
        request_path = _create_tag_rp(self.tag, self._plc.tags, self._plc.use_instance_ids)
        if request_path is None:
            self.error = 'Invalid Tag Request Path'
            
        else:
            if bits_write:
                request_path = _make_write_data_bit(tag_info, value, request_path)
                data_type = 'BOOL'
            else:
                request_path, data_type = _make_write_data_tag(tag_info, value, elements, request_path)

            super().add(
                request_path,
            )
            self.data_type = data_type

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self.tag!r}, value={_r(self.value)}, elements={self.elements!r})'


@logged
class WriteTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'write'
    _response_class = WriteTagFragmentedServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.value = None
        self.elements = None
        self.tag_info = None
        self.request_path = None
        self.data_type = None
        self.segment_size = None

    def add(self, tag, value, elements=1, tag_info=None):
        try:
            if tag_info['tag_type'] == 'struct':
                self._packed_type = b'\xA0\x02' + pack_uint(tag_info['data_type']['template']['structure_handle'])
                dt_size = tag_info['data_type']['template']['structure_size']
                self.data_type = tag_info['data_type']['name']
            else:
                self._packed_type = pack_uint(DATA_TYPE[self.data_type])
                dt_size = DATA_TYPE_SIZE[self.data_type]
                self.data_type = tag_info['data_type']

            self.tag = tag
            self.value = value
            self.elements = elements
            self.tag_info = tag_info
            self.request_path = _create_tag_rp(self.tag, self._plc.tags, self._plc.use_instance_ids)
            if self.request_path is None:
                self.error = 'Invalid Tag Request Path'
        except Exception as err:
            self.__log.exception('Failed adding request')
            self.error = err

    def send(self):
        if not self.error:
            responses = []
            segment_size = self._plc.connection_size - (len(self.request_path) + len(self._packed_type)
                                                        + 9)  # 9 = len of other stuff in the path

            pack_func = PACK_DATA_FUNCTION[self.data_type] if self.tag_info['tag_type'] == 'atomic' else lambda x: x
            segments = (self.value[i:i+segment_size]
                        for i in range(0, len(self.value), segment_size))

            offset = 0
            elements_packed = pack_uint(self.elements)

            for i, segment in enumerate(segments, start=1):
                segment_bytes = b''.join(pack_func(s) for s in segment) if not isinstance(segment, bytes) else segment
                self._msg.extend((
                    bytes([TAG_SERVICES_REQUEST["Write Tag Fragmented"]]),
                    self.request_path,
                    self._packed_type,
                    elements_packed,
                    pack_dint(offset),
                    segment_bytes
                ))

                self._send(self._build_request())
                self.__log.debug(f'Sent: {self!r} (part={i} offset={offset})')
                reply = self._receive()
                response = WriteTagFragmentedServiceResponsePacket(reply)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                offset += len(segment_bytes)
                self._msg = [pack_uint(self._plc._sequence), ]

            if all(responses):
                final_response = responses[-1]
                self.__log.debug(f'Reassembled Response: {final_response!r}')
                return final_response

        failed_response = WriteTagFragmentedServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        self.__log.debug(f'Reassembled Response: {failed_response!r}')
        return failed_response


@logged
class MultiServiceRequestPacket(SendUnitDataRequestPacket):
    type_ = 'multi'
    _response_class = MultiServiceResponsePacket

    def __init__(self, plc, sequence=1):
        super().__init__(plc)
        self.tags = []
        self._msg.extend((
            bytes([TAG_SERVICES_REQUEST["Multiple Service Packet"]]),  # the Request Service
            pack_usint(2),  # the Request Path Size length in word
            CLASS_TYPE["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_TYPE["8-bit"],
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

        request_path = _create_tag_rp(tag, self._plc.tags, self._plc.use_instance_ids)
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
        request_path = _create_tag_rp(tag, self._plc.tags, self._plc.use_instance_ids)
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
            self.__log.debug(f'Sent: {self!r}')
            reply = self._receive()
            response = MultiServiceResponsePacket(reply, tags=self.tags)
        else:
            self.error = f'Failed to create request path for: {", ".join(self._msg_errors)}'
            response = MultiServiceResponsePacket()
            response._error = self.error

        self.__log.debug(f'Received: {response!r}')
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
    return b''.join((
            bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]]),
            request_path,
            pack_uint(mask_size),
            pack_udint(or_mask)[:mask_size],
            pack_udint(and_mask)[:mask_size]
        ))


@logged
class SendRRDataRequestPacket(RequestPacket):
    _message_type = DATA_ITEM['Unconnected']
    _address_type = ADDRESS_ITEM['UCMM']
    _encap_command = ENCAPSULATION_COMMAND['send_rr_data']
    _response_class = SendRRDataResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return super()._build_common_packet_format(addr_data=None)


@logged
class RegisterSessionRequestPacket(RequestPacket):
    _encap_command = ENCAPSULATION_COMMAND['register_session']
    _response_class = RegisterSessionResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return self.message


@logged
class UnRegisterSessionRequestPacket(RequestPacket):
    _encap_command = ENCAPSULATION_COMMAND['unregister_session']
    _response_class = UnRegisterSessionResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''

    def _receive(self):
        return b''


@logged
class ListIdentityRequestPacket(RequestPacket):
    _encap_command = ENCAPSULATION_COMMAND['list_identity']
    _response_class = ListIdentityResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''


def _create_tag_rp(tag, tag_cache, use_instance_ids):
    """

    It returns the request packed wrapped around the tag passed.
    If any error it returns none
    """
    tags = tag.split('.')
    if tags:
        base, *attrs = tags

        if use_instance_ids and base in tag_cache:
            rp = [CLASS_TYPE['8-bit'],
                  CLASS_CODE['Symbol Object'],
                  INSTANCE_TYPE['16-bit'],
                  pack_uint(tag_cache[base]['instance_id'])]
        else:
            base_tag, index = _find_tag_index(base)
            base_len = len(base_tag)
            rp = [EXTENDED_SYMBOL,
                  pack_usint(base_len),
                  base_tag]
            if base_len % 2:
                rp.append(b'\x00')
            if index is None:
                return None
            else:
                rp += index

        for attr in attrs:
            attr, index = _find_tag_index(attr)
            tag_length = len(attr)
            # Create the request path
            attr_path = [EXTENDED_SYMBOL,
                         pack_usint(tag_length),
                         attr]
            # Add pad byte because total length of Request path must be word-aligned
            if tag_length % 2:
                attr_path.append(b'\x00')
            # Add any index
            if index is None:
                return None
            else:
                attr_path += index
            rp += attr_path

        # At this point the Request Path is completed,
        request_path = b''.join(rp)
        request_path = bytes([len(request_path) // 2]) + request_path

        return request_path

    return None


def _find_tag_index(tag):
    if '[' in tag:  # Check if is an array tag
        t = tag[:len(tag) - 1]  # Remove the last square bracket
        inside_value = t[t.find('[') + 1:]  # Isolate the value inside bracket
        index = inside_value.split(',')  # Now split the inside value in case part of multidimensional array
        tag = t[:t.find('[')]  # Get only the tag part
    else:
        index = []
    return tag.encode(), _encode_tag_index(index)


def _encode_tag_index(index):
        path = []
        for idx in index:
            val = int(idx)
            if val <= 0xff:
                path += [ELEMENT_TYPE["8-bit"], pack_usint(val)]
            elif val <= 0xffff:
                path += [ELEMENT_TYPE["16-bit"], pack_uint(val)]
            elif val <= 0xfffffffff:
                path += [ELEMENT_TYPE["32-bit"], pack_dint(val)]
            else:
                return None  # Cannot create a valid request packet
        return path


def generic_read_request(connected=True):

    base_class = SendUnitDataRequestPacket if connected else SendRRDataRequestPacket

    @logged
    class GenericReadRequestPacket(base_class):
        _response_class = generic_read_response(connected)

        def __init__(self, plc, service: bytes, class_code: bytes, instance: bytes, request_data: bytes = None,
                     data_format: DataFormatType = None, unconnected_send=False):
            super().__init__(plc)
            self.data_format = data_format
            self.class_code = class_code
            self.instance = instance
            self.service = service
            self.request_data = request_data
            class_type = CLASS_TYPE.get(len(class_code))

            if class_type is None:
                raise RequestError(f'Invalid Class Code Length ({len(class_code)}), must be 1 or 2 bytes')

            instance_type = INSTANCE_TYPE.get(len(instance))
            if instance_type is None:
                raise RequestError(f'Invalid Instance Length ({len(instance)}), must be 1 or 2 bytes')

            if unconnected_send:
                self.add(_unconnected_send())

            request_path = b''.join((class_type, class_code, instance_type, instance))
            request_path_len = bytes([len(request_path) // 2])
            self.add(service, request_path_len, request_path)

            if request_data is not None:
                self.add(request_data)

        def __repr__(self):
            return f'{self.__class__.__name__}(service={self.service!r}, class_code={self.class_code!r}, ' \
                   f'instance={self.instance!r}, request_data={self.request_data!r})'

        def send(self):
            if not self.error:
                self._send(self._build_request())
                self.__log.debug(f'Sent: {self!r}')
                reply = self._receive()
                response = self._response_class(reply, data_format=self.data_format)
            else:
                response = self._response_class()
                response._error = self.error
            self.__log.debug(f'Received: {response!r}')
            return response

    return GenericReadRequestPacket


def generic_write_request(connected=True):
    base_class = SendUnitDataRequestPacket if connected else SendRRDataRequestPacket

    @logged
    class GenericWriteRequestPacket(base_class):
        _response_class = generic_write_response(connected)

        def __init__(self, plc, service: bytes, class_code: bytes, instance: bytes, request_data: bytes = None,
                     unconnected_send=False):
            super().__init__(plc)
            self.class_code = class_code
            self.instance = instance
            self.service = service
            self.request_data = request_data
            class_type = CLASS_TYPE.get(len(class_code))

            if class_type is None:
                raise RequestError(f'Invalid Class Code Length ({len(class_code)}), must be 1 or 2 bytes')

            instance_type = INSTANCE_TYPE.get(len(instance))
            if instance_type is None:
                raise RequestError(f'Invalid Instance Length ({len(instance)}), must be 1 or 2 bytes')

            if unconnected_send:
                self.add(_unconnected_send())

            request_path = b''.join((class_type, class_code, instance_type, instance))
            request_path_len = bytes([len(request_path) // 2])
            self.add(service, request_path_len, request_path)

            if request_data is not None:
                self.add(request_data)

        def __repr__(self):
            return f'{self.__class__.__name__}(service={self.service!r}, class_code={self.class_code!r}, ' \
                   f'instance={self.instance!r}, request_data={self.request_data!r})'

    return GenericWriteRequestPacket


def _unconnected_send():
    return b''.join((
    UNCONNECTED_SEND,
    b'\x02',
    CLASS_TYPE['8-bit'],
    b'\x06',  # class
    INSTANCE_TYPE["8-bit"],
    b'\x01',  # instance
    b'\x0A',  # priority
    b'\x0e',  # timeout ticks
    b'\x06\x00',  # service size
))

