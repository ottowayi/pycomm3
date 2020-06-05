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
from reprlib import repr as _r
from itertools import tee, zip_longest, chain

from autologging import logged

from . import Packet, DataFormatType
from ..bytes_ import unpack_uint, unpack_usint, unpack_dint, UNPACK_DATA_FUNCTION, DATA_FUNCTION_SIZE
from ..const import (SUCCESS, INSUFFICIENT_PACKETS, TAG_SERVICES_REPLY, SERVICE_STATUS,EXTEND_CODES,
                     MULTI_PACKET_SERVICES, REPLY_START, STRUCTURE_READ_REPLY,
                     DATA_TYPE, DATA_TYPE_SIZE)


@logged
class ResponsePacket(Packet):

    def __init__(self, raw_data: bytes = None, *args, **kwargs):
        super().__init__()
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
    def error(self):
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

    def command_extended_status(self):
        return 'Unknown Error'

    def service_extended_status(self):
        return 'Unknown Error'

    def __repr__(self):
        return f'{self.__class__.__name__}(service={bytes([self.service]) if self.service else None!r}, command={self.command!r}, error={self.error!r})'

    __str__ = __repr__


@logged
class SendUnitDataResponsePacket(ResponsePacket):
    def __init__(self, raw_data: bytes = None, *args, **kwargs):
        super().__init__(raw_data, *args, **kwargs)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.service = self.raw[46]
            self.service_status = unpack_usint(self.raw[48:49])
            self.data = self.raw[REPLY_START:]
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self):
        valid = self.service_status == SUCCESS or (self.service_status == INSUFFICIENT_PACKETS and
                                                   self.service in MULTI_PACKET_SERVICES)
        return all((
            super().is_valid(),
            valid
        ))

    def command_extended_status(self):
        return f'{get_service_status(self.command_status)} - {get_extended_status(self.raw, 48)}'

    def service_extended_status(self):
        return f'{get_service_status(self.service_status)} - {get_extended_status(self.raw, 48)}'


def generic_read_response(connected=True):
    base_class = SendUnitDataResponsePacket if connected else SendRRDataResponsePacket

    @logged
    class GenericReadResponsePacket(base_class):
        def __init__(self, *args, data_format: DataFormatType = None, **kwargs):
            self.data_format = data_format
            self.value = None
            super().__init__(*args, **kwargs)

        def _parse_reply(self):
            super()._parse_reply()
            if self.data_format is None:
                self.value = self.data
            elif self.is_valid():
                try:
                    values = {}
                    start = 0
                    for name, typ in self.data_format:
                        if isinstance(typ, int):
                            value = self.data[start: start + typ]
                            start += typ
                        else:
                            unpack_func = UNPACK_DATA_FUNCTION[typ]
                            value = unpack_func(self.data[start:])
                            if typ == 'SHORT_STRING':
                                data_size = len(value) + 1
                            else:
                                data_size = DATA_FUNCTION_SIZE[typ]
                            start += data_size

                        if name:
                            values[name] = value
                except Exception as err:
                    self._error = f'Failed to parse reply - {err}'
                    self.value = None
                else:
                    self.value = values

        def __repr__(self):
            return f'{self.__class__.__name__}(value={_r(self.value)}, error={self.error!r})'

    return GenericReadResponsePacket


def generic_write_response(connected=True):
    base_class = SendUnitDataResponsePacket if connected else SendRRDataResponsePacket

    @logged
    class GenericWriteResponsePacket(base_class):
        ...

    return GenericWriteResponsePacket


@logged
class ReadTagServiceResponsePacket(SendUnitDataResponsePacket):
    def __init__(self, raw_data: bytes = None, tag_info=None, elements=1, tag=None, *args,  **kwargs):
        self.value = None
        self.elements = elements
        self.data_type = None
        self.tag_info = tag_info
        self.tag = tag
        super().__init__(raw_data, *args, **kwargs)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            if self.is_valid():
                self.value, self.data_type = parse_read_reply(self.data, self.tag_info, self.elements)
            else:
                self.value, self.data_type = None, None
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.data_type!r}, {_r(self.value)}, {self.service_status!r})'


