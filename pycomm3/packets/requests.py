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
from typing import Union
from reprlib import repr as _r

from . import Packet, DataFormatType
from . import (ResponsePacket, SendUnitDataResponsePacket, ReadTagServiceResponsePacket, RegisterSessionResponsePacket,
               UnRegisterSessionResponsePacket, ListIdentityResponsePacket, SendRRDataResponsePacket,
               MultiServiceResponsePacket, ReadTagFragmentedServiceResponsePacket, WriteTagServiceResponsePacket,
               WriteTagFragmentedServiceResponsePacket, GenericUnconnectedResponsePacket,
               GenericConnectedResponsePacket)
from ..exceptions import CommError, RequestError
from ..bytes_ import Pack, print_bytes_msg
from ..const import (EncapsulationCommand, INSUFFICIENT_PACKETS, DataItem, AddressItem, EXTENDED_SYMBOL, ELEMENT_TYPE,
                     Services, CLASS_TYPE, INSTANCE_TYPE, DataType, DataTypeSize, ConnectionManagerService,
                     ClassCode, Services, STRUCTURE_READ_REPLY, PRIORITY, TIMEOUT_TICKS, ATTRIBUTE_TYPE)


class RequestPacket(Packet):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = None
    _address_type = None
    _timeout = b'\x0a\x00'  # 10
    _encap_command = None
    _response_class = ResponsePacket
    _response_args = ()
    _response_kwargs = {}
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
                Pack.uint(length),  # Length UINT
                Pack.udint(self._plc._session),  # Session Handle UDINT
                b'\x00\x00\x00\x00',  # Status UDINT
                self._plc._cfg['context'],  # Sender Context 8 bytes
                Pack.udint(self._plc._cfg['option']),  # Option UDINT
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

    def _send(self, message):

        try:
            if self.VERBOSE_DEBUG:
                self.__log.debug(print_bytes_msg(message, '>>> SEND >>>'))
            self._plc._sock.send(message)
        except Exception as err:
            raise CommError('failed to send message') from err

    def _receive(self):
        """
        socket receive
        :return: reply data
        """
        try:
            reply = self._plc._sock.receive()
        except Exception as err:
            raise CommError('failed to receive reply') from err
        else:
            if self.VERBOSE_DEBUG:
                self.__log.debug(print_bytes_msg(reply, '<<< RECEIVE <<<'))
            return reply

    def send(self) -> ResponsePacket:
        if not self.error:
            self._send(self._build_request())
            self.__log.debug(f'Sent: {self!r}')
            reply = self._receive()
            response = self._response_class(reply, *self._response_args, **self._response_kwargs)
        else:
            response = self._response_class(*self._response_args, **self._response_kwargs)
            response._error = self.error
        self.__log.debug(f'Received: {response!r}')
        return response

    def __repr__(self):
        return f'{self.__class__.__name__}(message={_r(self._msg)})'

    __str__ = __repr__


class SendUnitDataRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = DataItem.connected
    _address_type = AddressItem.connection
    _response_class = SendUnitDataResponsePacket
    _encap_command = EncapsulationCommand.send_unit_data

    def __init__(self, plc):
        super().__init__(plc)
        self._msg = [Pack.uint(plc._sequence), ]


class ReadTagServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'read'
    _response_class = ReadTagServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.request_id = None

    def add(self, tag, request_path, elements, tag_info, request_id):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_id = request_id
        if request_path is None:
            self.error = 'Invalid Tag Request Path'

        super().add(
            Services.read_tag,
            request_path,
            Pack.uint(self.elements),
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


class ReadTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'read'
    _response_class = ReadTagFragmentedServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.request_path = None
        self.request_id = None

    def add(self, tag, request_path, elements, tag_info, request_id):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_path = request_path
        self.request_id = request_id
        if self.request_path is None:
            self.error = 'Invalid Tag Request Path'

    def send(self):
        if not self.error:
            offset = 0
            responses = []
            while offset is not None:
                self._msg.extend([Services.read_tag_fragmented,
                                  self.request_path,
                                  Pack.uint(self.elements),
                                  Pack.dint(offset)])
                self._send(self._build_request())
                self.__log.debug(f'Sent: {self!r} (offset={offset})')
                reply = self._receive()
                response = ReadTagFragmentedServiceResponsePacket(reply, self.tag_info, self.elements)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                if response.service_status == INSUFFICIENT_PACKETS:
                    offset += len(response.bytes_)
                    self._msg = [Pack.uint(self._plc._sequence)]
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


class WriteTagServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'write'
    _response_class = WriteTagServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tag = None
        self.elements = None
        self.tag_info = None
        self.value = None
        self.data_type = None
        self.request_id = None

    def add(self, tag, request_path, value, elements, tag_info, request_id, bits_write=None):
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.value = value
        self.request_id = request_id
        request_path = request_path
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


class WriteTagFragmentedServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
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
        self.request_id = None
        self._packed_type = None

    def add(self, tag, request_path, value, elements, tag_info, request_id):
        try:
            self.data_type = tag_info['data_type_name']
            self.tag = tag
            self.value = value
            self.elements = elements
            self.tag_info = tag_info
            self.request_path = request_path
            self.request_id = request_id

            if tag_info['tag_type'] == 'struct':
                self._packed_type = STRUCTURE_READ_REPLY + Pack.uint(tag_info['data_type']['template']['structure_handle'])
            else:
                self._packed_type = Pack.uint(DataType[self.data_type])

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

            pack_func = Pack[self.data_type] if self.tag_info['tag_type'] == 'atomic' else lambda x: x
            segments = (self.value[i:i+segment_size]
                        for i in range(0, len(self.value), segment_size))

            offset = 0
            elements_packed = Pack.uint(self.elements)

            for i, segment in enumerate(segments, start=1):
                segment_bytes = b''.join(pack_func(s) for s in segment) if not isinstance(segment, bytes) else segment
                self._msg.extend((
                    Services.write_tag_fragmented,
                    self.request_path,
                    self._packed_type,
                    elements_packed,
                    Pack.dint(offset),
                    segment_bytes
                ))

                self._send(self._build_request())
                self.__log.debug(f'Sent: {self!r} (part={i} offset={offset})')
                reply = self._receive()
                response = WriteTagFragmentedServiceResponsePacket(reply)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                offset += len(segment_bytes)
                self._msg = [Pack.uint(self._plc._sequence), ]

            if all(responses):
                final_response = responses[-1]
                self.__log.debug(f'Reassembled Response: {final_response!r}')
                return final_response

        failed_response = WriteTagFragmentedServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        self.__log.debug(f'Reassembled Response: {failed_response!r}')
        return failed_response


class MultiServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'multi'
    _response_class = MultiServiceResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.tags = []
        self._msg.extend((
            Services.multiple_service_request,  # the Request Service
            Pack.usint(2),  # the Request Path Size length in word
            CLASS_TYPE["8-bit"],
            ClassCode.message_router,
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
            offsets.append(Pack.uint(offset))
            offset += len(rp)

        msg = self._msg + [Pack.uint(len(rp_list))] + offsets + rp_list
        return b''.join(msg)

    def add_read(self, tag, request_path, elements, tag_info, request_id):
        if request_path is not None:
            rp = Services.read_tag + request_path + Pack.uint(elements)
            _tag = {
                'tag': tag,
                'elements': elements,
                'tag_info': tag_info,
                'rp': rp,
                'service': 'read',
                'request_id': request_id
            }
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

    def add_write(self, tag, request_path, value, elements, tag_info, request_id, bits_write=None):
        if request_path is not None:
            if bits_write:
                data_type = tag_info['data_type']
                request_path = _make_write_data_bit(tag_info, value, request_path)
            else:
                request_path, data_type = _make_write_data_tag(tag_info, value, elements, request_path)

            _tag = {'tag': tag, 'elements': elements, 'tag_info': tag_info, 'rp': request_path, 'service': 'write',
                    'value': value, 'data_type': data_type, 'request_id': request_id}

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
        _dt_value = b'\xA0\x02' + Pack.uint(tag_info['data_type']['template']['structure_handle'])
        data_type = tag_info['data_type']['name']

    elif data_type not in DataType:
        raise RequestError("Unsupported data type")
    else:
        _dt_value = Pack.uint(DataType[data_type])

    service = Services.write_tag_fragmented if fragmented else Services.write_tag

    rp = b''.join((service,
                   request_path,
                   _dt_value,
                   Pack.uint(elements),
                   value))
    return rp, data_type


def _make_write_data_bit(tag_info, value, request_path):
    mask_size = DataTypeSize.get(tag_info['data_type'])
    if mask_size is None:
        raise RequestError(f'Invalid data type {tag_info["data_type"]} for writing bits')

    or_mask, and_mask = value
    return b''.join((
        Services.read_modify_write,
        request_path,
        Pack.uint(mask_size),
        Pack.ulint(or_mask)[:mask_size],
        Pack.ulint(and_mask)[:mask_size]
        ))


class SendRRDataRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _message_type = DataItem.unconnected
    _address_type = AddressItem.uccm
    _encap_command = EncapsulationCommand.send_rr_data
    _response_class = SendRRDataResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return super()._build_common_packet_format(addr_data=None)


class RegisterSessionRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommand.register_session
    _response_class = RegisterSessionResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return self.message


class UnRegisterSessionRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommand.unregister_session
    _response_class = UnRegisterSessionResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''

    def _receive(self):
        return b''


class ListIdentityRequestPacket(RequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _encap_command = EncapsulationCommand.list_identity
    _response_class = ListIdentityResponsePacket

    def _build_common_packet_format(self, addr_data=None) -> bytes:
        return b''


class GenericConnectedRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _response_class = GenericConnectedResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.service = None
        self.class_code = None
        self.instance = None
        self.attribute = None
        self.request_data = None

    def build(self,
              service: bytes,
              class_code: bytes,
              instance: bytes,
              attribute: bytes = b'',
              request_data: bytes = b'',
              data_format: DataFormatType = None):

        self._response_kwargs = {'data_format': data_format}
        self.class_code = class_code
        self.instance = instance
        self.attribute = attribute
        self.service = service
        self.request_data = request_data
        req_path = request_path(class_code, instance, attribute)

        self.add(service, req_path, request_data)


class GenericUnconnectedRequestPacket(SendRRDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    _response_class = GenericUnconnectedResponsePacket

    def __init__(self, plc):
        super().__init__(plc)
        self.service = None
        self.class_code = None
        self.instance = None
        self.attribute = None
        self.request_data = None

    def build(self,
              service: Union[int, bytes],
              class_code: Union[int, bytes],
              instance: Union[int, bytes],
              attribute: Union[int, bytes] = b'',
              request_data: bytes = b'',
              route_path: bytes = b'',
              unconnected_send: bool = False,
              data_format: DataFormatType = None):
        self._response_kwargs = {'data_format': data_format}
        self.class_code = class_code
        self.instance = instance
        self.attribute = attribute
        self.service = service
        self.request_data = request_data
        req_path = request_path(class_code, instance, attribute)

        if unconnected_send:
            self.add(wrap_unconnected_send(b''.join((service, req_path, request_data)), route_path))
        else:
            self.add(service, req_path, request_data, route_path)


def wrap_unconnected_send(message, route_path):
    rp = request_path(class_code=ClassCode.connection_manager, instance=b'\x01')
    msg_len = len(message)
    return b''.join(
        [
            ConnectionManagerService.unconnected_send,
            rp,
            PRIORITY,
            TIMEOUT_TICKS,
            Pack.uint(msg_len),
            message,
            b'\x00' if msg_len % 2 else b'',
            route_path
        ]
    )


def request_path(class_code: Union[int, bytes], instance: Union[int, bytes],
                 attribute: Union[int, bytes] = b'', data: bytes = b''):

    path = [encode_segment(class_code, CLASS_TYPE), encode_segment(instance, INSTANCE_TYPE)]

    if attribute:
        path.append(encode_segment(attribute, ATTRIBUTE_TYPE))

    if data:
        path.append(data)

    return Pack.epath(b''.join(path))


def encode_segment(segment: Union[bytes, int], segment_types: dict):
    if isinstance(segment, int):
        if segment <= 0xff:
            segment = Pack.usint(segment)
        elif segment <= 0xffff:
            segment = Pack.uint(segment)
        elif segment <= 0xfffffffff:
            segment = Pack.dint(segment)
        else:
            raise RequestError('Invalid segment value')

    _type = segment_types.get(len(segment))

    if _type is None:
        raise RequestError('Segment value not valid for segment type')

    return _type + segment
