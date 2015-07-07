# -*- coding: utf-8 -*-
#
# clx.py - Ethernet/IP Client for Rockwell PLCs
#
#
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
from pycomm.cip.cip_base import *
from pycomm.common import setup_logger
import re
import logging


def parse_tag(tag):
    t = re.search(r"(?P<file_type>[CT])(?P<file_number>\d{1,3})"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(.)(?P<sub_element>ACC|PRE|EN|DN|TT|CU|CD|DN|OV|UN|UA)", tag, flags=re.IGNORECASE)
    if t:
        return True, t.group(0), {'file_type': t.group('file_type'),
                                  'file_number': t.group('file_number'),
                                  'element_number': t.group('element_number'),
                                  'sub_element': PCCC_CT[t.group('sub_element')],
                                  'read_func': '\xa2',
                                  'write_func': '\xaa',
                                  'address_field': 3}

    t = re.search(r"(?P<file_type>[SBCTRNFAIO])(?P<file_number>\d{1,3})"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(/(?P<sub_element>\d{1,4}))?", tag, flags=re.IGNORECASE)
    if t:
        if t.group('sub_element') is not None:
            address_field = 3
            read_fnc = '\xa2'
            write_fnc = '\xaa'
        else:
            address_field = 2
            read_fnc = '\xa1'
            write_fnc = '\xa9'
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'file_number': t.group('file_number'),
                                  'element_number': t.group('element_number'),
                                  'sub_element': t.group('sub_element'),
                                  'read_func': read_fnc,
                                  'write_func': write_fnc,
                                  'address_field': address_field}
    """
    t = re.search(r"(?P<file_type>[BN])(?P<file_number>\d{1,3})"
                  r"(/)(?P<element_number>\d{1,4})",  tag, flags=re.IGNORECASE)
    if t:
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'file_number': t.group('file_number'),
                                  'element_number': t.group('element_number'),
                                  'read_func': '\xa1',
                                  'write_func': '\xa9',
                                  'address_field': 2}

    t = re.search(r"(?P<file_type>[IOS])(:)(?P<element_number>\d{1,3})"
                  r"(/)(?P<sub_element>\d{1,4})", tag, flags=re.IGNORECASE)
    if t:
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'element_number': t.group('element_number'),
                                  'sub_element': t.group('sub_element'),
                                  'read_func': '\xa1',
                                  'write_func': '\xa9',
                                  'address_field': 2}
    """

    t = re.search(r"(?P<file_type>[IOS])(:)(?P<file_number>\d{1,3})"
                  r"(.)(?P<element_number>[0-7])", tag, flags=re.IGNORECASE)
    if t:
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'file_number': t.group('file_number'),
                                  'element_number': t.group('element_number'),
                                  'read_func': '\xa1',
                                  'write_func': '\xa9',
                                  'address_field': 2}

    """
    t = re.search(r"(?P<file_type>[IOS])(:)(?P<element_number>\d{1,3})", tag, flags=re.IGNORECASE)
    if t:
        return True, t.group(0), {'file_type': t.group('file_type'),'element_number': t.group('element_number')}
    """
    return False, tag


