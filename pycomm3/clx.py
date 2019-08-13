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

import struct
from collections import defaultdict
from autologging import logged

from . import DataError
from .base import Base
from .bytes_ import (pack_dint, pack_uint, pack_udint, pack_usint, unpack_usint, unpack_uint, unpack_dint, unpack_udint,
                     UNPACK_DATA_FUNCTION, PACK_DATA_FUNCTION, DATA_FUNCTION_SIZE)
from .const import (SUCCESS, EXTENDED_SYMBOL, ENCAPSULATION_COMMAND, DATA_TYPE, SERVICE_STATUS, BITS_PER_INT_TYPE,
                    REPLAY_INFO, TAG_SERVICES_REQUEST, PADDING_BYTE, ELEMENT_ID, DATA_ITEM, ADDRESS_ITEM,
                    CLASS_ID, CLASS_CODE, INSTANCE_ID, INSUFFICIENT_PACKETS, REPLY_START,
                    MULTISERVICE_READ_OVERHEAD, MULTISERVICE_WRITE_OVERHEAD, MIN_VER_INSTANCE_IDS, REQUEST_PATH_SIZE,
                    VENDORS, PRODUCT_TYPES)


@logged
class CLXDriver(Base):
    """
    This Ethernet/IP client is based on Rockwell specification. Please refer to the link below for details.

    http://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf

    The following services have been implemented:
        - Read Tag Service (0x4c)
        - Read Tag Fragment Service (0x52)
        - Write Tag Service (0x4d)
        - Write Tag Fragment Service (0x53)
        - Multiple Service Packet (0x0a)
        - Read Modify Write Tag (0xce)

    The client has been successfully tested with the following PLCs:
        - CompactLogix 5330ERM
        - CompactLogix 5370
        - ControlLogix 5572 and 1756-EN2T Module

"""

    def __init__(self, ip_address, *args, slot=0, large_packets=True, init_info=True, init_tags=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._instance_id_cache = {}
        self._struct_cache = {}
        self._template_cache = {}
        self._udt_cache = {}
        self._program_names = []
        self.attribs['ip address'] = ip_address
        self.attribs['cpu slot'] = slot
        self.attribs['extended forward open'] = large_packets
        self._connection_size = 4000 if large_packets else 500
        self._tags = {}
        self.use_instance_ids = True

        if init_tags or init_info:
            self.open()
            if init_info:
                self.get_plc_info()
                self.get_plc_name()
                self.use_instance_ids = self.info.get('version_major', 0) >= MIN_VER_INSTANCE_IDS

            if init_tags:
                self._tags = self.get_tag_list()
            self.close()

    def _check_reply(self, reply):
        """ check the replayed message for error"""
        try:
            if reply is None:
                self._status = (3, f'{REPLAY_INFO[unpack_dint(reply[:2])]} without reply')
                return False
            # Get the type of command
            typ = unpack_uint(reply[:2])

            # Encapsulation status check
            if unpack_dint(reply[8:12]) != SUCCESS:
                self._status = (3, f"{REPLAY_INFO[typ]} reply status:{SERVICE_STATUS[unpack_dint(reply[8:12])]}")
                return False

            # Command Specific Status check
            if typ == unpack_uint(ENCAPSULATION_COMMAND["send_rr_data"]):
                status = unpack_usint(reply[42:43])
                if status != SUCCESS:
                    self._status = (3, f"send_rr_data reply:{SERVICE_STATUS[status]} - "
                    f"Extend status:{self.get_extended_status(reply, 42)}")
                    return False
                else:
                    return True
            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = _unit_data_status(reply)
                if status not in (INSUFFICIENT_PACKETS, SUCCESS):
                    self._status = (3, f"send_unit_data reply:{SERVICE_STATUS[status]} - "
                    f"Extend status:{self.get_extended_status(reply, 48)}")
                    self.__log.warning(self._status)
                    return False
            return True
        except Exception as e:
            raise DataError(e)

    def create_tag_rp(self, tag, multi_requests=False):
        """ Create tag Request Packet

        It returns the request packed wrapped around the tag passed.
        If any error it returns none
        """
        tags = tag.split('.')
        index = []
        if tags:
            base, *attrs = tags

            if self.use_instance_ids and base in self._instance_id_cache:
                rp = [CLASS_ID['8-bit'],
                      CLASS_CODE['Symbol Object'],
                      INSTANCE_ID['16-bit'], b'\x00',
                      pack_uint(self._instance_id_cache[base])]
            else:
                base_len = len(base)
                rp = [EXTENDED_SYMBOL,
                      pack_usint(base_len),
                      base.encode()]
                if base_len % 2:
                    rp.append(PADDING_BYTE)

            for attr in attrs:
                # Check if is an array tag
                if '[' in attr:
                    # Remove the last square bracket
                    attr = attr[:len(attr) - 1]
                    # Isolate the value inside bracket
                    inside_value = attr[attr.find('[') + 1:]
                    # Now split the inside value in case part of multidimensional array
                    index = inside_value.split(',')
                    # Get only the tag part
                    attr = attr[:attr.find('[')]
                tag_length = len(attr)

                # Create the request path
                attr_path = [EXTENDED_SYMBOL,
                             pack_usint(tag_length),
                             attr.encode()]
                # Add pad byte because total length of Request path must be word-aligned
                if tag_length % 2:
                    attr_path.append(PADDING_BYTE)
                # Add any index

                for idx in index:
                    val = int(idx)
                    if val <= 0xff:
                        attr_path += [ELEMENT_ID["8-bit"], pack_usint(val)]
                    elif val <= 0xffff:
                        attr_path += [ELEMENT_ID["16-bit"], PADDING_BYTE, pack_uint(val)]
                    elif val <= 0xfffffffff:
                        attr_path += [ELEMENT_ID["32-bit"], PADDING_BYTE, pack_dint(val)]
                    else:
                        # Cannot create a valid request packet
                        return None

                rp += attr_path

            # At this point the Request Path is completed,
            request_path = b''.join(rp)
            if multi_requests:
                request_path = bytes([len(request_path) // 2]) + request_path

            return request_path

        return None

    def read_tag(self, *tags):
        """ read tag from a connected plc

        Possible combination can be passed to this method:
                - ('Counts') a single tag name
                - (['ControlWord']) a list with one tag or many
                - (['parts', 'ControlWord', 'Counts'])

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :return: None is returned in case of error otherwise the tag list is returned
        """
        self.clear()

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (6, "Target did not connected. read_tag will not be executed.")
                self.__log.warning(self._status)
                raise DataError(self._status[1])

        if len(tags) == 1:
            if isinstance(tags[0], (list, tuple)):
                return self._read_tag_multi(tags[0])
            else:
                return self._read_tag_single(tags[0])
        else:
            return self._read_tag_multi(tags)

    def _read_tag_multi(self, tags):
        tag_bits = defaultdict(list)
        rp_list, tags_read = [[]], [[]]
        request_len = 0
        for tag in tags:
            tag, bit = self._prep_bools(tag, 'BOOL', bits_only=True)
            read = bit is None or tag not in tag_bits
            if bit is not None:
                tag_bits[tag].append(bit)
            if read:
                rp = self.create_tag_rp(tag, multi_requests=True)
                if rp is None:
                    self._status = (6, f"Cannot create tag {tag} request packet. read_tag will not be executed.")
                    raise DataError(self._status[1])
                else:
                    tag_req_len = len(rp) + MULTISERVICE_READ_OVERHEAD
                    if tag_req_len + request_len >= self._connection_size:
                        rp_list.append([])
                        tags_read.append([])
                        request_len = 0
                    rp_list[-1].append(bytes([TAG_SERVICES_REQUEST['Read Tag']]) + rp + b'\x01\x00')
                    tags_read[-1].append(tag)
                    request_len += tag_req_len

        replies = []
        for req_list, tags_ in zip(rp_list, tags_read):
            message_request = self.build_multiple_service(req_list, self._get_sequence())
            msg = self.build_common_packet_format(
                DATA_ITEM['Connected'],
                b''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid, )
            reply = self.send_unit_data(msg)
            if reply is None:
                raise DataError("send_unit_data returned not valid data")

            replies += self._parse_multiple_request_read(reply, tags_, tag_bits)
        return replies

    def _read_tag_single(self, tag):
        tag, bit = self._prep_bools(tag, 'BOOL', bits_only=True)
        rp = self.create_tag_rp(tag)
        if rp is None:
            self._status = (6, f"Cannot create tag {tag} request packet. read_tag will not be executed.")
            return None
        else:
            # Creating the Message Request Packet
            message_request = [
                pack_uint(self._get_sequence()),
                bytes([TAG_SERVICES_REQUEST['Read Tag']]),  # the Request Service
                bytes([len(rp) // 2]),  # the Request Path Size length in word
                rp,  # the request path
                b'\x01\x00'
            ]

        reply = self.send_unit_data(
            self.build_common_packet_format(
                DATA_ITEM['Connected'],
                b''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid, )
        )
        if reply is None:
            raise DataError("send_unit_data returned not valid data")

            # Get the data type
        if self._status[0] == SUCCESS:
            data_type = unpack_uint(reply[50:52])
            typ = DATA_TYPE[data_type]
            try:
                value = UNPACK_DATA_FUNCTION[typ](reply[52:])
                if bit is not None:
                    value = bool(value & (1 << bit)) if bit < BITS_PER_INT_TYPE[typ] else None
                return value, typ
            except Exception as e:
                raise DataError(e)
        else:
            return None

    def read_array(self, tag, counts, raw=False):
        """ read array of atomic data type from a connected plc

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :param tag: the name of the tag to read
        :param counts: the number of element to read
        :param raw: the value should output as raw-value (hex)
        :return: None is returned in case of error otherwise the tag list is returned
        """
        self.clear()
        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (7, "Target did not connected. read_tag will not be executed.")
                self.__log.warning(self._status)
                raise DataError(self._status[1])

        offset = 0
        last_idx = 0
        tags = b'' if raw else []

        while offset != -1:
            rp = self.create_tag_rp(tag)
            if rp is None:
                self._status = (7, f"Cannot create tag {tag} request packet. read_tag will not be executed.")
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(self._get_sequence()),
                    bytes([TAG_SERVICES_REQUEST["Read Tag Fragmented"]]),  # the Request Service
                    bytes([len(rp) // 2]),  # the Request Path Size length in word
                    rp,  # the request path
                    pack_uint(counts),
                    pack_dint(offset)
                ]
            msg = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                  b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'],
                                                  addr_data=self._target_cid, )
            reply = self.send_unit_data(msg)
            if reply is None:
                raise DataError("send_unit_data returned not valid data")

            last_idx, offset = self._parse_fragment(reply, last_idx, offset, tags, raw)

        return tags

    @staticmethod
    def _prep_bools(tag, typ, bits_only=True):
        """
        if tag is a bool and a bit of an integer, returns the base tag and the bit value,
        else returns the tag name and None

        """
        if typ != 'BOOL':
            return tag, None
        if not bits_only and tag.endswith(']'):
            try:
                base, idx = tag[:-1].rsplit(sep='[', maxsplit=1)
                idx = int(idx)
                base = f'{base}[{idx // 32}]'
                return base, idx
            except Exception:
                return tag, None
        else:
            try:
                base, bit = tag.rsplit('.', maxsplit=1)
                bit = int(bit)
                return base, bit
            except Exception:
                return tag, None

    @staticmethod
    def _dword_to_boolarray(tag, bit):
        base, tmp = tag.rsplit(sep='[', maxsplit=1)
        i = int(tmp[:-1])
        return f'{base}[{(i * 32) + bit}]'

    def _write_tag_multi_write(self, tags):
        rp_list = [[]]
        tags_added = [[]]
        request_len = 0
        for name, value, typ in tags:
            name, bit = self._prep_bools(name, typ, bits_only=False)  # check if bit of int or bool array
            # Create the request path to wrap the tag name
            rp = self.create_tag_rp(name, multi_requests=True)
            if rp is None:
                self._status = (8, f"Cannot create tag {tags} req. packet. write_tag will not be executed")
                return None
            else:
                try:
                    if bit is not None:
                        rp = self.create_tag_rp(name, multi_requests=True)
                        request = bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]]) + rp
                        request += b''.join(self._make_write_bit_data(bit, value, bool_ary='[' in name))
                        if typ == 'BOOL' and name.endswith('['):
                            name = self._dword_to_boolarray(name, bit)
                        else:
                            name = f'{name}.{bit}'
                    else:
                        request = (bytes([TAG_SERVICES_REQUEST["Write Tag"]]) +
                                   rp +
                                   pack_uint(DATA_TYPE[typ]) +
                                   b'\x01\x00' +
                                   PACK_DATA_FUNCTION[typ](value))

                    tag_req_len = len(request) + MULTISERVICE_WRITE_OVERHEAD
                    if tag_req_len + request_len >= self._connection_size:
                        rp_list.append([])
                        tags_added.append([])
                        request_len = 0
                    rp_list[-1].append(request)
                    request_len += tag_req_len
                except (LookupError, struct.error) as e:
                    self._status = (8, f"Tag:{name} type:{typ} removed from write list. Error:{e}.")

                    # The tag in idx position need to be removed from the rp list because has some kind of error
                else:
                    tags_added[-1].append((name, value, typ))

        # Create the message request
        replies = []
        for req_list, tags_ in zip(rp_list, tags_added):
            message_request = self.build_multiple_service(req_list, self._get_sequence())
            msg = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                  b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'],
                                                  addr_data=self._target_cid, )
            reply = self.send_unit_data(msg)
            if reply:
                replies += self._parse_multiple_request_write(tags_, reply)
            else:
                raise DataError("send_unit_data returned not valid data")
        return replies

    def _write_tag_single_write(self, tag, value, typ):
        name, bit = self._prep_bools(tag, typ,
                                     bits_only=False)  # check if we're writing a bit of a integer rather than a BOOL

        rp = self.create_tag_rp(name)
        if rp is None:
            self._status = (8, f"Cannot create tag {tag} request packet. write_tag will not be executed.")
            self.__log.warning(self._status)
            return None
        else:
            # Creating the Message Request Packet
            message_request = [
                pack_uint(self._get_sequence()),
                bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]
                       if bit is not None else TAG_SERVICES_REQUEST["Write Tag"]]),
                bytes([len(rp) // 2]),  # the Request Path Size length in word
                rp,  # the request path
            ]
            if bit is not None:
                try:
                    message_request += self._make_write_bit_data(bit, value, bool_ary='[' in name)
                except Exception as err:
                    raise DataError(f'Unable to write bit, invalid bit number {repr(err)}')
            else:
                message_request += [
                    pack_uint(DATA_TYPE[typ]),  # data type
                    pack_uint(1),  # Add the number of tag to write
                    PACK_DATA_FUNCTION[typ](value)
                ]

            reply = self.send_unit_data(self.build_common_packet_format(DATA_ITEM['Connected'],
                                                                        b''.join(message_request),
                                                                        ADDRESS_ITEM['Connection Based'],
                                                                        addr_data=self._target_cid))
            if reply:
                return True

            raise DataError("send_unit_data returned not valid data")

    @staticmethod
    def _make_write_bit_data(bit, value, bool_ary=False):
        or_mask, and_mask = 0x00000000, 0xFFFFFFFF

        if bool_ary:
            mask_size = 4
            bit = bit % 32
        else:
            mask_size = 1 if bit < 8 else 2 if bit < 16 else 4

        if value:
            or_mask |= (1 << bit)
        else:
            and_mask &= ~(1 << bit)

        return [pack_uint(mask_size), pack_udint(or_mask)[:mask_size], pack_udint(and_mask)[:mask_size]]

    def write_tag(self, tag, value=None, typ=None):
        """ write tag/tags from a connected plc

        Possible combination can be passed to this method:
                - ('tag name', Value, data type)  as single parameters or inside a tuple
                - ([('tag name', Value, data type), ('tag name2', Value, data type)]) as array of tuples

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        The type accepted are:
            - BOOL
            - SINT
            - INT
            - DINT
            - REAL
            - LINT
            - BYTE
            - WORD
            - DWORD
            - LWORD

        :param tag: tag name, or an array of tuple containing (tag name, value, data type)
        :param value: the value to write or none if tag is an array of tuple or a tuple
        :param typ: the type of the tag to write or none if tag is an array of tuple or a tuple
        :return: None is returned in case of error otherwise the tag list is returned
        """
        self.clear()  # cleanup error string

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (8, "Target did not connected. write_tag will not be executed.")
                self.__log.warning(self._status)
                raise DataError(self._status[1])

        if isinstance(tag, (list, tuple)):
            return self._write_tag_multi_write(tag)
        else:
            if isinstance(tag, tuple):
                name, value, typ = tag
            else:
                name = tag
            return self._write_tag_single_write(name, value, typ)

    def write_array(self, tag, values, data_type, raw=False):
        """ write array of atomic data type from a connected plc
        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.
        :param tag: the name of the tag to read
        :param data_type: the type of tag to write
        :param values: the array of values to write, if raw: the frame with bytes
        :param raw: indicates that the values are given as raw values (hex)
        """
        self.clear()
        if not isinstance(values, list):
            self._status = (9, "A list of tags must be passed to write_array.")
            self.__log.warning(self._status)
            raise DataError(self._status[1])

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (9, "Target did not connected. write_array will not be executed.")
                self.__log.warning(self._status)
                raise DataError(self._status[1])

        array_of_values = b''
        byte_size = 0
        byte_offset = 0

        for i, value in enumerate(values):
            array_of_values += value if raw else PACK_DATA_FUNCTION[data_type](value)
            byte_size += DATA_FUNCTION_SIZE[data_type]

            if byte_size >= 450 or i == len(values) - 1:
                # create the message and send the fragment
                rp = self.create_tag_rp(tag)
                if rp is None:
                    self._status = (9, f"Cannot create tag {tag} request packet write_array will not be executed.")
                    return None
                else:
                    # Creating the Message Request Packet
                    message_request = [
                        pack_uint(self._get_sequence()),
                        bytes([TAG_SERVICES_REQUEST["Write Tag Fragmented"]]),  # the Request Service
                        bytes([len(rp) // 2]),  # the Request Path Size length in word
                        rp,  # the request path
                        pack_uint(DATA_TYPE[data_type]),  # Data type to write
                        pack_uint(len(values)),  # Number of elements to write
                        pack_dint(byte_offset),
                        array_of_values  # Fragment of elements to write
                    ]
                    byte_offset += byte_size

                msg = self.build_common_packet_format(
                            DATA_ITEM['Connected'],
                            b''.join(message_request),
                            ADDRESS_ITEM['Connection Based'],
                            addr_data=self._target_cid,
                        )

                reply = self.send_unit_data(msg)
                if reply is None:
                    raise DataError("send_unit_data returned not valid data")

                array_of_values = b''
                byte_size = 0
        return True

    def write_string(self, tag, value, size=82):
        """
            Rockwell define different string size:
                STRING  STRING_12   STRING_16   STRING_20   STRING_40   STRING_8
            by default we assume size 82 (STRING)
        """
        data_tag = ".".join((tag, "DATA"))
        len_tag = ".".join((tag, "LEN"))

        # create an empty array
        data_to_send = [0] * size
        for idx, val in enumerate(value):
            try:
                unsigned = ord(val)
                data_to_send[idx] = unsigned - 256 if unsigned > 127 else unsigned
            except IndexError:
                break

        str_len = len(value)
        if str_len > size:
            str_len = size

        result_len = self.write_tag(len_tag, str_len, 'DINT')
        result_data = self.write_array(data_tag, data_to_send, 'SINT')
        return result_data and result_len

    def read_string(self, tag, str_len=None):
        data_tag = f'{tag}.DATA'
        if str_len is None:
            len_tag = f'{tag}.LEN'
            tmp = self.read_tag(len_tag)
            length, _ = tmp or (None, None)
        else:
            length = str_len

        if length:
            values = self.read_array(data_tag, length)
            if values:
                _, values = zip(*values)
                chars = [chr(v + 256) if v < 0 else chr(v) for v in values]
                return ''.join(ch for ch in chars if ch != '\x00')
        return None

    def get_plc_name(self):
        try:
            if not self._target_is_connected:
                if not self.forward_open():
                    self._status = (10, "Target did not connected. get_plc_name will not be executed.")
                    self.__log.warning(self._status)
                    raise DataError(self._status[1])

            msg = [
                pack_uint(self._get_sequence()),
                bytes([TAG_SERVICES_REQUEST['Get Attributes']]),
                REQUEST_PATH_SIZE,
                CLASS_ID['8-bit'],
                CLASS_CODE['Program Name'],
                INSTANCE_ID["16-bit"],
                b'\x00',
                b'\x01\x00',  # Instance 1
                b'\x01\x00',  # Number of Attributes
                b'\x01\x00'  # Attribute 1 - program name
            ]

            request = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                      b''.join(msg),
                                                      ADDRESS_ITEM['Connection Based'],
                                                      addr_data=self._target_cid, )
            reply = self.send_unit_data(request)

            if reply:
                self._info['name'] = self._parse_plc_name(reply)
                return self._info['name']
            else:
                raise DataError('send_unit_data did not return valid data')

        except Exception as err:
            raise DataError(err)

    def get_plc_info(self):
        try:
            if not self._target_is_connected:
                if not self.forward_open():
                    self._status = (10, "Target did not connected. get_plc_name will not be executed.")
                    self.__log.warning(self._status)
                    raise DataError(self._status[1])

            msg = [
                pack_uint(self._get_sequence()),
                b'\x01',
                REQUEST_PATH_SIZE,
                CLASS_ID['8-bit'],
                CLASS_CODE['Identity Object'],
                INSTANCE_ID["16-bit"],
                b'\x00',
                b'\x01\x00',  # Instance 1
            ]
            request = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                      b''.join(msg),
                                                      ADDRESS_ITEM['Connection Based'],
                                                      addr_data=self._target_cid, )
            reply = self.send_unit_data(request)

            if reply:
                info = self._parse_identity_object(reply)
                self._info = {**self._info, **info}
                return info
            else:
                raise DataError('send_unit_data did not return valid data')

        except Exception as err:
            raise DataError(err)

    @staticmethod
    def _parse_plc_name(reply):
        status = _unit_data_status(reply)
        if status != SUCCESS:
            raise DataError(f'get_plc_name returned status {SERVICE_STATUS[status]}')
        data = reply[REPLY_START:]
        try:
            name_len = unpack_uint(data[6:8])
            name = data[8: 8 + name_len].decode()
            return name
        except Exception as err:
            raise DataError(err)

    @staticmethod
    def _parse_identity_object(reply):

        data = reply[REPLY_START:]
        vendor = unpack_uint(data[0:2])
        product_type = unpack_uint(data[2:4])
        product_code = unpack_uint(data[4:6])
        major_fw = int(data[6])
        minor_fw = int(data[7])
        keyswitch = data[8:10]
        serial_number = f'{unpack_udint(data[10:14]):0{8}x}'
        device_type_len = int(data[14])
        device_type = data[15:15 + device_type_len].decode()

        return {
            'vendor': VENDORS[vendor],
            'product_type': PRODUCT_TYPES[product_type],
            'product_code': product_code,
            'version_major': major_fw,
            'version_minor': minor_fw,
            'revision': f'{major_fw}.{minor_fw}',
            'serial': serial_number,
            'device_type': device_type
        }

    def get_tag_list(self, program=None):
        """
        Returns the list of tags from the controller. For only controller-scoped tags, get `program` to None.
        Set `program` to a program name to only get the program scoped tags from the specified program.
        To get all controller and all program scoped tags from all programs, set `program` to '*

        Note, for program scoped tags the tag['tag_name'] will be 'Program:{program}.{tag_name}'. This is so the tag
        list can be fed directly into the read function.
        """
        if program == '*':
            tags = self._get_tag_list()
            for prog in self._program_names:
                prog_tags = self._get_tag_list(prog)
                for t in prog_tags:
                    t['tag_name'] = f"{prog}.{t['tag_name']}"
                tags += prog_tags
        else:
            tags = self._get_tag_list(program)

        if cache:
            self._tags = {tag['tag_name']: tag for tag in tags}

        return tags

    def _get_tag_list(self, program=None):
        all_tags = self._get_instance_attribute_list_service(program)
        user_tags = self._isolating_user_tag(all_tags)
        for tag in user_tags:
            if tag['tag_type'] == 'struct':
                tag['template'] = self._get_structure_makeup(tag['template_instance_id'])
                tag['udt'] = self._parse_udt_raw(tag)
        return user_tags

    def _get_instance_attribute_list_service(self, program=None):
        """ Step 1: Finding user-created controller scope tags in a Logix5000 controller

        This service returns instance IDs for each created instance of the symbol class, along with a list
        of the attribute data associated with the requested attribute
        """
        try:
            if not self._target_is_connected:
                if not self.forward_open():
                    self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                    self.__log.warning(self._status)
                    raise DataError(self._status[1])

            last_instance = 0
            tag_list = []
            while last_instance != -1:
                # Creating the Message Request Packet
                path = []
                if program is not None and not program.startswith('Program:'):
                    program = f'Program:{program}'
                if program:
                    path = [EXTENDED_SYMBOL, pack_usint(len(program)), program.encode('utf-8')]
                    if len(program) % 2:
                        path.append(b'\x00')
                path += [
                    # Request Path ( 20 6B 25 00 Instance )
                    CLASS_ID["8-bit"],  # Class id = 20 from spec 0x20
                    CLASS_CODE["Symbol Object"],  # Logical segment: Symbolic Object 0x6B
                    INSTANCE_ID["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                    b'\x00',
                    pack_uint(last_instance),  # The instance
                ]
                path = b''.join(path)
                path_size = pack_usint(len(path) // 2)

                message_request = [
                    pack_uint(self._get_sequence()),
                    bytes([TAG_SERVICES_REQUEST['Get Instance Attributes List']]),
                    path_size,
                    path,
                    # Request Data
                    b'\x02\x00',  # Number of attributes to retrieve
                    b'\x01\x00',  # Attribute 1: Symbol name
                    b'\x02\x00',
                ]

                reply = self.send_unit_data(
                    self.build_common_packet_format(
                        DATA_ITEM['Connected'],
                        b''.join(message_request),
                        ADDRESS_ITEM['Connection Based'],
                        addr_data=self._target_cid,
                    ))
                if reply is None:
                    raise DataError("send_unit_data returned not valid data")

                last_instance = self._parse_instance_attribute_list(reply, tag_list)
            return tag_list

        except Exception as e:
            raise DataError(e)

    def _parse_instance_attribute_list(self, reply, tag_list):
        """ extract the tags list from the message received"""

        status = _unit_data_status(reply)
        tags_returned = reply[REPLY_START:]
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
                tag_list.append({'instance_id': instance,
                                 'tag_name': tag_name,
                                 'symbol_type': symbol_type})
        except Exception as e:
            raise DataError(e)

        if status == SUCCESS:
            last_instance = -1
        elif status == INSUFFICIENT_PACKETS:
            last_instance = instance + 1
        else:
            self._status = (1, 'unknown status during _parse_instance_attribute_list')
            last_instance = -1

        return last_instance

    def _isolating_user_tag(self, all_tags):
        try:
            user_tags = []
            for tag in all_tags:
                name = tag['tag_name'].decode()
                if 'Program:' in name:
                    self._program_names.append(name)
                    continue
                if ':' in name or '__' in name:
                    continue
                if tag['symbol_type'] & 0b0001000000000000:
                    continue

                self._instance_id_cache[name] = tag['instance_id']

                new_tag = {
                    'tag_name': name,
                    'dim': (tag['symbol_type'] & 0b0110000000000000) >> 13,
                    'instance_id': tag['instance_id']
                }

                if tag['symbol_type'] & 0b1000000000000000:
                    template_instance_id = tag['symbol_type'] & 0b0000111111111111
                    new_tag['tag_type'] = 'struct'
                    new_tag['data_type'] = 'user-created'
                    new_tag['template_instance_id'] = template_instance_id
                    new_tag['template'] = {}
                    new_tag['udt'] = {}
                else:
                    new_tag['tag_type'] = 'atomic'
                    datatype = tag['symbol_type'] & 0b0000000011111111
                    new_tag['data_type'] = DATA_TYPE[datatype]
                    if datatype == DATA_TYPE['BOOL']:
                        new_tag['bit_position'] = (tag['symbol_type'] & 0b0000011100000000) >> 8

                user_tags.append(new_tag)

            return user_tags
        except Exception as e:
            raise DataError(e)

    def _get_structure_makeup(self, instance_id):
        """
        get the structure makeup for a specific structure
        """
        if instance_id not in self._struct_cache:
            if not self._target_is_connected:
                if not self.forward_open():
                    self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                    self.__log.warning(self._status)
                    raise DataError(self._status[1])

            message_request = [
                pack_uint(self._get_sequence()),
                bytes([TAG_SERVICES_REQUEST['Get Attributes']]),
                b'\x03',  # Request Path ( 20 6B 25 00 Instance )
                CLASS_ID["8-bit"],  # Class id = 20 from spec 0x20
                CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
                INSTANCE_ID["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                b'\x00',
                pack_uint(instance_id),
                b'\x04\x00',  # Number of attributes
                b'\x04\x00',  # Template Object Definition Size UDINT
                b'\x05\x00',  # Template Structure Size UDINT
                b'\x02\x00',  # Template Member Count UINT
                b'\x01\x00'  # Structure Handle We can use this to read and write UINT
            ]

            reply = self.send_unit_data(self.build_common_packet_format(DATA_ITEM['Connected'],
                                                                        b''.join(message_request),
                                                                        ADDRESS_ITEM['Connection Based'],
                                                                        addr_data=self._target_cid, ))
            if reply is None:
                raise DataError("send_unit_data returned not valid data")

            self._struct_cache[instance_id] = self._parse_structure_makeup_attributes(reply)

        return self._struct_cache[instance_id]

    @staticmethod
    def _parse_structure_makeup_attributes(reply):
        """ extract the tags list from the message received"""
        structure = {}
        status = _unit_data_status(reply)
        if status != SUCCESS:
            structure['Error'] = status
            return

        attribute = reply[REPLY_START:]
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

    def _read_template(self, instance_id, object_definition_size):
        """ get a list of the tags in the plc

        """
        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                self.__log.warning(self._status)
                raise DataError(self._status[1])

        if instance_id not in self._template_cache:
            offset = 0
            template = b''
            try:
                while offset is not None:
                    message_request = [
                        pack_uint(self._get_sequence()),
                        bytes([TAG_SERVICES_REQUEST['Read Template']]),
                        b'\x03',  # Request Path ( 20 6B 25 00 Instance )
                        CLASS_ID["8-bit"],  # Class id = 20 from spec 0x20
                        CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
                        INSTANCE_ID["16-bit"],  # Instance Segment: 16 Bit instance 0x25
                        b'\x00',
                        pack_uint(instance_id),
                        pack_dint(offset),  # Offset
                        pack_uint(((object_definition_size * 4) - 21) - offset)
                    ]

                    reply = self.send_unit_data(self.build_common_packet_format(DATA_ITEM['Connected'],
                                                                                b''.join(message_request),
                                                                                ADDRESS_ITEM['Connection Based'],
                                                                                addr_data=self._target_cid, ))
                    if reply is None:
                        raise DataError("send_unit_data returned not valid data")

                    offset, template = self._parse_template(reply, offset, template)

                self._template_cache[instance_id] = template

            except Exception as e:
                raise DataError(e)
        return self._template_cache[instance_id]

    def _parse_template(self, reply, offset, template):
        """ extract the tags list from the message received"""
        tags_returned = reply[REPLY_START:]
        bytes_received = len(tags_returned)
        status = _unit_data_status(reply)

        template += tags_returned

        if status == SUCCESS:
            offset = None
        elif status == INSUFFICIENT_PACKETS:
            offset += bytes_received
        else:
            self._status = (1, f'unknown status {status} during _parse_template')
            self.__log.warning(self._status)
            offset = None

        return offset, template

    def _build_udt(self, data, member_count):
        udt = {'name': None, 'internal_tags': [], 'data_type': []}
        names = (x.decode(errors='replace') for x in data.split(b'\x00') if len(x) > 1)
        for name in names:
            if ';' in name and udt['name'] is None:
                udt['name'] = name[:name.find(';')]
            elif 'ZZZZZZZZZZ' in name:
                continue
            elif name.isalnum():
                udt['internal_tags'].append(name)
            else:
                continue
        if udt['name'] is None:
            udt['name'] = 'Not a user define structure'

        for _ in range(member_count):
            array_size = unpack_uint(data[:2])
            try:
                data_type = DATA_TYPE[unpack_uint(data[2:4])]
            except Exception:
                dtval = unpack_uint(data[2:4])
                instance_id = dtval & 0b0000111111111111
                if instance_id in DATA_TYPE:
                    data_type = DATA_TYPE[instance_id]
                else:
                    try:
                        template = self._get_structure_makeup(instance_id)
                        if not template.get('Error'):
                            _data = self._read_template(instance_id, template['object_definition_size'])
                            data_type = self._build_udt(_data, template['member_count'])
                        else:
                            data_type = 'None'
                    except Exception:
                        data_type = 'None'

            offset = unpack_dint(data[4:8])
            udt['data_type'].append((array_size, data_type, offset))

            data = data[8:]
        return udt

    def _parse_udt_raw(self, tag):
        if tag['template_instance_id'] not in self._udt_cache:
            try:
                buff = self._read_template(tag['template_instance_id'], tag['template']['object_definition_size'])
                member_count = tag['template']['member_count']
                self._udt_cache[tag['template_instance_id']] = self._build_udt(buff, member_count)
            except Exception as e:
                raise DataError(e)

        return self._udt_cache[tag['template_instance_id']]

    def _parse_fragment(self, reply, last_idx, offset, tags, raw=False):
        """ parse the fragment returned by a fragment service."""

        try:
            status = _unit_data_status(reply)
            data_type = unpack_uint(reply[REPLY_START:REPLY_START + 2])
            fragment_returned = reply[REPLY_START + 2:]
        except Exception as e:
            raise DataError(e)

        fragment_returned_length = len(fragment_returned)
        idx = 0
        while idx < fragment_returned_length:
            try:
                typ = DATA_TYPE[data_type]
                if raw:
                    value = fragment_returned[idx:idx + DATA_FUNCTION_SIZE[typ]]
                else:
                    value = UNPACK_DATA_FUNCTION[typ](fragment_returned[idx:idx + DATA_FUNCTION_SIZE[typ]])
                idx += DATA_FUNCTION_SIZE[typ]
            except Exception as e:
                raise DataError(e)
            if raw:
                tags += value
            else:
                tags.append((last_idx, value))
                last_idx += 1

        if status == SUCCESS:
            offset = -1
        elif status == 0x06:
            offset += fragment_returned_length
        else:
            self._status = (2, '{0}: {1}'.format(SERVICE_STATUS[status], self.get_extended_status(reply, 48)))
            self.__log.warning(self._status)
            offset = -1

        return last_idx, offset

    def _parse_multiple_request_read(self, reply, tags, tag_bits=None):
        """ parse the message received from a multi request read:

        For each tag parsed, the information extracted includes the tag name, the value read and the data type.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50
        tag_bits = tag_bits or {}
        try:
            number_of_service_replies = unpack_uint(reply[offset:offset + 2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(reply[position:position + 2])
                general_status = unpack_usint(reply[start + 2:start + 3])
                tag = tags[index]
                if general_status == 0:
                    typ = DATA_TYPE[unpack_uint(reply[start + 4:start + 6])]
                    value_begin = start + 6
                    value_end = value_begin + DATA_FUNCTION_SIZE[typ]
                    value = UNPACK_DATA_FUNCTION[typ](reply[value_begin:value_end])
                    if tag in tag_bits:
                        for bit in tag_bits[tag]:
                            val = bool(value & (1 << bit)) if bit < BITS_PER_INT_TYPE[typ] else None
                            tag_list.append((f'{tag}.{bit}', val, 'BOOL'))
                    else:
                        self._last_tag_read = (tag, value, typ)
                        tag_list.append(self._last_tag_read)
                else:
                    self._last_tag_read = (tag, None, None)
                    tag_list.append(self._last_tag_read)

            return tag_list
        except Exception as e:
            raise DataError(e)

    def _parse_multiple_request_write(self, tags, reply):
        """ parse the message received from a multi request writ:

        For each tag parsed, the information extracted includes the tag name and the status of the writing.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50

        try:
            number_of_service_replies = unpack_uint(reply[offset:offset + 2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(reply[position:position + 2])
                general_status = unpack_usint(reply[start + 2:start + 3])

                self._last_tag_write = (tags[index] + (general_status == 0,))
                tag_list.append(self._last_tag_write)
            return tag_list
        except Exception as e:
            raise DataError(e)

    @property
    def last_tag_read(self):
        """ Return the last tag read by a multi request read

        :return: A tuple (tag name, value, type)
        """
        return self._last_tag_read

    @property
    def last_tag_write(self):
        """ Return the last tag write by a multi request write

        :return: A tuple (tag name, 'GOOD') if the write was successful otherwise (tag name, 'BAD')
        """
        return self._last_tag_write

    @property
    def tags(self):
        return self._tags


def _unit_data_status(reply):
    return unpack_usint(reply[48:49])
