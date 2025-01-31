from __future__ import annotations

from dataclasses import dataclass, field
from typing import overload, TYPE_CHECKING, Callable
from io import BytesIO
from typing import TypeVar, no_type_check, Self

from ...data_types import (
    BYTES,
    PADDED_EPATH,
    USINT,
    WORD,
    DataType,
    LogicalSegment,
    StructType,
    attr,
    PADDED_EPATH_LEN,
    array,
)
from ..base import Request, Response
from ...exceptions import ResponseError


def request_path(
    class_code: int | bytes,
    instance: int | bytes,
    attribute: int | bytes = b"",
) -> bytes:
    """
    Encodes a PADDED_EPATH of the class code, instance, and (optionally) attribute
    """
    segments = [
        LogicalSegment(class_code, "class_id"),
        LogicalSegment(instance, "instance_id"),
    ]

    if attribute:
        segments.append(LogicalSegment(attribute, "attribute_id"))

    return PADDED_EPATH.encode(segments, length=True)


CIPRequestT = TypeVar("CIPRequestT", bound="CIPRequest")
CIPResponseT = TypeVar("CIPResponseT", bound="CIPResponse")

DataTypeT = TypeVar("DataTypeT", bound=DataType)


class CIPResponseHeader(StructType):
    service: USINT
    _reserved: BYTES[1] = attr(reserved=True)
    general_status: USINT
    extended_status: WORD[USINT]


class CIPResponse(Response[CIPResponseT, CIPRequestT]):
    """
    Base class for all CIP response, implements the standard message router response format.
    May be subclassed for customer CIP responses.
    """

    header: CIPResponseHeader = field(init=False)
    data: bytes = field(init=False)

    @staticmethod
    def _decode_header(buff: BytesIO) -> CIPResponseHeader:
        try:
            return CIPResponseHeader.decode(buff)
        except Exception as err:
            raise ResponseError("Error decoding header") from err

    @staticmethod
    def _decode_data(buff: BytesIO, data_type: type[DataType]) -> DataType:
        try:
            return data_type.decode(buff)
        except Exception as err:
            raise ResponseError("Error decoding header") from err

    @classmethod
    def _decode(
        cls: type[CIPResponseT],
        buff: BytesIO,
        request: CIPRequestT | None = None,
        data_type: type[DataType] = array(BYTES, ...),
        *args,
        **kwargs,
    ) -> CIPResponseT:
        header = cls._decode_header(buff)
        data = cls._decode_data(buff, header)
        return cls(header, data)


class CIPRequest(Request[CIPRequestT, CIPResponseT]):
    """
    Base class for all CIP requests, may be used directly for generic CIP requests (message router request format)
    or subclassed to create custom request types.
    """

    response_class = CIPResponse

    def __init__(
        self,
        service: int | bytes,
        class_code: int | bytes,
        instance: int | bytes,
        attribute: int | bytes | None = None,
        request_data: bytes = b"",
        response_types: dict[int, DataType | None] = None,  # {status_code: type}
    ):
        self.service: int | bytes = service
        self.class_code: int | bytes = class_code
        self.instance: int | bytes = instance
        self.attribute: int | bytes = attribute
        self.request_data: bytes = request_data
        self.response_types: dict[int, DataType] = response_types or {}
        super().__init__()

    def _build_message(self) -> bytes:
        return b"".join(
            [
                self.service,
                request_path(self.class_code, self.instance, self.attribute),
                self.request_data,
            ]
        )
