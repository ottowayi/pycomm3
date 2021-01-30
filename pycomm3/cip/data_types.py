import reprlib
from struct import pack, unpack
from typing import Any, Sequence, Optional, Tuple

from ..exceptions import DataError


class DataType:

    def __init__(self, name: Optional[str] = None):
        self.name = name

    @classmethod
    def pack(cls, value: Any) -> bytes:
        ...

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> Any:
        ...


class ElementaryDataType(DataType):
    code: int = 0x00
    size: int = 0
    _format: str = ''

    @classmethod
    def pack(cls, value: Any) -> bytes:
        try:
            return pack(cls._format, value)
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> Any:
        try:
            return unpack(cls._format, buffer[offset: offset + cls.size])[0]
        except Exception as err:
            raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err


class STRUCT(DataType):
    size: Sequence[int] = []
    _format: Sequence[str] = []


class BOOL(ElementaryDataType):
    code = 0xc1
    size = 1

    @classmethod
    def pack(cls, value: Any) -> bytes:
        return b'\xFF' if value else b'\x00'

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> bool:
        return bool(buffer[offset])


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
    def pack(cls, time: int, date: int) -> bytes:
        try:
            return UDINT.pack(time) + UINT.pack(date)
        except Exception as err:
            raise DataError(f'Error packing {time!r} as {cls.__name__}') from err

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> Tuple[int, int]:
        try:
            return UDINT.unpack(buffer, offset), UINT.unpack(buffer, offset=offset+UDINT.size)
        except Exception as err:
            raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err


class StringDataType(ElementaryDataType):
    len_type = None
    encoding = 'iso-8859-1'

    @classmethod
    def pack(cls, value: str) -> bytes:
        try:
            return cls.len_type.pack(len(value)) + value.encode(cls.encoding)
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> str:
        try:
            str_len = cls.len_type.unpack(buffer, offset)
            _offset = cls.len_type.size + offset
            return buffer[_offset: _offset + str_len].decode(cls.encoding)
        except Exception as err:
            raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err


class STRING(StringDataType):
    code = 0xd0
    len_type = UINT


class BytesDataType(ElementaryDataType):

    @classmethod
    def pack(cls, value: bytes) -> bytes:
        try:
            return value[:cls.size]
        except Exception as err:
            raise DataError(f'Error packing {value!r} as {cls.__name__}') from err

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> bytes:
        try:
            return buffer[offset: offset + cls.size]
        except Exception as err:
            raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err


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
    def pack(cls, value: str, char_size: int = 1) -> bytes:
        ...

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> Any:
        char_size = UINT.unpack(buffer, offset)
        char_count = UINT.unpack(buffer, offset + UINT.size)
        _offset = offset + UINT.size * 2
        try:
            encoding = cls.ENCODINGS[char_size]
        except KeyError as err:
            raise DataError(f'Unsupported character size: {char_size}') from err
        else:
            try:
                return buffer[_offset: _offset + char_count * char_size].decode(encoding)
            except Exception as err:
                raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err


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
    def pack(cls, *strings: Sequence[Tuple[str, StringDataType, str, int]]) -> bytes:
        try:
            count = len(strings)
            data = USINT.pack(count)

            for (string, str_type, lang, char_set) in strings:
                _str_type = bytes([str_type.code])
                _lang = bytes(lang, 'ascii')
                _char_set = UINT.pack(char_set)
                _string = str_type.pack(string)

                data += _lang + _str_type + _char_set + _string

            return data
        except Exception as err:
            raise DataError(f'Error packing {reprlib.repr(strings)} as {cls.__name__}') from err

    @classmethod
    def unpack(cls, buffer: bytes, offset: int = 0) -> Tuple[Sequence[str], Sequence[str], Sequence[int], int]:
        try:
            count = USINT.unpack(buffer, offset)
            _offset = offset + USINT.size

            strings = []
            langs = []
            char_sets = []
            for _ in range(count):
                lang = SHORT_STRING.unpack(b'\x03' + buffer[_offset: _offset + 3])
                _offset += 3
                langs.append(lang)

                _str_type = cls.STRING_TYPES[buffer[_offset]]
                _offset += 1

                char_set = UINT.unpack(buffer, _offset)
                _offset += UINT.size
                char_sets.append(char_set)

                string = _str_type.unpack(buffer, _offset)
                _offset += len(string) + _str_type.len_type.size
                strings.append(string)

            return strings, langs, char_sets, _offset
        except Exception as err:
            raise DataError(f'Error unpacking {reprlib.repr(buffer)} as {cls.__name__}') from err