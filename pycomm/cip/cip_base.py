# -*- coding: utf-8 -*-
#
# cip_base.py - A set of classes methods and structures  used to implement Ethernet/IP
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

import struct
import socket

from os import getpid
from pycomm.cip.cip_const import *
from pycomm.common import PycommError


import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CommError(PycommError):
    pass


class DataError(PycommError):
    pass


def pack_sint(n):
    return struct.pack('b', n)


def pack_usint(n):
    return struct.pack('B', n)


def pack_int(n):
    """pack 16 bit into 2 bytes little endian"""
    return struct.pack('<h', n)


def pack_uint(n):
    """pack 16 bit into 2 bytes little endian"""
    return struct.pack('<H', n)


def pack_dint(n):
    """pack 32 bit into 4 bytes little endian"""
    return struct.pack('<i', n)


def pack_real(r):
    """unpack 4 bytes little endian to int"""
    return struct.pack('<f', r)


def pack_lint(l):
    """unpack 4 bytes little endian to int"""
    return struct.unpack('<q', l)


def unpack_bool(st):
    if int(struct.unpack('B', st[0])[0]) == 255:
        return 1
    return 0


def unpack_sint(st):
    return int(struct.unpack('b', st[0])[0])


def unpack_usint(st):
    return int(struct.unpack('B', st[0])[0])


def unpack_int(st):
    """unpack 2 bytes little endian to int"""
    return int(struct.unpack('<h', st[0:2])[0])


def unpack_uint(st):
    """unpack 2 bytes little endian to int"""
    return int(struct.unpack('<H', st[0:2])[0])


def unpack_dint(st):
    """unpack 4 bytes little endian to int"""
    return int(struct.unpack('<i', st[0:4])[0])


def unpack_real(st):
    """unpack 4 bytes little endian to int"""
    return float(struct.unpack('<f', st[0:4])[0])


def unpack_lint(st):
    """unpack 4 bytes little endian to int"""
    return int(struct.unpack('<q', st[0:8])[0])


def get_bit(value, idx):
    """:returns value of bit at position idx"""
    return (value & (1 << idx)) != 0


PACK_DATA_FUNCTION = {
    'BOOL': pack_sint,
    'SINT': pack_sint,    # Signed 8-bit integer
    'INT': pack_int,     # Signed 16-bit integer
    'UINT': pack_uint,    # Unsigned 16-bit integer
    'DINT': pack_dint,    # Signed 32-bit integer
    'REAL': pack_real,    # 32-bit floating point
    'LINT': pack_lint,
    'BYTE': pack_sint,     # byte string 8-bits
    'WORD': pack_uint,     # byte string 16-bits
    'DWORD': pack_dint,    # byte string 32-bits
    'LWORD': pack_lint    # byte string 64-bits
}


UNPACK_DATA_FUNCTION = {
    'BOOL': unpack_bool,
    'SINT': unpack_sint,    # Signed 8-bit integer
    'INT': unpack_int,     # Signed 16-bit integer
    'UINT': unpack_uint,    # Unsigned 16-bit integer
    'DINT': unpack_dint,    # Signed 32-bit integer
    'REAL': unpack_real,    # 32-bit floating point,
    'LINT': unpack_lint,
    'BYTE': unpack_sint,     # byte string 8-bits
    'WORD': unpack_uint,     # byte string 16-bits
    'DWORD': unpack_dint,    # byte string 32-bits
    'LWORD': unpack_lint    # byte string 64-bits
}


DATA_FUNCTION_SIZE = {
    'BOOL': 1,
    'SINT': 1,    # Signed 8-bit integer
    'INT': 2,     # Signed 16-bit integer
    'UINT': 2,    # Unsigned 16-bit integer
    'DINT': 4,    # Signed 32-bit integer
    'REAL': 4,    # 32-bit floating point
    'LINT': 8,
    'BYTE': 1,     # byte string 8-bits
    'WORD': 2,     # byte string 16-bits
    'DWORD': 4,    # byte string 32-bits
    'LWORD': 8    # byte string 64-bits
}

UNPACK_PCCC_DATA_FUNCTION = {
    'N': unpack_int,
    'B': unpack_int,
    'T': unpack_int,
    'C': unpack_int,
    'S': unpack_int,
    'F': unpack_real,
    'A': unpack_sint,
    'R': unpack_dint,
    'O': unpack_int,
    'I': unpack_int
}

