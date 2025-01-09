from __future__ import annotations
from io import BytesIO
from typing import Union, Optional, TypeVar, Generic, TYPE_CHECKING, ClassVar, Protocol

from .. import DataType
from ..exceptions import RequestError, ResponseError
from ..util import DataclassMeta
from dataclasses import field, dataclass

RequestType = TypeVar("RequestType", bound="Request")
ResponseType = TypeVar("ResponseType", bound="Response")


class Response(metaclass=DataclassMeta):
    #: The request that this response is for
    request: RequestType | None
    #: Error message for failures, else None
    error: str | None

    def __bool__(self) -> bool:
        return self.error is None

    # @classmethod
    # def decode(cls: type[ResponseType], data: bytes | BytesIO, request: RequestType | None = None, *args, **kwargs) -> ResponseType:
    #     """
    #     Parses the encoded response (``data``) and returns a new ``Response`` object
    #     """
    #     try:
    #         if isinstance(data, bytes):
    #             buff, raw = BytesIO(data), data
    #         else:
    #             buff, raw = data, data.getvalue()
    #
    #         resp: ResponseType = cls._decode(buff, request, *args, **kwargs)
    #         resp.raw_data = raw
    #         resp.request = request
    #
    #         return resp
    #     except Exception as err:
    #         raise ResponseError('Error parsing response') from err
    #
    # @classmethod
    # def _decode(cls: type[ResponseType], buff: BytesIO, request: RequestType | None = None, *args, **kwargs) -> ResponseType:
    #     raise NotImplementedError('Response subclasses must implement _decode')


# class ErrResponse(Response):
#     error: str
#     raw_data: bytes | None = None
#
#     def __bool__(self) -> bool:
#         return False


class Request(Generic[RequestType, ResponseType], metaclass=DataclassMeta):
    response_parser: Parser[ResponseType] | None
    message: bytes
    has_response: bool


ReqT_co = TypeVar("ReqT_co", bound=Request, covariant=True)
RspT_co = TypeVar("RspT_co", bound=Response, covariant=True)


class Service(Protocol[ReqT_co]):
    def __call__(self, *args, **kwargs) -> ReqT_co: ...


class Parser(Protocol[RspT_co]):
    payload_parser: Optional[Parser]

    def __init__(self, payload_parser: Optional[Parser], *args, **kwargs) -> None: ...

    def parse(self, data: bytes | BytesIO, request: ReqT_co, *args, **kwargs) -> RspT_co: ...
