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
        ...

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        ...

    def __repr__(self) -> str:
        return self.__class__.__name__


class ElementaryDataType(DataType):
    code: int = 0x00
    size: int = 0
    _format: str = ''

    @classmethod
    def encode(cls, value: Any) -> bytes:
        try:
            return pack(cls._format, value)
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
        try:
            stream = _as_stream(buffer)
            data = stream.read(cls.size)
            if not data:
                raise BufferEmptyError()
            return unpack(cls._format, data)[0]
        except Exception as err:
            if isinstance(Exception, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


class BOOL(ElementaryDataType):
    code = 0xc1
    size = 1

    @classmethod
    def encode(cls, value: Any) -> bytes:
        return b'\xFF' if value else b'\x00'

    @classmethod
    def decode(cls, buffer: bytes) -> bool:
        stream = _as_stream(buffer)
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


class STIME(ElementaryDataType):
    code = 0xcc
    size = 4
    _format = '<i'


class DATE(UINT):
    code = 0xcd


class TIME_OF_DAY(UDINT):
    code = 0xce


class DATE_AND_TIME(ElementaryDataType):
    code = 0xcf
    size = 8

    @classmethod
    def encode(cls, time: int, date: int) -> bytes:
        try:
            return UDINT.encode(time) + UINT.encode(date)
        except Exception as err:
            raise DataError(f'Error packing {time!r} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: bytes, offset: int = 0) -> Tuple[int, int]:
        try:
            stream = _as_stream(buffer)
            return UDINT.decode(stream), UINT.decode(stream)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


class StringDataType(ElementaryDataType):
    len_type = None
    encoding = 'iso-8859-1'

    @classmethod
    def encode(cls, value: str) -> bytes:
        try:
            return cls.len_type.encode(len(value)) + value.encode(cls.encoding)
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> str:
        try:
            stream = _as_stream(buffer)
            str_len = cls.len_type.decode(stream)
            str_data = stream.read(str_len)
            if not str_data:
                raise BufferEmptyError()

            return str_data.decode(cls.encoding)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


class LOGIX_STRING(StringDataType):
    len_type = UDINT


class STRING(StringDataType):
    code = 0xd0
    len_type = UINT


class BytesDataType(ElementaryDataType):

    @classmethod
    def encode(cls, value: bytes) -> bytes:
        try:
            return value[:cls.size]
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> bytes:
        try:
            stream = _as_stream(buffer)
            data = stream.read(cls.size)
            if not data:
                raise BufferEmptyError()
            return data
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


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
    def decode(cls, buffer: _BufferType) -> Any:
        stream = _as_stream(buffer)
        char_size = UINT.decode(stream)
        char_count = UINT.decode(stream)

        try:
            encoding = cls.ENCODINGS[char_size]
        except KeyError as err:
            raise DataError(f'Unsupported character size: {char_size}') from err
        else:
            try:
                data = stream.read(char_count * char_size)
                if not data:
                    raise BufferEmptyError()

                return data.decode(encoding)
            except Exception as err:
                if isinstance(err, BufferEmptyError):
                    raise
                else:
                    raise DataError(f'Error unpacking {_repr(buffer)} as {cls.__name__}') from err


class SHORT_STRING(StringDataType):
    code = 0xda
    len_type = USINT


class TIME(DINT):
    code = 0xdb


class EPATH(ElementaryDataType):
    code = 0xdc


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
    struct = ()

    @classmethod
    def encode(cls, value: Any) -> bytes:
        ...

    @classmethod
    def decode(cls, buffer: _BufferType) -> Any:
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
        def encode(cls, values: Dict[str, Any]) -> bytes:
            try:
                for typ in cls.members:
                    return b''.join(typ.encode(values[typ.name]))
            except Exception as err:
                raise DataError(f'Error packing {reprlib.repr(values)} into {cls.__name__}]') from err

        @classmethod
        def decode(cls, buffer: _BufferType) -> Dict[str, Any]:
            try:
                stream = _as_stream(buffer)
                values = {
                    typ.name: typ.decode(stream)
                    for typ in cls.members
                }
                values.pop('', None)
                values.pop(None, None)
                return values
            except Exception as err:
                if isinstance(err, BufferEmptyError):
                    raise
                else:
                    raise DataError(f'Error unpacking into {cls.__name__} from {_repr(buffer)}') from err

    return Struct(name)


class IP_ADDR(DerivedDataType):

    @classmethod
    def encode(cls, value: str) -> bytes:
        try:
            return ipaddress.IPv4Address(value).packed
        except Exception as err:
            raise DataError(f'Error packing {value!r} into {cls.__name__}') from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> str:
        try:
            stream = _as_stream(buffer)
            data = stream.read(4)
            if not data:
                raise BufferEmptyError()
            return ipaddress.IPv4Address(data).exploded
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f'Error unpacking into {cls.__name__} from {_repr(buffer)} ') from err
