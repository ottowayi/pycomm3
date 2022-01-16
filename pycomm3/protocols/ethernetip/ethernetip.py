from abc import abstractmethod
from enum import IntEnum
from io import BytesIO
from typing import Type, Dict, Any, Sequence, Union, Optional
from pycomm3.data_types import DataType, Struct, USINT, UINT, UDINT, n_bytes, BYTES
from pycomm3.custom_types import ListIdentityObject
# from protocols.base import Request, Response
from .data_types import (
    EtherNetIPStatus,
    EtherNetIPHeader,
    EncapsulationCommands,
    ETHERNETIP_STATUS_CODES,
    CommonPacketFormat,
    ConnectedAddressItem,
    UnconnectedDataItem,
    UCMMAddressItem,
    CommonPacketFormatItem,
)
from ..cip.cip import CIPRequest

from ..base import Request, Response


class EtherNetIPResponse(Response):

    def __init__(self, data: bytes, request: Request):
        self.header = None
        self.value = None

        super().__init__(data, request)

    def is_valid(self) -> bool:
        return self.header['status'] == EtherNetIPStatus.Success

    def _parse_reply(self):
        self.header = self._parse_header()
        self.value = self._parse_command_specific_data()

    def _parse_header(self):
        return EtherNetIPHeader.decode(self._data)

    @abstractmethod
    def _parse_command_specific_data(self):
        ...

    @property
    def error(self) -> Optional[str]:
        status = self.header['status']
        if status != EtherNetIPStatus.Success:
            return ETHERNETIP_STATUS_CODES.get(status, f'UNKNOWN STATUS ({status:04#x})')


class EtherNetIPRequest(Request):
    command: bytes
    has_response: bool = True
    response_class: Type[EtherNetIPResponse]

    def __init__(self, session: int, context: bytes, option: int):
        self.session: int = session
        self.context: bytes = context
        self.option: int = option

        # encoded common packet format
        self._command_data: bytes = b''
        # encoded header
        self._header: bytes = b''

        super().__init__()

    def _build_message(self) -> bytes:
        self._command_data = self._build_command_data()
        self._header = self._build_header()

        return self._header + self._command_data

    def _build_header(self) -> bytes:
        return EtherNetIPHeader.encode(
            {
                'command': self.command,
                'length': len(self._command_data),
                'session': self.session,
                'status': 0,
                'context': self.context,
                'option': self.option
            }
        )

    @abstractmethod
    def _build_command_data(self) -> bytes:
        ...


class NOPRequest(EtherNetIPRequest):
    command = EncapsulationCommands.nop
    has_response = False

    def _build_command_data(self) -> bytes:
        return b''


class ListIdentityResponse(EtherNetIPResponse):

    def _parse_command_specific_data(self):
        count = UINT.decode(self._data)
        identities = [ListIdentityObject.decode(self._data) for _ in range(count)]
        if len(identities) == 1:
            return identities[0]
        return identities


class ListIdentityRequest(EtherNetIPRequest):
    response_class = ListIdentityResponse
    command = 0x0063

    def _build_command_data(self) -> bytes:
        return b''


class RegisterSessionResponse(EtherNetIPResponse):

    def _parse_command_specific_data(self):
        return {
            'protocol_version': UINT.decode(self._data),
            'options_flags': UINT.decode(self._data),
        }


class RegisterSessionRequest(EtherNetIPRequest):
    response_class = RegisterSessionResponse
    command = 0x0065

    def _build_command_data(self) -> bytes:
        # protocol version always 1, options always 0
        return b'\x01\x00\x00\x00'


class UnRegisterSessionRequest(EtherNetIPRequest):
    response_class = EtherNetIPResponse
    has_response = False
    command = 0x0066

    def _build_command_data(self) -> bytes:
        return b''


# TODO: ListServices service


class SendRRDataResponse(EtherNetIPResponse):

    def _parse_command_specific_data(self):
        item_count = UINT.decode(self._data)
        address_item = CommonPacketFormatItem.decode(self._data)
        data_item = CommonPacketFormatItem.decode(self._data)
        return data_item['data']


class SendRRDataRequest(EtherNetIPRequest):
    response_class = SendRRDataResponse
    command = 0x006F

    def __init__(self, session: int, context: bytes, option: int, cip_request: CIPRequest):
        self.cip_request = cip_request
        super().__init__(session, context, option)

    def _build_command_data(self) -> bytes:
        # encap the cip request using the common packet format, Vol 2. 2-6
        return b''.join((
            b'\x02\x00',  # item count always 2
            UCMMAddressItem.encode(None),  # no value to encode, None for placeholder
            UnconnectedDataItem.encode(self.cip_request.message)
        ))


class SendUnitDataResponse(EtherNetIPResponse):

    def _parse_command_specific_data(self):
        ...


class SendUnitDataRequest(EtherNetIPRequest):
    response_class = SendRRDataResponse
    command = 0x0070

    def __init__(
        self,
        session: int,
        context: bytes,
        option: int,
        cip_request: CIPRequest,
        connection_id: int,
    ):
        self.cip_request = cip_request
        self.connection_id = connection_id

        super().__init__(session, context, option)