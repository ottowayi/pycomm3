# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

__all__ = [
    "CIPDriver",
    "with_forward_open",
    "parse_connection_path",
]

import ipaddress
import logging
import socket
from functools import wraps
from os import urandom
from typing import Union, Optional, Tuple, List, Sequence, Type, Any, Dict, TypedDict


from .protocols.cip.object_library import (
    ConnectionManagerInstances,
    ClassCode,
    CIPObject,
CIPAttribute,
    ConnectionManagerObject,
)
from .protocols.cip.cip import CIPRequest, CIPResponse

from .protocols.cip.services import (     ConnectionManagerServices,
    Services)
from .data_types import(
CIPSegment, PortSegment, PADDED_EPATH,    DataType,
    UDINT,
    UINT,
    USINT,
)

from .const import (
    PRIORITY,
    TIMEOUT_MULTIPLIER,
    TIMEOUT_TICKS,
    TRANSPORT_CLASS,
    MSG_ROUTER_PATH,
    STANDARD_CONNECTION_SIZE,
    LARGE_CONNECTION_SIZE,
)
from .custom_types import ModuleIdentityObject
from .exceptions import ResponseError, CommError, RequestError
from .packets import (
    RequestPacket,
    ResponsePacket,
    PacketLazyFormatter,
    ListIdentityRequestPacket,
    RegisterSessionRequestPacket,
    UnRegisterSessionRequestPacket,
    GenericConnectedRequestPacket,
    GenericUnconnectedRequestPacket,
)
from .socket_ import Socket
from .tag import Tag
from .util import cycle

from .protocols.ethernetip.ethernetip import (
    ListIdentityRequest,
    EtherNetIPRequest,
    RegisterSessionRequest,
    UnRegisterSessionRequest,
    SendRRDataRequest,
)


def with_forward_open(func):
    """Decorator to ensure a forward open request has been completed with the plc"""

    @wraps(func)
    def wrapped(self: CIPDriver, *args, **kwargs):
        if self._target_is_connected:
            return func(self, *args, **kwargs)

        logger = logging.getLogger("pycomm3.cip_driver")
        opened = False
        if self._cfg["extended_forward_open"]:
            logger.info("Attempting an Extended Forward Open...")
        if not self._forward_open():
            if self._cfg["extended_forward_open"]:
                logger.info("Extended Forward Open failed, attempting standard Forward Open.")
                self._cfg["extended_forward_open"] = False
                self._cfg["connection_size"] = STANDARD_CONNECTION_SIZE
                if self._forward_open():
                    opened = True
        else:
            opened = True

        if not opened:
            msg = f"Target did not connected. {func.__name__} will not be executed."
            raise ResponseError(msg)
        return func(self, *args, **kwargs)

    return wrapped


class ConnectionConfig(TypedDict):
    priority_tick_time: int
    timeout_ticks: int
    o_t_connection_id: int
    t_o_connection_id: int
    connection_serial: int
    vendor_id: int
    originator_serial: int
    timeout_multiplier: int
    reserved: bytes
    o_t_rpi: int  # original pycomm value, RPIs not important for u
    t_o_rpi: int
    transport_type: int


class EtherNetIPConfig(TypedDict):
    session: int
    context: bytes
    option: int


class DriverConfig(TypedDict):
    port: int
    timeout: int
    ip_address: str
    cip_path: List[CIPSegment]
    extended_forward_open: bool
    connection_size: int
    ethernetip_params: EtherNetIPConfig
    connection_params: ConnectionConfig


