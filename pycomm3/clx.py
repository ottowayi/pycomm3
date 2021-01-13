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

__all__ = ['LogixDriver', ]

import datetime
import itertools
import logging
import time
from typing import List, Tuple, Optional, Union, Mapping, Dict

from . import util
from .exceptions import DataError, CommError, RequestError
from .tag import Tag
from .bytes_ import Pack, Unpack
from .cip_base import CIPDriver, with_forward_open
from .const import (EXTENDED_SYMBOL, CLASS_TYPE, INSTANCE_TYPE, ClassCode, DataType, PRODUCT_TYPES, VENDORS,
                    MICRO800_PREFIX, MULTISERVICE_READ_OVERHEAD, Services, SUCCESS, ELEMENT_TYPE,
                    INSUFFICIENT_PACKETS, BASE_TAG_BIT, MIN_VER_INSTANCE_IDS, SEC_TO_US, KEYSWITCH,
                    TEMPLATE_MEMBER_INFO_LEN, EXTERNAL_ACCESS, DataTypeSize, MIN_VER_EXTERNAL_ACCESS, )
from .packets import request_path, encode_segment, RequestTypes

AtomicValueType = Union[int, float, bool, str]
TagValueType = Union[AtomicValueType, List[AtomicValueType], Dict[str, 'TagValueType']]
ReadWriteReturnType = Union[Tag, List[Tag]]