PACK_PCCC_DATA_FUNCTION = {
    'N': pack_int,
    'B': pack_int,
    'T': pack_int,
    'C': pack_int,
    'S': pack_int,
    'F': pack_real,
    'A': pack_sint,
    'R': pack_dint,
    'O': pack_int,
    'I': pack_int
}


def print_bytes_line(msg):
    out = ''
    for ch in msg:
        out += "{:0>2x}".format(ord(ch))
    return out


def print_bytes_msg(msg, info=''):
    out = info
    new_line = True
    line = 0
    column = 0
    for idx, ch in enumerate(msg):
        if new_line:
            out += "\n({:0>4d}) ".format(line * 10)
            new_line = False
        out += "{:0>2x} ".format(ord(ch))
        if column == 9:
            new_line = True
            column = 0
            line += 1
        else:
            column += 1
    return out


def get_extended_status(msg, start):
    status = unpack_usint(msg[start:start+1])
    # send_rr_data
    # 42 General Status
    # 43 Size of additional status
    # 44..n additional status

    # send_unit_data
    # 48 General Status
    # 49 Size of additional status
    # 50..n additional status
    extended_status_size = (unpack_usint(msg[start+1:start+2]))*2
    extended_status = 0
    if extended_status_size != 0:
        # There is an additional status
        if extended_status_size == 1:
            extended_status = unpack_usint(msg[start+2:start+3])
        elif extended_status_size == 2:
            extended_status = unpack_uint(msg[start+2:start+4])
        elif extended_status_size == 4:
            extended_status = unpack_dint(msg[start+2:start+6])
        else:
            return 'Extended Status Size Unknown'
    try:
        return '{0}'.format(EXTEND_CODES[status][extended_status])
    except LookupError:
        return "Extended Status info not present"


def create_tag_rp(tag, multi_requests=False):
    """ Create tag Request Packet

    It returns the request packed wrapped around the tag passed.
    If any error it returns none
    """
    tags = tag.split('.')
    rp = []
    index = []
    for tag in tags:
        add_index = False
        # Check if is an array tag
        if tag.find('[') != -1:
            # Remove the last square bracket
            tag = tag[:len(tag)-1]
            # Isolate the value inside bracket
            inside_value = tag[tag.find('[')+1:]
            # Now split the inside value in case part of multidimensional array
            index = inside_value.split(',')
            # Flag the existence of one o more index
            add_index = True
            # Get only the tag part
            tag = tag[:tag.find('[')]
        tag_length = len(tag)

        # Create the request path
        rp.append(EXTENDED_SYMBOL)  # ANSI Ext. symbolic segment
        rp.append(chr(tag_length))  # Length of the tag

        # Add the tag to the Request path
        for char in tag:
            rp.append(char)
        # Add pad byte because total length of Request path must be word-aligned
        if tag_length % 2:
            rp.append(PADDING_BYTE)
        # Add any index
        if add_index:
            for idx in index:
                val = int(idx)
                if val <= 0xff:
                    rp.append(ELEMENT_ID["8-bit"])
                    rp.append(pack_usint(val))
                elif val <= 0xffff:
                    rp.append(ELEMENT_ID["16-bit"]+PADDING_BYTE)
                    rp.append(pack_uint(val))
                elif val <= 0xfffffffff:
                    rp.append(ELEMENT_ID["32-bit"]+PADDING_BYTE)
                    rp.append(pack_dint(val))
                else:
                    # Cannot create a valid request packet
                    return None

    # At this point the Request Path is completed,
    if multi_requests:
        request_path = chr(len(rp)/2) + ''.join(rp)
    else:
        request_path = ''.join(rp)
    return request_path


def build_common_packet_format(message_type, message, addr_type, addr_data=None, timeout=10):
    """ build_common_packet_format

    It creates the common part for a CIP message. Check Volume 2 (page 2.22) of CIP specification  for reference
    """
    msg = pack_dint(0)   # Interface Handle: shall be 0 for CIP
    msg += pack_uint(timeout)   # timeout
    msg += pack_uint(2)  # Item count: should be at list 2 (Address and Data)
    msg += addr_type  # Address Item Type ID

    if addr_data is not None:
        msg += pack_uint(len(addr_data))  # Address Item Length
        msg += addr_data
    else:
        msg += pack_uint(0)  # Address Item Length
    msg += message_type  # Data Type ID
    msg += pack_uint(len(message))   # Data Item Length
    msg += message
    return msg


