from typing import ClassVar

from pycomm3.data_types import UINT, BYTES, UDINT, DataType, DataclassMeta, attr, StructType
from dataclasses import dataclass, field
from io import BytesIO

from .data_types import (
    DEFAULT_CONTEXT,
    RegisterSessionData,
    SendRRDataData,
    SendUnitDataData,
    EncapsulationCommand,
    ListInterfacesData,
    ListIdentityData,
    ListServicesData,
)
from ._base import EtherNetIPHeader, EIPService, EIPRequest


class NOPService(EIPService):
    command: UINT = EncapsulationCommand.nop

    # defining this request statically, no need to regenerate it every time
    _request: ClassVar[EIPRequest] = EIPRequest(
        header=EtherNetIPHeader(
            command=EncapsulationCommand.nop,
            length=UINT(0),
            session=UDINT(0),
        ),
        data=b"",
        response_type=None,
    )

    def __call__(self, *args, **kwargs) -> EIPRequest:
        return self._request


class Services:
    nop: NOPService = NOPService()
    list_identity = EIPService(command=EncapsulationCommand.list_identity, response_type=ListIdentityData)
    list_interfaces = EIPService(command=EncapsulationCommand.list_interfaces, response_type=ListInterfacesData)
    register_session = EIPService(
        command=EncapsulationCommand.register_session,
        data=bytes(RegisterSessionData()),
        response_type=BYTES,  # has response, but session handle is in the header with no response data
    )
    unregister_session = EIPService(command=EncapsulationCommand.unregister_session)
    list_services = EIPService(command=EncapsulationCommand.list_services, response_type=ListServicesData)
    send_rr_data = EIPService(command=EncapsulationCommand.send_rr_data, response_type=SendRRDataData)
    send_unit_data = EIPService(command=EncapsulationCommand.send_unit_data, response_type=SendUnitDataData)
