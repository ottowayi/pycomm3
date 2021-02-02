import reprlib
import logging
import ipaddress
from io import BytesIO
from struct import pack, unpack
from typing import Any, Sequence, Optional, Tuple, Dict, Union, List

from ..exceptions import DataError, BufferEmptyError

_BufferType = Union[BytesIO, bytes]


def _repr(buffer: _BufferType) -> str:
    if isinstance(buffer, BytesIO):
        return repr(buffer.getvalue())
    else:
        return repr(buffer)


def _get_bytes(buffer: _BufferType, length: int) -> bytes:
    if isinstance(buffer, bytes):
        return buffer[:length]

    return buffer.read(length)


def _as_stream(buffer: _BufferType):
    if isinstance(buffer, bytes):
        return BytesIO(buffer)
    return buffer


class DataType:

    def __init__(self, name: Optional[str] = None):
        self.name = name

    @classmethod
    def encode(cls, value: Any) -> bytes:
        try:
            return cls._encode(value)
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        ...

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        try:
            stream = _as_stream(buffer)
            return cls._decode(stream)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        ...

    def __repr__(self) -> str:
        return self.__class__.__name__


class ElementaryDataType(DataType):
    code: int = 0x00
    size: int = 0
    _format: str = ''

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        data = stream.read(cls.size)
        if not data:
            raise BufferEmptyError()
        return unpack(cls._format, data)[0]


class BOOL(ElementaryDataType):
    code = 0xc1
    size = 1

    @classmethod
    def _encode(cls, value: Any) -> bytes:
        return b'\xFF' if value else b'\x00'

    @classmethod
    def _decode(cls, stream: BytesIO) -> bool:
        data = stream.read(cls.size)
        if not data:
            raise BufferEmptyError()
        return data != b'\x00'


class SINT(ElementaryDataType):
    code = 0xc2
    size = 1
    _format = '<b'


class INT(ElementaryDataType):
    code = 0xc3
    size = 2
    _format = '<h'


class DINT(ElementaryDataType):
    code = 0xc4
    size = 4
    _format = '<i'


class LINT(ElementaryDataType):
    code = 0xc5
    size = 8
    _format = '<q'


class USINT(ElementaryDataType):
    code = 0xc6
    size = 1
    _format = '<B'


class UINT(ElementaryDataType):
    code = 0xc7
    size = 2
    _format = '<H'


class UDINT(ElementaryDataType):
    code = 0xc8
    size = 4
    _format = '<I'


class ULINT(ElementaryDataType):
    code = 0xc9
    size = 8
    _format = '<Q'


class REAL(ElementaryDataType):
    code = 0xca
    size = 4
    _format = '<f'


class LREAL(ElementaryDataType):
    code = 0xcb
    size = 8
    _format = '<d'


class STIME(DINT):
    code = 0xcc


class DATE(UINT):
    code = 0xcd


class TIME_OF_DAY(UDINT):
    code = 0xce


class DATE_AND_TIME(ElementaryDataType):
    code = 0xcf
    size = 8

    @classmethod
    def encode(cls, time: int, date: int, *args, **kwargs) -> bytes:
        try:
            return UDINT.encode(time) + UINT.encode(date)
        except Exception as err:
            raise DataError(f'Error packing {time!r} as {cls.__name__}') from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> Tuple[int, int]:
        return UDINT.decode(stream), UINT.decode(stream)


class StringDataType(ElementaryDataType):
    len_type = None
    encoding = 'iso-8859-1'

    @classmethod
    def _encode(cls, value: str, *args, **kwargs) -> bytes:
        return cls.len_type.encode(len(value)) + value.encode(cls.encoding)

    @classmethod
    def _decode(cls, stream: BytesIO) -> str:
        str_len = cls.len_type.decode(stream)
        str_data = stream.read(str_len)
        if not str_data:
            raise BufferEmptyError()

        return str_data.decode(cls.encoding)


class LOGIX_STRING(StringDataType):
    len_type = UDINT


class STRING(StringDataType):
    code = 0xd0
    len_type = UINT