@logged
class ReadTagFragmentedServiceResponsePacket(SendUnitDataResponsePacket):
    def __init__(self, raw_data: bytes = None, tag_info=None, elements=1, *args,  **kwargs):
        self.value = None
        self.elements = elements
        self.data_type = None
        self.tag_info = tag_info
        self.bytes_ = None
        super().__init__(raw_data, *args, **kwargs)

    def _parse_reply(self):
        super()._parse_reply()
        if self.data[:2] == STRUCTURE_READ_REPLY:
            self.bytes_ = self.data[4:]
            self._data_type = self.data[:4]
        else:
            self.bytes_ = self.data[2:]
            self._data_type = self.data[:2]

    def parse_bytes(self):
        try:
            if self.is_valid():
                self.value, self.data_type = parse_read_reply(self._data_type + self.bytes_,
                                                          self.tag_info, self.elements)
            else:
                self.value, self.data_type = None, None
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'

    def __repr__(self):
        return f'{self.__class__.__name__}(raw_data={_r(self.raw)})'

    __str__ = __repr__


@logged
class WriteTagServiceResponsePacket(SendUnitDataResponsePacket):
    ...


@logged
class WriteTagFragmentedServiceResponsePacket(SendUnitDataResponsePacket):
    ...





@logged
class MultiServiceResponsePacket(SendUnitDataResponsePacket):

    def __init__(self, raw_data: bytes = None, tags=None, *args, **kwargs):
        self.tags = tags
        self.values = None
        self.request_statuses = None
        super().__init__(raw_data, *args, **kwargs)

    def _parse_reply(self):
        super()._parse_reply()
        num_replies = unpack_uint(self.data)
        offset_data = self.data[2:2 + 2 * num_replies]
        offsets = (unpack_uint(offset_data[i:i+2]) for i in range(0, len(offset_data), 2))
        start, end = tee(offsets)  # split offsets into start/end indexes
        next(end)   # advance end by 1 so 2nd item is the end index for the first item
        reply_data = [self.data[i:j] for i, j in zip_longest(start, end)]
        values = []

        for data, tag in zip(reply_data, self.tags):
            service = unpack_uint(data)
            service_status = data[2]
            tag['service_status'] = service_status
            if service_status != SUCCESS:
                tag['error'] = f'{get_service_status(service_status)} - {get_extended_status(data, 2)}'

            if service == TAG_SERVICES_REPLY['Read Tag']:
                if service_status == SUCCESS:
                    value, dt = parse_read_reply(data[4:], tag['tag_info'], tag['elements'])
                else:
                    value, dt = None, None

                values.append(value)
                tag['value'] = value
                tag['data_type'] = dt

        self.values = values

    def __repr__(self):
        return f'{self.__class__.__name__}(values={_r(self.values)}, error={self.error!r})'


@logged
class SendRRDataResponsePacket(ResponsePacket):

    def __init__(self, raw_data: bytes = None, *args, **kwargs):
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

    def command_extended_status(self):
        return f'{get_service_status(self.command_status)} - {get_extended_status(self.raw, 42)}'

    def service_extended_status(self):
        return f'{get_service_status(self.service_status)} - {get_extended_status(self.raw, 42)}'


@logged
class RegisterSessionResponsePacket(ResponsePacket):

    def __init__(self, raw_data: bytes = None, *args, **kwargs):
        self.session = None
        super().__init__(raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.session = unpack_dint(self.raw[4:8])
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self):
        return all((
            super().is_valid(),
            self.session is not None
        ))

    def __repr__(self):
        return f'{self.__class__.__name__}(session={self.session!r}, error={self.error!r})'


@logged
class UnRegisterSessionResponsePacket(ResponsePacket):

    def _parse_reply(self):
        ...  # nothing to parse

    def is_valid(self):
        return True

    def __repr__(self):
        return 'UnRegisterSessionResponsePacket()'


