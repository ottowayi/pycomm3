from dataclasses import dataclass, field
from functools import wraps
from os import urandom
from typing import Final, Literal, Sequence, cast, Generator

from pycomm3 import get_logger
from pycomm3.data_types import UDINT, UINT, USINT, DWORD, DataType, WORD
from pycomm3.data_types.cip import LogicalSegment, LogicalSegmentType
from pycomm3.exceptions import ResponseError
from pycomm3.util import cycle
from .cip_object import CIPAttribute, CIPObject, GetAttrsAll
from .cip_route import CIPRoute
from .object_library.connection_manager import (
    ConnectionManager,
    ConnectionPriority,
    ConnectionTimeoutMultiplier,
    ConnectionType,
    ForwardCloseRequest,
    ForwardOpenFailedResponse,
    ForwardOpenRequest,
    ForwardOpenResponse,
    LargeForwardOpenRequest,
    TickTime,
    ProductionTrigger,
)
from .object_library.message_router import MessageRouter
from .protocol_base import CIPRequest, CIPResponse
from ..connection import is_connected
from ..ethernetip import EIPConnection

STANDARD_CONNECTION_SIZE: Final[int] = 511
LARGE_CONNECTION_SIZE: Final[int] = 4000
PYCOMM3_VENDOR_ID: Final[UINT] = UINT(0xA455)


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
    o2t_connection_id: UDINT = UDINT(0)
    t2o_connection_id: UDINT = UDINT(0)  # if 0, then generate random one
    connection_serial: UINT = UINT(0)  # if 0, then generate random one
    vendor_id: UINT = PYCOMM3_VENDOR_ID
    originator_serial: UDINT = UDINT(0)  # if 0, then generate random one
    timeout_multiplier: ConnectionTimeoutMultiplier = ConnectionTimeoutMultiplier.x512
    o2t_rpi: int = 2113537  # idk, these are just what I had?
    t2o_rpi: int = 2113537
    direction: Literal["client", "server"] = "server"
    production_trigger: ProductionTrigger = ProductionTrigger.application_object
    transport_class: Literal[0, 1, 2, 3] = 3


@dataclass
class CIPConfig:
    route: CIPRoute = field(default_factory=CIPRoute)
    unconnected_config: UnconnectedConfig = field(default_factory=UnconnectedConfig)
    connected_config: ConnectedConfig = field(default_factory=ConnectedConfig)


def is_cip_connected(func):
    @wraps(func)
    def wrapped(self: "CIPConnection", *args, **kwargs):
        if not self.cip_connected:
            raise ConnectionError("not cip connected")
        return func(self, *args, **kwargs)

    return is_connected(wrapped)