def build_multiple_service(rp_list, sequence=None):

    mr = []
    if sequence is not None:
        mr.append(pack_uint(sequence))

    mr.append(chr(TAG_SERVICES_REQUEST["Multiple Service Packet"]))  # the Request Service
    mr.append(pack_usint(2))                 # the Request Path Size length in word
    mr.append(CLASS_ID["8-bit"])
    mr.append(CLASS_CODE["Message Router"])
    mr.append(INSTANCE_ID["8-bit"])
    mr.append(pack_usint(1))                 # Instance 1
    mr.append(pack_uint(len(rp_list)))      # Number of service contained in the request

    # Offset calculation
    offset = (len(rp_list) * 2) + 2
    for index, rp in enumerate(rp_list):
        if index == 0:
            mr.append(pack_uint(offset))   # Starting offset
        else:
            mr.append(pack_uint(offset))
        offset += len(rp)

    for rp in rp_list:
        mr.append(rp)
    return mr


def parse_multiple_request(message, tags, typ):
    """ parse_multi_request
    This function should be used to parse the message replayed to a multi request service rapped around the
    send_unit_data message.


    :param message: the full message returned from the PLC
    :param tags: The list of tags to be read
    :param typ: to specify if multi request service READ or WRITE
    :return: a list of tuple in the format [ (tag name, value, data type), ( tag name, value, data type) ].
             In case of error the tuple will be (tag name, None, None)
    """
    offset = 50
    position = 50
    number_of_service_replies = unpack_uint(message[offset:offset+2])
    tag_list = []
    for index in range(number_of_service_replies):
        position += 2
        start = offset + unpack_uint(message[position:position+2])
        general_status = unpack_usint(message[start+2:start+3])

        if general_status == 0:
            if typ == "READ":
                data_type = unpack_uint(message[start+4:start+6])
                try:
                    value_begin = start + 6
                    value_end = value_begin + DATA_FUNCTION_SIZE[I_DATA_TYPE[data_type]]
                    value = message[value_begin:value_end]
                    tag_list.append((tags[index],
                                    UNPACK_DATA_FUNCTION[I_DATA_TYPE[data_type]](value),
                                    I_DATA_TYPE[data_type]))
                except LookupError:
                    tag_list.append((tags[index], None, None))
            else:
                tag_list.append((tags[index] + ('GOOD',)))
        else:
            if typ == "READ":
                tag_list.append((tags[index], None, None))
            else:
                tag_list.append((tags[index] + ('BAD',)))
    return tag_list


