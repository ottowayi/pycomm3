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

import re
import logging
from typing import Union, List, Tuple, Optional

from .exceptions import DataError, CommError, RequestError
from .tag import Tag

from .bytes_ import Pack, Unpack
from .cip_base import CIPDriver, with_forward_open
from .const import (TagService, EXTENDED_SYMBOL, CLASS_TYPE, INSTANCE_TYPE, ClassCode, DataType, PRODUCT_TYPES, VENDORS,
                    MICRO800_PREFIX, READ_RESPONSE_OVERHEAD, MULTISERVICE_READ_OVERHEAD, CommonService, SUCCESS,
                    INSUFFICIENT_PACKETS, BASE_TAG_BIT, MIN_VER_INSTANCE_IDS, SEC_TO_US, KEYSWITCH,
                    TEMPLATE_MEMBER_INFO_LEN, EXTERNAL_ACCESS, DataTypeSize, MIN_VER_EXTERNAL_ACCESS, PCCC_CT, PCCC_DATA_TYPE,
                    PCCC_DATA_SIZE, PCCC_ERROR_CODE)
from .packets import request_path
from autologging import logged


class SLCDriver(CIPDriver):
    __log = logging.getLogger(__qualname__)

    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, large_packets=False, **kwargs)

    @with_forward_open
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
            raise RequestError(f"Error parsing the tag passed to read_tag({tag},{n})")

        bit_read = False
        bit_position = 0
        if int(res[2]['address_field'] == 3):
            bit_read = True
            bit_position = int(res[2]['sub_element'])

        data_size = PCCC_DATA_SIZE[res[2]['file_type']]

        # Creating the Message Request Packet
        self._last_sequence = Pack.uint(self._sequence)

        message_request = [
            # self._last_sequence,

            # no clue what this part is
            b'\x4b',
            b'\x02',
            CLASS_TYPE["8-bit"],
            b'\x67\x24\x01',
            b'\x07',
            self._cfg['vid'],
            self._cfg['vsn'],

            # page 83 of eip manual
            b'\x0f',  # request command code
            b'\x00',  # status code
            Pack.usint(self._last_sequence[1]),  # transaction identifier
            Pack.usint(self._last_sequence[0]),  #  "        "
            res[2]['read_func'],  # function code
            Pack.usint(data_size * n),  # byte size
            Pack.usint(int(res[2]['file_number'])),
            PCCC_DATA_TYPE[res[2]['file_type']],
            Pack.usint(int(res[2]['element_number'])),
            b'\x00' if 'pos_number' not in res[2] else Pack.usint(int(res[2]['pos_number']))  # sub-element number
        ]

        request = self.new_request('send_unit_data')
        request.add(b''.join(message_request))
        result = request.send()
        self.__log.debug("SLC read_tag({0},{1})".format(tag, n))

        self._reply = result.raw

        try:
            if not result:
                self.__log.debug('read failed')
                # sts_txt = PCCC_ERROR_CODE[sts]
                # self._status = (1000, "Error({0}) returned from read_tag({1},{2})".format(sts_txt, tag, n))
                # self.__log.warning(self._status)
                # raise DataError("Error({0}) returned from read_tag({1},{2})".format(sts_txt, tag, n))

            new_value = 61
            if bit_read:
                if res[2]['file_type'] == 'T' or res[2]['file_type'] == 'C':
                    if bit_position == PCCC_CT['PRE']:
                        return Unpack[res[2]['file_type']](self._reply[new_value + 2:new_value + 2 + data_size])
                    elif bit_position == PCCC_CT['ACC']:
                        return Unpack[res[2]['file_type']](
                            self._reply[new_value + 4:new_value + 4 + data_size])

                tag_value = Unpack[res[2]['file_type']](
                    self._reply[new_value:new_value + data_size])
                return get_bit(tag_value, bit_position)

            else:
                values_list = []
                while len(self._reply[new_value:]) >= data_size:
                    unpack_func = Unpack[f'pccc_{res[2]["file_type"].lower()}']
                    values_list.append(
                        unpack_func(self._reply[new_value:new_value + data_size])
                    )
                    new_value = new_value + data_size

                print( 'Values!!!!: ', values_list )
                if len(values_list) > 1:
                    return values_list
                else:
                    return values_list[0]

        except Exception as e:
            self._status = (1000, "Error({0}) parsing the data returned from read_tag({1},{2})".format(e, tag, n))
            self.__log.warning(self._status)
            raise DataError("Error({0}) parsing the data returned from read_tag({1},{2})".format(e, tag, n))