class LogixDriver(CIPDriver):
    """
    An Ethernet/IP Client driver for reading and writing tags in ControlLogix and CompactLogix PLCs.
    """
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, path: str, *args,  micro800: bool = False,
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

        super().__init__(path, *args, **kwargs)
        self._cache = None
        self._data_types = {}
        self._tags = {}
        self._micro800 = micro800
        self._cfg['use_instance_ids'] = True

        if init_tags or init_info:
            self.open()

        if init_info:
            target_identity = self._list_identity()
            self._micro800 = target_identity.get('product_name', '').startswith(MICRO800_PREFIX)
            self.get_plc_info()

            self.use_instance_ids = (self.info.get('version_major', 0) >= MIN_VER_INSTANCE_IDS) and not self._micro800
            if not self._micro800:
                self.get_plc_name()

        if self._micro800:  # strip off backplane/0 from path, not used for these processors
            _path = Pack.epath(self._cfg['cip_path'][:-2])
            self._cfg['cip_path'] = _path[1:]  # leave out the len, we sometimes add to the path later

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
    def use_instance_ids(self):
        return self._cfg['use_instance_ids']

    @use_instance_ids.setter
    def use_instance_ids(self, value):
        self._cfg['use_instance_ids'] = value

    @with_forward_open
    def get_plc_name(self) -> str:
        """
        Requests the name of the program running in the PLC. Uses KB `23341`_ for implementation.

        .. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

        :return:  the controller program name
        """
        try:
            response = self.generic_message(
                service=Services.get_attribute_list,
                class_code=ClassCode.program_name,
                instance=b'\x01\x00',  # instance 1
                request_data=b'\x01\x00\x01\x00',  # num attributes, attribute 1 (program name)
                data_format=((None, 6), ('program_name', 'STRING')),
            )
            if response:
                self._info['name'] = response.value['program_name']
                return self._info['name']
            else:
                raise DataError(f'response did not return valid data - {response.error}')

        except Exception as err:
            raise DataError('failed to get the plc name') from err

    def get_plc_info(self) -> dict:
        """
        Reads basic information from the controller, returns it and stores it in the ``info`` property.
        """
        try:
            response = self.generic_message(
                class_code=ClassCode.identity_object, instance=b'\x01',
                service=Services.get_attributes_all,
                data_format=[
                    ('vendor', 'UINT'), ('product_type', 'UINT'), ('product_code', 'UINT'),
                    ('version_major', 'SINT'), ('version_minor', 'USINT'), ('_keyswitch', 2),
                    ('serial', 'UDINT'), ('device_type', 'SHORT_STRING')
                ],
                connected=False, unconnected_send=not self._micro800)

            if response:
                info = _parse_plc_info(response.value)
                self._info = {**self._info, **info}
                return info
            else:
                raise DataError(f'get_plc_info did not return valid data - {response.error}')

        except Exception as err:
            raise DataError('Failed to get PLC info') from err

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
                tag['data_type_name'] = tag['data_type']['name']

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
                    path = [EXTENDED_SYMBOL, Pack.usint(len(program)), program.encode('utf-8')]
                    if len(program) % 2:
                        path.append(b'\x00')

                # just manually build the request path b/c there my be the extended symbol portion
                path += [
                    # Request Path ( 20 6B 25 00 Instance )
                    CLASS_TYPE["8-bit"],  # Class id = 20 from spec 0x20
                    ClassCode.symbol_object,  # Logical segment: Symbolic Object 0x6B
                    INSTANCE_TYPE["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                    Pack.uint(last_instance),  # The instance
                ]
                path = b''.join(path)
                path_size = Pack.usint(len(path) // 2)
                request = RequestTypes.send_unit_data(self)

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
                    Services.get_instance_attribute_list,
                    path_size,
                    path,
                    Pack.uint(len(attributes)),
                    *attributes

                )
                response = request.send()
                if not response:
                    raise DataError(f"send_unit_data returned not valid data - {response.error}")

                last_instance = self._parse_instance_attribute_list(response, tag_list)
            return tag_list

        except Exception as err:
            raise DataError('failed to get attribute list') from err

    def _parse_instance_attribute_list(self, response, tag_list):
        """ extract the tags list from the message received"""

        tags_returned = response.data
        tags_returned_length = len(tags_returned)
        idx = count = instance = 0
        try:
            while idx < tags_returned_length:
                instance = Unpack.dint(tags_returned[idx:idx + 4])
                idx += 4
                tag_length = Unpack.uint(tags_returned[idx:idx + 2])
                idx += 2
                tag_name = tags_returned[idx:idx + tag_length]
                idx += tag_length
                symbol_type = Unpack.uint(tags_returned[idx:idx + 2])
                idx += 2
                count += 1
                symbol_address = Unpack.udint(tags_returned[idx:idx + 4])
                idx += 4
                symbol_object_address = Unpack.udint(tags_returned[idx:idx + 4])
                idx += 4
                software_control = Unpack.udint(tags_returned[idx:idx + 4])
                idx += 4

                dim1 = Unpack.udint(tags_returned[idx:idx + 4])
                idx += 4
                dim2 = Unpack.udint(tags_returned[idx:idx + 4])
                idx += 4
                dim3 = Unpack.udint(tags_returned[idx:idx + 4])
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

        except Exception as err:
            raise DataError('failed to parse instance attribute list') from err

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
        except Exception as err:
            raise DataError('failed isolating user tags') from err

    def _get_structure_makeup(self, instance_id):
        """
        get the structure makeup for a specific structure
        """
        if instance_id not in self._cache['id:struct']:
            request = RequestTypes.send_unit_data(self)
            req_path = request_path(ClassCode.template_object, Pack.uint(instance_id))
            request.add(
                Services.get_attribute_list,
                req_path,

                # service data:
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
                request = RequestTypes.send_unit_data(self)
                req_path = request_path(ClassCode.template_object, instance=Pack.uint(instance_id))
                request.add(
                    Services.read_tag,
                    req_path,
                    # service data:
                    Pack.dint(offset),
                    Pack.uint(((object_definition_size * 4) - 21) - offset)
                )
                response = request.send()

                if response.service_status not in (SUCCESS, INSUFFICIENT_PACKETS):
                    raise DataError('Error reading template', response)

                template_raw += response.data

                if response.service_status == SUCCESS:
                    break

                offset += len(response.data)

        except Exception as err:
            raise DataError('Failed to read template') from err
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
        except (ValueError, UnicodeDecodeError) as err:
            raise DataError(f'Unable to decode template or member names') from err

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
            if not (member.startswith('ZZZZZZZZZZ') or member.startswith('__')):
                template['attributes'].append(member)
            template['internal_tags'][member] = info

        if template['attributes'] == ['LEN', 'DATA'] and \
                template['internal_tags']['DATA']['data_type'] == 'SINT' and \
                template['internal_tags']['DATA'].get('array'):
            template['string'] = template['internal_tags']['DATA']['array']

        return template

    def _parse_template_data_member_info(self, info):
        type_info = Unpack.uint(info[:2])
        typ = Unpack.uint(info[2:4])
        member = {'offset': Unpack.udint(info[4:])}
        tag_type = 'atomic'

        data_type = DataType.get(typ)
        if data_type is None:
            instance_id = typ & 0b0000_1111_1111_1111
            data_type = DataType.get(instance_id)
        if data_type is None:
            tag_type = 'struct'
            data_type = self._get_data_type(instance_id)

        member['tag_type'] = tag_type
        member['data_type'] = data_type
        member['data_type_name'] = data_type['name'] if tag_type == 'struct' else data_type

        if data_type == 'BOOL':
            member['bit'] = type_info
        elif data_type is not None:
            member['array'] = type_info

        return member

    def _get_data_type(self, instance_id):
        if instance_id not in self._cache['id:udt']:
            try:
                template = self._get_structure_makeup(instance_id)  # instance id from type
                if not template.get('error'):
                    _data = self._read_template(instance_id, template['object_definition_size'])
                    data_type = self._parse_template_data(_data, template['member_count'])
                    data_type['template'] = template
                    self._cache['id:udt'][instance_id] = data_type
                    self._data_types[data_type['name']] = data_type
            except Exception as err:
                raise DataError('Failed to get data type information') from err

        return self._cache['id:udt'][instance_id]

    @with_forward_open
    def read(self, *tags: str) -> ReadWriteReturnType:
        """
        Read the value of tag(s).  Automatically will split tags into multiple requests by tracking the request and
        response size.  Will use the multi-service request to group many tags into a single packet and also will automatically
        use fragmented read requests if the response size will not fit in a single packet.  Supports arrays (specify element
        count in using curly braces (array{10}).  Also supports full structure reading (when possible), return value
        will be a dict of {attribute name: value}.

        :param tags: one or many tags to read
        :return: a single or list of ``Tag`` objects
        """

        parsed_requests = self._parse_requested_tags(tags)
        requests = self._read_build_requests(parsed_requests)
        read_results = self._send_requests(requests)

        results = []

        for i, tag in enumerate(tags):
            try:
                request_data = parsed_requests[i]
                if request_data.get('error'):
                    results.append(Tag(tag, None, None, request_data['error']))
                    continue

                result = read_results[i]
                if request_data.get('bit') is None:
                    results.append(result)
                else:
                    if result:
                        typ, bit = request_data['bit']
                        val = bool(result.value & 1 << bit) if typ == 'bit' else result.value[bit % 32]
                        results.append(Tag(tag, val, 'BOOL', None))
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
            requests = (self._read_build_single_request(parsed_tags[request_id]) for request_id in parsed_tags)
            return [r for r in requests if r is not None]
        else:
            return self._read_build_multi_requests(parsed_tags)

    def _read_build_multi_requests(self, parsed_tags):
        """
        creates a list of multi-request packets
        """
        requests = []
        response_size = MULTISERVICE_READ_OVERHEAD
        current_request = RequestTypes.multi_request(self)
        requests.append(current_request)
        for request_id, tag_data in parsed_tags.items():
            if tag_data.get('error') is None:
                return_size = _tag_return_size(tag_data) + len(tag_data['rp']) + 4  # 4 = DINT element count
                if return_size > self.connection_size:
                    _request = RequestTypes.read_tag_fragmented(self)
                    _request.add(tag_data['plc_tag'], tag_data['rp'], tag_data['elements'],
                                 tag_data['tag_info'], request_id)
                    requests.append(_request)
                else:
                    try:
                        return_size += 2  # add 2 bytes for offset list in reply
                        if response_size + return_size < self.connection_size:
                            if current_request.add_read(tag_data['plc_tag'], tag_data['rp'], tag_data['elements'],
                                                        tag_data['tag_info'], request_id):
                                response_size += return_size
                            else:
                                response_size = return_size + MULTISERVICE_READ_OVERHEAD
                                current_request = RequestTypes.multi_request(self)
                                current_request.add_read(tag_data['plc_tag'], tag_data['rp'], tag_data['elements'],
                                                         tag_data['tag_info'], request_id)
                                requests.append(current_request)
                        else:
                            response_size = return_size + MULTISERVICE_READ_OVERHEAD
                            current_request = RequestTypes.multi_request(self)
                            current_request.add_read(tag_data['plc_tag'], tag_data['rp'], tag_data['elements'],
                                                     tag_data['tag_info'], request_id)
                            requests.append(current_request)
                    except RequestError:
                        self.__log.exception(f'Failed to build request for {tag_data["request_tag"]} - skipping')
                        continue
            else:
                self.__log.error(f'Skipping making request for {tag_data["request_tag"]}, error: {tag_data.get("error")}')
                continue

        return (r for r in requests if (r.type_ == 'multi' and r.tags) or r.type_ == 'read')

    def _read_build_single_request(self, parsed_tag):
        """
        creates a single read_tag request packet
        """

        if parsed_tag.get('error') is None:
            return_size = _tag_return_size(parsed_tag) + len(parsed_tag['rp']) + 4  # 4 = DINT element count
            if return_size > self.connection_size:
                request = RequestTypes.read_tag_fragmented(self)
            else:
                request = RequestTypes.read_tag(self)

            request.add(parsed_tag['plc_tag'], parsed_tag['rp'], parsed_tag['elements'],
                        parsed_tag['tag_info'], parsed_tag['request_id'])

            return request

        self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
        return None

    @with_forward_open
    def write(self, *tags_values: Tuple[str, TagValueType]) -> ReadWriteReturnType:
        """
        Write to tag(s). Automatically will split tags into multiple requests by tracking the request and
        response size.  Will use the multi-service request to group many tags into a single packet and also will automatically
        use fragmented read requests if the response size will not fit in a single packet.  Supports arrays (specify element
        count in using curly braces (array{10}).  Also supports full structure writing (when possible), value must be a
        sequence of values or a dict of {attribute: value} matching the exact structure of the destination tag.

        :param tags_values: one or many 2-element tuples (tag name, value)
        :return: a single or list of ``Tag`` objects.
        """
        tags = (tag for (tag, value) in tags_values)
        parsed_requests = self._parse_requested_tags(tags)

        for i, (tag, value) in enumerate(tags_values):
            parsed_requests[i]['value'] = value

        requests, bit_writes = self._write_build_requests(parsed_requests)
        write_results = self._send_requests(requests)

        for bw in bit_writes:   # restore original request ids that were handled by a bits write
            bit_request_id = bit_writes[bw]['request_id']
            result = write_results.pop(bit_request_id)
            for req_id in bit_writes[bw]['request_ids']:
                write_results[req_id] = result

        results = []
        for i, (tag, value) in enumerate(tags_values):
            try:
                request_data = parsed_requests[i]
                if request_data.get('error'):
                    results.append(Tag(tag, None, None, request_data['error']))
                    continue
                    
                bit = parsed_requests[i].get('bit')
                result = write_results[i]
                data_type = request_data['tag_info']['data_type_name']
                if bit is not None:
                    data_type = 'BOOL'
                elif data_type == 'DWORD':
                    data_type = f'BOOL[{request_data["elements"] * 32}]'
                elif request_data['elements'] > 1:
                    data_type = f'{data_type}[{request_data["elements"]}]'

                tag_name = tag if bit is not None else request_data['plc_tag']

                user_result = Tag(tag_name, value, data_type, result.error)

                results.append(user_result)
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
        current_request = RequestTypes.multi_request(self)
        requests.append(current_request)

        for request_id, tag_data in parsed_tags.items():
            if tag_data.get('error') is None:

                if _bit_request(tag_data, bit_writes):
                    continue

                tag_data['write_value'] = writable_value(tag_data)
                req_size = len(tag_data['write_value']) + len(tag_data['rp']) + 4
                if req_size > self.connection_size:
                    _request = RequestTypes.write_tag_fragmented(self)
                    _request.add(tag_data['plc_tag'], tag_data['rp'], tag_data['write_value'], tag_data['elements'],
                                 tag_data['tag_info'], request_id)
                    requests.append(_request)
                    continue

                try:
                    if not current_request.add_write(tag_data['plc_tag'], tag_data['rp'], tag_data['write_value'],
                                                     tag_data['elements'], tag_data['tag_info'], request_id):

                        current_request = RequestTypes.multi_request(self)
                        requests.append(current_request)
                        current_request.add_write(tag_data['plc_tag'], tag_data['rp'], tag_data['write_value'],
                                                  tag_data['elements'], tag_data['tag_info'], request_id)

                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag_data["request_tag"]} - skipping')
                    continue

        if bit_writes:
            for i, tag in enumerate(bit_writes):
                try:
                    # multiple requests are merged into a single request for bit writes
                    # so create a new request_id for those and then we'll restore the original ones later
                    _request_id = f'bit-write-{i}'
                    bit_writes[tag]['request_id'] = _request_id
                    value = bit_writes[tag]['or_mask'], bit_writes[tag]['and_mask']
                    rp = tag_request_path(tag, self._tags, self.use_instance_ids)
                    if not current_request.add_write(tag, rp, value, 1, bit_writes[tag]['tag_info'],
                                                     _request_id, bits_write=True):
                        current_request = RequestTypes.multi_request(self)
                        requests.append(current_request)
                        current_request.add_write(tag, rp, value, 1, bit_writes[tag]['tag_info'],
                                                  _request_id, bits_write=True)
                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag} - skipping')
                    continue

        return (r for r in requests if (r.type_ == 'multi' and r.tags) or r.type_ == 'write')

    def _write_build_single_request(self, parsed_tag, bit_writes):
        if parsed_tag.get('error') is None:
            if not _bit_request(parsed_tag, bit_writes):
                parsed_tag['write_value'] = writable_value(parsed_tag)
                req_size = len(parsed_tag['write_value']) + len(parsed_tag['rp']) + 4
                if req_size > self.connection_size:
                    request = RequestTypes.write_tag_fragmented(self)
                else:
                    request = RequestTypes.write_tag(self)

                request.add(parsed_tag['plc_tag'],
                            parsed_tag['rp'],
                            parsed_tag['write_value'],
                            parsed_tag['elements'],
                            parsed_tag['tag_info'],
                            parsed_tag['request_id'])
                return request
            else:
                try:
                    tag = parsed_tag['plc_tag']
                    request_id = f'bit-write-0'
                    bit_writes[tag]['request_id'] = request_id
                    value = bit_writes[tag]['or_mask'], bit_writes[tag]['and_mask']
                    request = RequestTypes.write_tag(self)
                    rp = tag_request_path(tag, self._tags, self.use_instance_ids)
                    request.add(tag, rp, value, 1, bit_writes[tag]['tag_info'], request_id,
                                bits_write=True)
                    return request
                except RequestError:
                    self.__log.exception(f'Failed to build request for {tag} - skipping')
                    return None
        else:
            self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
            return None

    def get_tag_info(self, tag_name: str) -> Optional[dict]:
        """
        Returns the tag information for a tag collected during the tag list upload.  Can be a base tag or an attribute.

        :param tag_name: name of tag to get info for
        :return: a dict of the tag's definition

        """
        base, *attrs = tag_name.split('.')
        return self._get_tag_info(base, attrs)

    def _get_tag_info(self, base, attrs) -> Optional[dict]:

        def _recurse_attrs(attrs, data):
            cur, *remain = attrs
            curr_tag = util.strip_array(cur)
            if not len(remain):
                return data[curr_tag]
            else:
                if curr_tag in data:
                    return _recurse_attrs(remain, data[curr_tag]['data_type']['internal_tags'])
                else:
                    return None
        try:
            data = self._tags[util.strip_array(base)]
            if not len(attrs):
                return data
            else:
                return _recurse_attrs(attrs, data['data_type']['internal_tags'])

        except KeyError as err:
            raise RequestError(f"Tag doesn't exist - {err.args[0]}")

        except Exception as err:
            _msg = f"failed to get tag data for: {base}, {attrs}"
            self.__log.exception(_msg)
            raise RequestError(_msg) from err

    def _parse_requested_tags(self, tags):
        requests = {}
        for i, tag in enumerate(tags):
            parsed = {
                'request_id': i,
                'request_tag': tag
            }
            try:
                parsed_request = self._parse_tag_request(tag)
                if parsed_request is not None:
                    plc_tag, bit, elements, tag_info = parsed_request
                    parsed['plc_tag'] = plc_tag
                    parsed['bit'] = bit
                    parsed['elements'] = elements
                    parsed['tag_info'] = tag_info
                    rp = tag_request_path(plc_tag, self._tags, self.use_instance_ids)
                    parsed['rp'] = rp
                    if rp is None:
                        parsed['error'] = 'Failed to create request path'
                else:
                    parsed['error'] = 'Failed to parse tag request'

            except RequestError as err:
                parsed['error'] = str(err)

            finally:
                requests[i] = parsed
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
                tag = base if not len(attrs) else f"{base}.{''.join(attrs)}"
            tag_info = self._get_tag_info(base, attrs)

            if tag_info['data_type'] == 'DWORD' and elements == 1:
                _tag, idx = util.get_array_index(tag)
                tag = f'{_tag}[{idx // 32}]'
                bit = ('bool_array', idx)

            return tag, bit, elements, tag_info
        except RequestError:
            raise
        except Exception as err:
            raise RequestError('Failed to parse tag request', tag) from err

    def _send_requests(self, requests):
        results = {}

        for request in requests:
            try:
                response = request.send()
            except (RequestError, DataError) as err:
                self.__log.exception('Error sending request')
                if request.type_ != 'multi':
                    results[request.request_id] = Tag(request.tag, None, None, str(err))
                else:
                    for tag in request.tags:
                        results[tag['request_id']] = Tag(tag['tag'], None, None, str(err))
            else:
                if request.type_ != 'multi':
                    if response:
                        results[request.request_id] = Tag(request.tag,
                                                         response.value if request.type_ == 'read' else request.value,
                                                         response.data_type if request.type_ == 'read' else request.data_type,
                                                         response.error)
                    else:
                        results[request.request_id] = Tag(request.tag, None, None, response.error)
                else:
                    for tag in response.tags:
                        if tag['service_status'] == SUCCESS:
                            results[tag['request_id']] = Tag(tag['tag'], tag['value'], tag['data_type'], None)
                        else:
                            results[tag['request_id']] = Tag(tag['tag'], None, None,
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
        tag = self.generic_message(
            service=Services.get_attribute_list,
            class_code=ClassCode.wall_clock_time,
            instance=b'\x01',
            request_data=b'\x01\x00\x0B\x00',
            data_format=[(None, 6), ('us', 'ULINT'), ]
        )
        if tag:
            _time = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=tag.value['us'])
            value = {'datetime': _time, 'microseconds': tag.value['us'], 'string': _time.strftime(fmt)}
        else:
            value = None
        return Tag('__GET_PLC_TIME__', value, None, error=tag.error)

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
            Pack.ulint(microseconds),
        ])
        return self.generic_message(
            service=Services.set_attribute_list,
            class_code=ClassCode.wall_clock_time,
            instance=b'\x01',
            request_data=request_data, name='__SET_PLC_TIME__'
        )


