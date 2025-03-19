import socket
from dataclasses import dataclass
from typing import Final, cast

from pycomm3.data_types import BYTES, UDINT, Array
from pycomm3.exceptions import CommError, DataError
from pycomm3 import get_logger

from ..connection import Connection
from ._base import EIPRequest, EIPResponse, EtherNetIPHeader, DEFAULT_CONTEXT
from .services import Services
from .data_types import (
    CIPIdentity,
    CommonPacketFormat,
    InterfaceInfo,
    SendRRDataData,
    ServiceInfo,
    EncapsulationCommand,
    UnconnectedData,
    NullAddress,
    ConnectedData,
    SendUnitDataData,
    ConnectedAddress,
)

ETHERNETIP_PORT: Final[int] = 44818


@dataclass
class EIPConfig:
    host: str
    port: int = ETHERNETIP_PORT
    timeout: float = 5.0
    sender_context: BYTES[8] = DEFAULT_CONTEXT


class EIPConnection(Connection):
    __log = get_logger(__qualname__)

    def __init__(self, config: EIPConfig):
        self.config = config
        self._sock: socket.socket | None = None
        self._connected: bool = False
        self._session_id: UDINT = UDINT(0)

    def connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.config.timeout)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._sock.connect((self.config.host, self.config.port))
            self._connected = True
        except Exception as err:
            self._connected = False
            raise CommError(f"Failed to connect to {self.config.host}:{self.config.port}") from err
        else:
            try:
                self._session_id = UDINT(0)
                self.register_session()
            except Exception as err:
                self._connected = False
                self._session_id = UDINT(0)
                raise CommError(f"Failed to register session with {self.config.host}:{self.config.port}") from err

    @property
    def connected(self) -> bool:
        return self._session_id != 0 and self._connected

    @property
    def session_id(self) -> UDINT:
        return self._session_id

    def disconnect(self):
        self.__log.debug(f"Disconnecting from {self.config.host}:{self.config.port}...")
        if not self._connected:
            self.__log.debug("Not connected, returning")
            return
        try:
            if self._session_id:
                self.unregister_session()
        except Exception as err:
            self._session_id = UDINT(0)
            self.__log.debug(f"Failed to unregister session: {err}")

        try:
            if self._sock is not None:
                self._sock.close()
        except Exception as err:
            raise CommError(f"Failed to disconnect from {self.config.host}:{self.config.port}") from err
        else:
            self.__log.debug("... disconnected")
        finally:
            self._connected = False

    def register_session(self):
        if self.session_id:
            raise ConnectionError("Session already registered")

        request = Services.register_session(self.session_id, context=self.config.sender_context)
        if response := self.send(request):
            self._session_id = response.header.session

    def unregister_session(self):
        if not self.session_id:
            raise ConnectionError("Session not registered")

        request = Services.unregister_session(self.session_id, context=self.config.sender_context)
        self.send(request)
        self._session_id = UDINT(0)

    def list_identity(self) -> CIPIdentity | None:
        request = Services.list_identity(self.session_id, context=self.config.sender_context)
        if response := self.send(request):
            return cast(CIPIdentity, response.data.identities[0])  # type: ignore

    def list_interfaces(self) -> Array[InterfaceInfo, None] | None:
        request = Services.list_interfaces(self.session_id, context=self.config.sender_context)
        if response := self.send(request):
            return cast(Array[InterfaceInfo, None], response.data.interfaces)

    def list_services(self) -> Array[ServiceInfo, None] | None:
        request = Services.list_services(self.session_id, context=self.config.sender_context)
        if response := self.send(request):
            return cast(Array[ServiceInfo, None], response.data.services)  # type: ignore

    def send_unit_data(self, connection_id: UDINT, msg: bytes) -> EIPResponse | None:
        if not self.connected:
            raise ConnectionError("Connection closed")
        cpf = CommonPacketFormat(
            address_item=ConnectedAddress(connection_id=connection_id),
            data_item=ConnectedData(data=BYTES(msg)),
        )
        data = SendUnitDataData(cpf)
        request = Services.send_unit_data(session=self._session_id, data=data, context=self.config.sender_context)
        return self.send(request)

    def send_rr_data(self, msg: bytes) -> EIPResponse | None:
        if not self.connected:
            raise ConnectionError("Connection closed")
        data = SendRRDataData(
            CommonPacketFormat(address_item=NullAddress(), data_item=UnconnectedData(data=BYTES(msg)))
        )

        request = Services.send_rr_data(session=self._session_id, data=data, context=self.config.sender_context)
        return self.send(request)

    def send(self, request: EIPRequest) -> EIPResponse | None:
        if not self._connected:
            raise ConnectionError("Not connected")
        if request.header.command != EncapsulationCommand.register_session and not self.session_id:
            raise ConnectionError("Session not registered")

        self.__log.debug(f"Sending request: {request}")

        self.__log.log_bytes(">> SENT >>", request.message)
        self._send(request.message)

        if request.response_type is not None:
            resp = self._recv(request)
            return resp

    def _send(self, msg: bytes):
        total_sent = 0
        while total_sent < len(msg):
            try:
                sent = self._sock.send(msg[total_sent:])  # type: ignore
                if sent == 0:
                    raise CommError("Failed to send any data")
                total_sent += sent
            except socket.error as err:
                raise CommError(f"Failed to send {len(msg)} bytes, sent {total_sent}") from err
        return total_sent

    def _recv(self, request: EIPRequest) -> EIPResponse:
        _header = self._recv_size(EtherNetIPHeader.size)
        try:
            header: EtherNetIPHeader = EtherNetIPHeader.decode(_header)
            self.__log.verbose(f"Received header: {header}")
        except DataError as err:
            raise DataError("Failed to decode EtherNet/IP response header") from err
        data = self._recv_size(header.length)
        self.__log.log_bytes("<< RECEIVED <<", _header + data)
        resp_data = None if request.response_type is None else request.response_type.decode(data)
        resp = EIPResponse(request=request, header=header, data=resp_data)
        self.__log.debug(f"Received response: {resp}")
        return resp

    def _recv_size(self, size: int) -> bytes:
        chunks = []
        recvd = 0
        try:
            while recvd < size:
                chunk = self._sock.recv(size - recvd)  # type: ignore
                chunks.append(chunk)
                recvd += len(chunk)

            return b"".join(chunks)
        except socket.error as err:
            self.__log.error(f"Socket error: {err}")
            if chunks:
                self.__log.log_bytes("<< RECEIVED (BEFORE ERROR) <<", b"".join(chunks))
            raise CommError(f"Failed to read {size} bytes from connection, got {recvd}") from err

    def __str__(self) -> str:
        return f"EtherNetIPConnection<{self.config.host}:{self.config.port}> - {'DIS' if not self._connected else ''}CONNECTED (session_id={self.session_id})"
