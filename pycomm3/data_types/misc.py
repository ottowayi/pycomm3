from __future__ import annotations

from ..map import EnumMap
from ._base import ElementaryDataType
from .binary import BOOL, BYTE, DWORD, LWORD, WORD, ENGUNIT
from .cip import PACKED_EPATH, PADDED_EPATH
from .datetime import DATE, DATE_AND_TIME, FTIME, ITIME, LTIME, STIME, TIME, TIME_OF_DAY
from .numeric import DINT, INT, LINT, LREAL, REAL, SINT, UDINT, UINT, ULINT, USINT
from .string import LOGIX_STRING, SHORT_STRING, STRING, STRING2, STRINGI, STRINGN

__all__ = ('DataTypes', )


def _by_type_code(typ: ElementaryDataType) -> int:
    return typ.code


class DataTypes(EnumMap):
    """
    Lookup table/map of elementary data types.  Reverse lookup is by CIP code for data type.
    """

    _return_caps_only_ = True
    _value_key_ = _by_type_code

    bool = BOOL
    sint = SINT
    int = INT
    dint = DINT
    lint = LINT

    usint = USINT
    uint = UINT
    udint = UDINT
    ulint = ULINT

    real = REAL
    lreal = LREAL

    stime = STIME
    date = DATE
    time_of_day = TIME_OF_DAY
    date_and_time = DATE_AND_TIME

    logix_string = LOGIX_STRING
    string = STRING

    byte = BYTE
    word = WORD
    dword = DWORD
    lword = LWORD

    string2 = STRING2

    ftime = FTIME
    ltime = LTIME
    itime = ITIME

    stringn = STRINGN
    short_string = SHORT_STRING

    time = TIME

    padded_epath = PADDED_EPATH
    packed_epath = PACKED_EPATH

    engunit = ENGUNIT

    stringi = STRINGI

    @classmethod
    def get_type(cls, type_code) -> type[ElementaryDataType]:
        return cls.get(cls.get(type_code))
