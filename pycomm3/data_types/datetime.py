from __future__ import annotations
from typing import ClassVar

from ._base import StructType
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


class DATE_AND_TIME(StructType):
    """
    Date and time of day
    """

    code: ClassVar[int] = 0xCF  #: 0xCF

    time: UDINT
    date: UINT


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

