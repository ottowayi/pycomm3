from __future__ import annotations
from io import BytesIO
from typing import Sequence, Tuple

from ..exceptions import DataError
from ._base import ElementaryDataType
from .numeric import DINT, UDINT, UINT, INT, LINT


__all__ = (
    'STIME',
    'DATE',
    'TIME_OF_DAY',
    'DATE_AND_TIME',
    'FTIME',
    'LTIME',
    'ITIME',
    'TIME',
)


class STIME(DINT):
    """
    Synchronous time information
    """

    code = 0xCC  #: 0xCC


class DATE(UINT):
    """
    Date information
    """

    code = 0xCD  #: 0xCD


class TIME_OF_DAY(UDINT):
    """
    Time of day
    """

    code = 0xCE  #: 0xCE


class DATE_AND_TIME(ElementaryDataType[Tuple[int, int]]):
    """
    Date and time of day
    """

    code = 0xCF  #: 0xCF
    size = 8

    @classmethod
    def encode(cls, time_date: tuple[int, int], *args, **kwargs) -> bytes:
        try:
            return UDINT.encode(time_date[0]) + UINT.encode(time_date[1])
        except Exception as err:
            raise DataError(f"Error packing {time_date!r} as {cls.__name__}") from err

    @classmethod
    def _decode(cls, stream: BytesIO) -> tuple[int, int]:
        return UDINT.decode(stream), UINT.decode(stream)


class FTIME(DINT):
    """
    duration - high resolution
    """

    code = 0xD6  #: 0xD6


class LTIME(LINT):
    """
    duration - long
    """

    code = 0xD7  #: 0xD7


class ITIME(INT):
    """
    duration - short
    """

    code = 0xD8  #: 0xD8


class TIME(DINT):
    """
    duration - milliseconds
    """

    code = 0xDB  #: 0xDB