class Socket:

    def __init__(self, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def connect(self, host, port):
        try:
            self.sock.connect((host, port))
        except socket.timeout:
            raise CommError("Socket timeout during connection.")

    def send(self, msg, timeout=0):
        if timeout != 0:
            self.sock.settimeout(timeout)
        total_sent = 0
        while total_sent < len(msg):
            try:
                sent = self.sock.send(msg[total_sent:])
                if sent == 0:
                    raise CommError("socket connection broken.")
                total_sent += sent
            except socket.error:
                raise CommError("socket connection broken.")
        return total_sent

    def receive(self, timeout=0):
        if timeout != 0:
            self.sock.settimeout(timeout)
        msg_len = 28
        chunks = []
        bytes_recd = 0
        one_shot = True
        while bytes_recd < msg_len:
            try:
                chunk = self.sock.recv(min(msg_len - bytes_recd, 2048))
                if chunk == '':
                    raise CommError("socket connection broken.")
                if one_shot:
                    data_size = int(struct.unpack('<H', chunk[2:4])[0])  # Length
                    msg_len = HEADER_SIZE + data_size
                    one_shot = False

                chunks.append(chunk)
                bytes_recd += len(chunk)
            except socket.error as e:
                raise CommError(e)
        return ''.join(chunks)

    def close(self):
        self.sock.close()


def parse_symbol_type(symbol):
    """ parse_symbol_type

    It parse the symbol to Rockwell Spec
    :param symbol: the symbol associated to a tag
    :return: A tuple containing information about the tag
    """
    pass

    return None


class Base(object):
    _sequence = 0


    def __init__(self):
        if Base._sequence == 0:
            Base._sequence = getpid()
        else:
            Base._sequence = Base._get_sequence()

        self.__version__ = '0.1'
        self.__sock = None
        self._session = 0
        self._connection_opened = False
        self._reply = None
        self._message = None
        self._target_cid = None
        self._target_is_connected = False
        self._tag_list = []
        self._buffer = {}
        self._device_description = "Device Unknown"
        self._last_instance = 0
        self._byte_offset = 0
        self._last_position = 0
        self._more_packets_available = False
        self._last_tag_read = ()
        self._last_tag_write = ()
        self._status = (0, "")
        self._output_raw = False    #indicating value should be output as raw (hex)

        self.attribs = {'context': '_pycomm_', 'protocol version': 1, 'rpi': 5000, 'port': 0xAF12, 'timeout': 10,
                        'backplane': 1, 'cpu slot': 0, 'option': 0, 'cid': '\x27\x04\x19\x71', 'csn': '\x27\x04',
                        'vid': '\x09\x10', 'vsn': '\x09\x10\x19\x71', 'name': 'Base', 'ip address': None}

    def __len__(self):
        return len(self.attribs)

    def __getitem__(self, key):
        return self.attribs[key]

    def __setitem__(self, key, value):
        self.attribs[key] = value

    def __delitem__(self, key):
        try:
            del self.attribs[key]
        except LookupError:
            pass

    def __iter__(self):
        return iter(self.attribs)

    def __contains__(self, item):
        return item in self.attribs

    def _check_reply(self):
        raise Socket.ImplementationError("The method has not been implemented")

    @staticmethod
    def _get_sequence():
        """ Increase and return the sequence used with connected messages

        :return: The New sequence
        """
        if Base._sequence < 65535:
            Base._sequence += 1
        else:
            Base._sequence = getpid()
        return Base._sequence

    def nop(self):
        """ No replay command

        A NOP provides a way for either an originator or target to determine if the TCP connection is still open.
        """
        self._message = self.build_header(ENCAPSULATION_COMMAND['nop'], 0)
        self._send()

    def __repr__(self):
        return self._device_description

    def description(self):
        return self._device_description

    def list_identity(self):
        """ ListIdentity command to locate and identify potential target

        return true if the replay contains the device description
        """
        self._message = self.build_header(ENCAPSULATION_COMMAND['list_identity'], 0)
        self._send()
        self._receive()
        if self._check_reply():
            try:
                self._device_description = self._reply[63:-1]
                return True
            except Exception as e:
                raise CommError(e)
        return False

    def send_rr_data(self, msg):
        """ SendRRData transfer an encapsulated request/reply packet between the originator and target

        :param msg: The message to be send to the target
        :return: the replay received from the target
        """
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_rr_data"], len(msg))
        self._message += msg
        self._send()
        self._receive()
        return self._check_reply()

    def send_unit_data(self, msg):
        """ SendUnitData send encapsulated connected messages.

        :param msg: The message to be send to the target
        :return: the replay received from the target
        """
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_unit_data"], len(msg))
        self._message += msg
        self._send()
        self._receive()
        return self._check_reply()

    def get_status(self):
        """ Get the last status/error

        This method can be used after any call to get any details in case of error
        :return: A tuple containing (error group, error message)
        """
        return self._status

    def clear(self):
        """ Clear the last status/error

        :return: return am empty tuple
        """
        self._status = (0, "")

    def build_header(self, command, length):
        """ Build the encapsulate message header

        The header is 24 bytes fixed length, and includes the command and the length of the optional data portion.

         :return: the headre
        """
        try:
            h = command                                 # Command UINT
            h += pack_uint(length)                      # Length UINT
            h += pack_dint(self._session)                # Session Handle UDINT
            h += pack_dint(0)                           # Status UDINT
            h += self.attribs['context']                # Sender Context 8 bytes
            h += pack_dint(self.attribs['option'])      # Option UDINT
            return h
        except Exception as e:
            raise CommError(e)

    def register_session(self):
        """ Register a new session with the communication partner

        :return: None if any error, otherwise return the session number
        """
        if self._session:
            return self._session

        self._session = 0
        self._message = self.build_header(ENCAPSULATION_COMMAND['register_session'], 4)
        self._message += pack_uint(self.attribs['protocol version'])
        self._message += pack_uint(0)
        self._send()
        self._receive()
        if self._check_reply():
            self._session = unpack_dint(self._reply[4:8])
            logger.debug("Session ={0} has been registered.".format(print_bytes_line(self._reply[4:8])))
            return self._session

        self._status = 'Warning ! the session has not been registered.'
        logger.warning(self._status)
        return None

    def forward_open(self):
        """ CIP implementation of the forward open message

        Refer to ODVA documentation Volume 1 3-5.5.2

        :return: False if any error in the replayed message
        """
        if self._session == 0:
            self._status = (4, "A session need to be registered before to call forward_open.")
            raise CommError("A session need to be registered before to call forward open")

        forward_open_msg = [
            FORWARD_OPEN,
            pack_usint(2),
            CLASS_ID["8-bit"],
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_ID["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            pack_dint(0),
            self.attribs['cid'],
            self.attribs['csn'],
            self.attribs['vid'],
            self.attribs['vsn'],
            TIMEOUT_MULTIPLIER,
            '\x00\x00\x00',
            pack_dint(self.attribs['rpi'] * 1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            pack_dint(self.attribs['rpi'] * 1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            TRANSPORT_CLASS,  # Transport Class
            CONNECTION_SIZE['Backplane'],
            pack_usint(self.attribs['backplane']),
            pack_usint(self.attribs['cpu slot']),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_usint(1)
        ]

        if self.send_rr_data(
                build_common_packet_format(DATA_ITEM['Unconnected'], ''.join(forward_open_msg), ADDRESS_ITEM['UCMM'],)):
            self._target_cid = self._reply[44:48]
            self._target_is_connected = True
            return True
        self._status = (4, "forward_open returned False")
        return False

    def forward_close(self):
        """ CIP implementation of the forward close message

        Each connection opened with the froward open message need to be closed.
        Refer to ODVA documentation Volume 1 3-5.5.3

        :return: False if any error in the replayed message
        """

        if self._session == 0:
            self._status = (5, "A session need to be registered before to call forward_close.")
            raise CommError("A session need to be registered before to call forward_close.")

        forward_close_msg = [
            FORWARD_CLOSE,
            pack_usint(2),
            CLASS_ID["8-bit"],
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_ID["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            self.attribs['csn'],
            self.attribs['vid'],
            self.attribs['vsn'],
            CONNECTION_SIZE['Backplane'],
            '\x00',     # Reserved
            pack_usint(self.attribs['backplane']),
            pack_usint(self.attribs['cpu slot']),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_usint(1)
        ]
        if self.send_rr_data(
                build_common_packet_format(DATA_ITEM['Unconnected'], ''.join(forward_close_msg), ADDRESS_ITEM['UCMM'])):
            self._target_is_connected = False
            return True
        self._status = (5, "forward_close returned False")
        logger.warning(self._status)
        return False

    def un_register_session(self):
        """ Un-register a connection

        """
        self._message = self.build_header(ENCAPSULATION_COMMAND['unregister_session'], 0)
        self._send()
        self._session = None

    def _send(self):
        """
        socket send
        :return: true if no error otherwise false
        """
        try:
            logger.debug(print_bytes_msg(self._message, '-------------- SEND --------------'))
            self.__sock.send(self._message)
        except Exception as e:
            #self.clean_up()
            raise CommError(e)

    def _receive(self):
        """
        socket receive
        :return: true if no error otherwise false
        """
        try:
            self._reply = self.__sock.receive()
            logger.debug(print_bytes_msg(self._reply, '----------- RECEIVE -----------'))
        except Exception as e:
            #self.clean_up()
            raise CommError(e)

    def open(self, ip_address):
        """
        socket open
        :return: true if no error otherwise false
        """
        # handle the socket layer

        if not self._connection_opened:
            try:
                if self.__sock is None:
                    self.__sock = Socket()
                self.__sock.connect(ip_address, self.attribs['port'])
                self._connection_opened = True
                self.attribs['ip address'] = ip_address
                if self.register_session() is None:
                    self._status = (13, "Session not registered")
                    return False
                self.forward_close()
                return True
            except Exception as e:
                #self.clean_up()
                raise CommError(e)

    def close(self):
        """
        socket close
        :return: true if no error otherwise false
        """
        try:
            if self._target_is_connected:
                self.forward_close()
            if self._session != 0:
                self.un_register_session()
            if self.__sock:
                self.__sock.close()
        except Exception as e:
            raise CommError(e)

        self.clean_up()

    def clean_up(self):
        self.__sock = None
        self._target_is_connected = False
        self._session = 0
        self._connection_opened = False

    def is_connected(self):
        return self._connection_opened
