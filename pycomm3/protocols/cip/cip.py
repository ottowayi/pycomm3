from typing import Union, Sequence
from ..base import Request, Response
from ...data_types import LogicalSegment, PADDED_EPATH, DataType


def request_path(
    class_code: Union[int, bytes],
    instance: Union[int, bytes],
    attribute: Union[int, bytes] = b"",
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


class CIPRequest(Request):
    """
    Base class for all CIP requests, may be used directly for generic CIP requests or
    subclassed to create custom request types.
    """

    def __init__(
        self,
        service: Union[int, bytes],
        class_code: Union[int, bytes],
        instance: Union[int, bytes],
        attribute: Union[int, bytes, None] = None,
        request_data: bytes = b'',
        response_type: Union[DataType, None] = None

    ):
        self.service: Union[int, bytes] = service
        self.class_code: Union[int, bytes] = class_code
        self.instance: Union[int, bytes] = instance
        self.attribute: Union[int, bytes] = attribute
        self.request_data: bytes = request_data
        self.response_type: Union[DataType, None] = response_type

        super().__init__()

    def _build_message(self) -> bytes:
        return b''.join([self.service, request_path(self.class_code, self.instance, self.attribute), self.request_data])


class CIPResponse(Response):
    ...