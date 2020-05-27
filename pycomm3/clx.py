# -*- coding: utf-8 -*-
#
# const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
# Copyright (c) 2019 Ian Ottoway <ian@ottoway.dev>
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
#

import socket
import logging
import datetime
import time
from functools import wraps
from os import urandom
from typing import Union, List, Sequence, Tuple, Optional

from autologging import logged

from . import DataError, CommError
from . import Tag, RequestError
from .bytes_ import (pack_usint, pack_udint, pack_uint, pack_dint, unpack_uint, unpack_udint, pack_ulint, pack_char,
                     unpack_dint, pack_sint, PACK_DATA_FUNCTION)
from .const import (DATA_TYPE, TAG_SERVICES_REQUEST, EXTENDED_SYMBOL, PATH_SEGMENTS, ELEMENT_TYPE, CLASS_CODE, CLASS_TYPE,
                    INSTANCE_TYPE, FORWARD_CLOSE, FORWARD_OPEN, LARGE_FORWARD_OPEN, CONNECTION_MANAGER_INSTANCE, PRIORITY,
                    TIMEOUT_MULTIPLIER, TIMEOUT_TICKS, TRANSPORT_CLASS, UNCONNECTED_SEND, PRODUCT_TYPES, VENDORS, STATES,
                    MICRO800_PREFIX, READ_RESPONSE_OVERHEAD, MULTISERVICE_READ_OVERHEAD)
from .const import (SUCCESS, INSUFFICIENT_PACKETS, BASE_TAG_BIT, MIN_VER_INSTANCE_IDS, REQUEST_PATH_SIZE, SEC_TO_US,
                    KEYSWITCH, TEMPLATE_MEMBER_INFO_LEN, EXTERNAL_ACCESS, DATA_TYPE_SIZE, MIN_VER_EXTERNAL_ACCESS)
from .packets import REQUEST_MAP, RequestPacket, get_service_status, DataFormatType
from .socket_ import Socket

AtomicType = Union[int, float, bool, str]
TagType = Union[AtomicType, List[AtomicType]]
ReturnType = Union[Tag, List[Tag]]

# re_bit = re.compile(r'(?P<base>^.*)\.(?P<bit>([0-2][0-9])|(3[01])|[0-9])$')


def with_forward_open(func):
    """Decorator to ensure a forward open request has been completed with the plc"""

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        opened = False
        if not self._forward_open():
            if self.attribs['extended forward open']:
                logger = logging.getLogger('pycomm3.clx.LogixDriver')
                logger.info('Extended Forward Open failed, attempting standard Forward Open.')
                self.attribs['extended forward open'] = False
                if self._forward_open():
                    opened = True
        else:
            opened = True

        if not opened:
            msg = f'Target did not connected. {func.__name__} will not be executed.'
            raise DataError(msg)
        return func(self, *args, **kwargs)

    return wrapped