def parse_tag(tag):
    t = re.search(r"(?P<file_type>[CT])(?P<file_number>\d{1,3})"
                  r"(:)(?P<element_number>\d{1,3})"
                  r"(.)(?P<sub_element>ACC|PRE|EN|DN|TT|CU|CD|DN|OV|UN|UA)", tag, flags=re.IGNORECASE)
    if (
        t
        and (1 <= int(t.group('file_number')) <= 255)
        and (0 <= int(t.group('element_number')) <= 255)
    ):
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'file_number': t.group('file_number'),
                                  'element_number': t.group('element_number'),
                                  'sub_element': PCCC_CT[t.group('sub_element').upper()],
                                  'read_func': b'\xa2',
                                  'write_func': b'\xab',
                                  'address_field': 3}

    t = re.search(r"(?P<file_type>[LFBN])(?P<file_number>\d{1,3})"
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
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
                                          'address_field': 3}
        else:
            if (1 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': t.group('file_number'),
                                          'element_number': t.group('element_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
                                          'address_field': 2}

    t = re.search(r"(?P<file_type>[IO])(:)(?P<element_number>\d{1,3})"
                  r"(.)(?P<position_number>\d{1,3})"
                  r"(/(?P<sub_element>\d{1,2}))?", tag, flags=re.IGNORECASE)
    if t:
        if t.group('sub_element') is not None:
            if (0 <= int(t.group('file_number')) <= 255) \
                    and (0 <= int(t.group('element_number')) <= 255) \
                    and (0 <= int(t.group('sub_element')) <= 15):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': '0',
                                          'element_number': t.group('element_number'),
                                          'pos_number': t.group('position_number'),
                                          'sub_element': t.group('sub_element'),
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
                                          'address_field': 3}
        else:
            if (0 <= int(t.group('element_number')) <= 255):

                return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                          'file_number': '0',
                                          'element_number': t.group('element_number'),
                                          'pos_number': t.group('position_number'),
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
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
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
                                          'address_field': 3}
        else:
            if 0 <= int(t.group('element_number')) <= 255:
                return True, t.group(0), {'file_type':  t.group('file_type').upper(),
                                          'file_number': '2',
                                          'element_number': t.group('element_number'),
                                          'read_func': b'\xa2',
                                          'write_func': b'\xab',
                                          'address_field': 2}

    t = re.search(r"(?P<file_type>B)(?P<file_number>\d{1,3})"
                  r"(/)(?P<element_number>\d{1,4})",
                  tag, flags=re.IGNORECASE)
    if (
        t
        and (1 <= int(t.group('file_number')) <= 255)
        and (0 <= int(t.group('element_number')) <= 4095)
    ):
        bit_position = int(t.group('element_number'))
        element_number = bit_position / 16
        sub_element = bit_position - (element_number * 16)
        return True, t.group(0), {'file_type': t.group('file_type').upper(),
                                  'file_number': t.group('file_number'),
                                  'element_number': element_number,
                                  'sub_element': sub_element,
                                  'read_func': b'\xa2',
                                  'write_func': b'\xab',
                                  'address_field': 3}

    return False, tag

def get_bit(value, idx):
    """:returns value of bit at position idx"""
    return (value & (1 << idx)) != 0