class CIPDriver:
    """
    A base CIP driver for the SLCDriver and LogixDriver classes.  Implements common CIP services like
    (un)registering sessions, forward open/close, generic messaging, etc.
    """

    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    _auto_slot_cip_path = False

    def __init__(self, path: str, *args, **kwargs):
        """
        :param path: CIP path to intended target

            The path may contain 3 forms:

            - IP Address Only (``10.20.30.100``) - Use for a ControlLogix PLC is in slot 0 or if connecting to a CompactLogix or Micro800 PLC.
            - IP Address/Slot (``10.20.30.100/1``) - (ControlLogix) if PLC is not in slot 0
            - CIP Routing Path (``1.2.3.4/backplane/2/enet/6.7.8.9/backplane/0``) - Use for more complex routing.

            .. note::

                Both the IP Address and IP Address/Slot options are shortcuts, they will be replaced with the
                CIP path automatically.  The ``enet`` / ``backplane`` (or ``bp``) segments are symbols for the CIP routing
                port numbers and will be replaced with the correct value.

        """

        self._sequence: cycle = cycle(65535, start=1)
        self._sock: Optional[Socket] = None
        self._connection_opened: bool = False
        self._target_is_connected: bool = False
        self._info: Dict[str, Any] = {}
        self._cip_path = path
        ip, _path = parse_connection_path(path, self._auto_slot_cip_path)

        self._cfg: DriverConfig = DriverConfig(
            port=44818,
            timeout=10,
            ip_address=ip,
            cip_path=_path,
            extended_forward_open=True,
            connection_size=LARGE_CONNECTION_SIZE,
            ethernetip_params=EtherNetIPConfig(
                session=0,
                context=b"_pycomm_",
                option=0,
            ),
            connection_params=ConnectionConfig(
                priority_tick_time=PRIORITY,
                timeout_ticks=TIMEOUT_TICKS,
                o_t_connection_id=0,
                t_o_connection_id=UDINT.decode(urandom(4)),
                connection_serial=UINT.decode(urandom(2)),
                vendor_id=0x6f69,
                originator_serial=UDINT.decode(urandom(4)),
                timeout_multiplier=TIMEOUT_MULTIPLIER,
                reserved=bytes(3),
                o_t_rpi=2113537,
                t_o_rpi=2113537,
                transport_type=TRANSPORT_CLASS,
            ),
        )

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except CommError:
            self.__log.exception("Error closing connection.")
            return False
        else:
            if not exc_type:
                return True
            self.__log.exception("Unhandled Client Error", exc_info=(exc_type, exc_val, exc_tb))
            return False

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self._cip_path})"

    def __str__(self):
        _rev = self._info.get("revision", {"major": -1, "minor": -1})
        return f"Device: {self._info.get('product_type', 'None')}, Revision: {_rev['major']}.{_rev['minor']}"

    @property
    def connected(self) -> bool:
        """
        Read-Only Property to check whether or not a connection is open.

        :return: True if a connection is open, False otherwise
        """
        return self._connection_opened

    @property
    def connection_size(self):
        """CIP connection size, ``4000`` if using Extended Forward Open else ``500``"""
        return self._cfg["connection_size"]

    @classmethod
    def list_identity(cls, path) -> Optional[str]:
        """
        Uses the ListIdentity service to identify the target

        :return: device identity if reply contains valid response else None
        """
        plc = cls(path)
        plc.open()
        identity = plc._list_identity()
        plc.close()
        return identity

    @classmethod
    def discover(cls) -> List[Dict[str, Any]]:
        """
        Discovers available devices on the current network(s).
        Returns a list of the discovered devices Identity Object (as ``dict``).
        """
        cls.__log.info("Discovering devices...")
        ip_addrs = [
            sockaddr[0]
            for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None)
            if family == socket.AddressFamily.AF_INET
        ]

        driver = CIPDriver("0.0.0.0")  # dummy driver for creating the list_identity request
        request = ListIdentityRequestPacket()
        message = request.build_request(None, driver._cfg['ethernetip_params']['session'], b"\x00" * 8, 0)
        devices = []

        for ip in ip_addrs:
            cls.__log.debug(f"Broadcasting discover for IP: %s", ip)
            devices += cls._broadcast_discover(ip, message, request)

        if not devices:
            cls.__log.debug(
                "No devices found so far, attempting broadcast without binding to an IP."
            )
            devices += cls._broadcast_discover(None, message, request)

        if devices:
            cls.__log.info(f"Discovered %d device(s): %r", len(devices), devices)
        else:
            cls.__log.info("No Ethernet/IP devices discovered")

        return devices

    @classmethod
    def _broadcast_discover(cls, ip, message, request):
        devices = []
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            if ip:
                sock.bind((ip, 0))

            sock.sendto(message, ("255.255.255.255", 44818))

            while True:
                try:
                    resp = sock.recv(4096)
                    response = request.response_class(request, resp)
                    if response:
                        devices.append(response.identity)
                except Exception:
                    break
        except Exception:
            cls.__log.exception("Error broadcasting discover request")
        finally:
            return devices

    def _list_identity(self):
        request = ListIdentityRequest(*self._enip_args)
        return self._send_eip_request(request).value

        # request = ListIdentityRequestPacket()
        # response = self.send(request)
        # return response.identity

    def get_module_info(self, slot: int) -> dict:
        """
        Get the Identity object for a given slot in the rack of the current connection
        """
        try:
            response = self.generic_message(
                service=Services.get_attributes_all,
                class_code=ClassCode.identity_object,
                instance=b"\x01",
                connected=False,
                unconnected_send=True,
                route_path=PADDED_EPATH.encode(
                    (
                        *self._cfg["cip_path"][:-1],
                        PortSegment("bp", slot),
                    ),
                    length=True,
                    pad_length=True,
                ),
                name="get_module_info",
            )

            if response:
                return ModuleIdentityObject.decode(response.value)
            else:
                raise ResponseError(f"generic_message did not return valid data - {response.error}")

        except Exception as err:
            raise ResponseError("error getting module info") from err

    def open(self):
        """
        Creates a new Ethernet/IP socket connection to target device and registers a CIP session.

        :return: True if successful, False otherwise
        """
        # handle the socket layer
        if self._connection_opened:
            return True
        try:
            if self._sock is None:
                self._sock = Socket()
            self.__log.debug(f'Opening connection to {self._cfg["ip_address"]}')
            self._sock.connect(self._cfg["ip_address"], self._cfg["port"])
            self._connection_opened = True
            self._cfg['connection_params']["t_o_connection_id"] = UDINT.decode(urandom(4))
            self._cfg['connection_params']["originator_serial"] = UDINT.decode(urandom(4))
            if self._register_session() is None:
                self.__log.error("Session not registered")
                return False
            return True
        except Exception as err:
            raise CommError("failed to open a connection") from err

    def _register_session(self) -> Optional[int]:
        """
        Registers a new CIP session with the target.

        :return: the session id if session registered successfully, else None
        """
        if self._cfg['ethernetip_params']['session']:
            return self._cfg['ethernetip_params']['session']

        # request = RegisterSessionRequestPacket(self._cfg["protocol version"])
        request = RegisterSessionRequest(**self._cfg['ethernetip_params'])
        response: RegisterSessionRequest.response_class = self._send_eip_request(request)
        if response:
            self._cfg['ethernetip_params']['session'] = response.header['session_id']
            self.__log.info("Session=%d has been registered.",  self._cfg['ethernetip_params']['session'])
            return self._cfg['ethernetip_params']['session']

        self.__log.error("Failed to register session: %s", response.error)
        return None

    def _forward_open(self):
        """
        Opens a new connection with the target PLC using the *Forward Open* or *Extended Forward Open* service.

        :return: True if connection is open or was successfully opened, False otherwise
        """

        if self._target_is_connected:
            return True

        if self._cfg['ethernetip_params']['session'] == 0:
            raise CommError("A session must be registered before a Forward Open")

        # bits (+16 for extended forward open):
        # 15: redundant owner ( 0 = exclusive owner)
        # 14-13: Connection type (10 = point to point)
        # 12: reserved
        # 11-10: priority ( 00 = low)
        # 9: fixed/variable ( 1 = variable, aka messages any size up to connection size)
        # 8-0: connection size
        init_net_params = 0b_0100_0010_0000_0000  # CIP Vol 1 - 3-5.5.1.1

        if self._cfg['extended_forward_open']:
            net_params = (self.connection_size & 0xFFFF) | init_net_params << 16
        else:
            net_params = (self.connection_size & 0x01FF) | init_net_params

        request_params = {
            **self._cfg['connection_params'],
            'connection_path': self._cfg["cip_path"] + MSG_ROUTER_PATH,
            'o_t_connection_params': net_params,
            't_o_connection_params': net_params,
        }

        if self._cfg['extended_forward_open']:
            cip_request = ConnectionManagerObject.large_forward_open(
                instance=ConnectionManagerObject.Instance.open_request,
                request_data=request_params,
            )
        else:
            cip_request = ConnectionManagerObject.forward_open(
                instance=ConnectionManagerObject.Instance.open_request,
                request_data=request_params,
            )

        request = SendRRDataRequest(
            *self._enip_args,
            cip_request=cip_request
        )

        response = self._send_eip_request(request)
        cip_response = cip_request.response_type(response.value)

        # response = self.generic_message(
        #     service=service,
        #     class_code=ClassCode.connection_manager,
        #     instance=ConnectionManagerInstances.open_request,
        #     request_data=request_params_type.encode(request_params),
        #     route_path=False,
        #     connected=False,
        #     name="forward_open",
        # )

        if response:
            self._cfg['connection_params']['o_t_connection_id'] = cip_response.value['o_t_connection_id']
            self._target_is_connected = True
            self.__log.info(
                f"{'Extended ' if self._cfg['extended_forward_open'] else ''}Forward Open succeeded. "
                f"O->T Connection ID={self._cfg['connection_params']['o_t_connection_id']}"
            )
            return True
        self.__log.error(f"forward_open failed - {response.error}")
        return False

    def close(self):
        """
        Closes the current connection and un-registers the session.
        """
        errs = []

        try:
            if self._target_is_connected:
                self._forward_close()
            if self._cfg['ethernetip_params']['session'] != 0:
                self._un_register_session()
        except Exception as err:
            errs.append(err)
            self.__log.exception("Error closing connection with device")

        try:
            if self._sock:
                self._sock.close()
        except Exception as err:
            errs.append(err)
            self.__log.exception("Error closing socket connection")

        self._sock = None
        self._target_is_connected = False
        self._cfg['ethernetip_params']['session'] = 0
        self._connection_opened = False

        if errs:
            raise CommError(" - ".join(str(e) for e in errs))

    def _un_register_session(self):
        """
        Un-registers the current session with the target.
        """
        request = UnRegisterSessionRequest(*self._enip_args)
        self._send_eip_request(request)
        self._cfg['ethernetip_params']['session'] = 0
        self.__log.info("Session Unregistered")

    def _forward_close(self):
        """CIP implementation of the forward close message

        Each connection opened with the forward open message need to be closed.
        Refer to ODVA documentation Volume 1 3-5.5.3

        :return: False if any error in the replayed message
        """

        if self._cfg['ethernetip_params']['session'] == 0:
            raise CommError("A session must be registered before a Forward Open")

        route_path = PADDED_EPATH.encode(
            self._cfg["cip_path"] + MSG_ROUTER_PATH, length=True, pad_length=True
        )

        forward_close_msg = [
            USINT.encode(PRIORITY),
            USINT.encode(TIMEOUT_TICKS),
            UINT.encode(self._cfg['connection_params']['connection_serial']),
            UINT.encode(self._cfg['connection_params']['vendor_id']),
            UDINT.encode(self._cfg['connection_params']["originator_serial"]),
        ]

        response = self.generic_message(
            service=ConnectionManagerServices.forward_close,
            class_code=ClassCode.connection_manager,
            instance=ConnectionManagerInstances.open_request,
            connected=False,
            route_path=route_path,
            request_data=b"".join(forward_close_msg),
            name="forward_close",
        )
        if response:
            self._target_is_connected = False
            self.__log.info("Forward Close succeeded.")
            return True

        self.__log.error("forward_close failed: %s", response.error)
        return False

    def get_attributes_all(
        self,
        cip_object: Type[CIPObject],
        instance: int = CIPObject.Instance.DEFAULT,
        route_path: Union[bool, Sequence[CIPSegment], bytes, str] = True,
    ) -> Tag:

        return self.generic_message(
            service=Services.get_attributes_all,
            class_code=cip_object.class_code,
            instance=instance,
            data_type=(
                cip_object._class_all_type
                if instance == CIPObject.Instance.CLASS
                else cip_object._instance_all_type
            ),
            route_path=route_path,
            name="get_attributes_all",
            connected=True,
        )

    def generic_message(
        self,
        service: Union[int, bytes],
        class_code: Union[int, bytes],
        instance: Union[int, bytes],
        attribute: Union[int, bytes] = b"",
        request_data: Any = b"",
        data_type: Optional[Union[Type[DataType], DataType]] = None,
        name: str = "generic",
        connected: bool = True,
        unconnected_send: bool = False,
        route_path: Union[bool, Sequence[CIPSegment], bytes, str] = True,
        **kwargs,
    ) -> Tag:
        """
        Perform a generic CIP message.  Similar to how MSG instructions work in Logix.

        :param service: service code for the request (single byte)
        :param class_code: request object class ID
        :param instance: ID for an instance of the class
                         If set with 0, request class attributes.
        :param attribute: (optional) attribute ID for the service/class/instance
        :param request_data: (optional) any additional data required for the request.
        :param data_type: a ``DataType`` class that will be used to decode the response, None to return just bytes
        :param name:  return ``Tag.tag`` value, arbitrary but can be used for tracking returned Tags
        :param connected: ``True`` if service required a CIP connection (forward open), ``False`` to use UCMM
        :param unconnected_send: (Unconnected Only) wrap service in an UnconnectedSend service
        :param route_path: (Unconnected Only) ``True`` to use current connection route to destination, ``False`` to ignore,
                           Or provide a path string, list of segments to be encoded as a PADDED_EPATH, or
                           an already encoded path.
        :return: a Tag with the result of the request. (Tag.value for writes will be the request_data)
        """

        if connected:
            with_forward_open(lambda _: None)(self)

        _kwargs = {
            "service": service,
            "class_code": class_code,
            "instance": instance,
            "attribute": attribute,
            "request_data": request_data,
            "data_type": data_type,
        }

        if connected:
            _kwargs["sequence"] = self._sequence
        else:
            if route_path is True:
                _kwargs["route_path"] = PADDED_EPATH.encode(
                    self._cfg["cip_path"], length=True, pad_length=True
                )
            elif isinstance(route_path, str):
                _kwargs["route_path"] = PADDED_EPATH.encode(
                    parse_cip_route(route_path), length=True, pad_length=True
                )
            elif isinstance(route_path, bytes):
                _kwargs["route_path"] = route_path
            elif route_path:
                _kwargs["route_path"] = PADDED_EPATH.encode(
                    route_path, length=True, pad_length=True
                )

            _kwargs["unconnected_send"] = unconnected_send

        req_class = GenericConnectedRequestPacket if connected else GenericUnconnectedRequestPacket
        request = req_class(**_kwargs)

        self.__log.info("Sending generic message: %s", name)
        response = self.send(request)
        if not response:
            self.__log.error("Generic message %r failed: %s", name, response.error)
        else:
            self.__log.info("Generic message %r completed", name)

        if kwargs.get("return_response_packet"):
            return Tag(name, response, data_type, error=response.error)

        return Tag(name, response.value, data_type, error=response.error)

    def send(self, request: RequestPacket) -> ResponsePacket:
        if not request.error:
            request_kwargs = {
                # "target_cid": self._target_cid,
                "session_id": self._cfg['ethernetip_params']['session'],
                "context": self._cfg['ethernetip_params']["context"],
                "option": self._cfg['ethernetip_params']["option"],
                "sequence": self._sequence,
            }

            self._send(request.build_request(**request_kwargs))
            self.__log.debug("Sent: %r", request)
            reply = None if request.no_response else self._receive()
        else:
            reply = None

        response = request.response_class(request, reply)
        self.__log.debug("Received: %r", response)
        return response

    def _send_cip_request(
        self,
        request: CIPRequest,
        connected: bool = True,
        route_path: Union[bool, Sequence[CIPSegment], bytes, str] = True,
    ):
        if connected:
            eip_request = self._create_connected_eip_request(request)
        else:
            eip_request = self._create_unconnected_eip_request(request, route_path)

    def _create_connected_eip_request(self, request, route_path: Union[bool, Sequence[CIPSegment], bytes, str]) -> SendUnitDataRequest:
        ...

    def _create_unconnected_eip_request(self, request, route_path: Union[bool, Sequence[CIPSegment], bytes, str]) -> SendRRDataRequest:
        if route_path is True and self._cfg['cip_path']:
            encoded_route = PADDED_EPATH.encode(self._cfg["cip_path"], length=True, pad_length=True)
        elif route_path:
            if isinstance(route_path, str):
                encoded_route = PADDED_EPATH.encode(parse_cip_route(route_path), length=True, pad_length=True)
            elif isinstance(route_path, bytes):
                encoded_route = route_path
            else:
                encoded_route = PADDED_EPATH.encode(route_path, length=True, pad_length=True)
        else:
            encoded_route = None

        if encoded_route:
            request = ConnectionManagerObject.unconnected_send(
                request,
                self._cfg['connection_params']['priority_tick_time'],
                self._cfg['connection_params']['timeout_ticks'],
                route_path=encoded_route,
            )

        eip_request = SendRRDataRequest(
            **self._cfg['ethernetip_params'],
            cip_request=request,
        )

        return eip_request

    def _send_eip_request(self, request: EtherNetIPRequest):
        self._send(request.message)
        if request.has_response:
            resp = self._receive()
            return request.response_class(resp, request)

    def _send(self, message):
        try:
            self.__log.verbose(">>> SEND >>> \n%s", PacketLazyFormatter(message))
            self._sock.send(message)
        except Exception as err:
            raise CommError("failed to send message") from err

    def _receive(self):
        try:
            reply = self._sock.receive()
        except Exception as err:
            raise CommError("failed to receive reply") from err
        else:
            self.__log.verbose("<<< RECEIVE <<< \n%s", PacketLazyFormatter(reply))
            return reply


