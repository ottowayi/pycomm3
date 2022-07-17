from __future__ import annotations

import reprlib
from dataclasses import dataclass
from enum import IntEnum, Enum
from io import BytesIO
from typing import Sequence, cast

from ..exceptions import BufferEmptyError, DataError
from ._base import (
    StringDataType,
    _as_stream,
    _BufferType,
    _repr,
    StructType,
    DataType,
    DerivedDataType,
    _ArrayableElementaryDataTypeMeta,
    ElementaryDataType,
)
from .numeric import UDINT, UINT, USINT

__all__ = (
    'LOGIX_STRING',
    'STRING',
    'STRING2',
    'STRINGN',
    'STRINGI',
    'SHORT_STRING',
    'StringDataType',
)


class LOGIX_STRING(StringDataType):  # noqa
    """
    Character string, 1-byte per character, 4-byte length
    """

    len_type = UDINT


class STRING(StringDataType):
    """
    Character string, 1-byte per character, 2-byte length
    """

    code = 0xD0  #: 0xD0
    len_type = UINT


class STRING2(StringDataType):
    """
    character string, 2-bytes per character
    """

    code = 0xD5  #: 0xD5
    len_type = UINT
    encoding = "utf-16-le"


class STRINGN(StringDataType):  # noqa
    """
    character string, n-bytes per character
    """

    code = 0xD9  #: 0xD9

    class Encoding(IntEnum):
        """
        Supported encodings and their char sizes.
        """

        utf_8 = 1
        utf_16 = 2
        utf_32 = 4

    _encodings: dict[Encoding, str] = {
        Encoding.utf_8: "utf-8",
        Encoding.utf_16: "utf-16-le",
        Encoding.utf_32: "utf-32-le",
    }

    encoding: Encoding = Encoding.utf_8

    def __new__(cls, value: str, encoding: Encoding = Encoding.utf_8, *args, **kwargs) -> STRINGN:
        try:
            # skipping the __new__ behavior for StringDataType/ElementaryDataType
            # so that encoding can be an instance var and still be passed thru to the encode
            # method without needing to make this a non-str subclass
            obj = super(ElementaryDataType, cls).__new__(cls, value, *args, **kwargs)
            obj.encoding = encoding
        except Exception as err:
            raise DataError(f'invalid value for {cls}: {value!r}') from err
        obj.__encoded_value__ = cls.encode(value, encoding, *args, **kwargs)
        return obj

    @classmethod
    def encode(cls, value: str, encoding: Encoding = Encoding.utf_8, *args, **kwargs) -> bytes:
        try:
            encoding_name = cls._encodings[encoding]
            return UINT.encode(encoding) + UINT.encode(len(value)) + value.encode(encoding_name)
        except Exception as err:
            raise DataError(f"Error encoding {value!r} as STRINGN using {encoding}") from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> STRINGN:
        char_size = UINT.decode(stream)
        char_count = UINT.decode(stream)

        try:
            encoding = cls.Encoding(char_size)
            encoding_name = cls._encodings[encoding]
        except KeyError as err:
            raise DataError(f"Unsupported character size: {char_size}") from err
        else:
            data = cls._stream_read(stream, char_count * char_size)

            return STRINGN(data.decode(encoding_name), encoding=encoding)


class SHORT_STRING(StringDataType):  # noqa
    """
    character string, 1-byte per character, 1-byte length
    """

    code = 0xDA  #: 0xDA
    len_type = USINT


