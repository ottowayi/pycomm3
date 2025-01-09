import socket
from dataclasses import dataclass
from typing import Final

from .services import EIPRequest, EIPResponse
from ..connection import Connection
from pycomm3.exceptions import CommError, DataError
from ... import BYTES
from ..base import Response, Parser
from .data_types import EtherNetIPHeader


ETHERNETIP_PORT: Final[int] = 44818


@dataclass
class EIPConfig:
    host: str
    port: str = ETHERNETIP_PORT
    timeout: float = 5.0
    sender_context: BYTES[8] = BYTES[8](b"\x00" * 8)


class EIPConnection(Connection):
    def __init__(self, config: EIPConfig):
        self.config = config
        self._sock: socket.socket | None = None

    def connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.config.timeout)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._sock.connect((self.config.host, self.config.port))
        except Exception as err:
            raise CommError(f"Failed to connect to {self.config.host}:{self.config.port}") from err

    def send(self, request: EIPRequest) -> EIPResponse | None:
        self._send(request.message)

        if request.has_response:
            return self._recv(request)

    def _send(self, msg: bytes):
        while (total_sent := 0) < len(msg):
            try:
                sent = self._sock.send(msg[total_sent:])
                if sent == 0:
                    raise CommError("Failed to send any data")
                total_sent += sent
            except socket.error as err:
                raise CommError(f"Failed to send {len(msg)} bytes, sent {total_sent}") from err
        return total_sent

    def _recv(self, request: EIPRequest) -> EIPResponse:
        _header = self._recv_size(EtherNetIPHeader.size)
        try:
            header = EtherNetIPHeader.decode(_header)
        except DataError as err:
            raise DataError("Failed to decode EtherNet/IP response header") from err

        data = self._recv_size(header.length)

    def _recv_size(self, size: int) -> bytes:
        chunks = []
        recvd = 0
        try:
            while recvd < size:
                chunk = self._sock.recv(size - recvd)
                chunks.append(chunk)
                recvd += len(chunk)

            return b"".join(chunks)
        except socket.error as err:
            raise CommError(f"Failed to read {size} bytes from connection, got {recvd}") from err
