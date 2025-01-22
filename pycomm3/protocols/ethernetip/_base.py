from dataclasses import dataclass, field

from pycomm3.data_types import BYTES, UDINT, UINT, DataclassMeta, DataType

from .data_types import DEFAULT_CONTEXT, ETHERNETIP_STATUS_CODES, EtherNetIPHeader, EtherNetIPStatus


@dataclass
class EIPRequest[T: DataType]:
    # the request header
    header: EtherNetIPHeader
    # service data, encoded
    data: bytes
    # full encoded request
    message: bytes = field(init=False, repr=False)
    # DataType to decode response data or None if no response
    response_type: type[T] | None = None

    def __post_init__(self):
        self.message = bytes(self.header) + self.data

    def __str__(self):
        return f"EIPRequest(header={self.header!s}, data={self.data!r})"


class EIPService[T: DataType](metaclass=DataclassMeta):
    command: UINT
    data: bytes | DataType = b""
    # DataType to decode response data or None if no response
    response_type: type[T] | None = None

    def __call__(
        self,
        session: UDINT,
        *args,
        data: bytes | DataType = b"",
        context: BYTES[8] = DEFAULT_CONTEXT,
        **kwargs,
    ) -> EIPRequest[T]:
        #
        _data = data or self.data
        payload = bytes(_data) if isinstance(_data, DataType) else _data
        header = EtherNetIPHeader(command=self.command, length=UINT(len(payload)), session=session, context=context)
        return EIPRequest(header=header, data=payload, response_type=self.response_type)


@dataclass
class EIPResponse[T: DataType]:
    request: EIPRequest[T] = field(repr=False)
    header: EtherNetIPHeader
    data: T | None
    status_msg: str = field(init=False)

    def __post_init__(self):
        self.status_msg = ETHERNETIP_STATUS_CODES.get(
            self.header.status, f"Unknown status code: {self.header.status:#06x}"
        )

    def __bool__(self) -> bool:
        return self.header is not None and self.header.status == EtherNetIPStatus.Success

    def __str__(self):
        return f"EIPResponse(header={self.header!s}, data={self.data!r}, request={self.request!s})"
