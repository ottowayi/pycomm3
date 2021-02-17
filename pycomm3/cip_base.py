# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Ian Ottoway <ian@ottoway.dev>
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

__all__ = ['CIPDriver', 'with_forward_open', 'parse_connection_path', ]

import logging
import ipaddress
from functools import wraps
from os import urandom
from typing import Union, Optional

from .exceptions import DataError, CommError, RequestError
from .tag import Tag
from .bytes_ import Pack, Unpack
from .const import (PATH_SEGMENTS, ConnectionManagerInstance, PRIORITY, ClassCode, TIMEOUT_MULTIPLIER, TIMEOUT_TICKS,
                    TRANSPORT_CLASS, PRODUCT_TYPES, VENDORS, STATES, MSG_ROUTER_PATH,
                    ConnectionManagerService, Services)
from .packets import DataFormatType, RequestTypes
from .socket_ import Socket


def with_forward_open(func):
    """Decorator to ensure a forward open request has been completed with the plc"""

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        opened = False
        if not self._forward_open():
            if self._cfg['extended forward open']:
                logger = logging.getLogger('pycomm3.clx.LogixDriver')
                logger.info('Extended Forward Open failed, attempting standard Forward Open.')
                self._cfg['extended forward open'] = False
                if self._forward_open():
                    opened = True
        else:
            opened = True

        if not opened:
            msg = f'Target did not connected. {func.__name__} will not be executed.'
            raise DataError(msg)
        return func(self, *args, **kwargs)

    return wrapped