class BytesDataType(ElementaryDataType):

    @classmethod
    def _encode(cls, value: bytes, *args, **kwargs) -> bytes:
        return value[:cls.size]

    @classmethod
    def _decode(cls, stream: BytesIO) -> bytes:
        data = stream.read(cls.size)
        if len(data) < cls.size:
            raise BufferEmptyError()
        return data


def n_bytes(count: int, name: str = ''):
    class BYTES(BytesDataType):
        size = count

    return BYTES(name)


class BYTE(BytesDataType):
    code = 0xd1
    size = 1


class WORD(BytesDataType):
    code = 0xd2
    size = 2


class DWORD(BytesDataType):
    code = 0xd3
    size = 4


class LWORD(BytesDataType):
    code = 0xd4
    size = 8


class STRING2(StringDataType):
    code = 0xd5
    len_type = UINT
    encoding = 'utf-16-le'


class FTIME(DINT):
    code = 0xd6


class LTIME(LINT):
    code = 0xd7


class ITIME(INT):
    code = 0xd8


class STRINGN(StringDataType):
    code = 0xd9
    ENCODINGS = {
        1: 'utf-8',
        2: 'utf-16-le',
        4: 'utf-32-le'
    }

    @classmethod
    def encode(cls, value: str, char_size: int = 1) -> bytes:
        ...

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        char_size = UINT.decode(stream)
        char_count = UINT.decode(stream)

        try:
            encoding = cls.ENCODINGS[char_size]
        except KeyError as err:
            raise DataError(f'Unsupported character size: {char_size}') from err
        else:
            data = stream.read(char_count * char_size)
            if not data:
                raise BufferEmptyError()

            return data.decode(encoding)


class SHORT_STRING(StringDataType):
    code = 0xda
    len_type = USINT


class TIME(DINT):
    code = 0xdb


