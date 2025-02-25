from dataclasses import dataclass, field

from pycomm3.exceptions import ResponseError

from ..ethernetip import EIPConnection
from pycomm3 import get_logger
from ._base import CIPRequest, CIPRoute
from .object_library.connection_manager import ConnectionManager, TickTime
from .cip_object import CIPObject


@dataclass
class UnconnectedConfig:
    tick_time: TickTime = TickTime.ms_1024
    num_ticks: int = 1
    # priority: bool = False  # always False in spec, so don't expose?


@dataclass
class CIPConfig:
    cip_path: CIPRoute | None = None
    unconnected_config: UnconnectedConfig = field(default_factory=UnconnectedConfig)


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
        return self.connected and False  # TODO: actual logic here

    def get_attributes_all(self, cip_object: type[CIPObject], instance: int = 1):
        request = cip_object.get_attributes_all(instance=instance)
        resp = self.send(request)
        return resp.data

    def send(self, msg: CIPRequest):
        if self.cip_connected:
            return self._connected_send(msg)
        else:
            return self._unconnected_send(msg)

    def _unconnected_send(
        self,
        msg: CIPRequest,
        config: UnconnectedConfig | None = None,
        cip_path: CIPRoute | None = None,
    ):
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
        self.__log.debug(request)
        enip_resp = self._transport.send_rr_data(msg=bytes(request.message))
        self.__log.verbose(enip_resp)
        if enip_resp:
            resp = request.response_parser.parse(enip_resp.data.packet.data.data, request)
            # if _path:  # used unconnected_send, need to strip that
            #     resp = msg.response_parser.parse(resp.data, msg)
            return resp
        else:
            raise ResponseError("ethernet/ip response error", enip_resp)

    def _connected_send(self, msg: CIPRequest): ...