def _parse_plc_info(data):
    parsed = {k: v for k, v in data.items() if not k.startswith('_')}
    parsed['vendor'] = VENDORS.get(parsed['vendor'], 'UNKNOWN')
    parsed['product_type'] = PRODUCT_TYPES.get(parsed['product_type'], 'UNKNOWN')
    parsed['revision'] = f"{parsed['version_major']}.{parsed['version_minor']}"
    parsed['serial'] = f"{parsed['serial']:08x}"
    parsed['keyswitch'] = KEYSWITCH.get(data['_keyswitch'][0], {}).get(data['_keyswitch'][1], 'UNKNOWN')

    return parsed


def _parse_structure_makeup_attributes(response):
    """
    extract the tags list from the message received
    """
    structure = {}

    if response.service_status != SUCCESS:
        structure['error'] = response.service_status
        return

    attribute = response.data
    idx = 4
    try:
        if Unpack.uint(attribute[idx:idx + 2]) == SUCCESS:
            idx += 2
            structure['object_definition_size'] = Unpack.dint(attribute[idx:idx + 4])
        else:
            structure['error'] = 'object_definition Error'
            return structure

        idx += 6
        if Unpack.uint(attribute[idx:idx + 2]) == SUCCESS:
            idx += 2
            structure['structure_size'] = Unpack.dint(attribute[idx:idx + 4])
        else:
            structure['error'] = 'structure Error'
            return structure

        idx += 6
        if Unpack.uint(attribute[idx:idx + 2]) == SUCCESS:
            idx += 2
            structure['member_count'] = Unpack.uint(attribute[idx:idx + 2])
        else:
            structure['error'] = 'member_count Error'
            return structure

        idx += 4
        if Unpack.uint(attribute[idx:idx + 2]) == SUCCESS:
            idx += 2
            structure['structure_handle'] = Unpack.uint(attribute[idx:idx + 2])
        else:
            structure['error'] = 'structure_handle Error'
            return structure

        return structure

    except Exception as err:
        raise DataError('failed to parse structure attributes') from err