@logged
class ListIdentityResponsePacket(ResponsePacket):

    def __init__(self, raw_data: bytes = None, *args, **kwargs):
        self.identity = None
        super().__init__(raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            self.identity = self.raw[63:-1].decode()
        except Exception as err:
            self._error = f'Failed to parse reply - {err}'

    def is_valid(self):
        return all((
            super().is_valid(),
            self.identity is not None
        ))

    def __repr__(self):
        return f'{self.__class__.__name__}(identity={self.identity!r}, error={self.error!r})'


def parse_read_reply(data, data_type, elements):
    if data[:2] == STRUCTURE_READ_REPLY:
        data = data[4:]
        size = data_type['data_type']['template']['structure_size']
        dt_name = data_type['data_type']['name']
        if elements > 1:
            value = [parse_read_reply_struct(data[i: i + size], data_type['data_type'])
                     for i in range(0, len(data), size)]
        else:
            value = parse_read_reply_struct(data, data_type['data_type'])
    else:
        datatype = DATA_TYPE[unpack_uint(data[:2])]
        dt_name = datatype
        if elements > 1:
            func = UNPACK_DATA_FUNCTION[datatype]
            size = DATA_TYPE_SIZE[datatype]
            data = data[2:]
            value = [func(data[i:i + size]) for i in range(0, len(data), size)]
            if datatype == 'DWORD':
                value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
        else:
            value = UNPACK_DATA_FUNCTION[datatype](data[2:])
            if datatype == 'DWORD':
                value = dword_to_bool_array(value)

    if dt_name == 'DWORD':
        dt_name = f'BOOL[{elements * 32}]'
    elif elements > 1:
        dt_name = f'{dt_name}[{elements}]'

    return value, dt_name


def parse_read_reply_struct(data, data_type):
    values = {}
    size = data_type['template']['structure_size']

    if data_type.get('string'):
        return parse_string(data)

    for tag, type_def in data_type['internal_tags'].items():
        datatype = type_def['data_type']
        array = type_def.get('array')
        offset = type_def['offset']
        if type_def['tag_type'] == 'atomic':
            dt_len = DATA_TYPE_SIZE[datatype]
            func = UNPACK_DATA_FUNCTION[datatype]
            if array:
                ary_data = data[offset:offset + (dt_len * array)]
                value = [func(ary_data[i:i + dt_len]) for i in range(0, array * dt_len, dt_len)]
                if datatype == 'DWORD':
                    value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
            else:
                if datatype == 'BOOL':
                    bit = type_def.get('bit', 0)
                    value = bool(data[offset] & (1 << bit))
                else:
                    value = func(data[offset:offset + dt_len])
                    if datatype == 'DWORD':
                        value = dword_to_bool_array(value)

            values[tag] = value
        elif datatype.get('string'):
            str_size = datatype['template']['structure_size']
            if array:
                array_data = data[offset:offset + (str_size * array)]
                values[tag] = [parse_string(array_data[i:i+str_size]) for i in range(0, len(array_data), str_size)]
            else:
                values[tag] = parse_string(data[offset:offset + str_size])
        else:
            if array:
                ary_data = data[offset:offset + (size * array)]
                values[tag] = [parse_read_reply_struct(ary_data[i:i + size], datatype) for i in
                               range(0, len(ary_data), size)]
            else:
                values[tag] = parse_read_reply_struct(data[offset:offset + size], datatype)

    return {k: v for k, v in values.items() if k in data_type['attributes']}


def parse_string(data):
    str_len = unpack_dint(data)
    str_data = data[4:4+str_len]
    string = ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)
    return string


def dword_to_bool_array(dword):
    bits = [x == '1' for x in bin(dword)[2:]]
    bools = [False for _ in range(32 - len(bits))] + bits
    bools.reverse()
    return bools


def get_service_status(status):
    return SERVICE_STATUS.get(status, f'Unknown Error ({status:0>2x})')


def get_extended_status(msg, start):
    status = unpack_usint(msg[start:start + 1])
    # send_rr_data
    # 42 General Status
    # 43 Size of additional status
    # 44..n additional status

    # send_unit_data
    # 48 General Status
    # 49 Size of additional status
    # 50..n additional status
    extended_status_size = (unpack_usint(msg[start + 1:start + 2])) * 2
    extended_status = 0
    if extended_status_size != 0:
        # There is an additional status
        if extended_status_size == 1:
            extended_status = unpack_usint(msg[start + 2:start + 3])
        elif extended_status_size == 2:
            extended_status = unpack_uint(msg[start + 2:start + 4])
        elif extended_status_size == 4:
            extended_status = unpack_dint(msg[start + 2:start + 6])
        else:
            return 'Extended Status Size Unknown'
    try:
        return f'{EXTEND_CODES[status][extended_status]}  ({status:0>2x}, {extended_status:0>2x})'
    except LookupError:
        return "No Extended Status"
