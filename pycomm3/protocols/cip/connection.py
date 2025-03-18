from dataclasses import dataclass, field
from typing import Final, Literal, cast
from pycomm3.data_types.binary import WORD
from pycomm3.data_types.cip import LogicalSegment, LogicalSegmentType
from pycomm3.exceptions import ResponseError

from ..ethernetip import EIPConnection
from pycomm3 import get_logger
from ._base import CIPRequest, CIPResponse, CIPRoute
from .object_library.connection_manager import (
    ConnectionManager,
    ConnectionPriority,
    ConnectionTimeoutMultiplier,
    ConnectionType,
    ForwardOpenRequest,
    ForwardOpenResponse,
    LargeForwardOpenRequest,
    TickTime,
    ProductionTrigger,
)
from .object_library.message_router import MessageRouter
from .cip_object import CIPObject
from os import urandom
from pycomm3.data_types import UDINT, UINT, USINT, DWORD

STANDARD_CONNECTION_SIZE: Final[int] = 511
LARGE_CONNECTION_SIZE: Final[int] = 4000
PYCOMM3_VENDOR_ID: Final[int] = 0xA455


@dataclass
class UnconnectedConfig:
    tick_time: TickTime = TickTime.ms_1024
    num_ticks: int = 1
    # priority: bool = False  # always False in spec, so don't expose?


@dataclass
class ConnectedConfig:
    type: ConnectionType = ConnectionType.point_to_point
    priority: ConnectionPriority = ConnectionPriority.high
    sizing: Literal["fixed", "variable"] = "variable"
    size: int = STANDARD_CONNECTION_SIZE
    redundant_owner: bool = False
    o2t_connection_id: int = 0
    t2o_connection_id: int = 0  # if 0, then generate random one
    connection_serial: int = 0  # if 0, then generate random one
    vendor_id: int = PYCOMM3_VENDOR_ID
    originator_serial: int = 0  # if 0, then generate random one
    timeout_multiplier: ConnectionTimeoutMultiplier = ConnectionTimeoutMultiplier.x512
    o2t_rpi: int = 2113537  # idk, these are just what I had?
    t2o_rpi: int = 2113537
    direction: Literal["client", "server"] = "server"
    production_trigger: ProductionTrigger = ProductionTrigger.application_object
    transport_class: Literal[0, 1, 2, 3] = 3


@dataclass
class CIPConfig:
    cip_path: CIPRoute | None = None
    unconnected_config: UnconnectedConfig = field(default_factory=UnconnectedConfig)
    connected_config: ConnectedConfig = field(default_factory=ConnectedConfig)


class CIPConnection:
    __log = get_logger(__qualname__)

    def __init__(self, config: CIPConfig, transport: EIPConnection):
        self.config = config
        self._transport: EIPConnection = transport
        self._connected: bool = False

    @property
    def connected(self) -> bool:
        return self._transport.connected

    @property
    def cip_connected(self) -> bool:
        return self.connected and self.config.connected_config.o2t_connection_id != 0

    def get_attributes_all(self, cip_object: type[CIPObject], instance: int = 1):
        request = cip_object.get_attributes_all(instance=instance)
        resp = self.send(request)
        return resp.data

    def forward_open(self):
        self.__log.info("beginning forward open...")
        request = self._build_forward_open_request()
        if enip_resp := self._transport.send_rr_data(bytes(request.message)):
            if resp := request.response_parser.parse(enip_resp.data.packet.data.data, request):
                resp_data = cast(ForwardOpenResponse, resp.data)  # type: ignore
                self.config.connected_config.o2t_connection_id = resp_data.o2t_connection_id
                self.__log.info('... forward open succeeded, o->t connection id: %d', self.config.connected_config.o2t_connection_id)  # fmt: skip
            else:
                self.__log.info("...forward open failed: %s", resp)
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    def _build_forward_open_request(self) -> CIPRequest:
        self.__log.debug("building forward_open request")
        cfg = self.config.connected_config
        t2o_connection_id = UDINT(cfg.t2o_connection_id) or UDINT.decode(urandom(4))
        connection_serial = UINT(cfg.connection_serial) or UINT.decode(urandom(2))
        originator_serial = UDINT(cfg.originator_serial) or UDINT.decode(urandom(4))
        transport_class_trigger = cfg.production_trigger | cfg.transport_class
        if cfg.direction == "server":
            transport_class_trigger |= 1 << 7
        params = cfg.type | cfg.priority
        if cfg.redundant_owner:
            params |= 1 << 15
        if cfg.sizing == "variable":
            params |= 1 << 9
        connection_path = (self.config.cip_path or CIPRoute()).epath(padded=True, length=True) / (
            LogicalSegment(type=LogicalSegmentType.type_class_id, value=MessageRouter.class_code),
            LogicalSegment(type=LogicalSegmentType.type_instance_id, value=0x01),
        )
        if cfg.size > STANDARD_CONNECTION_SIZE:
            params <<= 16
            net_params = DWORD(params | cfg.size)
            request_cls = LargeForwardOpenRequest
            service = ConnectionManager.large_forward_open
        else:
            request_cls = ForwardOpenRequest
            service = ConnectionManager.forward_open
            net_params = WORD(params | cfg.size)

        request_data = request_cls(  # type: ignore
            priority_tick_time=USINT(self.config.unconnected_config.tick_time),
            timeout_ticks=USINT(self.config.unconnected_config.num_ticks),
            o2t_connection_id=UDINT(0),
            t2o_connection_id=t2o_connection_id,
            connection_serial=connection_serial,
            originator_vendor_id=UINT(cfg.vendor_id),
            originator_serial=originator_serial,
            timeout_multiplier=USINT(cfg.timeout_multiplier),
            o2t_rpi=UDINT(cfg.o2t_rpi),
            o2t_connection_params=net_params,  # type: ignore
            t2o_rpi=UDINT(cfg.t2o_rpi),
            t2o_connection_params=net_params,  # type: ignore
            transport_type=USINT(transport_class_trigger),
            connection_path=connection_path,
        )
        self.__log.debug("forward_open request data: %s", request_data)
        request = service(
            data=request_data,  # type: ignore
            instance=ConnectionManager.Instance.open_request,
        )
        self.__log.debug("built forward_open request: %s", request)
        return request

    def send(self, msg: CIPRequest) -> CIPResponse:
        if self.cip_connected:
            return self._connected_send(msg)
        else:
            return self._unconnected_send(msg)

    def _unconnected_send(
        self,
        msg: CIPRequest,
        config: UnconnectedConfig | None = None,
        cip_path: CIPRoute | None = None,
    ) -> CIPResponse:
        _path = cip_path if cip_path is not None else p if (p := self.config.cip_path) is not None else CIPRoute()
        if _path:
            request = ConnectionManager.unconnected_send(
                msg=msg,
                route_path=_path,
                tick_time=(config.tick_time if config is not None else self.config.unconnected_config.tick_time),
                num_ticks=(config.num_ticks if config is not None else self.config.unconnected_config.num_ticks),
            )
        else:
            request = msg
        self.__log.debug("sending unconnected_send request: %s", request)
        if enip_resp := self._transport.send_rr_data(msg=bytes(request.message)):
            self.__log.debug("parsing unconnected_send response: %s", enip_resp.data.packet.data.data)
            resp = request.response_parser.parse(enip_resp.data.packet.data.data, request)
            self.__log.debug("parsed unconnected_send response: %s", resp)
            return resp
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    def _connected_send(self, msg: CIPRequest) -> CIPResponse: ...