class STRINGI(DerivedDataType):
    """
    international character string
    """

    code = 0xDE  #: 0xDE
    istr: type[cast(dataclass, 'istr')]
    STRING_TYPES: dict[int, type[STRING | STRING2 | STRINGN | SHORT_STRING]] = {
        STRING.code: STRING,
        STRING2.code: STRING2,
        STRINGN.code: STRINGN,
        SHORT_STRING.code: SHORT_STRING,
    }

    class Language(str, Enum):
        english = "eng"
        french = "fra"
        spanish = "spa"
        italian = "ita"
        german = "deu"
        japanese = "jpn"
        portuguese = "por"
        chinese = "zho"
        russian = "rus"

    class CharSet(IntEnum):
        iso_8859_1 = 4
        iso_8859_2 = 5
        iso_8859_3 = 6
        iso_8859_4 = 7
        iso_8859_5 = 8
        iso_8859_6 = 9
        iso_8859_7 = 10
        iso_8859_8 = 11
        iso_8859_9 = 12
        utf_16_le = 1000
        utf_32_le = 1001

    _encodings: dict[CharSet, str] = {
        CharSet.iso_8859_1: 'iso-8859-1',
        CharSet.iso_8859_2: 'iso-8859-2',
        CharSet.iso_8859_3: 'iso-8859-3',
        CharSet.iso_8859_4: 'iso-8859-4',
        CharSet.iso_8859_5: 'iso-8859-5',
        CharSet.iso_8859_6: 'iso-8859-6',
        CharSet.iso_8859_7: 'iso-8859-7',
        CharSet.iso_8859_8: 'iso-8859-8',
        CharSet.iso_8859_9: 'iso-8859-9',
        CharSet.utf_16_le: 'utf-16-le',
        CharSet.utf_32_le: 'utf-32-le',
    }

    def __init__(self, *strings: StrI):
        self._strs: tuple[StrI] = strings
        self._by_lang: dict[STRINGI.Language : StrI] = {s.lang: s for s in strings}
        self.__encoded_value__ = self.encode(self)

    def get(self, lang: STRINGI.Language | None = None) -> str:
        if lang is None:
            return self._strs[0].value
        if lang not in self._by_lang:
            raise ValueError(f'invalid language: {lang}')

        return self._by_lang[lang].value

    @classmethod
    def _encode(cls, value: STRINGI, **kwargs) -> bytes:
        """
        Encodes ``strings`` to bytes
        """
        try:
            count = len(value._strs)
            data = USINT.encode(count)

            for stri in value._strs:
                _str_type = USINT(stri.str_type.code)
                _lang = bytes(stri.lang, "ascii")
                _char_set = UINT(stri.char_set)
                _string = bytes(stri.str_type.len_type(len(stri.value))) + stri.value.encode(
                    cls._encodings[cls.CharSet(_char_set)]
                )

                data += b''.join(bytes(x) for x in (_lang, _str_type, _char_set, _string))

            return data
        except Exception as err:
            raise DataError(f"Error packing {reprlib.repr(value._strs)} as {cls.__name__}") from err

    @classmethod
    def decode(cls, buffer: _BufferType) -> STRINGI:
        stream = _as_stream(buffer)
        strings = []
        try:
            count = USINT.decode(stream)
            for _ in range(count):
                lang = SHORT_STRING.decode(b"\x03" + stream.read(3))
                _str_type = cls.STRING_TYPES[USINT.decode(stream)]
                char_set = UINT.decode(stream)
                string = _str_type.decode(stream)
                strings.append(
                    StrI(
                        value=string,
                        str_type=_str_type,
                        lang=STRINGI.Language(lang),
                        char_set=STRINGI.CharSet(char_set),
                    )
                )

            return STRINGI(*strings)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f"Error unpacking {_repr(buffer)} as {cls.__name__}") from err

    @staticmethod
    def istr(
        value: str,
        str_type: type[STRING | STRING2 | STRINGN | SHORT_STRING],
        lang: STRINGI.Language = Language.english,
        char_set: STRINGI.CharSet = CharSet.utf_16_le,
    ):
        return StrI(value, str_type, lang, char_set)


@dataclass
class StrI:
    value: str
    str_type: type[STRING | STRING2 | STRINGN | SHORT_STRING]
    lang: STRINGI.Language = STRINGI.Language.english
    char_set: STRINGI.CharSet = STRINGI.CharSet.utf_16_le
