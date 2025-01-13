from typing import Final
from unittest import case

from pycomm3.data_types import UINT, BYTES, UDINT, DataType, DataclassMeta, StructType
from dataclasses import dataclass, field
from io import BytesIO

from .data_types import DEFAULT_CONTEXT, ListIdentityData, RegisterSessionData


class EtherNetIPHeader(StructType):
    command: UINT
    length: UINT
    session: UDINT
    status: UDINT = UDINT(0)
    context: BYTES[8] = DEFAULT_CONTEXT
    options: UDINT = UDINT(0)

    def __str__(self) -> str:
        command = f"{self.command:#0x}: '{ENCAP_COMMAND_NAMES.get(self.command, 'UNKNOWN')}'"
        status = f"{self.status:#04x}: '{ETHERNETIP_STATUS_CODES.get(self.status, 'UNKNOWN')}'"
        session = self.session
        return f"{self.__class__.__name__}({command=!s}, {status=!s}, {session=})"


class EncapsulationCommand:
    nop = UINT(0)
    list_targets = UINT(0x01)
    list_services = UINT(0x04)
    list_identity = UINT(0x63)
    list_interfaces = UINT(0x64)
    register_session = UINT(0x65)
    unregister_session = UINT(0x66)
    send_rr_data = UINT(0x6F)
    send_unit_data = UINT(0x70)


ENCAP_COMMAND_NAMES: Final[dict[UINT, str]] = {
    v: k.replace("_", " ").title() for k, v in vars(EncapsulationCommand).items() if isinstance(v, UINT)
}


@dataclass
class EIPRequest:
    header: EtherNetIPHeader
    data: bytes
    message: bytes = field(init=False, repr=False)
    has_response: bool = True

    def __post_init__(self):
        self.message = bytes(self.header) + self.data

    def __str__(self):
        return f"EIPRequest(header={self.header!s}, data={self.data!r})"


class EIPService(metaclass=DataclassMeta):
    command: UINT
    has_response: bool = True

    def __call__(
        self,
        session: UDINT,
        data: bytes | DataType,
        *args,
        context: BYTES[8] = DEFAULT_CONTEXT,
        **kwargs,
    ) -> EIPRequest:
        payload = bytes(data) if isinstance(data, DataType) else data
        header = EtherNetIPHeader(command=self.command, length=UINT(len(payload)), session=session, context=context)
        return EIPRequest(header=header, data=payload)


class EtherNetIPStatus:
    Success = UDINT(0x0000)
    InvalidOrUnsupportedEncapCommand = UDINT(0x0001)
    InsufficientReceiverMemory = UDINT(0x0002)
    BadData = UDINT(0x0003)
    InvalidSessionHandle = UDINT(0x0064)
    InvalidMessageLength = UDINT(0x0065)
    UnsupportedEncapProtocolRevision = UDINT(0x0069)  # nice


ETHERNETIP_STATUS_CODES: dict[UDINT, str] = {
    EtherNetIPStatus.Success: "Success",
    EtherNetIPStatus.InvalidOrUnsupportedEncapCommand: "Invalid or unsupported encapsulation command",
    EtherNetIPStatus.InsufficientReceiverMemory: "Insufficient memory to handle command",
    EtherNetIPStatus.BadData: "Poorly formed or incorrect command data",
    EtherNetIPStatus.InvalidSessionHandle: "Invalid session handle",
    EtherNetIPStatus.InvalidMessageLength: "Invalid message length",
    EtherNetIPStatus.UnsupportedEncapProtocolRevision: "Unsupported encapsulation protocol revision",
}


@dataclass
class EIPResponse[T: DataType]:
    request: EIPRequest = field(repr=False)
    header: EtherNetIPHeader
    data: bytes | T
    status_msg: str = field(init=False)

    def __post_init__(self):
        self.status_msg = ETHERNETIP_STATUS_CODES.get(self.header.status, f"Unknown status code: {self.header.status}")

    def __bool__(self) -> bool:
        return self.header is not None and self.header.status == EtherNetIPStatus.Success

    def __str__(self):
        return f"EIPResponse(header={self.header!s}, data={self.data!r}, request={self.request!s})"


class EIPResponseParser:
    def parse(self, data: bytes | BytesIO, header: EtherNetIPHeader, request: EIPRequest) -> EIPResponse:
        match header.command:
            case EncapsulationCommand.nop:
                payload = b""
            case EncapsulationCommand.list_targets:
                ...
            case EncapsulationCommand.list_services:
                ...
            case EncapsulationCommand.list_identity:
                payload = ListIdentityData.decode(data)
            case EncapsulationCommand.register_session:
                payload = RegisterSessionData.decode(data)

        return EIPResponse(request=request, header=header, data=payload)
