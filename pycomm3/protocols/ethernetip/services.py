from typing import ClassVar

from pycomm3.data_types import UINT, BYTES, UDINT, DataType, DataclassMeta, attr, StructType
from dataclasses import dataclass, field
from io import BytesIO

from .data_types import DEFAULT_CONTEXT, RegisterSessionData, SendRRDataData, SendUnitDataData
from ._base import EtherNetIPHeader, EIPService, EncapsulationCommand, EIPRequest


class NOPService(EIPService):
    command: UINT = EncapsulationCommand.nop
    has_response: bool = False

    # defining this request statically, no need to regenerate it every time
    _request: ClassVar[EIPRequest] = EIPRequest(
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


class StaticEIPService(EIPService):
    data: bytes = b""

    def __call__(self, session: UDINT, *args, context: BYTES[8] = DEFAULT_CONTEXT, **kwargs) -> EIPRequest:
        header = EtherNetIPHeader(
            command=self.command,
            length=UINT(len(self.data)),
            session=session,
        )

        return EIPRequest(header=header, data=self.data, has_response=self.has_response)


class SimpleEIPService[T: DataType](EIPService):
    def __call__(
        self, session: UDINT, data: T | bytes, *args, context: BYTES[8] = DEFAULT_CONTEXT, **kwargs
    ) -> EIPRequest:
        if isinstance(data, DataType):
            data = bytes(data)
        header = EtherNetIPHeader(command=self.command, length=UINT(len(data)), session=session, context=context)
        return EIPRequest(header=header, data=data, has_response=self.has_response)


class Services:
    nop: NOPService = NOPService()
    list_identity: StaticEIPService = StaticEIPService(command=EncapsulationCommand.list_identity)
    list_interfaces: StaticEIPService = StaticEIPService(command=EncapsulationCommand.list_interfaces)
    register_session = StaticEIPService(
        command=EncapsulationCommand.register_session,
        data=bytes(RegisterSessionData()),
    )
    unregister_session: StaticEIPService = StaticEIPService(
        command=EncapsulationCommand.unregister_session,
        has_response=False,
    )
    list_services: StaticEIPService = StaticEIPService(command=EncapsulationCommand.list_services)
    send_rr_data: SimpleEIPService[SendRRDataData] = SimpleEIPService(command=EncapsulationCommand.send_rr_data)
    send_unit_data: SimpleEIPService[SendUnitDataData] = SimpleEIPService(command=EncapsulationCommand.send_unit_data)