class EPATH(ElementaryDataType):
    code = 0xdc
    padded = False

    @classmethod
    def encode(cls, segments: Sequence['CIPSegment'], length: bool = False, pad_length: bool = False) -> bytes:
        try:
            path = b''.join(segment.encode(segment, padded=cls.padded) for segment in segments)
            if length:
                _len = USINT.encode(len(path) // 2)
                if pad_length:
                    _len += b'\x00'
                path = _len + path
            return path
        except Exception as err:
            raise DataError(f'Error packing {reprlib.repr(segments)} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Sequence['CIPSegment']:
        raise NotImplementedError('Decoding EPATHs not supported')


class PADDED_EPATH(EPATH):
    padded = True


class PACKED_EPATH(EPATH):
    padded = False


class ENGUNIT(WORD):
    code = 0xdd
    # TODO: create lookup table of defined eng. units


class STRINGI(StringDataType):
    code = 0xde

    STRING_TYPES = {
        STRING.code: STRING,
        STRING2.code: STRING2,
        STRINGN.code: STRINGN,
        SHORT_STRING.code: SHORT_STRING
    }

    LANGUAGE_CODES = {
        'english': 'eng',
        'french': 'fra',
        'spanish': 'spa',
        'italian': 'ita',
        'german': 'deu',
        'japanese': 'jpn',
        'portuguese': 'por',
        'chinese': 'zho',
        'russian': 'rus'
    }

    CHARACTER_SETS = {
        'iso-8859-1': 4,
        'iso-8859-2': 5,
        'iso-8859-3': 6,
        'iso-8859-4': 7,
        'iso-8859-5': 8,
        'iso-8859-6': 9,
        'iso-8859-7': 10,
        'iso-8859-8': 11,
        'iso-8859-9': 12,
        'utf-16-le': 1000,
        'utf-32-le': 1001
    }

    @classmethod
    def encode(cls, *strings: Sequence[Tuple[str, StringDataType, str, int]]) -> bytes:
        try:
            count = len(strings)
            data = USINT.encode(count)

            for (string, str_type, lang, char_set) in strings:
                _str_type = bytes([str_type.code])
                _lang = bytes(lang, 'ascii')
                _char_set = UINT.encode(char_set)
                _string = str_type.encode(string)

                data += _lang + _str_type + _char_set + _string

            return data
        except Exception as err:
            raise DataError(f'Error packing {reprlib.repr(strings)} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Tuple[Sequence[str], Sequence[str], Sequence[int]]:
        stream = _as_stream(buffer)
        try:
            count = USINT.decode(stream)
            strings = []
            langs = []
            char_sets = []
            for _ in range(count):
                lang = SHORT_STRING.decode(b'\x03' + stream.read(3))
                langs.append(lang)
                _str_type = cls.STRING_TYPES[stream.read(1)[0]]
                char_set = UINT.decode(stream)
                char_sets.append(char_set)
                string = _str_type.decode(stream)
                strings.append(string)

            return strings, langs, char_sets
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


class DerivedDataType(DataType):
    ...


def array(length_: Union[USINT, UINT, UDINT, ULINT, int, None],
          element_type_: DataType, name: str = '') -> 'Array':
    """
    length_:
        int - fixed length of the array
        DataType - length read from beginning of buffer as type
        None - array consumes rest buffer
    """

    class Array(DerivedDataType):
        _log = logging.getLogger(f'{__module__}.{__qualname__}')

        length = length_
        element_type = element_type_

        @classmethod
        def encode(cls, values: List[Any]) -> bytes:
            if isinstance(cls.length, int):
                if len(values) < cls.length:
                    raise DataError(f'Not enough values to encode array of {cls.element_type}[{cls.length}]')
                if len(values) > cls.length:
                    cls._log.warning(f'Too many values supplied, truncating {len(values)} to {cls.length}')

                _len = cls.length
            else:
                _len = len(values)

            try:
                return b''.join(cls.element_type.encode(values[i]) for i in range(_len))
            except Exception as err:
                raise DataError(f'Error packing {reprlib.repr(values)} into {cls.element_type}[{cls.length}]') from err

        @classmethod
        def _decode_all(cls, stream):
            _array = []
            while True:
                try:
                    _array.append(cls.element_type.decode(stream))
                except BufferEmptyError:
                    break
            return _array

        @classmethod
        def decode(cls, buffer: _BufferType) -> List[str]:
            try:
                stream = _as_stream(buffer)
                if cls.length is None:
                    return cls._decode_all(stream)

                if isinstance(cls.length, DataType):
                    _len = cls.length.decode(stream)
                else:
                    _len = cls.length

                return [cls.element_type.decode(stream) for _ in range(cls.length)]
            except Exception as err:
                if isinstance(err, BufferEmptyError):
                    raise
                else:
                    raise DataError(f'Error unpacking into {cls.element_type}[{cls.length}] from {_repr(buffer)}') from err

    return Array(name)


def struct(members_: Sequence[DataType], name: str = '') -> 'Struct':

    class Struct(DerivedDataType):
        members = members_

        @classmethod
        def _encode(cls, values: Dict[str, Any]) -> bytes:
            return b''.join(typ.encode(values[typ.name]) for typ in cls.members)

        @classmethod
        def _decode(cls, stream: BytesIO) -> Any:
            values = {
                typ.name: typ.decode(stream)
                for typ in cls.members
            }
            values.pop('', None)
            values.pop(None, None)
            return values

    return Struct(name)


class IP_ADDR(DerivedDataType):

    @classmethod
    def _encode(cls, value: str) -> bytes:
        return ipaddress.IPv4Address(value).packed

    @classmethod
    def _decode(cls, stream: BytesIO) -> Any:
        data = stream.read(4)
        if not data:
            raise BufferEmptyError()
        return ipaddress.IPv4Address(data).exploded


class CIPSegment(DataType):
    #   Segment      Segment
    #    Type        Format
    # [7, 6, 5] [4, 3, 2, 1, 0]
    segment_type = 0b_000_00000

    @classmethod
    def encode(cls, segment: 'CIPSegment', padded: bool = False) -> bytes:
        try:
            return cls._encode(segment, padded)
        except Exception as err:
            raise DataError(f'Error packing {reprlib.repr(segment)} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        raise NotImplementedError('Decoding of CIP Segments not supported')


class PortSegment(CIPSegment):
    #   Segment   Extended      Port
    #    Type    Link Addr   Identifier
    # [7, 6, 5]     [4]     [3, 2, 1, 0]
    segment_type = 0b_000_0_0000
    extended_link = 0b_000_1_0000

    port_segments = {
        'backplane': 0b_000_0_0001,
        'bp': 0b_000_0_0001,
        'enet': 0b_000_0_0010,
        'dhrio-a': 0b_000_0_0010,
        'dhrio-b': 0b_000_0_0011,
        'dnet': 0b_000_0_0010,
        'cnet': 0b_000_0_0010,
        'dh485-a': 0b_000_0_0010,
        'dh485-b': 0b_000_0_0011,
    }

    def __init__(self, port: Union[int, str], link_address: Union[int, str, bytes], name: str = ''):
        super().__init__(name)
        self.port = port
        self.link_address = link_address

    @classmethod
    def _encode(cls, segment: 'PortSegment', padded: bool = False) -> bytes:
        if isinstance(segment.port, str):
            port = cls.port_segments[segment.port]
        else:
            port = segment.port
        if isinstance(segment.link_address, str):
            if segment.link_address.isnumeric():
                link = USINT.encode(int(segment.link_address))
            else:
                ipaddress.ip_address(segment.link_address)
                link = segment.link_address.encode()
        elif isinstance(segment.link_address, int):
            link = USINT.encode(segment.link_address)
        else:
            link = segment.link_address

        if len(link) > 1:
            port |= cls.extended_link
            _len = USINT.encode(len(link))
        else:
            _len = b''

        _segment = USINT.encode(port) + _len + link
        if len(_segment) % 2:
            _segment += b'\x00'

        return _segment


class LogicalSegment(CIPSegment):
    segment_type = 0b_001_00000

    #  Segment      Logical    Logical
    #   Type          Type     Format
    # [7, 6, 5]    [4, 3, 2]   [1, 0]
    logical_types = {
        'class_id': 0b_000_000_00,
        'instance_id': 0b_000_001_00,
        'member_id': 0b_000_010_00,
        'connection_point': 0b_000_011_00,
        'attribute_id': 0b_000_100_00,
        'special': 0b_000_101_00,
        'service_id': 0b_000_110_00
    }

    logical_format = {
        1: 0b_000_000_00,  # 8-bit
        2: 0b_000_000_01,  # 16-bit
        4: 0b_000_000_11,  # 32-bit
    }
    # 32-bit only valid for Instance ID and Connection Point types

    def __init__(self, logical_value: Union[int, bytes], logical_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logical_value = logical_value
        self.logical_type = logical_type

    @classmethod
    def _encode(cls, segment: 'LogicalSegment', padded: bool = False) -> bytes:
        _type = cls.logical_types.get(segment.logical_type)
        _value = segment.logical_value
        if _type is None:
            raise DataError('Invalid logical type')

        if isinstance(_value, int):
            if _value <= 0xff:
                _value = USINT.encode(_value)
            elif _value <= 0xffff:
                _value = UINT.encode(_value)
            elif _value <= 0xffff_ffff:
                _value = UDINT.encode(_value)
            else:
                raise DataError(f'Invalid segment value: {segment!r}')

        _fmt = cls.logical_format.get(len(_value))

        if _fmt is None:
            raise DataError(f'Segment value not valid for segment type')

        _segment = bytes([cls.segment_type | _type | _fmt])
        if padded and (len(_segment) + len(_value)) % 2:
            _segment += b'\x00'

        return _segment + _value


class NetworkSegment(CIPSegment):
    segment_type = 0b_010_00000


class SymbolicSegment(CIPSegment):
    segment_type = 0b_011_00000


class DataSegment(CIPSegment):
    segment_type = 0b_100_00000


class ConstructedDataTypeSegment(CIPSegment):
    segment_type = 0b_101_00000


class ElementaryDataTypeSegment(CIPSegment):
    segment_type = 0b_110_00000