@logged
class LogixDriver:
    """
    An Ethernet/IP Client library for reading and writing tags in ControlLogix and CompactLogix PLCs.
    """

    def __init__(self, path: str, *args,  large_packets: bool = True, micro800: bool = False,
                 init_info: bool = True, init_tags: bool = True, init_program_tags: bool = False, **kwargs):
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

        :param init_info:  if True (default), initializes controller info (name, revision, etc) on connect

            .. note::

                Initializing the controller info will enable/disable the use of *Symbol Instance Addressing* in
                the :meth:`.read` and :meth:`.write` methods.  If you disable this option and are using an older firmware
                (below v21), you will need to set ``plc.use_instance_ids`` to False or the reads and writes will fail.

        :param init_tags: if True (default), uploads all controller-scoped tag definitions on connect
        :param init_program_tags: if True, uploads all program-scoped tag definitions on connect
        :param micro800: set to True if connecting to a Micro800 series PLC with ``init_info`` disabled, it will disable unsupported features

        .. tip::

            Initialization of tags is required for the :meth:`.read` and :meth:`.write` to work.  This is because
            they require information about the data type and structure of the tags inside the controller.  If opening
            multiple connections to the same controller, you may disable tag initialization in all but the first connection
            and set ``plc2._tags = plc1.tags`` to prevent needing to upload the tag definitions multiple times.

        """

        self._sequence_number = 1
        self._sock = None
        # self.__direct_connections = direct_connection

        self._session = 0
        self._connection_opened = False
        self._target_cid = None
        self._target_is_connected = False
        self._info = {}
        ip, _path = _parse_connection_path(path, micro800)

        self.attribs = {
            'context': b'_pycomm_',
            'protocol version': b'\x01\x00',
            'rpi': 5000,
            'port': 0xAF12,  # 44818
            'timeout': 10,
            'ip address': ip,
            'cip_path': _path,
            'option': 0,
            'cid': b'\x27\x04\x19\x71',
            'csn': b'\x27\x04',
            'vid': b'\x09\x10',
            'vsn': b'\x09\x10\x19\x71',
            'name': 'Base',
            'extended forward open': large_packets}
        self._cache = None
        self._data_types = {}
        self._tags = {}
        self._micro800 = micro800
        self.use_instance_ids = True

        if init_tags or init_info:
            self.open()
            if init_info:
                self.get_plc_info()
                self._micro800 = self.info['device_type'].startswith(MICRO800_PREFIX)
                _, _path = _parse_connection_path(path, self._micro800)  # need to update path if using a Micro800
                self.attribs['cip_path'] = _path
                self.use_instance_ids = (self.info.get('version_major', 0) >= MIN_VER_INSTANCE_IDS) and not self._micro800
                if not self._micro800:
                    self.get_plc_name()

            if init_tags:
                self.get_tag_list(program='*' if init_program_tags else None)

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
    def tags(self) -> dict:
        """
        Read-only property to access all the tag definitions uploaded from the controller.
        """
        return self._tags

    @property
    def data_types(self) -> dict:
        """
        Read-only property for access to all data type definitions uploaded from the controller.
        """
        return self._data_types

    @property
    def connected(self) -> bool:
        """
        Read-Only Property to check whether or not a connection is open.

        :return: True if a connection is open, False otherwise
        """
        return self._connection_opened

    @property
    def info(self) -> dict:
        """
        Property containing a dict of all the information collected about the connected PLC.

        **Fields**:

        - *vendor* - name of hardware vendor, e.g. ``'Rockwell Automation/Allen-Bradley'``
        - *product_type* - typically ``'Programmable Logic Controller'``
        - *product_code* - code identifying the product type
        - *version_major* - numeric value of major firmware version, e.g. ``28``
        - *version_minor* - numeric value of minor firmware version, e.g ``13``
        - *revision* - string value of firmware major and minor version, e.g. ``'28.13'``
        - *serial* - hex string of PLC serial number, e.g. ``'FFFFFFFF'``
        - *device_type* - string value for PLC device type, e.g. ``'1756-L83E/B'``
        - *keyswitch* - string value representing the current keyswitch position, e.g. ``'REMOTE RUN'``
        - *name* - string value of the current PLC program name, e.g. ``'PLCA'``

        **The following fields are added from calling** :meth:`.get_tag_list`

        - *programs* - dict of all Programs in the PLC and their routines, ``{program: {'routines': [routine, ...}...}``
        - *tasks* - dict of all Tasks in the PLC, ``{task: {'instance_id': ...}...}``
        - *modules* - dict of I/O modules in the PLC, ``{module: {'slots': {1: {'types': ['O,' 'I', 'C']}, ...}, 'types':[...]}...}``

        """
        return self._info

    @property
    def name(self) -> Optional[str]:
        """
        :return: name of PLC program
        """
        return self._info.get('name')

    @property
    def connection_size(self):
        """CIP connection size, ``4000`` if using Extended Forward Open else ``500``"""
        return 4000 if self.attribs['extended forward open'] else 500

    def new_request(self, command: str, *args, **kwargs) -> RequestPacket:
        """
        Creates a new request packet for the given command.
        If the command is invalid, a base :class:`RequestPacket` is created.

        Commands:
            - `send_unit_data`
            - `send_rr_data`
            - `register_session`
            - `unregister_session`
            - `list_identity`
            - `multi_request`
            - `read_tag`
            - `read_tag_fragmented`
            - `write_tag`
            - `write_tag_fragmented`
            - `generic_read`
            - `generic_write`
            - `generic_read_unconnected`
            - `generic_write_unconnected`

        :param command: the service for which a request will be created
        :return: a new request for the command
        """
        cls = REQUEST_MAP[command]
        return cls(self, *args, **kwargs)

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
        request = plc.new_request('list_identity')
        response = request.send()
        plc.close()
        return response.identity

    def get_module_info(self, slot):
        try:
            request = self.new_request('send_rr_data')
            request.add(
                # unnconnected send portion
                UNCONNECTED_SEND,
                b'\x02',
                CLASS_TYPE['8-bit'],
                b'\x06',  # class
                INSTANCE_TYPE["8-bit"],
                b'\x01',  # instance
                b'\x0A',  # priority
                b'\x0e',  # timeout ticks
                b'\x06\x00',  # service size

                # Identity request portion
                b'\x01',  # Service
                b'\x02',
                CLASS_TYPE['8-bit'],
                CLASS_CODE['Identity Object'],
                INSTANCE_TYPE["8-bit"],
                b'\x01',  # Instance 1
                b'\x01\x00',
                b'\x01',  # backplane
                pack_usint(slot),
            )
            response = request.send()

            if response:
                info = _parse_identity_object(response.data)
                return info
            else:
                raise DataError(f'send_rr_data did not return valid data - {response.error}')

        except Exception as err:
            raise DataError(err)

    def open(self):
        """
        Creates a new Ethernet/IP socket connection to target device and registers a CIP session.

        :return: True if successful, False otherwise
        """
        # handle the socket layer
        if not self._connection_opened:
            try:
                if self._sock is None:
                    self._sock = Socket()
                self._sock.connect(self.attribs['ip address'], self.attribs['port'])
                self._connection_opened = True
                self.attribs['cid'] = urandom(4)
                self.attribs['vsn'] = urandom(4)
                if self._register_session() is None:
                    self.__log.warning("Session not registered")
                    return False
                return True
            except Exception as e:
                raise CommError(e)

    def _register_session(self) -> Optional[int]:
        """
        Registers a new CIP session with the target.

        :return: the session id if session registered successfully, else None
        """
        if self._session:
            return self._session

        self._session = 0
        request = self.new_request('register_session')
        request.add(
            self.attribs['protocol version'],
            b'\x00\x00'
        )

        response = request.send()
        if response:
            self._session = response.session
            self.__log.debug(f"Session = {response.session} has been registered.")
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

        if self.attribs['extended forward open']:
            net_params = pack_udint((self.connection_size & 0xFFFF) | init_net_params << 16)
        else:
            net_params = pack_uint((self.connection_size & 0x01FF) | init_net_params)

        forward_open_msg = [
            FORWARD_OPEN if not self.attribs['extended forward open'] else LARGE_FORWARD_OPEN,
            b'\x02',  # CIP Path size
            CLASS_TYPE["8-bit"],  # class type
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_TYPE["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            b'\x00\x00\x00\x00',
            self.attribs['cid'],
            self.attribs['csn'],
            self.attribs['vid'],
            self.attribs['vsn'],
            TIMEOUT_MULTIPLIER,
            b'\x00\x00\x00',
            b'\x01\x40\x20\x00',
            net_params,
            b'\x01\x40\x20\x00',
            net_params,
            TRANSPORT_CLASS,
            self.attribs['cip_path']
        ]
        request = self.new_request('send_rr_data')
        request.add(*forward_open_msg)
        response = request.send()
        if response:
            self._target_cid = response.data[:4]
            self._target_is_connected = True
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
        request = self.new_request('unregister_session')
        request.send()
        self._session = None

    def _forward_close(self):
        """ CIP implementation of the forward close message

        Each connection opened with the forward open message need to be closed.
        Refer to ODVA documentation Volume 1 3-5.5.3

        :return: False if any error in the replayed message
        """

        if self._session == 0:
            raise CommError("A session need to be registered before to call forward_close.")
        request = self.new_request('send_rr_data')

        path_size, *path = self.attribs['cip_path']  # for some reason we need to add a 0x00 between these? CIP Vol 1

        forward_close_msg = [
            FORWARD_CLOSE,
            b'\x02',
            CLASS_TYPE["8-bit"],
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_TYPE["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            self.attribs['csn'],
            self.attribs['vid'],
            self.attribs['vsn'],
            bytes([path_size, 0, *path])
        ]

        request.add(*forward_close_msg)
        response = request.send()
        if response:
            self._target_is_connected = False
            return True

        self.__log.warning(f"forward_close failed - {response.error}")
        return False

    @with_forward_open
    def get_plc_name(self) -> str:
        """
        Requests the name of the program running in the PLC. Uses KB `23341`_ for implementation.

        .. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

        :return:  the controller program name
        """
        try:
            request = self.new_request('send_unit_data')
            request.add(
                bytes([TAG_SERVICES_REQUEST['Get Attributes']]),
                REQUEST_PATH_SIZE,
                CLASS_TYPE['8-bit'],
                CLASS_CODE['Program Name'],
                INSTANCE_TYPE["16-bit"],
                b'\x01\x00',  # Instance 1
                b'\x01\x00',  # Number of Attributes
                b'\x01\x00'  # Attribute 1 - program name
            )

            response = request.send()

            if response:
                self._info['name'] = _parse_plc_name(response)
                return self._info['name']
            else:
                raise DataError(f'send_unit_data did not return valid data - {response.error}')

        except Exception as err:
            raise DataError(err)

    def get_plc_info(self) -> dict:
        """
        Reads basic information from the controller, returns it and stores it in the ``info`` property.
        """
        try:
            route = self.attribs['cip_path'][1:-4]  # trim to just the route
            route_len = pack_uint(len(route) // 2)
            request_data = route_len + route
            response = self.generic_read(class_code=CLASS_CODE['Identity Object'], instance=b'\x01',
                                         service=b'\x01', request_data=request_data,
                                         data_format=[
                                            ('vendor', 'INT'), ('product_type', 'INT'), ('product_code', 'INT'),
                                            ('version_major', 'SINT'), ('version_minor', 'SINT'), ('_keyswitch', 2),
                                            ('serial', 'DINT'), ('device_type', 'SHORT_STRING')
                                         ],
                                         connected=False, unconnected_send=True)

            if response:
                info = _parse_plc_info(response.value)
                self._info = {**self._info, **info}
                return info
            else:
                raise DataError(f'send_unit_data did not return valid data - {response.error}')

        except Exception as err:
            raise DataError(err)

    @with_forward_open
    def get_tag_list(self, program: str = None, cache: bool = True) -> List[dict]:
        """
        Reads the tag list from the controller and the definition for each tag.  Definitions include tag name, tag type
        (atomic vs struct), data type (including nested definitions for structs), external access, dimensions defined (0-3)
        for arrays and their length, etc.

        .. note::

            For program scoped tags the tag['tag_name'] will be ``'Program:{program}.{tag_name}'``. This is so the tag
            list can be fed directly into the read function.


        :param program: scope to retrieve tag list, None for controller-only tags, ``'*'`` for all tags, else name of program
        :param cache: store the retrieved list in the :attr:`.tags` property.  Disable if you wish to get tags retrieved
                      to not overwrite the currently cached definition. For instance if you're checking tags in a single
                      program but currently reading controller-scoped tags.

        :return: a list containing dicts for each tag definition collected
        """

        self._cache = {
            'tag_name:id': {},
            'id:struct': {},
            'handle:id': {},
            'id:udt': {}
        }

        if program in ('*', None):
            self._info['programs'] = {}
            self._info['tasks'] = {}
            self._info['modules'] = {}

        if program == '*':
            tags = self._get_tag_list()
            for prog in self._info['programs']:
                tags += self._get_tag_list(prog)
        else:
            tags = self._get_tag_list(program)

        if cache:
            self._tags = {tag['tag_name']: tag for tag in tags}

        self._cache = None

        return tags

    def _get_tag_list(self, program=None):
        all_tags = self._get_instance_attribute_list_service(program)
        user_tags = self._isolate_user_tags(all_tags, program)
        for tag in user_tags:
            if tag['tag_type'] == 'struct':
                tag['data_type'] = self._get_data_type(tag['template_instance_id'])

        return user_tags

    def _get_instance_attribute_list_service(self, program=None):
        """ Step 1: Finding user-created controller scope tags in a Logix5000 controller

        This service returns instance IDs for each created instance of the symbol class, along with a list
        of the attribute data associated with the requested attribute
        """
        try:
            last_instance = 0
            tag_list = []
            while last_instance != -1:
                # Creating the Message Request Packet
                path = []
                if program:
                    if not program.startswith('Program:'):
                        program = f'Program:{program}'
                    path = [EXTENDED_SYMBOL, pack_usint(len(program)), program.encode('utf-8')]
                    if len(program) % 2:
                        path.append(b'\x00')

                path += [
                    # Request Path ( 20 6B 25 00 Instance )
                    CLASS_TYPE["8-bit"],  # Class id = 20 from spec 0x20
                    CLASS_CODE["Symbol Object"],  # Logical segment: Symbolic Object 0x6B
                    INSTANCE_TYPE["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                    pack_uint(last_instance),  # The instance
                ]
                path = b''.join(path)
                path_size = pack_usint(len(path) // 2)
                request = self.new_request('send_unit_data')

                attributes = [
                    b'\x01\x00',  # Attr. 1: Symbol name
                    b'\x02\x00',  # Attr. 2 : Symbol Type
                    b'\x03\x00',  # Attr. 3 : Symbol Address
                    b'\x05\x00',  # Attr. 5 : Symbol Object Address
                    b'\x06\x00',  # Attr. 6 : ? - Not documented (Software Control?)
                    b'\x08\x00'  # Attr. 8 : array dimensions [1,2,3]
                ]

                if self.info.get('version_major', 0) >= MIN_VER_EXTERNAL_ACCESS:
                    attributes.append(b'\x0a\x00')  # Attr. 10 : external access

                request.add(
                    bytes([TAG_SERVICES_REQUEST['Get Instance Attributes List']]),
                    path_size,
                    path,
                    pack_uint(len(attributes)),
                    *attributes

                )
                response = request.send()
                if not response:
                    raise DataError(f"send_unit_data returned not valid data - {response.error}")

                last_instance = self._parse_instance_attribute_list(response, tag_list)
            return tag_list

        except Exception as e:
            raise DataError(e)

    def _parse_instance_attribute_list(self, response, tag_list):
        """ extract the tags list from the message received"""

        tags_returned = response.data
        tags_returned_length = len(tags_returned)
        idx = count = instance = 0
        try:
            while idx < tags_returned_length:
                instance = unpack_dint(tags_returned[idx:idx + 4])
                idx += 4
                tag_length = unpack_uint(tags_returned[idx:idx + 2])
                idx += 2
                tag_name = tags_returned[idx:idx + tag_length]
                idx += tag_length
                symbol_type = unpack_uint(tags_returned[idx:idx + 2])
                idx += 2
                count += 1
                symbol_address = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4
                symbol_object_address = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4
                software_control = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4

                dim1 = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4
                dim2 = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4
                dim3 = unpack_udint(tags_returned[idx:idx + 4])
                idx += 4

                if self.info.get('version_major', 0) >= MIN_VER_EXTERNAL_ACCESS:
                    access = tags_returned[idx] & 0b_0011
                    idx += 1
                else:
                    access = None

                tag_list.append({'instance_id': instance,
                                 'tag_name': tag_name,
                                 'symbol_type': symbol_type,
                                 'symbol_address': symbol_address,
                                 'symbol_object_address': symbol_object_address,
                                 'software_control': software_control,
                                 'external_access': EXTERNAL_ACCESS.get(access, 'Unknown'),
                                 'dimensions': [dim1, dim2, dim3]})

        except Exception as e:
            raise DataError(e)

        if response.service_status == SUCCESS:
            last_instance = -1
        elif response.service_status == INSUFFICIENT_PACKETS:
            last_instance = instance + 1
        else:
            self.__log.warning('unknown status during _parse_instance_attribute_list')
            last_instance = -1

        return last_instance

    def _isolate_user_tags(self, all_tags, program=None):
        try:
            user_tags = []
            for tag in all_tags:
                io_tag = False
                name = tag['tag_name'].decode()

                if name.startswith('Program:'):
                    prog_name = name.replace('Program:', '')
                    self._info['programs'][prog_name] = {'instance_id': tag['instance_id'], 'routines': []}
                    continue

                if name.startswith('Routine:'):
                    rtn_name = name.replace('Routine:', '')
                    _program = self._info['programs'].get(program)
                    if _program is None:
                        self.__log.error(f'Program {program} not defined in tag list')
                    else:
                        _program['routines'].append(rtn_name)
                    continue

                if name.startswith('Task:'):
                    self._info['tasks'][name.replace('Task:', '')] = {'instance_id': tag['instance_id']}
                    continue

                # system tags that may interfere w/ finding I/O modules
                if 'Map:' in name or 'Cxn:' in name:
                    continue

                # I/O module tags
                # Logix 5000 Controllers I/O and Tag Data, page 17  (1756-pm004_-en-p.pdf)
                if any(x in name for x in (':I', ':O', ':C', ':S')):
                    io_tag = True
                    mod = name.split(':')
                    mod_name = mod[0]
                    if mod_name not in self._info['modules']:
                        self._info['modules'][mod_name] = {'slots': {}}
                    if len(mod) == 3 and mod[1].isdigit():
                        mod_slot = int(mod[1])
                        if mod_slot not in self._info['modules'][mod_name]:
                            self._info['modules'][mod_name]['slots'][mod_slot] = {'types': []}
                        self._info['modules'][mod_name]['slots'][mod_slot]['types'].append(mod[2])
                    elif len(mod) == 2:
                        if 'types' not in self._info['modules'][mod_name]:
                            self._info['modules'][mod_name]['types'] = []
                        self._info['modules'][mod_name]['types'].append(mod[1])
                    # Not sure if this branch will ever be hit, but added to see if above branches may need additional work
                    else:
                        if '__UNKNOWN__' not in self._info['modules'][mod_name]:
                            self._info['modules'][mod_name]['__UNKNOWN__'] = []
                        self._info['modules'][mod_name]['__UNKNOWN__'].append(':'.join(mod[1:]))

                # other system or junk tags
                if (not io_tag and ':' in name) or name.startswith('__'):
                    continue
                if tag['symbol_type'] & 0b0001_0000_0000_0000:
                    continue

                if program is not None:
                    name = f'Program:{program}.{name}'

                self._cache['tag_name:id'][name] = tag['instance_id']

                user_tags.append(_create_tag(name, tag))

            return user_tags
        except Exception as e:
            raise DataError(e)

    def _get_structure_makeup(self, instance_id):
        """
        get the structure makeup for a specific structure
        """
        if instance_id not in self._cache['id:struct']:
            request = self.new_request('send_unit_data')
            request.add(
                bytes([TAG_SERVICES_REQUEST['Get Attributes']]),
                b'\x03',  # path size
                CLASS_TYPE["8-bit"],  # Class id = 20 from spec 0x20
                CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
                INSTANCE_TYPE["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                pack_uint(instance_id),
                b'\x04\x00',  # Number of attributes
                b'\x04\x00',  # Template Object Definition Size UDINT
                b'\x05\x00',  # Template Structure Size UDINT
                b'\x02\x00',  # Template Member Count UINT
                b'\x01\x00',  # Structure Handle We can use this to read and write UINT
            )

            response = request.send()
            if not response:
                raise DataError(f"send_unit_data returned not valid data", response.error)
            _struct = _parse_structure_makeup_attributes(response)
            self._cache['id:struct'][instance_id] = _struct
            self._cache['handle:id'][_struct['structure_handle']] = instance_id

        return self._cache['id:struct'][instance_id]

    def _read_template(self, instance_id, object_definition_size):
        """ get a list of the tags in the plc

        """

        offset = 0
        template_raw = b''
        try:
            while True:
                request = self.new_request('send_unit_data')
                request.add(
                    bytes([TAG_SERVICES_REQUEST['Read Tag']]),
                    b'\x03',  # Request Path ( 20 6B 25 00 Instance )
                    CLASS_TYPE["8-bit"],  # Class id = 20 from spec
                    CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
                    INSTANCE_TYPE["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                    pack_uint(instance_id),
                    pack_dint(offset),  # Offset
                    pack_uint(((object_definition_size * 4) - 21) - offset)
                )
                response = request.send()

                if response.service_status not in (SUCCESS, INSUFFICIENT_PACKETS):
                    raise DataError('Error reading template', response)

                template_raw += response.data

                if response.service_status == SUCCESS:
                    break

                offset += len(response.data)

        except Exception:
            raise
        else:
            return template_raw

    def _parse_template_data(self, data, member_count):
        info_len = member_count * TEMPLATE_MEMBER_INFO_LEN
        info_data = data[:info_len]
        member_data = [self._parse_template_data_member_info(info)
                       for info in (info_data[i:i + TEMPLATE_MEMBER_INFO_LEN]
                                    for i in range(0, info_len, TEMPLATE_MEMBER_INFO_LEN))]
        member_names = []
        template_name = None
        try:
            for name in (x.decode(errors='replace') for x in data[info_len:].split(b'\x00') if len(x)):
                if template_name is None and ';' in name:
                    template_name, _ = name.split(';', maxsplit=1)
                else:
                    member_names.append(name)
        except (ValueError, UnicodeDecodeError):
            raise DataError(f'Unable to decode template or member names')

        predefine = template_name is None
        if predefine:
            template_name = member_names.pop(0)

        if template_name == 'ASCIISTRING82':  # internal name for STRING builtin type
            template_name = 'STRING'

        template = {
            'name': template_name,  # predefined types put name as first member (DWORD)
            'internal_tags': {},
            'attributes': []
        }

        for member, info in zip(member_names, member_data):
            if not member.startswith('ZZZZZZZZZZ') and not member.startswith('__'):
                template['attributes'].append(member)
            template['internal_tags'][member] = info

        if template['attributes'] == ['LEN', 'DATA'] and \
                template['internal_tags']['DATA']['data_type'] == 'SINT' and \
                template['internal_tags']['DATA'].get('array'):
            template['string'] = template['internal_tags']['DATA']['array']

        return template

    def _parse_template_data_member_info(self, info):
        type_info = unpack_uint(info[:2])
        typ = unpack_uint(info[2:4])
        member = {'offset': unpack_udint(info[4:])}
        tag_type = 'atomic'
        if typ in DATA_TYPE:
            data_type = DATA_TYPE[typ]
        else:
            instance_id = typ & 0b0000_1111_1111_1111
            if instance_id in DATA_TYPE:
                data_type = DATA_TYPE[instance_id]
            else:
                tag_type = 'struct'
                data_type = self._get_data_type(instance_id)

        member['tag_type'] = tag_type
        member['data_type'] = data_type

        if data_type == 'BOOL':
            member['bit'] = type_info
        elif data_type is not None:
            member['array'] = type_info

        return member

    def _get_data_type(self, instance_id):
        if instance_id not in self._cache['id:udt']:
            try:
                template = self._get_structure_makeup(instance_id)  # instance id from type
                if not template.get('Error'):
                    _data = self._read_template(instance_id, template['object_definition_size'])
                    data_type = self._parse_template_data(_data, template['member_count'])
                    data_type['template'] = template
                    self._cache['id:udt'][instance_id] = data_type
                    self._data_types[data_type['name']] = data_type
            except Exception:
                self.__log.exception('fuck')

        return self._cache['id:udt'][instance_id]

    @with_forward_open
    def read(self, *tags: str) -> ReturnType:
        """

        :param tags: one or many tags to read
        :return: one or many ``Tag`` objects
        """

        parsed_requests = self._parse_requested_tags(tags)
        requests = self._read_build_requests(parsed_requests)
        read_results = self._send_requests(requests)

        results = []

        for tag in tags:
            try:
                request_data = parsed_requests[tag]
                result = read_results[(request_data['plc_tag'], request_data['elements'])]
                if request_data.get('bit') is None:
                    results.append(result)
                else:
                    if result:
                        typ, bit = request_data['bit']
                        if typ == 'bit':
                            val = bool(result.value & (1 << bit))
                        else:
                            val = result.value[bit % 32]
                        results.append(Tag(tag, val, 'BOOL'))
                    else:
                        results.append(Tag(tag, None, None, result.error))
            except Exception as err:
                results.append(Tag(tag, None, None, f'Invalid tag request - {err}'))

        if len(tags) > 1:
            return results
        else:
            return results[0]

    def _read_build_requests(self, parsed_tags):
        if len(parsed_tags) == 1 or self._micro800:
            requests = (self._read_build_single_request(parsed_tags[tag]) for tag in parsed_tags)
            return [r for r in requests if r is not None]
        else:
            return self._read_build_multi_requests(parsed_tags)

    def _read_build_multi_requests(self, parsed_tags):
        """
        creates a list of multi-request packets
        """
        requests = []
        response_size = MULTISERVICE_READ_OVERHEAD
        current_request = self.new_request('multi_request')
        requests.append(current_request)
        tags_in_requests = set()
        for tag, tag_data in parsed_tags.items():
            if tag_data.get('error') is None and (tag_data['plc_tag'], tag_data['elements']) not in tags_in_requests:
                tags_in_requests.add((tag_data['plc_tag'], tag_data['elements']))
                return_size = _tag_return_size(tag_data)
                if return_size > self.connection_size:
                    _request = self.new_request('read_tag_fragmented')
                    _request.add(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                    requests.append(_request)
                else:
                    try:
                        return_size += 2  # add 2 bytes for offset list in reply
                        if response_size + return_size < self.connection_size:
                            if current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info']):
                                response_size += return_size
                            else:
                                response_size = return_size + MULTISERVICE_READ_OVERHEAD
                                current_request = self.new_request('multi_request')
                                current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                                requests.append(current_request)
                        else:
                            response_size = return_size + MULTISERVICE_READ_OVERHEAD
                            current_request = self.new_request('multi_request')
                            current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                            requests.append(current_request)
                    except RequestError:
                        self.__log.exception(f'Failed to build request for {tag} - skipping')
                        continue
            else:
                self.__log.error(f'Skipping making request for {tag}, error: {tag_data.get("error")}')
                continue

        return (r for r in requests if (r.type_ == 'multi' and r.tags) or r.type_ == 'read')

    def _read_build_single_request(self, parsed_tag):
        """
        creates a single read_tag request packet
        """

        if parsed_tag.get('error') is None:
            return_size = _tag_return_size(parsed_tag)
            if return_size > self.connection_size:
                request = self.new_request('read_tag_fragmented')
            else:
                request = self.new_request('read_tag')

            request.add(parsed_tag['plc_tag'], parsed_tag['elements'], parsed_tag['tag_info'])

            return request

        self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
        return None

    @with_forward_open
    def write(self, *tags_values: Tuple[str, TagType]) -> ReturnType:
        tags = (tag for (tag, value) in tags_values)
        parsed_requests = self._parse_requested_tags(tags)

        normal_tags = set()
        bit_tags = set()

        for tag, value in tags_values:
            parsed_requests[tag]['value'] = value

            if parsed_requests[tag].get('bit') is None:
                normal_tags.add(tag)
            else:
                bit_tags.add(tag)

        requests, bit_writes = self._write_build_requests(parsed_requests)
        write_results = self._send_requests(requests)
        results = []
        for tag, value in tags_values:
            try:
                request_data = parsed_requests[tag]
                bit = parsed_requests[tag].get('bit')
                result = write_results[(request_data['plc_tag'], request_data['elements'])]

                if request_data['elements'] > 1:
                    result = result._replace(type=f'{result.type}[{request_data["elements"]}]')
                if bit is not None:
                    result = result._replace(tag=tag, type='BOOL', value=value)
                else:
                    result = result._replace(tag=request_data['plc_tag'], value=value)
                results.append(result)
            except Exception as err:
                results.append(Tag(tag, None, None, f'Invalid tag request - {err}'))

        if len(tags_values) > 1:
            return results
        else:
            return results[0]

    def _write_build_requests(self, parsed_tags):
        bit_writes = {}
        if len(parsed_tags) == 1 or self._micro800:
            requests = (self._write_build_single_request(parsed_tags[tag], bit_writes) for tag in parsed_tags)
            return [r for r in requests if r is not None], bit_writes
        else:
            return self._write_build_multi_requests(parsed_tags, bit_writes), bit_writes

    def _write_build_multi_requests(self, parsed_tags, bit_writes):
        requests = []
        current_request = self.new_request('multi_request')
        requests.append(current_request)

        tags_in_requests = set()
        for tag, tag_data in parsed_tags.items():
            if tag_data.get('error') is None and (tag_data['plc_tag'], tag_data['elements']) not in tags_in_requests:
                tags_in_requests.add((tag_data['plc_tag'], tag_data['elements']))

                if _bit_request(tag_data, bit_writes):
                    continue

                tag_data['write_value'] = writable_value(tag_data)

                if len(tag_data['write_value']) > self.connection_size:
                    _request = self.new_request('write_tag_fragmented')
                    _request.add(tag_data['plc_tag'], tag_data['value'], tag_data['elements'], tag_data['tag_info'])
                    requests.append(_request)
                    continue

                try:
                    if not current_request.add_write(tag_data['plc_tag'], tag_data['write_value'], tag_data['elements'],
                                                     tag_data['tag_info']):
                        current_request = self.new_request('multi_request')
                        requests.append(current_request)
                        current_request.add_write(tag_data['plc_tag'], tag_data['write_value'], tag_data['elements'],
                                                  tag_data['tag_info'])

                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag} - skipping')
                    continue

        if bit_writes:
            for tag in bit_writes:
                try:
                    value = bit_writes[tag]['or_mask'], bit_writes[tag]['and_mask']
                    if not current_request.add_write(tag, value, tag_info=bit_writes[tag]['tag_info'], bits_write=True):
                        current_request = self.new_request('multi_request')
                        requests.append(current_request)
                        current_request.add_write(tag, value, tag_info=bit_writes[tag]['tag_info'], bits_write=True)
                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag} - skipping')
                    continue

        return (r for r in requests if (r.type_ == 'multi' and r.tags) or r.type_ == 'write')

    def _write_build_single_request(self, parsed_tag, bit_writes):
        if parsed_tag.get('error') is None:
            if not _bit_request(parsed_tag, bit_writes):
                parsed_tag['write_value'] = writable_value(parsed_tag)
                if len(parsed_tag['write_value']) > self.connection_size:
                    request = self.new_request('write_tag_fragmented')
                else:
                    request = self.new_request('write_tag')

                request.add(parsed_tag['plc_tag'], parsed_tag['write_value'], parsed_tag['elements'],
                            parsed_tag['tag_info'])
                return request
            else:
                try:
                    tag = parsed_tag['plc_tag']
                    value = bit_writes[tag]['or_mask'], bit_writes[tag]['and_mask']
                    request = self.new_request('write_tag')
                    request.add(tag, value, tag_info=bit_writes[tag]['tag_info'], bits_write=True)
                    return request
                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag} - skipping')
                    return None
        else:
            self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
            return None

    def _get_tag_info(self, base, attrs) -> Optional[dict]:

        def _recurse_attrs(attrs, data):
            cur, *remain = attrs
            curr_tag = _strip_array(cur)
            if not len(remain):
                return data.get(curr_tag)
            else:
                if curr_tag in data:
                    return _recurse_attrs(remain, data[curr_tag]['data_type']['internal_tags'])
                else:
                    return None
        try:
            data = self._tags.get(_strip_array(base))
            if not len(attrs):
                return data
            else:
                return _recurse_attrs(attrs, data['data_type']['internal_tags'])

        except Exception as err:
            self.__log.exception(f'Failed to lookup tag data for {base}, {attrs}')
            raise

    def _parse_requested_tags(self, tags):
        requests = {}
        for tag in tags:
            parsed = {}
            try:
                parsed_request = self._parse_tag_request(tag)
                if parsed_request is not None:
                    plc_tag, bit, elements, tag_info = parsed_request
                    parsed['plc_tag'] = plc_tag
                    parsed['bit'] = bit
                    parsed['elements'] = elements
                    parsed['tag_info'] = tag_info
                else:
                    parsed['error'] = 'Failed to parse tag request'
            except RequestError as err:
                parsed['error'] = str(err)

            finally:
                requests[tag] = parsed
        return requests

    def _parse_tag_request(self, tag: str) -> Optional[Tuple[str, Optional[int], int, dict]]:
        try:
            if tag.endswith('}') and '{' in tag:
                tag, _tmp = tag.split('{')
                elements = int(_tmp[:-1])
            else:
                elements = 1

            bit = None

            base, *attrs = tag.split('.')
            if base.startswith('Program:'):
                base = f'{base}.{attrs.pop(0)}'
            if len(attrs) and attrs[-1].isdigit():
                _bit = attrs.pop(-1)
                bit = ('bit', int(_bit))
                if not len(attrs):
                    tag = base
                else:
                    tag = f"{base}.{''.join(attrs)}"

            tag_info = self._get_tag_info(base, attrs)

            if tag_info['data_type'] == 'DWORD' and elements == 1:
                _tag, idx = _get_array_index(tag)
                tag = f'{_tag}[{idx // 32}]'
                bit = ('bool_array', idx)
                elements = 1

            return tag, bit, elements, tag_info

        except Exception as err:
            # something went wrong parsing the tag path
            raise RequestError('Failed to parse tag request', tag)

    def _send_requests(self, requests):

        def _mkkey(t=None, r=None):
            if t is not None:
                return t['tag'], t['elements']
            else:
                return r.tag, r.elements

        results = {}

        for request in requests:
            try:
                response = request.send()
            except Exception as err:
                self.__log.exception('Error sending request')
                if request.type_ != 'multi':
                    results[_mkkey(r=request)] = Tag(request.tag, None, None, str(err))
                else:
                    for tag in request.tags:
                        results[_mkkey(t=tag)] = Tag(tag['tag'], None, None, str(err))
            else:
                if request.type_ != 'multi':
                    if response:
                        results[_mkkey(r=request)] = Tag(request.tag,
                                                         response.value if request.type_ == 'read' else request.value,
                                                         response.data_type if request.type_ == 'read' else request.data_type)
                    else:
                        results[_mkkey(r=request)] = Tag(request.tag, None, None, response.error)
                else:
                    for tag in response.tags:
                        if tag['service_status'] == SUCCESS:
                            results[_mkkey(t=tag)] = Tag(tag['tag'], tag['value'], tag['data_type'])
                        else:
                            results[_mkkey(t=tag)] = Tag(tag['tag'], None, None,
                                                         tag.get('error', 'Unknown Service Error'))
        return results

    def get_plc_time(self, fmt: str='%A, %B %d, %Y %I:%M:%S%p') -> Tag:
        """
        Gets the current time of the PLC system clock. The ``value`` attribute will be a dict containing the time in
        3 different forms, *datetime* is a Python datetime.datetime object, *microseconds* is the integer value epoch time,
        and *string* is the *datetime* formatted using ``strftime`` and the ``fmt`` parameter.

        :param fmt: format string for converting the time to a string
        :return: a Tag object with the current time
        """
        tag = self.generic_read(class_code=CLASS_CODE['Wall-Clock Time'], instance=b'\x01', request_data=b'\x01\x00\x0B\x00',
                                data_format=[(None, 6), ('us', 'ULINT'), ])
        if tag:
            time = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=tag.value['us'])
            value = {'datetime': time, 'microseconds': tag.value['us'], 'string': time.strftime(fmt)}
        else:
            value = None
        return Tag('__GET_PLC_TIME__', value, error=tag.error)

    def set_plc_time(self, microseconds: Optional[int] = None) -> Tag:
        """
        Set the time of the PLC system clock.

        :param microseconds: None to use client PC clock, else timestamp in microseconds to set the PLC clock to
        :return: Tag with status of request
        """
        if microseconds is None:
            microseconds = int(time.time() * SEC_TO_US)

        request_data = b''.join([
            b'\x01\x00',  # attribute count
            b'\x06\x00',  # attribute
            pack_ulint(microseconds),
        ])
        return self.generic_write(b'\x04', CLASS_CODE['Wall-Clock Time'], b'\x01',
                                  request_data=request_data, name='__SET_PLC_TIME__')

    def generic_read(self, class_code: bytes, instance: bytes, request_data: bytes = None,
                     data_format: DataFormatType = None, name: str = 'generic',
                     service=bytes([TAG_SERVICES_REQUEST['Get Attributes']]),
                     connected=True, unconnected_send=False) -> Tag:

        _req = 'generic_read' if connected else 'generic_read_unconnected'

        if connected:
            with_forward_open(lambda _: None)(self)

        request = self.new_request(_req, service, class_code, instance, request_data, data_format, unconnected_send)
        response = request.send()

        return Tag(name, response.value, error=response.error)

    def generic_write(self, service, class_code, instance, request_data: bytes, name: str = 'generic',
                      connected=True, unconnected_send=False) -> Tag:

        _req = 'generic_write' if connected else 'generic_write_unconnected'

        if connected:
            with_forward_open(lambda _: None)(self)

        request = self.new_request(_req, service, class_code, instance, request_data, unconnected_send)
        response = request.send()
        return Tag(name, request_data, error=response.error)


def _parse_plc_name(response):
    if response.service_status != SUCCESS:
        raise DataError(f'get_plc_name returned status {get_service_status(response.error)}')
    try:
        name_len = unpack_uint(response.data[6:8])
        name = response.data[8: 8 + name_len].decode()
        return name
    except Exception as err:
        raise DataError(err)


def _parse_plc_info(data):
    parsed = {k: v for k, v in data.items() if not k.startswith('_')}
    parsed['vendor'] = VENDORS.get(parsed['vendor'], 'UNKNOWN')
    parsed['product_type'] = PRODUCT_TYPES.get(parsed['product_type'], 'UNKNOWN')
    parsed['revision'] = f"{parsed['version_major']}.{parsed['version_minor']}"
    parsed['serial'] = f"{parsed['serial']:08x}"
    parsed['keyswitch'] = KEYSWITCH.get(data['_keyswitch'][0], {}).get(data['_keyswitch'][1], 'UNKNOWN')

    return parsed


def _parse_identity_object(reply):
    vendor = unpack_uint(reply[:2])
    product_type = unpack_uint(reply[2:4])
    product_code = unpack_uint(reply[4:6])
    major_fw = int(reply[6])
    minor_fw = int(reply[7])
    status = f'{unpack_uint(reply[8:10]):0{16}b}'
    serial_number = f'{unpack_udint(reply[10:14]):0{8}x}'
    product_name_len = int(reply[14])
    tmp = 15 + product_name_len
    device_type = reply[15:tmp].decode()

    state = unpack_uint(reply[tmp:tmp + 4]) if reply[tmp:] else -1  # some modules don't return a state

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


def _parse_structure_makeup_attributes(response):
        """ extract the tags list from the message received"""
        structure = {}

        if response.service_status != SUCCESS:
            structure['Error'] = response.service_status
            return

        attribute = response.data
        idx = 4
        try:
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                structure['object_definition_size'] = unpack_dint(attribute[idx:idx + 4])
            else:
                structure['Error'] = 'object_definition Error'
                return structure

            idx += 6
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                structure['structure_size'] = unpack_dint(attribute[idx:idx + 4])
            else:
                structure['Error'] = 'structure Error'
                return structure

            idx += 6
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                structure['member_count'] = unpack_uint(attribute[idx:idx + 2])
            else:
                structure['Error'] = 'member_count Error'
                return structure

            idx += 4
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                structure['structure_handle'] = unpack_uint(attribute[idx:idx + 2])
            else:
                structure['Error'] = 'structure_handle Error'
                return structure

            return structure

        except Exception as e:
            raise DataError(e)


def writable_value(parsed_tag):
    if isinstance(parsed_tag['value'], bytes):
        return parsed_tag['value']

    try:
        value = parsed_tag['value']
        elements = parsed_tag['elements']
        data_type = parsed_tag['tag_info']['data_type']

        if elements > 1:
            if len(value) < elements:
                raise RequestError('Insufficient data for requested elements')
            if len(value) > elements:
                value = value[:elements]

        if parsed_tag['tag_info']['tag_type'] == 'struct':
            return _writable_value_structure(value, elements, data_type)
        else:
            pack_func = PACK_DATA_FUNCTION[data_type]

            if elements > 1:
                return b''.join(pack_func(value[i]) for i in range(elements))
            else:
                return pack_func(value)
    except Exception as err:
        raise RequestError('Unable to create a writable value', err)


def _strip_array(tag):
    if '[' in tag:
        return tag[:tag.find('[')]
    return tag


def _get_array_index(tag):
    if tag.endswith(']') and '[' in tag:
        tag, _tmp = tag.split('[')
        idx = int(_tmp[:-1])
    else:
        idx = 0

    return tag, idx


def _tag_return_size(tag_data):
    tag_info = tag_data['tag_info']
    if tag_info['tag_type'] == 'atomic':
        size = DATA_TYPE_SIZE[tag_info['data_type']]
    else:
        size = tag_info['data_type']['template']['structure_size']

    size = (size * tag_data['elements']) + READ_RESPONSE_OVERHEAD  # account for service overhead

    return size


def _writable_value_structure(value, elements, data_type):
    if elements > 1:
        return b''.join(_pack_structure(val, data_type) for val in value)
    else:
        return _pack_structure(value, data_type)


def _pack_string(value, string_len):
    sint_array = [b'\x00' for _ in range(string_len)]
    if len(value) > string_len:
        value = value[:string_len]
    for i, s in enumerate(value):
        sint_array[i] = pack_char(s)

    return pack_dint(len(value)) + b''.join(sint_array)


def _pack_structure(val, data_type):
    string_len = data_type.get('string')
    if string_len is None:
        raise NotImplementedError('Writing of structures besides strings is not supported')

    if string_len:
        packed_bytes = _pack_string(val, string_len)
    else:
        packed_bytes = b''  # TODO: support for structure writing here

    return packed_bytes + b'\x00' * (len(packed_bytes) % 4)  # pad data to 4-byte boundaries


def _bit_request(tag_data, bit_requests):
    if tag_data.get('bit') is None:
        return None

    if tag_data['plc_tag'] not in bit_requests:
        bit_requests[tag_data['plc_tag']] = {'and_mask': 0xFFFFFFFF,
                                             'or_mask': 0x00000000,
                                             'bits': [],
                                             'tag_info': tag_data['tag_info']}

    bits_ = bit_requests[tag_data['plc_tag']]
    typ_, bit = tag_data['bit']
    bits_['bits'].append(bit)

    if typ_ == 'bool_array':
        bit = bit % 32

    if tag_data['value']:
        bits_['or_mask'] |= (1 << bit)
    else:
        bits_['and_mask'] &= ~(1 << bit)

    return True


def _parse_connection_path(path, micro800):
    ip, *segments = path.split('/')
    try:
        socket.inet_aton(ip)
    except OSError:
        raise ValueError('Invalid IP Address', ip)
    segments = [_parse_path_segment(s) for s in segments]

    if not segments:
        if not micro800:
            _path = [pack_usint(PATH_SEGMENTS['backplane']), b'\x00']  # default backplane/0
        else:
            _path = []
    elif len(segments) == 1:
        _path = [pack_usint(PATH_SEGMENTS['backplane']), pack_usint(segments[0])]
    else:
        pairs = (segments[i:i + 2] for i in range(0, len(segments), 2))
        _path = []
        for port, dest in pairs:
            if isinstance(dest, bytes):
                port |= 1 << 4  # set Extended Link Address bit, CIP Vol 1 C-1.3
                dest_len = len(dest)
                if dest_len % 2:
                    dest += b'\x00'
                _path.extend([pack_usint(port), pack_usint(dest_len), dest])
            else:
                _path.extend([pack_usint(port), pack_usint(dest)])

    _path += [
        CLASS_TYPE['8-bit'],
        CLASS_CODE['Message Router'],
        INSTANCE_TYPE['8-bit'],
        b'\x01'
    ]

    _path_bytes = b''.join(_path)

    if len(_path_bytes) % 2:
        _path_bytes += b'\x00'

    return ip, pack_usint(len(_path_bytes) // 2) + _path_bytes


def _parse_path_segment(segment: str):
    try:
        if segment.isnumeric():
            return int(segment)
        else:
            tmp = PATH_SEGMENTS.get(segment.lower())
            if tmp:
                return tmp
            else:
                try:
                    socket.inet_aton(segment)
                    return b''.join(pack_usint(ord(c)) for c in segment)
                except OSError:
                    raise ValueError('Invalid IP Address Segment', segment)
    except Exception:
        raise ValueError(f'Failed to parse path segment', segment)


def _create_tag(name, raw_tag):

    new_tag = {
        'tag_name': name,
        'dim': (raw_tag['symbol_type'] & 0b0110000000000000) >> 13,  # bit 13 & 14, number of array dims
        'instance_id': raw_tag['instance_id'],
        'symbol_address': raw_tag['symbol_address'],
        'symbol_object_address': raw_tag['symbol_object_address'],
        'software_control': raw_tag['software_control'],
        'alias': False if raw_tag['software_control'] & BASE_TAG_BIT else True,
        'external_access': raw_tag['external_access'],
        'dimensions': raw_tag['dimensions']
    }

    if raw_tag['symbol_type'] & 0b_1000_0000_0000_0000:  # bit 15, 1 = struct, 0 = atomic
        template_instance_id = raw_tag['symbol_type'] & 0b_0000_1111_1111_1111
        new_tag['tag_type'] = 'struct'
        new_tag['template_instance_id'] = template_instance_id
    else:
        new_tag['tag_type'] = 'atomic'
        datatype = raw_tag['symbol_type'] & 0b_0000_0000_1111_1111
        new_tag['data_type'] = DATA_TYPE[datatype]
        if datatype == DATA_TYPE['BOOL']:
            new_tag['bit_position'] = (raw_tag['symbol_type'] & 0b_0000_0111_0000_0000) >> 8

    return new_tag