class CIPDriver:
    """
    A base CIP driver for the SLCDriver and LogixDriver classes.  Implements common CIP services like
    (un)registering sessions, forward open/close, generic messaging, etc.
    """
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, path: str, *args, large_packets: bool = True, **kwargs):
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

        :param large_packets: if True (default), the *Extended Forward Open* service will be used

            .. note::

                *Extended Forward Open* allows the used of 4KBs of service data in each request.
                The standard *Forward Open* is limited to 500 bytes.  Not all hardware supports the large packet size,
                like ENET or ENBT modules or ControlLogix version 19 or lower.  **This argument is no longer required
                as of 0.5.1, since it will automatically try a standard Forward Open if the extended one fails**
        """

        self._sequence_number = 1
        self._sock = None
        self._session = 0
        self._connection_opened = False
        self._target_cid = None
        self._target_is_connected = False
        self._info = {}
        ip, _path = parse_connection_path(path)

        self._cfg = {
            'context': b'_pycomm_',
            'protocol version': b'\x01\x00',
            'rpi': 5000,
            'port': 0xAF12,  # 44818
            'timeout': 10,
            'ip address': ip,
            # is cip_path the right term?  or request_path? or something else?
            'cip_path': _path[1:],  # leave out the len, we sometimes add to the path later
            'option': 0,
            'cid': b'\x27\x04\x19\x71',
            'csn': b'\x27\x04',
            'vid': b'\x09\x10',
            'vsn': b'\x09\x10\x19\x71',
            'name': 'LogixDriver',
            'extended forward open': large_packets}

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except CommError:
            self.__log.exception('Error closing connection.')
            return False
        else:
            if not exc_type:
                return True
            else:
                self.__log.exception('Unhandled Client Error', exc_info=(exc_type, exc_val, exc_tb))
                return False

    def __repr__(self):
        _ = self._info
        return f"Program Name: {_.get('name')}, Device: {_.get('device_type', 'None')}, Revision: {_.get('revision', 'None')}"

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
        return 4000 if self._cfg['extended forward open'] else 500

    @property
    def _sequence(self) -> int:
        """
        Increment and return the sequence id used with connected messages

        :return: The next sequence number
        """
        self._sequence_number += 1

        if self._sequence_number >= 65535:
            self._sequence_number = 1

        return self._sequence_number

    @classmethod
    def list_identity(cls, path) -> Optional[str]:
        """
        Uses the ListIdentity service to identify the target

        :return: device identity if reply contains valid response else None
        """
        plc = cls(path, init_tags=False, init_info=False)
        plc.open()
        identity = plc._list_identity()
        plc.close()
        return identity

    def _list_identity(self):
        request = RequestTypes.list_identity(self)
        response = request.send()
        return response.identity

    def get_module_info(self, slot):
        try:
            response = self.generic_message(
                service=Services.get_attributes_all,
                class_code=ClassCode.identity_object, instance=b'\x01',
                connected=False, unconnected_send=True,
                route_path=Pack.epath(Pack.usint(PATH_SEGMENTS['bp']) + Pack.usint(slot), pad_len=True)
            )

            if response:
                return _parse_identity_object(response.value)
            else:
                raise DataError(f'generic_message did not return valid data - {response.error}')

        except Exception as err:
            raise DataError('error getting module info') from err

    def open(self):
        """
        Creates a new Ethernet/IP socket connection to target device and registers a CIP session.

        :return: True if successful, False otherwise
        """
        # handle the socket layer
        if self._connection_opened:
            return
        try:
            if self._sock is None:
                self._sock = Socket()
            self._sock.connect(self._cfg['ip address'], self._cfg['port'])
            self._connection_opened = True
            self._cfg['cid'] = urandom(4)
            self._cfg['vsn'] = urandom(4)
            if self._register_session() is None:
                self.__log.warning("Session not registered")
                return False
            return True
        except Exception as err:
            raise CommError('failed to open a connection') from err

    def _register_session(self) -> Optional[int]:
        """
        Registers a new CIP session with the target.

        :return: the session id if session registered successfully, else None
        """
        if self._session:
            return self._session

        self._session = 0
        request = RequestTypes.register_session(self)
        request.add(
            self._cfg['protocol version'],
            b'\x00\x00'
        )

        response = request.send()
        if response:
            self._session = response.session
            self.__log.info(f"Session = {response.session} has been registered.")
            return self._session

        self.__log.warning('Session has not been registered.')
        return None

    def _forward_open(self):
        """
        Opens a new connection with the target PLC using the *Forward Open* or *Extended Forward Open* service.

        :return: True if connection is open or was successfully opened, False otherwise
        """

        if self._target_is_connected:
            return True

        if self._session == 0:
            raise CommError("A Session Not Registered Before forward_open.")

        init_net_params = 0b_0100_0010_0000_0000  # CIP Vol 1 - 3-5.5.1.1

        if self._cfg['extended forward open']:
            net_params = Pack.udint((self.connection_size & 0xFFFF) | init_net_params << 16)
        else:
            net_params = Pack.uint((self.connection_size & 0x01FF) | init_net_params)

        route_path = Pack.epath(self._cfg['cip_path'] + MSG_ROUTER_PATH)
        service = (ConnectionManagerService.forward_open
                   if not self._cfg['extended forward open']
                   else ConnectionManagerService.large_forward_open)

        forward_open_msg = [
            PRIORITY,
            TIMEOUT_TICKS,
            b'\x00\x00\x00\x00',  # O->T produced connection ID, not needed for us so leave blank
            self._cfg['cid'],
            self._cfg['csn'],
            self._cfg['vid'],
            self._cfg['vsn'],
            TIMEOUT_MULTIPLIER,
            b'\x00\x00\x00',  # reserved
            b'\x01\x40\x20\x00',  # O->T RPI in microseconds, RPIs are not important for us so fixed value is fine
            net_params,
            b'\x01\x40\x20\x00',  # T->O RPI
            net_params,
            TRANSPORT_CLASS,
        ]

        response = self.generic_message(
            service=service,
            class_code=ClassCode.connection_manager,
            instance=ConnectionManagerInstance.open_request,
            request_data=b''.join(forward_open_msg),
            route_path=route_path,
            connected=False,
            name='__FORWARD_OPEN__'
        )

        if response:
            self._target_cid = response.value[:4]
            self._target_is_connected = True
            self.__log.info(
                f"{'Extended ' if self._cfg['extended forward open'] else ''}Forward Open succeeded. Target CID={self._target_cid}")
            return True
        self.__log.warning(f"forward_open failed - {response.error}")
        return False

    def close(self):
        """
        Closes the current connection and un-registers the session.
        """
        errs = []
        try:
            if self._target_is_connected:
                self._forward_close()
            if self._session != 0:
                self._un_register_session()
        except Exception as err:
            errs.append(err)
            self.__log.warning(f"Error on close() -> session Err: {err}")

        try:
            if self._sock:
                self._sock.close()
        except Exception as err:
            errs.append(err)
            self.__log.warning(f"close() -> _sock.close Err: {err}")

        self._sock = None
        self._target_is_connected = False
        self._session = 0
        self._connection_opened = False

        if errs:
            raise CommError(' - '.join(str(e) for e in errs))

    def _un_register_session(self):
        """
        Un-registers the current session with the target.
        """
        request = RequestTypes.unregister_session(self)
        request.send()
        self._session = None
        self.__log.info('Session Unregistered')

    def _forward_close(self):
        """ CIP implementation of the forward close message

        Each connection opened with the forward open message need to be closed.
        Refer to ODVA documentation Volume 1 3-5.5.3

        :return: False if any error in the replayed message
        """

        if self._session == 0:
            raise CommError("A session need to be registered before to call forward_close.")

        route_path = Pack.epath(self._cfg['cip_path'] + MSG_ROUTER_PATH, pad_len=True)

        forward_close_msg = [
            PRIORITY,
            TIMEOUT_TICKS,
            self._cfg['csn'],
            self._cfg['vid'],
            self._cfg['vsn'],
        ]

        response = self.generic_message(
            service=ConnectionManagerService.forward_close,
            class_code=ClassCode.connection_manager,
            instance=ConnectionManagerInstance.open_request,
            connected=False,
            route_path=route_path,
            request_data=b''.join(forward_close_msg),
            name='__FORWARD_CLOSE__'
        )
        if response:
            self._target_is_connected = False
            self.__log.info('Forward Close succeeded.')
            return True

        self.__log.warning(f"forward_close failed - {response.error}")
        return False

    def generic_message(self,
                        service: Union[int, bytes],
                        class_code: Union[int, bytes],
                        instance: Union[int, bytes],
                        attribute: Union[int, bytes] = b'',
                        request_data: bytes = b'',
                        data_format: Optional[DataFormatType] = None,
                        name: str = 'generic',
                        connected: bool = True,
                        unconnected_send: bool = False,
                        route_path: Union[bool, bytes] = True) -> Tag:
        """
        Perform a generic CIP message.  Similar to how MSG instructions work in Logix.

        :param service: service code for the request (single byte)
        :param class_code: request object class ID
        :param instance: instance ID of the class
        :param attribute: (optional) attribute ID for the service/class/instance
        :param request_data: (optional) any additional data required for the request
        :param data_format: (reads only) If provided, a read response will automatically be unpacked into the attributes
                            defined, must be a sequence of tuples, (attribute name, data_type).
                            If name is ``None`` or an empty string, it will be ignored. If data-type is an ``int`` it will
                            not be unpacked, but left as ``bytes``.  Data will be returned as a ``dict``.
                            If ``None``, response data will be returned as just ``bytes``.
        :param name:  return ``Tag.tag`` value, arbitrary but can be used for tracking returned Tags
        :param connected: ``True`` if service required a CIP connection (forward open), ``False`` to use UCMM
        :param unconnected_send: (Unconnected Only) wrap service in an UnconnectedSend service
        :param route_path: (Unconnected Only) ``True`` to use current connection route to destination, ``False`` to ignore,
                           Or provide a packed EPATH (``bytes``) route to use.
        :return: a Tag with the result of the request. (Tag.value for writes will be the request_data)
        """

        if connected:
            with_forward_open(lambda _: None)(self)

        _kwargs = {
            'service': service,
            'class_code': class_code,
            'instance': instance,
            'attribute': attribute,
            'request_data': request_data,
            'data_format': data_format,
        }

        if not connected:
            if route_path is True:
                _kwargs['route_path'] = Pack.epath(self._cfg['cip_path'], pad_len=True)
            elif route_path:
                _kwargs['route_path'] = route_path

            _kwargs['unconnected_send'] = unconnected_send

        req_class = RequestTypes.generic_connected if connected else RequestTypes.generic_unconnected
        request = req_class(self)
        request.build(**_kwargs)

        response = request.send()

        return Tag(name, response.value, None, error=response.error)


def parse_connection_path(path):
    try:
        path = path.replace('\\', '/')
        ip, *segments = path.split('/')
        try:
            ipaddress.ip_address(ip)
        except ValueError as err:
            raise RequestError(f'Invalid IP Address: {ip}') from err
        segments = [_parse_cip_path_segment(s) for s in segments]

        if not segments:
            _path = [Pack.usint(PATH_SEGMENTS['backplane']), b'\x00']
        elif len(segments) == 1:
            _path = [Pack.usint(PATH_SEGMENTS['backplane']), Pack.usint(segments[0])]
        else:
            pairs = (segments[i:i + 2] for i in range(0, len(segments), 2))
            _path = []
            for port, dest in pairs:
                if isinstance(dest, bytes):
                    port |= 1 << 4  # set Extended Link Address bit, CIP Vol 1 C-1.3
                    dest_len = len(dest)
                    if dest_len % 2:
                        dest += b'\x00'
                    _path.extend([Pack.usint(port), Pack.usint(dest_len), dest])
                else:
                    _path.extend([Pack.usint(port), Pack.usint(dest)])

    except Exception as err:
        raise RequestError(f'Failed to parse connection path: {path}') from err
    else:
        return ip, Pack.epath(b''.join(_path))


def _parse_cip_path_segment(segment: str):
    try:
        if segment.isnumeric():
            return int(segment)
        else:
            tmp = PATH_SEGMENTS.get(segment.lower())
            if tmp:
                return tmp
            else:
                try:
                    ipaddress.ip_address(segment)
                    return b''.join(Pack.usint(ord(c)) for c in segment)
                except ValueError as err:
                    raise RequestError(f'Invalid IP Address Segment: {segment}') from err
    except Exception as err:
        raise RequestError(f'Failed to parse path segment: {segment}') from err


def _parse_identity_object(reply):
    vendor = Unpack.uint(reply[:2])
    product_type = Unpack.uint(reply[2:4])
    product_code = Unpack.uint(reply[4:6])
    major_fw = int(reply[6])
    minor_fw = int(reply[7])
    status = f'{Unpack.uint(reply[8:10]):0{16}b}'
    serial_number = f'{Unpack.udint(reply[10:14]):0{8}x}'
    product_name_len = int(reply[14])
    tmp = 15 + product_name_len
    device_type = reply[15:tmp].decode()

    state = Unpack.uint(reply[tmp:tmp + 4]) if reply[tmp:] else -1  # some modules don't return a state

    return {
        'vendor': VENDORS.get(vendor, 'UNKNOWN'),
        'product_type': PRODUCT_TYPES.get(product_type, 'UNKNOWN'),
        'product_code': product_code,
        'version_major': major_fw,
        'version_minor': minor_fw,
        'revision': f'{major_fw}.{minor_fw}',
        'serial': serial_number,
        'device_type': device_type,
        'status': status,
        'state': STATES.get(state, 'UNKNOWN'),
    }