def writable_value(parsed_tag: dict) -> bytes:
    if isinstance(parsed_tag['value'], bytes):
        return parsed_tag['value']

    try:
        value = parsed_tag['value']
        elements = parsed_tag['elements']
        data_type = parsed_tag['tag_info']['data_type']

        value_elements = elements * 32 if data_type == 'DWORD' else elements

        if value_elements > 1:
            if len(value) < value_elements:
                raise RequestError(f'Insufficient data for requested elements, expected {value_elements} and got {len(value)}')
            if len(value) > value_elements:
                value = value[:value_elements]

        if parsed_tag['tag_info']['tag_type'] == 'struct':
            return _writable_value_structure(value, elements, data_type)
        else:
            pack_func = Pack[data_type]
            if data_type == 'DWORD':
                return b''.join(pack_func(_pack_bool_array(value[i:i+32])) for i in range(0, value_elements, 32))

            else:
                if elements > 1:
                    return b''.join(pack_func(value[i]) for i in range(elements))
                else:
                    return pack_func(value)
    except Exception as err:
        raise RequestError('Unable to create a writable value') from err


def _tag_return_size(tag_data):
    tag_info = tag_data['tag_info']
    if tag_info['tag_type'] == 'atomic':
        size = DataTypeSize[tag_info['data_type']]
    else:
        size = tag_info['data_type']['template']['structure_size']

    size = (size * tag_data['elements'])

    return size