class CIPConnection:
    __log = get_logger(__qualname__)

    def __init__(self, config: CIPConfig, transport: EIPConnection):
        self.config = config
        self._transport: EIPConnection = transport
        self._sequence_generator: Generator[int, None, None] = cycle(65535, start=1)

    @property
    def connected(self) -> bool:
        """
        Returns `True` if the connection has been established (the EtherNet/IP connection is registered), `False` otherwise.
        """
        return self._transport.connected

    @property
    def cip_connected(self) -> bool:
        """
        Returns `True` if the connection has an active Explicit Messaging connection
        (a forward open established a connection with the Message Router of the target),
        `False` otherwise.
        """
        return self.connected and self.config.connected_config.o2t_connection_id != 0

    def get_attributes_all[TIns: GetAttrsAll, TCls: GetAttrsAll](
        self, cip_object: type[CIPObject[TIns, TCls]], instance: int | None = 1, cip_connected: bool | None = None
    ):
        request = cip_object.get_attributes_all(instance=instance)
        resp = self.send(request, cip_connected=cip_connected)
        return resp

    def _get_attributes_all_individually(
        self,
        cip_object: type[CIPObject],
    ): ...

    def get_attribute_single[T: DataType](
        self, attribute: CIPAttribute[T], instance: int = 1, cip_connected: bool | None = None
    ):
        request = attribute.object.get_attribute_single(attribute=attribute, instance=instance)
        resp = self.send(request, cip_connected=cip_connected)
        return resp

    def get_attribute_list(
        self, attributes: Sequence[CIPAttribute], instance: int = 1, cip_connected: bool | None = None
    ):
        if len({a.object for a in attributes}) != 1:
            raise ValueError("attributes must all be from the same object")

        request = attributes[0].object.get_attribute_list(attributes=attributes, instance=instance)
        resp = self.send(request, cip_connected=cip_connected)
        return resp

    def connect(self):
        if self.connected:
            raise ConnectionError("already connected")
        self._transport.connect()

    def disconnect(self):
        if not self.connected:
            raise ConnectionError("not connected")
        self._transport.disconnect()

    @is_connected
    def forward_open(self):
        if self.cip_connected:
            raise ConnectionError("already cip connected")
        self.__log.info("beginning forward open...")
        request = self._build_forward_open_request()
        if enip_resp := self._transport.send_rr_data(bytes(request.message)):
            if resp := request.response_parser.parse(enip_resp.data.packet.data.data, request):
                resp_data = cast(ForwardOpenResponse, resp.data)
                self.config.connected_config.o2t_connection_id = resp_data.o2t_connection_id
                self.config.connected_config.t2o_connection_id = resp_data.t2o_connection_id
                self.config.connected_config.connection_serial = resp_data.connection_serial
                self.config.connected_config.originator_serial = resp_data.originator_serial
                self._sequence_generator = cycle(65535, start=1)
                self.__log.info("...forward open succeeded, o->t connection id: %d", resp_data.o2t_connection_id)
            else:
                self.__log.debug("forward open response: %s", resp)
                self.__log.error("...forward open failed: %s", resp.status_message or "Unknown Error")
                raise ConnectionError("forward open failed")
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    def _build_forward_open_request(self) -> CIPRequest[ForwardOpenResponse | ForwardOpenFailedResponse]:
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
        connection_path = (self.config.route or CIPRoute()).epath(padded=True, length=True) / (
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
        request = service(params=request_data)  # type: ignore
        self.__log.debug("built forward_open request: %s", request)
        return request

    def send[T: DataType](self, msg: CIPRequest[T], cip_connected: bool | None = None):
        """
        Sends a CIPRequest, by default will send an unconnected message if the connection is not
        *CIP Connected* else will send a connected message (`cip_connected=None`).
        Else, set `cip_connected=True` to force send connected message and `False` for an unconnected one.
        """
        if (cip_connected is None and self.cip_connected) or cip_connected:
            return self._connected_send(msg)
        else:
            return self.unconnected_send(msg)

    @is_connected
    def unconnected_send[T: DataType](
        self,
        msg: CIPRequest[T],
        config: UnconnectedConfig | None = None,
        cip_path: CIPRoute | None = None,
    ):
        _path = cip_path if cip_path is not None else p if (p := self.config.route) is not None else CIPRoute()
        request = ConnectionManager.unconnected_send(
            msg=msg,
            route_path=_path,
            tick_time=(config.tick_time if config is not None else self.config.unconnected_config.tick_time),
            num_ticks=(config.num_ticks if config is not None else self.config.unconnected_config.num_ticks),
        )

        self.__log.debug("sending unconnected_send request: %s", request)
        if enip_resp := self._transport.send_rr_data(msg=bytes(request.message)):
            self.__log.debug("parsing unconnected_send response: %s", enip_resp.data.packet.data.data)
            resp = request.response_parser.parse(enip_resp.data.packet.data.data, request)
            self.__log.debug("parsed unconnected_send response: %s", resp)
            return resp
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    @is_cip_connected
    def _connected_send[T: DataType](self, request: CIPRequest[T]) -> CIPResponse[T]:
        self.__log.debug("sending connected request: %s", request)
        encoded_msg = bytes(request.message)
        if has_seq_id := (0 < self.config.connected_config.transport_class <= 3):
            sequence_number = UINT(next(self._sequence_generator))
            encoded_msg = bytes(sequence_number) + encoded_msg
        if enip_resp := self._transport.send_unit_data(
            msg=encoded_msg, connection_id=self.config.connected_config.o2t_connection_id
        ):
            self.__log.debug("parsing connected response: %s", enip_resp.data.packet.data.data)
            resp_data = enip_resp.data.packet.data.data
            if has_seq_id:
                resp_seq_id = UINT.decode(resp_data)
                self.__log.verbose("response sequence number: %d", resp_seq_id)
                resp_data = resp_data[UINT.size :]
            resp = request.response_parser.parse(resp_data, request)
            self.__log.debug("parsed connected response: %s", resp)
            return resp
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    @is_cip_connected
    def forward_close(self):
        connection_path = (self.config.route or CIPRoute()).epath(padded=True, length=True, padded_len=True) / (
            LogicalSegment(type=LogicalSegmentType.type_class_id, value=MessageRouter.class_code),
            LogicalSegment(type=LogicalSegmentType.type_instance_id, value=0x01),
        )

        request = ConnectionManager.forward_close(
            params=ForwardCloseRequest(
                priority_tick_time=USINT(self.config.unconnected_config.tick_time),
                timeout_ticks=USINT(self.config.unconnected_config.num_ticks),
                connection_serial=self.config.connected_config.connection_serial,
                originator_vendor_id=self.config.connected_config.vendor_id,
                originator_serial=self.config.connected_config.originator_serial,
                connection_path=connection_path,
            ),
        )

        if enip_resp := self._transport.send_rr_data(bytes(request.message)):
            if resp := request.response_parser.parse(enip_resp.data.packet.data.data, request):
                self.config.connected_config.o2t_connection_id = UDINT(0)
                self.config.connected_config.t2o_connection_id = UDINT(0)
                self.config.connected_config.connection_serial = UINT(0)
                self.config.connected_config.originator_serial = UDINT(0)
                self.__log.info("...forward close succeeded")
            else:
                self.__log.debug("forward close response: %s", resp)
                self.__log.error("...forward close failed: %s", resp.status_message or "Unknown Error")
                raise ConnectionError("forward close failed")
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)
