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

from io import BytesIO
from typing import Union

from ..cip import (ClassCode, ConnectionManagerServices, SERVICE_STATUS, EXTEND_CODES, StringDataType,
                   ArrayType, UDINT, BitArrayType, LogicalSegment, PADDED_EPATH, DataSegment, UINT, USINT)
from ..const import PRIORITY, TIMEOUT_TICKS, STRUCTURE_READ_REPLY

__all__ = ['wrap_unconnected_send', 'request_path', 'tag_request_path', 'get_service_status', 'get_extended_status',
           'parse_read_reply', 'dword_to_bool_array', 'print_bytes_msg', 'PacketLazyFormatter']


def wrap_unconnected_send(message: bytes, route_path: bytes) -> bytes:
    rp = request_path(class_code=ClassCode.connection_manager, instance=b'\x01')
    msg_len = len(message)
    return b''.join(
        [
            ConnectionManagerServices.unconnected_send,
            rp,
            PRIORITY,
            TIMEOUT_TICKS,
            UINT.encode(msg_len),
            message,
            b'\x00' if msg_len % 2 else b'',
            route_path
        ]
    )


def request_path(class_code: Union[int, bytes], instance: Union[int, bytes],
                 attribute: Union[int, bytes] = b'') -> bytes:

    segments = [
        LogicalSegment(class_code, 'class_id'),
        LogicalSegment(instance, 'instance_id'),
    ]

    if attribute:
        segments.append(LogicalSegment(attribute, 'attribute_id'))

    return PADDED_EPATH.encode(segments, length=True)

    # path = [encode_segment(class_code, CLASS_TYPE), encode_segment(instance, INSTANCE_TYPE)]
    #
    # if attribute:
    #     path.append(encode_segment(attribute, ATTRIBUTE_TYPE))
    #
    # if data:
    #     path.append(data)
    #
    #
    #
    # return Pack.epath(b''.join(path))


# def encode_segment(segment: Union[bytes, int], segment_types: dict) -> bytes:
#     if isinstance(segment, int):
#         if segment <= 0xff:
#             segment = Pack.usint(segment)
#         elif segment <= 0xffff:
#             segment = Pack.uint(segment)
#         elif segment <= 0xfffffffff:
#             segment = Pack.dint(segment)
#         else:
#             raise RequestError('Invalid segment value')
#
#     _type = segment_types.get(len(segment))
#
#     if _type is None:
#         raise RequestError('Segment value not valid for segment type')
#
#     return _type + segment


def tag_request_path(tag, tag_cache, use_instance_ids):
    """
    It returns the request packed wrapped around the tag passed.
    If any error it returns none
    """

    tags = tag.split('.')
    # segments = []
    if tags:
        base, *attrs = tags
        base_tag, index = _find_tag_index(base)
        if use_instance_ids and base_tag in tag_cache:
            # rp = [CLASS_TYPE['8-bit'],
            #       ClassCode.symbol_object,
            #       INSTANCE_TYPE['16-bit'],
            #       Pack.uint(tag_cache[base_tag]['instance_id'])]
            segments = [
                LogicalSegment(ClassCode.symbol_object, 'class_id'),
                LogicalSegment(tag_cache[base_tag]['instance_id'], 'instance_id')
            ]
        else:
            # base_len = len(base_tag)
            # rp = [EXTENDED_SYMBOL,
            #       Pack.usint(base_len),
            #       base_tag.encode()]
            # if base_len % 2:
            #     rp.append(b'\x00')

            segments = [
                DataSegment(base_tag),
            ]
        if index is None:
            return None
        # rp += _encode_tag_index(index)
        segments += [
            LogicalSegment(int(idx), 'member_id')
            for idx in index
        ]

        for attr in attrs:
            attr, index = _find_tag_index(attr)
            # tag_length = len(attr)
            # # Create the request path
            # attr_path = [EXTENDED_SYMBOL,
            #              Pack.usint(tag_length),
            #              attr.encode()]
            attr_segments = [
                DataSegment(attr)
            ]
            attr_segments += [
                LogicalSegment(int(idx), 'member_id')
                for idx in index
            ]
            # # Add pad byte because total length of Request path must be word-aligned
            # if tag_length % 2:
            #     attr_path.append(b'\x00')
            # # Add any index
            # if index is None:
            #     return None
            # else:
            #     attr_path += _encode_tag_index(index)
            # rp += attr_path
            segments += attr_segments

        # old_ = Pack.epath(b''.join(rp))
        # if new_ != old_:
        #     print(tag)
        #     print(new_)
        #     print(old_)

        return PADDED_EPATH.encode(segments, length=True)

    return None


