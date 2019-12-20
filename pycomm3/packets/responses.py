from . import Packet
from ..bytes_ import pack_uint, pack_dint, print_bytes_msg, unpack_uint, unpack_usint, unpack_dint, UNPACK_DATA_FUNCTION
# from .. import CommError, LogixDriver, Tag
from autologging import logged
from ..const import (ENCAPSULATION_COMMAND, REPLY_INFO, SUCCESS, INSUFFICIENT_PACKETS, TAG_SERVICES_REPLY,
                    get_service_status, get_extended_status, MULTI_PACKET_SERVICES, DATA_ITEM, ADDRESS_ITEM,
                    REPLY_START, TAG_SERVICES_REQUEST, STRUCTURE_READ_REPLY, DATA_TYPE, DATA_TYPE_SIZE)
from collections import defaultdict


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


@logged
class ReadTagServiceResponsePacket(SendUnitDataResponsePacket):
    def __init__(self, raw_data: bytes = None, *args, tag_info=None, string_types=None, **kwargs):
        self.value = None
        self.data_type = None
        self.tag_info = tag_info
        self._string_types = string_types or []
        super().__init__(raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            if self.data[:2] == STRUCTURE_READ_REPLY:
                self.data_type = unpack_uint(self.data[2:4])
                # print(f'raw = {self.data[4:]}')
                self.value = self._parse_structure_reply(self.data[4:], self.tag_info['udt'])

            else:
                data_type = DATA_TYPE[unpack_uint(self.data[:2])]
                value = UNPACK_DATA_FUNCTION[data_type](self.data[2:])
                self.data_type = data_type
                self.value = value

        except Exception as err:
            self.__log.exception('fuck')
            self._error = f'Failed to parse reply - {err}'

    def _parse_structure_reply(self, data, data_type):
        values = {}
        size = data_type['template']['structure_size']

        for tag, type_def in data_type['internal_tags'].items():
            data_type = type_def['data_type']
            array = type_def.get('array')
            offset = type_def['offset']
            if type_def['atomic']:
                dt_len = DATA_TYPE_SIZE[data_type]
                func = UNPACK_DATA_FUNCTION[data_type]
                if array:
                    ary_data = data[offset:offset + (dt_len * array)]
                    value = [func(ary_data[i:i+dt_len]) for i in range(0, array, dt_len)]
                else:
                    if data_type == 'BOOL':
                        bit = type_def.get('bit', 0)
                        value = bool(data[offset] & (1 << bit))
                    else:
                        value = func(data[offset:offset + dt_len])
                        if data_type == 'DWORD':
                            bits = [x == '1' for x in bin(value)[2:]]
                            value = [False for _ in range(32 - len(bits))] + bits
                values[tag] = value
            elif data_type['name'] in self._string_types:

                str_len = unpack_dint(data[offset:offset + 4])
                str_data = data[offset + 4: offset + 4 + str_len]
                values[tag] = ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)
            else:
                if array:
                    ary_data = data[offset:offset + (size * array)]
                    values[tag] = [self._parse_structure_reply(ary_data[i:i+size], data_type) for i in range(0, array, size)]
                else:
                    values[tag] = self._parse_structure_reply(data[offset:offset+size], data_type)
        return values

    def __str__(self):
        return f'{self.__class__.__name__}({self.data_type}, {self.value}, {self.service_status})'

    __repr__ = __str__


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


