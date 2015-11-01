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
import re
import logging
import math

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def parse_tag(tag):
    t = re.search(r"(?P<file_type>[CT])(?P<file_number>\d{1,3})"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(.)(?P<sub_element>ACC|PRE|EN|DN|TT|CU|CD|DN|OV|UN|UA)", tag, flags=re.IGNORECASE)
    if t:
        if (1 <= int(t.group('file_number')) <= 255) \
                and (0 <= int(t.group('element_number')) <= 255):
            return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                      'file_number': t.group('file_number'),
                                      'element_number': t.group('element_number'),
                                      'sub_element': PCCC_CT[t.group('sub_element').upper()],
                                      'read_func': '\xa2',
                                      'write_func': '\xab',
                                      'address_field': 3}

    t = re.search(r"(?P<file_type>[FBN])(?P<file_number>\d{1,3})"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(/(?P<sub_element>\d{1,2}))?",
                  tag, flags=re.IGNORECASE)
    if t:
        if t.group('sub_element') is not None:
            if (1 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255) \
                    and (0 <= int(t.group('sub_element')) <= 15):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': t.group('file_number'),
                                          'element_number': t.group('element_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 3}
        else:
            if (1 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': t.group('file_number'),
                                          'element_number': t.group('element_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 2}

    t = re.search(r"(?P<file_type>[IO])(:)(?P<file_number>\d{1,3})"
                  r"(.)(?P<element_number>\d{1,3})"
                  r"(/(?P<sub_element>\d{1,2}))?", tag, flags=re.IGNORECASE)
    if t:
        if t.group('sub_element') is not None:
            if (0 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255) \
                    and (0 <= int(t.group('sub_element')) <= 15):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': t.group('file_number'),
                                          'element_number': t.group('element_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 3}
        else:
            if (0 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': t.group('file_number'),
                                          'element_number': t.group('element_number'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 2}

    t = re.search(r"(?P<file_type>S)"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(/(?P<sub_element>\d{1,2}))?", tag, flags=re.IGNORECASE)
    if t:
        if t.group('sub_element') is not None:
            if (0 <= int(t.group('element_number')) <= 255) \
                    and (0 <= int(t.group('sub_element')) <= 15):
                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': '2',
                                          'element_number': t.group('element_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 3}
        else:
            if 0 <= int(t.group('element_number')) <= 255:
                return True, t.group(0), {'file_type':  t.group('file_type').upper(),
                                          'file_number': '2',
                                          'element_number': t.group('element_number'),
                                          'read_func': '\xa2',
                                          'write_func': '\xab',
                                          'address_field': 2}

    t = re.search(r"(?P<file_type>B)(?P<file_number>\d{1,3})"
                  r"(/)(?P<element_number>\d{1,4})",
                  tag, flags=re.IGNORECASE)
    if t:
        if (1 <= int(t.group('file_number')) <= 255) \
                and (0 <= int(t.group('element_number')) <= 4095):
            bit_position = int(t.group('element_number'))
            element_number = bit_position / 16
            sub_element = bit_position - (element_number * 16)
            return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                      'file_number': t.group('file_number'),
                                      'element_number': element_number,
                                      'sub_element': sub_element,
                                      'read_func': '\xa2',
                                      'write_func': '\xab',
                                      'address_field': 3}

    return False, tag


class Driver(Base):
    """
    SLC/PLC_5 Implementation
    """
    def __init__(self):
        super(Driver, self).__init__()

        self.__version__ = '0.1'
        self._last_sequence = 0

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
                status = unpack_usint(self._reply[42:43])
                if status != SUCCESS:
                    self._status = (3, "send_rr_data reply:{0} - Extend status:{1}".format(
                        SERVICE_STATUS[status], get_extended_status(self._reply, 42)))
                    return False
                else:
                    return True

            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = unpack_usint(self._reply[48:49])
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Read Tag Fragmented"]:
                    self._parse_fragment(50, status)
                    return True
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Get Instance Attributes List"]:
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

            return True
        except Exception as e:
            raise DataError(e)

    def read_tag(self, tag, n=1):
        """ read tag from a connected plc

        Possible combination can be passed to this method:
            print c.read_tag('F8:0', 3)    return a list of 3 registers starting from F8:0
            print c.read_tag('F8:0')   return one value

        It is possible to read status bit

        :return: None is returned in case of error
        """
        res = parse_tag(tag)
        if not res[0]:
            self._status = (1000, "Error parsing the tag passed to read_tag({0},{1})".format(tag, n))
            logger.warning(self._status)
            raise DataError("Error parsing the tag passed to read_tag({0},{1})".format(tag, n))

        bit_read = False
        bit_position = 0
        sub_element = 0
        if int(res[2]['address_field'] == 3):
            bit_read = True
            bit_position = int(res[2]['sub_element'])

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (5, "Target did not connected. read_tag will not be executed.")
                logger.warning(self._status)
                raise DataError("Target did not connected. read_tag will not be executed.")

        data_size = PCCC_DATA_SIZE[res[2]['file_type']]

        # Creating the Message Request Packet
        self._last_sequence = pack_uint(Base._get_sequence())

        message_request = [
            self._last_sequence,
            '\x4b',
            '\x02',
            CLASS_ID["8-bit"],
            PATH["PCCC"],
            '\x07',
            self.attribs['vid'],
            self.attribs['vsn'],
            '\x0f',
            '\x00',
            self._last_sequence[1],
            self._last_sequence[0],
            res[2]['read_func'],
            pack_usint(data_size * n),
            pack_usint(int(res[2]['file_number'])),
            PCCC_DATA_TYPE[res[2]['file_type']],
            pack_usint(int(res[2]['element_number'])),
            pack_usint(sub_element)
        ]

        logger.debug("SLC read_tag({0},{1})".format(tag, n))
        if self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid,)):
            sts = int(unpack_usint(self._reply[58]))
            try:
                if sts != 0:
                    sts_txt = PCCC_ERROR_CODE[sts]
                    self._status = (1000, "Error({0}) returned from read_tag({1},{2})".format(sts_txt, tag, n))
                    logger.warning(self._status)
                    raise DataError("Error({0}) returned from read_tag({1},{2})".format(sts_txt, tag, n))

                new_value = 61
                if bit_read:
                    if res[2]['file_type'] == 'T' or res[2]['file_type'] == 'C':
                        if bit_position == PCCC_CT['PRE']:
                            return UNPACK_PCCC_DATA_FUNCTION[res[2]['file_type']](
                                self._reply[new_value+2:new_value+2+data_size])
                        elif bit_position == PCCC_CT['ACC']:
                            return UNPACK_PCCC_DATA_FUNCTION[res[2]['file_type']](
                                self._reply[new_value+4:new_value+4+data_size])

                    tag_value = UNPACK_PCCC_DATA_FUNCTION[res[2]['file_type']](
                        self._reply[new_value:new_value+data_size])
                    return get_bit(tag_value, bit_position)

                else:
                    values_list = []
                    while len(self._reply[new_value:]) >= data_size:
                        values_list.append(
                            UNPACK_PCCC_DATA_FUNCTION[res[2]['file_type']](self._reply[new_value:new_value+data_size])
                        )
                        new_value = new_value+data_size

                    if len(values_list) > 1:
                        return values_list
                    else:
                        return values_list[0]

            except Exception as e:
                self._status = (1000, "Error({0}) parsing the data returned from read_tag({1},{2})".format(e, tag, n))
                logger.warning(self._status)
                raise DataError("Error({0}) parsing the data returned from read_tag({1},{2})".format(e, tag, n))
        else:
            raise DataError("send_unit_data returned not valid data")

    def write_tag(self, tag, value):
        """ write tag from a connected plc

        Possible combination can be passed to this method:
            c.write_tag('N7:0', [-30, 32767, -32767])
            c.write_tag('N7:0', 21)
            c.read_tag('N7:0', 10)

        It is not possible to write status bit

        :return: None is returned in case of error
        """
        res = parse_tag(tag)
        if not res[0]:
            self._status = (1000, "Error parsing the tag passed to read_tag({0},{1})".format(tag, value))
            logger.warning(self._status)
            raise DataError("Error parsing the tag passed to read_tag({0},{1})".format(tag, value))

        if isinstance(value, list) and int(res[2]['address_field'] == 3):
            self._status = (1000, "Function's parameters error.  read_tag({0},{1})".format(tag, value))
            logger.warning(self._status)
            raise DataError("Function's parameters error.  read_tag({0},{1})".format(tag, value))

        if isinstance(value, list) and int(res[2]['address_field'] == 3):
            self._status = (1000, "Function's parameters error.  read_tag({0},{1})".format(tag, value))
            logger.warning(self._status)
            raise DataError("Function's parameters error.  read_tag({0},{1})".format(tag, value))

        bit_field = False
        bit_position = 0
        sub_element = 0
        if int(res[2]['address_field'] == 3):
            bit_field = True
            bit_position = int(res[2]['sub_element'])
            values_list = ''
        else:
            values_list = '\xff\xff'

        multi_requests = False
        if isinstance(value, list):
            multi_requests = True

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (1000, "Target did not connected. write_tag will not be executed.")
                logger.warning(self._status)
                raise DataError("Target did not connected. write_tag will not be executed.")

        try:
            n = 0
            if multi_requests:
                data_size = PCCC_DATA_SIZE[res[2]['file_type']]
                for v in value:
                    values_list += PACK_PCCC_DATA_FUNCTION[res[2]['file_type']](v)
                    n += 1
            else:
                n = 1
                if bit_field:
                    data_size = 2

                    if (res[2]['file_type'] == 'T' or res[2]['file_type'] == 'C') \
                            and (bit_position == PCCC_CT['PRE'] or bit_position == PCCC_CT['ACC']):
                        sub_element = bit_position
                        values_list = '\xff\xff' + PACK_PCCC_DATA_FUNCTION[res[2]['file_type']](value)
                    else:
                        sub_element = 0
                        if value > 0:
                            values_list = pack_uint(math.pow(2, bit_position)) + pack_uint(math.pow(2, bit_position))
                        else:
                            values_list = pack_uint(math.pow(2, bit_position)) + pack_uint(0)

                else:
                    values_list += PACK_PCCC_DATA_FUNCTION[res[2]['file_type']](value)
                    data_size = PCCC_DATA_SIZE[res[2]['file_type']]

        except Exception as e:
                self._status = (1000, "Error({0}) packing the values to write  to the"
                                      "SLC write_tag({1},{2})".format(e, tag, value))
                logger.warning(self._status)
                raise DataError("Error({0}) packing the values to write  to the "
                                "SLC write_tag({1},{2})".format(e, tag, value))

        data_to_write = values_list

        # Creating the Message Request Packet
        self._last_sequence = pack_uint(Base._get_sequence())

        message_request = [
            self._last_sequence,
            '\x4b',
            '\x02',
            CLASS_ID["8-bit"],
            PATH["PCCC"],
            '\x07',
            self.attribs['vid'],
            self.attribs['vsn'],
            '\x0f',
            '\x00',
            self._last_sequence[1],
            self._last_sequence[0],
            res[2]['write_func'],
            pack_usint(data_size * n),
            pack_usint(int(res[2]['file_number'])),
            PCCC_DATA_TYPE[res[2]['file_type']],
            pack_usint(int(res[2]['element_number'])),
            pack_usint(sub_element)
        ]

        logger.debug("SLC write_tag({0},{1})".format(tag, value))
        if self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request) + data_to_write,
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid,)):
            sts = int(unpack_usint(self._reply[58]))
            try:
                if sts != 0:
                    sts_txt = PCCC_ERROR_CODE[sts]
                    self._status = (1000, "Error({0}) returned from SLC write_tag({1},{2})".format(sts_txt, tag, value))
                    logger.warning(self._status)
                    raise DataError("Error({0}) returned from SLC write_tag({1},{2})".format(sts_txt, tag, value))

                return True
            except Exception as e:
                self._status = (1000, "Error({0}) parsing the data returned from "
                                      "SLC write_tag({1},{2})".format(e, tag, value))
                logger.warning(self._status)
                raise DataError("Error({0}) parsing the data returned from "
                            "SLC write_tag({1},{2})".format(e, tag, value))
        else:
            raise DataError("send_unit_data returned not valid data")