def _writable_value_structure(value, elements, data_type):
    if elements > 1:
        return b''.join(_pack_structure(val, data_type) for val in value)
    else:
        return _pack_structure(value, data_type)


def _pack_bool_array(bools):
    if len(bools) != 32:
        raise RequestError(f'boolean arrays must have 32 elements: not {len(bools)}')
    value = 0
    for i, val in enumerate(bools):
        if val:
            value |= 1 << i
    return value


def _pack_string(value, string_len, struct_size):
    try:
        sint_array = [b'\x00' for _ in range(struct_size-4)]  # 4 for .LEN
        if len(value) > string_len:
            value = value[:string_len]
        for i, s in enumerate(value):
            sint_array[i] = Pack.char(s)
    except Exception as err:
        raise RequestError('Failed to pack string') from err
    return Pack.dint(len(value)) + b''.join(sint_array)


def _pack_structure(value, data_type):
    string_len = data_type.get('string')

    if string_len:
        data = _pack_string(value, string_len, data_type['template']['structure_size'])
    else:
        # NOTE:  start with object-definition-size array, then replace sections with offset + data len
        #        DONT use bytes, needs to be a list for swapping values later on
        data = [0 for _ in range(data_type['template']['structure_size'])]
        try:
            val_is_dict = isinstance(value, Mapping)

            for i, attr in enumerate(data_type['attributes']):
                val = value[attr] if val_is_dict else value[i]

                dtype = data_type['internal_tags'][attr]
                offset = dtype['offset']

                ary = dtype.get('array')
                if dtype['tag_type'] == 'struct':
                    if ary:
                        value_bytes = [_pack_structure(val[i], dtype['data_type']) for i in range(ary)]
                    else:
                        value_bytes = [_pack_structure(val, dtype['data_type']), ]
                else:
                    pack_func = Pack[dtype['data_type']]
                    bit = dtype.get('bit')
                    if bit is not None:  # attributes that are aliased to a bit
                        _byte = data[offset]
                        if val:
                            _byte |= 1 << bit
                        else:
                            _byte &= ~(1 << bit)

                        data[offset] = _byte
                        continue

                    elif dtype['data_type'] == 'DWORD':  # boolean arrays
                        value_bytes = [b''.join(pack_func(_pack_bool_array(val[i:i + 32])) for i in range(0, ary*32, 32)), ]
                    else:  # all other types
                        if ary:
                            value_bytes = [pack_func(val[i]) for i in range(ary)]
                        else:
                            value_bytes = [pack_func(val), ]

                val_bytes = list(itertools.chain.from_iterable(value_bytes))
                data[offset:offset+len(val_bytes)] = val_bytes

        except Exception as err:
            raise RequestError('Value Invalid for Structure') from err

    return bytes(data)