def _find_tag_index(tag):
    if '[' in tag:  # Check if is an array tag
        t = tag[:len(tag) - 1]  # Remove the last square bracket
        inside_value = t[t.find('[') + 1:]  # Isolate the value inside bracket
        index = inside_value.split(',')  # Now split the inside value in case part of multidimensional array
        tag = t[:t.find('[')]  # Get only the tag part
    else:
        index = []
    return tag, index


# def _encode_tag_index(index):
#     return [encode_segment(int(idx), ELEMENT_TYPE) for idx in index]


def get_service_status(status) -> str:
    return SERVICE_STATUS.get(status, f'Unknown Error ({status:0>2x})')


def get_extended_status(msg, start) -> str:
    status = USINT.decode(msg[start:start + 1])
    # send_rr_data
    # 42 General Status
    # 43 Size of additional status
    # 44..n additional status

    # send_unit_data
    # 48 General Status
    # 49 Size of additional status
    # 50..n additional status
    extended_status_size = (USINT.decode(msg[start + 1:start + 2])) * 2
    extended_status = 0
    if extended_status_size != 0:
        # There is an additional status
        if extended_status_size == 1:
            extended_status = USINT.decode(msg[start + 2:start + 3])
        elif extended_status_size == 2:
            extended_status = UINT.decode(msg[start + 2:start + 4])
        elif extended_status_size == 4:
            extended_status = UDINT.decode(msg[start + 2:start + 6])
        else:
            return 'Extended Status Size Unknown'
    try:
        return f'{EXTEND_CODES[status][extended_status]}  ({status:0>2x}, {extended_status:0>2x})'
    except LookupError:
        return "No Extended Status"


# def make_write_data_bit(tag_info, value, request_path):
#     mask_size = DataTypeSize.get(tag_info['data_type'])
#     if mask_size is None:
#         raise RequestError(f'Invalid data type {tag_info["data_type"]} for writing bits')
#
#     or_mask, and_mask = value
#     return b''.join((
#         Services.read_modify_write,
#         request_path,
#         Pack.uint(mask_size),
#         Pack.ulint(or_mask)[:mask_size],
#         Pack.ulint(and_mask)[:mask_size]
#         ))

#
# DataFormatType = Sequence[Tuple[Optional[str], Union[str, int]]]
#
#
# def parse_reply_data_by_format(data, fmt: DataFormatType):
#     values = {}
#     start = 0
#     for name, typ in fmt:
#         if isinstance(typ, int):
#             value = data[start: start + typ]
#             start += typ
#         elif typ == '*':
#             values[name] = data[start:]
#             break
#         elif typ == 'IP':
#             value = ipaddress.IPv4Address(data[start: start + 4]).exploded
#             start += 4
#         else:
#             typ, cnt = util.get_array_index(typ)
#             unpack_func = Unpack[typ]
#
#             if typ == 'STRINGI':
#                 value, langs, data_size = unpack_func(data[start:])
#
#             elif typ in StringTypeLenSize:
#                 value = unpack_func(data[start:])
#                 data_size = len(value) + StringTypeLenSize[typ]
#
#             else:
#                 data_size = DataTypeSize[typ]
#                 if cnt:
#                     value = tuple(unpack_func(data[i:]) for i in range(start, data_size * cnt, data_size))
#                     data_size *= cnt
#                 else:
#                     value = unpack_func(data[start:])
#
#             start += data_size
#
#         if name:
#             values[name] = value
#
#     return values


