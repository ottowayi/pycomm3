from pycomm3 import UDINT, DataType, DataclassMeta
from pycomm3.data_types import UINT, BYTES
from dataclasses import dataclass, InitVar, field
from enum import Enum
from typing import Protocol
from io import BytesIO

from pycomm3.protocols.ethernetip.data_types import EtherNetIPHeader, DEFAULT_CONTEXT
from ..base import Request


class EncapsulationCommand(UINT, Enum):
    nop = UINT(0)
    list_targets = UINT(1)
    list_services = UINT(4)
    list_identity = UINT(0x63)
    list_interfaces = UINT(0x64)
    register_session = UINT(0x65)
    unregister_session = UINT(0x66)
    send_rr_data = UINT(0x6F)
    send_unit_data = UINT(0x70)


@dataclass
class EIPRequest:
    header: EtherNetIPHeader
    data: bytes
    message: bytes = field(init=False)
    has_response: bool = True

    def __post_init__(self):
        self.message = bytes(self.header) + self.data


class EIPService(metaclass=DataclassMeta):
    command: EncapsulationCommand
    has_response: bool = True

    def __call__(
        self, session: UDINT, data: bytes | DataType, context: BYTES[8] = DEFAULT_CONTEXT, *args, **kwargs
    ) -> EIPRequest:
        payload = bytes(data) if isinstance(data, DataType) else data
        header = EtherNetIPHeader(command=self.command, length=UINT(len(payload)), session=session)
        return EIPRequest(header=header, data=payload)


class NOPService(EIPService):
    command: EncapsulationCommand = EncapsulationCommand.nop
    has_response: bool = False

    # defining this request statically, no need to regenerate it every time
    _request: EIPRequest = EIPRequest(
        header=EtherNetIPHeader(
            command=EncapsulationCommand.nop,
            length=UINT(0),
            session=UDINT(0),
        ),
        data=b"",
        has_response=False,
    )

    def __call__(self, *args, **kwargs) -> EIPRequest:
        return self._request


class EtherNetIPStatus(UDINT, Enum):
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
class EIPResponse:
    request: EIPRequest
    header: EtherNetIPHeader
    data: bytes | DataType
    status_msg: str = field(init=False)

    def __post_init__(self):
        self.status_msg = ETHERNETIP_STATUS_CODES.get(self.header.status, f"Unknown status code: {self.header.status}")

    def __bool__(self) -> bool:
        return self.header is not None and self.header.status == EtherNetIPStatus.Success


class EIPResponseParser:
    def parse(self, data: bytes | BytesIO, header: EtherNetIPHeader, request: EIPRequest) -> EIPResponse:
        match header.command:
            case EncapsulationCommand.nop:
                payload = b""
            case EncapsulationCommand.list_targets:
                ...

        return EIPResponse(request=request, header=header, data=payload)