def _bit_request(tag_data, bit_requests):
    if tag_data.get('bit') is None:
        return None

    if tag_data['plc_tag'] not in bit_requests:
        bit_requests[tag_data['plc_tag']] = {'and_mask': 0xFFFFFFFF,
                                             'or_mask': 0x00000000,
                                             'bits': [], 'request_ids': [],
                                             'tag_info': tag_data['tag_info']}

    bits_ = bit_requests[tag_data['plc_tag']]
    typ_, bit = tag_data['bit']
    bits_['bits'].append(bit)
    bits_['request_ids'].append(tag_data['request_id'])

    if typ_ == 'bool_array':
        bit = bit % 32

    # update both masks so if same bit written to multiple times
    # only the last one is accurate/used
    if tag_data['value']:
        bits_['or_mask'] |= (1 << bit)
        bits_['and_mask'] |= (1 << bit)
    else:
        bits_['and_mask'] &= ~(1 << bit)
        bits_['or_mask'] &= ~(1 << bit)

    return True


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
        new_tag['data_type'] = DataType.get(datatype)
        new_tag['data_type_name'] = new_tag['data_type']
        if datatype == DataType.bool:
            new_tag['bit_position'] = (raw_tag['symbol_type'] & 0b_0000_0111_0000_0000) >> 8

    return new_tag