class Driver(Base):
    """
    SLC/PLC_5 Implementation
    """
    def __init__(self, debug=False, filename=None):
        if debug:
            super(Driver, self).__init__(setup_logger('ab_comm.slc', logging.DEBUG, filename))
        else:
            super(Driver, self).__init__(setup_logger('ab_comm.slc', logging.INFO, filename))

        self.__version__ = '0.1'

    def _check_reply(self):
        """
        check the replayed message for error
        """
        self._more_packets_available = False
        try:
            if self._reply is None:
                self._status = (3, '%s without reply' % REPLAY_INFO[unpack_dint(self._message[:2])])
                return False
            # Get the type of command
            typ = unpack_uint(self._reply[:2])

            # Encapsulation status check
            if unpack_dint(self._reply[8:12]) != SUCCESS:
                self._status = (3, "{0} reply status:{1}".format(REPLAY_INFO[typ],
                                                                 SERVICE_STATUS[unpack_dint(self._reply[8:12])]))
                return False

            # Command Specific Status check
            if typ == unpack_uint(ENCAPSULATION_COMMAND["send_rr_data"]):
                status = unpack_sint(self._reply[42:43])
                if status != SUCCESS:
                    self._status = (3, "send_rr_data reply:{0} - Extend status:{1}".format(
                        SERVICE_STATUS[status], get_extended_status(self._reply, 42)))
                    return False
                else:
                    return True

            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = unpack_sint(self._reply[48:49])
                if unpack_sint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Read Tag Fragmented"]:
                    self._parse_fragment(50, status)
                    return True
                if unpack_sint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Get Instance Attributes List"]:
                    self._parse_tag_list(50, status)
                    return True
                if status == 0x06:
                    self._status = (3, "Insufficient Packet Space")
                    self._more_packets_available = True
                elif status != SUCCESS:
                    self._status = (3, "send_unit_data reply:{0} - Extend status:{1}".format(
                        SERVICE_STATUS[status], get_extended_status(self._reply, 48)))
                    return False
                else:
                    return True

        except LookupError:
            self._status = (3, "LookupError inside _check_replay")
            return False

        return True

    def read_tag(self, tag, n=1):
        res = parse_tag(tag)
        if not res[0]:
            self._status = (1000, "Error parsing the tag passed to read_tag({0},{1})".format(tag, n))
            self.logger.warning(self._status)
            return None

        if self._session == 0:
            self._status = (6, "A session need to be registered before to call read_tag.")
            self.logger.warning(self._status)
            return None

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (5, "Target did not connected. read_tag will not be executed.")
                self.logger.warning(self._status)
                return None

        data_size = PCCC_DATA_SIZE[res[2]['file_type']]

        # Creating the Message Request Packet
        seq = pack_uint(Base._get_sequence())
        message_request = [
            seq,
            '\x4b',
            '\x02',
            CLASS_ID["8-bit"],
            PATH["PCCC"],
            '\x07',
            self.attribs['vid'],
            self.attribs['vsn'],
            '\x0f',
            '\x00',
            seq[1],
            seq[0],
            res[2]['read_func'],
            pack_sint(data_size * n),
            pack_sint(int(res[2]['file_number'])),
            PCCC_DATA_TYPE[res[2]['file_type']],
            pack_sint(int(res[2]['element_number'])),
        ]

        if res[2]['address_field'] == 3:
            message_request.append(pack_sint(int(res[2]['sub_element'])))
        self.logger.debug("SLC read_tag({0},{1})".format(tag, n))
        if self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid,)):
            sts = int(unpack_sint(self._reply[58]))
            try:
                if sts != 0:
                    sts_txt = PCCC_ERROR_CODE[sts]
                    self._status = (1000, "Error({0}) returned from read_tag({1},{2})".format(sts_txt, tag, n))
                    self.logger.warning(self._status)
                    return None

                new_value = 61
                values_list = []
                while len(self._reply[new_value:]) >= data_size:
                    values_list.append(
                        UNPACK_PCCC_DATA_FUNCTION[res[2]['file_type']](self._reply[new_value:new_value+data_size])
                    )
                    new_value = new_value+data_size

                return values_list
            except Exception as err:
                self._status = (1000, "Error({0}) parsing the data returned from read_tag({1},{2})".format(err, tag, n))
                self.logger.warning(self._status)
                return None
        else:
            return None

    def write_tag(self, tag, value):
        res = parse_tag(tag)
        if not res[0]:
            self._status = (1000, "Error parsing the tag passed to read_tag({0},{1})".format(tag, n))
            self.logger.warning(self._status)
            return None

        multi_requests = False
        if isinstance(value, list):
            multi_requests = True

        if self._session == 0:
            self._status = (8, "A session need to be registered before to call write_tag.")
            self.logger.warning(self._status)
            return None

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (8, "Target did not connected. write_tag will not be executed.")
                self.logger.warning(self._status)
                return None
        try:
            values = ""
            if multi_requests:
                for v in value:
                    values += PACK_PCCC_DATA_FUNCTION[res[2]['file_type']](v)
                    if res[2]['file_type'] == 'C' or res[2]['file_type'] == 'T':
                        values += '\x00\x00'
            else:
                values += PACK_PCCC_DATA_FUNCTION[res[2]['file_type']](value)
                if res[2]['file_type'] == 'C' or res[2]['file_type'] == 'T':
                    values += '\x00\x00'

        except Exception as err:
                self._status = (1000, "Error({0}) packing the values to write  to the"
                                      "SLC write_tag({1},{2})".format(err, tag, value))
                self.logger.warning(self._status)
                return None

        data_to_write = values
        # Creating the Message Request Packet
        seq = pack_uint(Base._get_sequence())

        message_request = [
            seq,
            '\x4b',
            '\x02',
            CLASS_ID["8-bit"],
            PATH["PCCC"],
            '\x07',
            self.attribs['vid'],
            self.attribs['vsn'],
            '\x0f',
            '\x00',
            seq[1],
            seq[0],
            res[2]['write_func'],
            pack_sint(len(data_to_write)),
            pack_sint(int(res[2]['file_number'])),
            PCCC_DATA_TYPE[res[2]['file_type']],
            pack_sint(int(res[2]['element_number'])),
        ]

        self.logger.debug("SLC write_tag({0},{1})".format(tag, value))
        if self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request) + data_to_write,
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid,)):
            sts = int(unpack_sint(self._reply[58]))
            try:
                if sts != 0:
                    sts_txt = PCCC_ERROR_CODE[sts]
                    self._status = (1000, "Error({0}) returned from SLC write_tag({1},{2})".format(sts_txt, tag, value))
                    self.logger.warning(self._status)
                    return None

                return True
            except Exception as err:
                self._status = (1000, "Error({0}) parsing the data returned from "
                                      "SLC write_tag({1},{2})".format(err, tag, value))
                self.logger.warning(self._status)
                return None
        else:
            return None