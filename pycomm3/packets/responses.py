from . import Packet
from ..bytes_ import pack_uint, pack_dint, print_bytes_msg, unpack_uint, unpack_usint, unpack_dint, UNPACK_DATA_FUNCTION
# from .. import CommError, LogixDriver, Tag
from autologging import logged
from ..const import (ENCAPSULATION_COMMAND, REPLY_INFO, SUCCESS, INSUFFICIENT_PACKETS, TAG_SERVICES_REPLY,
                    get_service_status, get_extended_status, MULTI_PACKET_SERVICES, DATA_ITEM, ADDRESS_ITEM,
                    REPLY_START, TAG_SERVICES_REQUEST, STRUCTURE_READ_REPLY, DATA_TYPE, DATA_TYPE_SIZE)
from collections import defaultdict
from itertools import tee, zip_longest, chain

import better_exceptions


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


def parse_read_reply_struct(data, data_type):
    values = {}
    size = data_type['template']['structure_size']

    for tag, type_def in data_type['internal_tags'].items():
        data_type = type_def['data_type']
        array = type_def.get('array')
        offset = type_def['offset']
        if type_def['tag_type'] == 'atomic':
            dt_len = DATA_TYPE_SIZE[data_type]
            func = UNPACK_DATA_FUNCTION[data_type]
            if array:
                ary_data = data[offset:offset + (dt_len * array)]
                value = [func(ary_data[i:i + dt_len]) for i in range(0, array * dt_len, dt_len)]
                if data_type == 'DWORD':
                    value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
                    value.reverse()
            else:
                if data_type == 'BOOL':
                    bit = type_def.get('bit', 0)
                    value = bool(data[offset] & (1 << bit))
                else:
                    value = func(data[offset:offset + dt_len])
                    if data_type == 'DWORD':
                        value = dword_to_bool_array(value)

            values[tag] = value
        elif data_type.get('string'):
            str_size = data_type.get('string') + 4
            if array:
                array_data = data[offset:offset + (str_size * array)]
                values[tag] = [parse_string(array_data[i:i+str_size]) for i in range(0, array*str_size, str_size)]
            else:
                str_len = unpack_dint(data[offset:offset + 4])
                str_data = data[offset + 4: offset + 4 + str_len]
                values[tag] = ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)
        else:
            if array:
                ary_data = data[offset:offset + (size * array)]
                values[tag] = [parse_read_reply_struct(ary_data[i:i + size], data_type) for i in
                               range(0, array*size, size)]
            else:
                values[tag] = parse_read_reply_struct(data[offset:offset + size], data_type)
    return values


def parse_string(data):
    str_len = unpack_dint(data)
    str_data = data[4:4+str_len]
    string = ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)
    return string


def dword_to_bool_array(dword):
    bits = [x == '1' for x in bin(dword)[2:]]
    bools = [False for _ in range(32 - len(bits))] + bits
    return bools


def parse_read_reply(data, data_type, elements):
    if data[:2] == STRUCTURE_READ_REPLY:
        # data_type = data_type['udt']['name']
        data = data[4:]
        size = data_type['udt']['template']['structure_size']
        dt = data_type['udt']['name']
        if elements > 1:
            dt = f'{dt}[{elements}]'
            value = [parse_read_reply_struct(data[i: i + size], data_type['udt'])
                     for i in range(0, len(data), size)]
        else:
            value = parse_read_reply_struct(data, data_type['udt'])

    else:
        data_type = DATA_TYPE[unpack_uint(data[:2])]
        dt = data_type
        if elements > 1:
            func = UNPACK_DATA_FUNCTION[data_type]
            size = DATA_TYPE_SIZE[data_type]
            data = data[2:]
            value = [func(data[i:i + size]) for i in range(0, len(data), size)]
            dt = f'{data_type}[{elements}]'
        else:
            value = UNPACK_DATA_FUNCTION[data_type](data[2:])
    return value, dt


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
            self.value, self.data_type = parse_read_reply(self.data, self.tag_info, self.elements)
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'

    def __str__(self):
        return f'{self.__class__.__name__}({self.data_type}, {self.value}, {self.service_status})'

    def __repr__(self):
        return self.__str__()


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
            self.value, self.data_type = parse_read_reply(self._data_type + self.bytes_,
                                                          self.tag_info, self.elements)
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'


class MultiServiceResponsePacket(SendUnitDataResponsePacket):

    def __init__(self, raw_data: bytes = None, tags=None, *args, **kwargs):
        self.tags = tags
        self.values = None
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
            service = unpack_dint(data)
            if service == TAG_SERVICES_REPLY['Read Tag']:
                service_status = data[2]
                tag['service_status'] = service_status
                if service_status == SUCCESS:
                    value, dt = parse_read_reply(data[4:], tag['tag_info'], tag['elements'])
                else:
                    value, dt = None, None
                values.append(value)
                tag['value'] = value
                tag['data_type'] = dt
        self.values = values


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


@logged
class UnRegisterSessionResponsePacket(ResponsePacket):

    def _parse_reply(self):
        ...  # nothing to parse

    def is_valid(self):
        return True


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