def tag_request_path(tag, tag_cache, use_instance_ids):
    """
    It returns the request packed wrapped around the tag passed.
    If any error it returns none
    """

    tags = tag.split('.')
    if tags:
        base, *attrs = tags
        base_tag, index = _find_tag_index(base)
        if use_instance_ids and base_tag in tag_cache:
            rp = [CLASS_TYPE['8-bit'],
                  ClassCode.symbol_object,
                  INSTANCE_TYPE['16-bit'],
                  Pack.uint(tag_cache[base_tag]['instance_id'])]
        else:
            base_len = len(base_tag)
            rp = [EXTENDED_SYMBOL,
                  Pack.usint(base_len),
                  base_tag.encode()]
            if base_len % 2:
                rp.append(b'\x00')
        if index is None:
            return None
        else:
            rp += _encode_tag_index(index)

        for attr in attrs:
            attr, index = _find_tag_index(attr)
            tag_length = len(attr)
            # Create the request path
            attr_path = [EXTENDED_SYMBOL,
                         Pack.usint(tag_length),
                         attr.encode()]
            # Add pad byte because total length of Request path must be word-aligned
            if tag_length % 2:
                attr_path.append(b'\x00')
            # Add any index
            if index is None:
                return None
            else:
                attr_path += _encode_tag_index(index)
            rp += attr_path

        return Pack.epath(b''.join(rp))

    return None


def _find_tag_index(tag):
    if '[' in tag:  # Check if is an array tag
        t = tag[:len(tag) - 1]  # Remove the last square bracket
        inside_value = t[t.find('[') + 1:]  # Isolate the value inside bracket
        index = inside_value.split(',')  # Now split the inside value in case part of multidimensional array
        tag = t[:t.find('[')]  # Get only the tag part
    else:
        index = []
    return tag, index


def _encode_tag_index(index):
    return [encode_segment(int(idx), ELEMENT_TYPE) for idx in index]