def parse_read_reply(data, data_type, elements):
    dt_name = data_type['data_type_name']
    _type = data_type['type_class']
    # value = _type.decode(data)
    is_struct = data[:2] == STRUCTURE_READ_REPLY
    stream = BytesIO(data[4:] if is_struct else data[2:])
    if issubclass(_type, ArrayType):
        _value = _type.decode(stream, length=elements)

        if elements == 1 and not issubclass(_type.element_type, BitArrayType):
            _value = _value[0]
    else:
        _value = _type.decode(stream)
        if is_struct and not issubclass(_type, StringDataType):
            _value = {
                attr: _value[attr]
                for attr in data_type['data_type']['attributes']
            }

    # if data[:2] == STRUCTURE_READ_REPLY:
    #     data = data[4:]
    #     size = data_type['data_type']['template']['structure_size']
    #     dt_name = data_type['data_type']['name']
    #     if elements > 1:
    #         value = [parse_read_reply_struct(data[i: i + size], data_type['data_type'])
    #                  for i in range(0, len(data), size)]
    #     else:
    #         value = parse_read_reply_struct(data, data_type['data_type'])
    # else:
    #     datatype = DataTypes.get_type(DataTypes.uint.decode(data[:2]))
    #     dt_name = str(datatype)
    #     if elements > 1:
    #         size = datatype.size
    #         data = data[2:]
    #         value = [datatype.decode(data[i:i + size]) for i in range(0, len(data), size)]
    #         if datatype == TYPES.DWORD:
    #             value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
    #     else:
    #         # value = Unpack[datatype](data[2:])
    #         value = datatype.decode(data[2:])
    #         if datatype == TYPES.DWORD:
    #             value = dword_to_bool_array(value)

    if dt_name == 'DWORD':
        dt_name = f'BOOL[{elements * 32}]'
        # if elements > 1:
        #     _value = list(chain.from_iterable(_value))
        # if elements == 1:
        #     _value = dword_to_bool_array(_value)
        # else:
        #     _value = list(chain.from_iterable(dword_to_bool_array(val) for val in _value))

    elif elements > 1:
        dt_name = f'{dt_name}[{elements}]'

    return _value, dt_name


# def parse_read_reply_struct(data, data_type):
#     values = {}
#
#     if data_type.get('string'):
#         return parse_string(data)
#
#     for tag, type_def in data_type['internal_tags'].items():
#         datatype = type_def['data_type']
#         array = type_def.get('array')
#         offset = type_def['offset']
#         if type_def['tag_type'] == 'atomic':
#             dt_len = DataTypeSize[datatype]
#             func = Unpack[datatype]
#             if array:
#                 ary_data = data[offset:offset + (dt_len * array)]
#                 value = [func(ary_data[i:i + dt_len]) for i in range(0, array * dt_len, dt_len)]
#                 if datatype == 'DWORD':
#                     value = list(chain.from_iterable(dword_to_bool_array(val) for val in value))
#             else:
#                 if datatype == 'BOOL':
#                     bit = type_def.get('bit', 0)
#                     value = bool(data[offset] & (1 << bit))
#                 else:
#                     value = func(data[offset:offset + dt_len])
#                     if datatype == 'DWORD':
#                         value = dword_to_bool_array(value)
#
#             values[tag] = value
#         elif datatype.get('string'):
#             str_size = datatype['template']['structure_size']
#             if array:
#                 array_data = data[offset:offset + (str_size * array)]
#                 values[tag] = [parse_string(array_data[i:i+str_size]) for i in range(0, len(array_data), str_size)]
#             else:
#                 values[tag] = parse_string(data[offset:offset + str_size])
#         else:
#             struct_size = datatype['template']['structure_size']
#             if array:
#                 ary_data = data[offset:offset + (struct_size * array)]
#                 values[tag] = [parse_read_reply_struct(ary_data[i:i + struct_size], datatype) for i in
#                                range(0, len(ary_data), struct_size)]
#             else:
#                 values[tag] = parse_read_reply_struct(data[offset:offset + struct_size], datatype)
#
#     return {k: v for k, v in values.items() if k in data_type['attributes']}
#
#
# def parse_string(data):
#     str_len = Unpack.dint(data)
#     str_data = data[4:4+str_len]
#     return ''.join(chr(v + 256) if v < 0 else chr(v) for v in str_data)


def dword_to_bool_array(dword: Union[bytes, int]):
    dword = UDINT.decode(dword) if isinstance(dword, bytes) else dword
    bits = [x == '1' for x in bin(dword)[2:]]
    bools = [False for _ in range(32 - len(bits))] + bits
    bools.reverse()
    return bools


def _to_hex(bites):
    return ' '.join((f"{b:0>2x}" for b in bites))


def _to_ascii(bites):
    return ''.join(f'{chr(b)}' if 33 <= b <= 254 else '•' for b in bites)


def print_bytes_msg(msg):
    line_len = 16
    lines = (msg[i:i + line_len] for i in range(0, len(msg), line_len))

    formatted_lines = (
        f'({i * line_len:0>4x}) {_to_hex(line): <48}    {_to_ascii(line)}'
        for i, line in enumerate(lines)
    )

    return '\n'.join(formatted_lines)


class PacketLazyFormatter:

    def __init__(self, data):
        self._data = data

    def __str__(self):
        return print_bytes_msg(self._data)

    def __len__(self):
        return len(self._data)