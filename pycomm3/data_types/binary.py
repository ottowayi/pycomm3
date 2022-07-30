from __future__ import annotations

from ._base import BytesDataType, BitArrayType, BoolDataType
from .numeric import USINT, UINT, UDINT, ULINT

__all__ = (
    'BOOL',
    'BYTES',
    'BYTE',
    'ENGUNIT',
    'WORD',
    'DWORD',
    'LWORD',
)


class BOOL(BoolDataType):
    """
    A boolean value, decodes ``0x00`` and ``False`` and ``True`` otherwise.
    ``True`` encoded as ``0xFF`` and ``False`` as ``0x00``
    """

    code = 0xC1  #: 0xC1
    size = 1


class BYTES(BytesDataType):
    size = 1


class BYTE(BitArrayType, USINT):
    """
    bit string - 8-bits
    """

    code = 0xD1  #: 0xD1


class WORD(BitArrayType, UINT):
    """
    bit string - 16-bits
    """

    code = 0xD2  #: 0xD2


class DWORD(BitArrayType, UDINT):
    """
    bit string - 32-bits
    """

    code = 0xD3  #: 0xD3


class LWORD(BitArrayType, ULINT):
    """
    bit string - 64-bits
    """

    code = 0xD4  #: 0xD4


class ENGUNIT(WORD):  # noqa
    """
    engineering units
    """

    code = 0xDD  #: 0xDD
    # TODO: create lookup table of defined eng. units
