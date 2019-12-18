from autologging import logged


@logged
class Packet:
    ...


from .responses import (ResponsePacket, SendUnitDataResponsePacket, SendRRDataResponsePacket, ListIdentityResponsePacket,
                        RegisterSessionResponsePacket, UnRegisterSessionResponsePacket, ReadTagServiceResponsePacket)

from .requests import (RequestPacket, SendUnitDataRequestPacket, SendRRDataRequestPacket, ListIdentityRequestPacket,
                       RegisterSessionRequestPacket, UnRegisterSessionRequestPacket, ReadTagServiceRequestPacket)

from collections import defaultdict



REQUEST_MAP = defaultdict(RequestPacket,
{
    'send_unit_data': SendUnitDataRequestPacket,
    'send_rr_data': SendRRDataRequestPacket,
    'register_session': RegisterSessionRequestPacket,
    'unregister_session': UnRegisterSessionRequestPacket,
    'list_identity': ListIdentityRequestPacket,
    'read_tag': ReadTagServiceRequestPacket
})
