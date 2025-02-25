from typing import ClassVar

from pycomm3.data_types import UINT, BYTES, UDINT

from .data_types import (
    RegisterSessionData,
    SendRRDataData,
    SendUnitDataData,
    EncapsulationCommand,
    ListInterfacesData,
    ListIdentityData,
    ListServicesData,
)
from ._base import EtherNetIPHeader, EIPService, EIPRequest


class NOPService(EIPService[None, BYTES]):
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
    list_identity: EIPService[None, ListIdentityData] = EIPService(
        command=EncapsulationCommand.list_identity, response_type=ListIdentityData
    )
    list_interfaces: EIPService[None, ListInterfacesData] = EIPService(
        command=EncapsulationCommand.list_interfaces, response_type=ListInterfacesData
    )
    register_session: EIPService[RegisterSessionData, BYTES] = EIPService(
        command=EncapsulationCommand.register_session,
        data=RegisterSessionData(),
        response_type=BYTES,  # has response, but session handle is in the header with no response data
    )
    unregister_session: EIPService[None, ListInterfacesData] = EIPService(
        command=EncapsulationCommand.unregister_session
    )
    list_services: EIPService[None, ListServicesData] = EIPService(
        command=EncapsulationCommand.list_services, response_type=ListServicesData
    )
    send_rr_data: EIPService[SendRRDataData, SendRRDataData] = EIPService(
        command=EncapsulationCommand.send_rr_data, response_type=SendRRDataData
    )
    send_unit_data: EIPService[SendUnitDataData, SendUnitDataData] = EIPService(
        command=EncapsulationCommand.send_unit_data, response_type=SendUnitDataData
    )
