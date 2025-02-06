from dataclasses import dataclass

from ..ethernetip import EIPConnection
from pycomm3.data_types import EPATH
from pycomm3 import get_logger


@dataclass
class CIPConfig:
    cip_path: EPATH | None = None


class CIPConnection:
    __log = get_logger(__qualname__)

    def __init__(self, config: CIPConfig, transport: EIPConnection):
        self.config = config
        self._transport: EIPConnection = transport
        self._connected: bool = False

    def send(self, CIPRequest): ...