def parse_connection_path(path: str, auto_slot: bool = False) -> Tuple[str, List[PortSegment]]:
    """
    Parses and validates the CIP path into the destination IP and
    sequence of port/link segments.
    Returns the IP and a list of PortSegments
    """
    try:
        path = path.replace("\\", "/")
        ip, *route = path.split("/")

        try:
            ipaddress.ip_address(ip)
        except ValueError as err:
            raise RequestError(f"Invalid IP Address: {ip}") from err

        _path = parse_cip_route(route, auto_slot)

    except RequestError:
        raise
    except Exception as err:
        raise RequestError(f"Failed to parse connection path: {path}") from err
    else:
        return ip, _path


def parse_cip_route(path: Union[str, List[str]], auto_slot: bool = False) -> List[PortSegment]:
    try:
        if isinstance(path, str):
            path = path.replace("\\", "/")
            segments = path.split("/")
        else:
            segments = path

        if not segments:
            _path = [PortSegment("bp", 0)] if auto_slot else []
        elif len(segments) == 1 and auto_slot:
            _path = [PortSegment("bp", segments[0])]
        else:
            if len(segments) % 2:
                raise RequestError(
                    "Invalid connection path, must contain segment pairs(port/link), "
                    f"{len(segments)} segments provided."
                )
            pairs = (segments[i : i + 2] for i in range(0, len(segments), 2))
            _path = [
                PortSegment(int(port) if port.isdigit() else port, link) for port, link in pairs
            ]
    except RequestError:
        raise
    except Exception as err:
        raise RequestError(f"Failed to parse cip route: {path}") from err
    else:
        return _path
