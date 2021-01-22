import ipaddress
from itertools import chain
from typing import Union, Sequence, Tuple, Optional

from .. import util
from ..bytes_ import Pack, Unpack
from ..const import (ClassCode, ConnectionManagerServices, PRIORITY, TIMEOUT_TICKS, CLASS_TYPE, INSTANCE_TYPE,
                     ATTRIBUTE_TYPE, SERVICE_STATUS, DataType, DataTypeSize, StringTypeLenSize, STRUCTURE_READ_REPLY,
                     Services, EXTEND_CODES)
from ..exceptions import RequestError


def wrap_unconnected_send(message: bytes, route_path: bytes) -> bytes:
    rp = request_path(class_code=ClassCode.connection_manager, instance=b'\x01')
    msg_len = len(message)
    return b''.join(
        [
            ConnectionManagerServices.unconnected_send,
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
                 attribute: Union[int, bytes] = b'', data: bytes = b'') -> bytes:

    path = [encode_segment(class_code, CLASS_TYPE), encode_segment(instance, INSTANCE_TYPE)]

    if attribute:
        path.append(encode_segment(attribute, ATTRIBUTE_TYPE))

    if data:
        path.append(data)

    return Pack.epath(b''.join(path))


def encode_segment(segment: Union[bytes, int], segment_types: dict) -> bytes:
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


def get_service_status(status) -> str:
    return SERVICE_STATUS.get(status, f'Unknown Error ({status:0>2x})')


def get_extended_status(msg, start) -> str:
    status = Unpack.usint(msg[start:start + 1])
    # send_rr_data
    # 42 General Status
    # 43 Size of additional status
    # 44..n additional status

    # send_unit_data
    # 48 General Status
    # 49 Size of additional status
    # 50..n additional status
    extended_status_size = (Unpack.usint(msg[start + 1:start + 2])) * 2
    extended_status = 0
    if extended_status_size != 0:
        # There is an additional status
        if extended_status_size == 1:
            extended_status = Unpack.usint(msg[start + 2:start + 3])
        elif extended_status_size == 2:
            extended_status = Unpack.uint(msg[start + 2:start + 4])
        elif extended_status_size == 4:
            extended_status = Unpack.dint(msg[start + 2:start + 6])
        else:
            return 'Extended Status Size Unknown'
    try:
        return f'{EXTEND_CODES[status][extended_status]}  ({status:0>2x}, {extended_status:0>2x})'
    except LookupError:
        return "No Extended Status"


def make_write_data_tag(tag_info, value, elements, request_path, fragmented=False):
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


def make_write_data_bit(tag_info, value, request_path):
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


DataFormatType = Sequence[Tuple[Optional[str], Union[str, int]]]


def parse_reply_data_by_format(data, fmt: DataFormatType):
    values = {}
    start = 0
    for name, typ in fmt:
        if isinstance(typ, int):
            value = data[start: start + typ]
            start += typ
        elif typ == '*':
            values[name] = data[start:]
            break
        elif typ == 'IP':
            value = ipaddress.IPv4Address(data[start: start + 4]).exploded
            start += 4
        else:
            typ, cnt = util.get_array_index(typ)
            unpack_func = Unpack[typ]

            if typ == 'STRINGI':
                value, langs, data_size = unpack_func(data[start:])

            elif typ in StringTypeLenSize:
                value = unpack_func(data[start:])
                data_size = len(value) + StringTypeLenSize[typ]

            else:
                data_size = DataTypeSize[typ]
                if cnt:
                    value = tuple(unpack_func(data[i:]) for i in range(start, data_size * cnt, data_size))
                    data_size *= cnt
                else:
                    value = unpack_func(data[start:])

            start += data_size

        if name:
            values[name] = value

    return values


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
        datatype = DataType[Unpack.uint(data[:2])]
        dt_name = datatype
        if elements > 1:
            func = Unpack[datatype]
            size = DataTypeSize[datatype]
            data = data[2:]
            value = [func(data[i:i + size]) for i in range(0, len(data), size)]
            if datatype == 'DWORD':
                value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
        else:
            value = Unpack[datatype](data[2:])
            if datatype == 'DWORD':
                value = dword_to_bool_array(value)

    if dt_name == 'DWORD':
        dt_name = f'BOOL[{elements * 32}]'
    elif elements > 1:
        dt_name = f'{dt_name}[{elements}]'

    return value, dt_name


def parse_read_reply_struct(data, data_type):
    values = {}

    if data_type.get('string'):
        return parse_string(data)

    for tag, type_def in data_type['internal_tags'].items():
        datatype = type_def['data_type']
        array = type_def.get('array')
        offset = type_def['offset']
        if type_def['tag_type'] == 'atomic':
            dt_len = DataTypeSize[datatype]
            func = Unpack[datatype]
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
            struct_size = datatype['template']['structure_size']
            if array:
                ary_data = data[offset:offset + (struct_size * array)]
                values[tag] = [parse_read_reply_struct(ary_data[i:i + struct_size], datatype) for i in
                               range(0, len(ary_data), struct_size)]
            else:
                values[tag] = parse_read_reply_struct(data[offset:offset + struct_size], datatype)

    return {k: v for k, v in values.items() if k in data_type['attributes']}


def parse_string(data):
    str_len = Unpack.dint(data)
    str_data = data[4:4+str_len]
    return ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)


def dword_to_bool_array(dword):
    bits = [x == '1' for x in bin(dword)[2:]]
    bools = [False for _ in range(32 - len(bits))] + bits
    bools.reverse()
    return bools