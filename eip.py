__version__ = "$Revision$"
# $Source$

import socket
import struct
from multiprocessing import Process, Event
from time import sleep

COMMAND = {
    "nop": 0x00,
    "list_targets": 0x01,
    "list_services": 0x04,
    "list_identity": 0x63,
    "list_interfaces": 0x64,
    "register_session": 0x65,
    "unregister_session": 0x66,
    "send_rr_data": 0x6F,
    "send_unit_data": 0x70

}

STATUS = {
    0x0000: "Success",
    0x0001: "The sender issued an invalid or unsupported encapsulation command",
    0x0002: "Insufficient memory",
    0x0003: "Poorly formed or incorrect data in the data portion",
    0x0064: "An originator used an invalid session handle when sending an encapsulation message to the target",
    0x0065: "The target received a message of invalid length",
    0x0069: "Unsupported Protocol Version"
}

SERVICES = {
    "Read Tag": 0x45,
    "Read Tag fragmented": 0x52,
    "Write Tag": 0x4d,
    "Write Data Fragmented": 0x53,
    "Read Modify Write Tag": 0x4c
}

MR_GENERAL_STATUS = {
    0x0000: "Success",
    0x0001: "Ext error code",
    0x0002: "Resource unavailable",
    0x0003: "Invalid parameters value",
    0x0004: "Path segment error",
    0x0005: "Path destination unknow",
    0x0006: "Partial transferred",
    0x0007: "Connection lost",
    0x0008: "Service not supported",
    0x0009: "Invalid attribute value",
    0x000A: "Attribute list error",
    0x000B: "Already in requested mode/state",
    0x000C: "Object state conflict",
    0x000D: "Object already exist",
    0x000E: "Attribute not settable",
    0x000F: "Privilege violation",
    0x0010: "Device state conflict",
    0x0011: "Reply data too large",
    0x0012: "Fragmentation of a primitive value",
    0x0013: "Not enough data",
    0x0014: "Attribute not supported",
    0x0015: "Too much data",
    0x0016: "Object does not exist",
    0x0017: "Service fragmentation sequence not in progress",
    0x0018: "No stored attribute data",
    0x0019: "Store operation failure",
    0x001A: "Routing failure,request packet too large",
    0x001B: "Routing failure,response packet too large",
    0x001C: "Missing attribute list entry data",
    0x001D: "Invalid attribute value list",
    0x001E: "Embedded service error",
    0x001F: "Vendor specific",
    0x0020: "Invalid parameter",
    0x0021: "Write once value or medium already written",
    0x0022: "Invalid reply received",
    0x0025: "Key failure in path",
    0x0026: "Path size invalid",
    0x0027: "Unexpected attribute in list",
    0x0028: "Invalid member ID",
    0x0029: "Member not settable",
    0x002A: "Group 2 only server general failure"
}

MR_EXTEND_STATUS = {
    0x0100: "Connection in use or Duplicate Forward Open",
    0x0103: "Transport Class and Trigger combination not supported",
    0x0106: "Ownership conflict",
    0x0107: "Connection not found at target application",
    0x0108: "Invalid session type",
    0x0109: "Invalid session size",
    0x0110: "Device not configured",
    0x0111: "RPI not supported",
    0x0113: "Connection manager cannot support any more connections",
    0x0114: "Vendor Id or product code in the key segment did not match the device",
    0x0115: "Product type in the key segment did not match the device",
    0x0116: "Major or minor revision information in the key segment did not match the device",
    0x0117: "Invalid session point",
    0x0118: "Invalid configuration format",
    0x0119: "Connection request fails since there is no controlling session currently open"
}


HEADER_SIZE = 24


def pack_uint(n):
    """pack 16 bit into 2 bytes little indian"""
    return struct.pack('<H', n)

def pack_dint(n):
    """pack 32 bit into 4 bytes little indian"""
    return struct.pack('<I', n)

def unpack_uint(st):
    """unpack 2 bytes little indian to int"""
    return int(struct.unpack('<H', st[0:2])[0])

def unpack_dint(st):
    """unpack 4 bytes little indian to int"""
    return int(struct.unpack('<I', st[0:4])[0])


def print_info(msg):
    """
    nice formatted print for the encapsulated message
    :param msg: the encapsulated message to print
    :return:
    """
    print
    n = len(msg)
    print "  Full length of EIP = %d (0x%04x)" % (n, n)

    cmd = unpack_uint(msg[:2])
    print "         EIP Command =",
    if cmd == 0:
        print "NOP"
    elif cmd == 0x01:
        print "List Targets"
    elif cmd == 0x04:
        print "List Services"
    elif cmd == 0x63:
        print "List Identity"
    elif cmd == 0x64:
        print "List Interfaces"
    elif cmd == 0x65:
        print "Register Session"
    elif cmd == 0x66:
        print "Unregister Session"
    elif cmd == 0x6f:
        print "SendRRData"
    elif cmd == 0x70:
        print "SendUnitData"
    else:
        print "Unknown command: 0x%02x" % cmd

    # The Data Part
    d = unpack_uint(msg[2:4])
    print "Attached Data Length = %d" % d

    n = unpack_dint(msg[4:8])
    print "      Session Handle = %d (0x%08x)" % (n, n)

    n = unpack_dint(msg[8:12])
    print "      Session Status = %d (0x%08x)" % (n, n)

    print "      Sender Context = %s" % msg[12:20]

    n = unpack_dint(msg[20:24])
    print "    Protocol Options = %d (0x%08x)" % (n, n)

    if 0 < d < 500:
        print "data =", list(msg[24:])
    elif d > 500:
        print "attached data is longer than 500 bytes"
    print

    return msg


def print_bytes(msg):
    print '[%d]\n' % len(msg)
    for ch in msg:
        print ("%02X" % ord(ch))
    return


class Eip:
    class ConnectionError(Exception):
        pass

    class Socket:
        def __init__(self, timeout):
            self.timeout = 5.0
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if timeout is None:
                self.sock.settimeout(self.timeout)
            else:
                self.sock.settimeout(timeout)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        @property
        def timeout(self):
            return self.timeout

        @timeout.setter
        def timeout(self, par):
            self.timeout = par

        def connect(self, host, port):
            try:
                self.sock.connect((host, port))
            except socket.timeout:
                raise RuntimeError("socket connection timeout")

        def send(self, msg):
            total_sent = 0
            while total_sent < len(msg):
                try:
                    sent = self.sock.send(msg[total_sent:])
                    if sent == 0:
                        raise RuntimeError("socket connection broken")
                    total_sent += sent
                except socket.error:
                    raise RuntimeError("socket connection broken")
            return total_sent

        def receive(self):
            msg_len = 28
            chunks = []
            bytes_recd = 0
            one_shot = True
            while bytes_recd < msg_len:
                try:
                    chunk = self.sock.recv(min(msg_len - bytes_recd, 2048))
                    if chunk == '':
                        raise RuntimeError("socket connection broken")

                    if one_shot:
                        msg_len = HEADER_SIZE + int(struct.unpack('<H', chunk[2:4])[0])
                        if msg_len == 0:
                            msg_len = HEADER_SIZE + int(struct.unpack('<H', chunk[24:28])[0])
                        print "Size of received msg %d" % msg_len
                        one_shot = False

                    chunks.append(chunk)
                    bytes_recd += len(chunk)
                except socket.error:
                    raise RuntimeError("socket connection broken")
            return ''.join(chunks)

        def close(self):
            self.sock.close()

    def __init__(self):
        self.__version__ = '0.1'
        self.__sock = self.Socket(None)
        self.session = 0
        self.context = '_pycomm_'
        self.protocol_version = 1
        self.status = 0
        self.name = 'ucmm'
        self.option = 0
        self.port = 0xAF12
        self.session_registered = False
        self.connection_opened = False


    @property
    def port(self):
        return self.port

    @port.setter
    def port(self, par):
        self.port = par

    @property
    def session(self):
        """The session property"""
        return self.session

    @session.setter
    def session(self, par):
        self.session = par

    @property
    def context(self):
        return self.context

    @context.setter
    def context(self, par):
        self.context = par

    @property
    def status(self):
        return self.status

    @status.setter
    def status(self, par):
        self.status = par

    @property
    def name(self):
        return self.port

    @name.setter
    def name(self, par):
        self.name = par

    def returned_status(self, rsp):
        self.status = unpack_dint(rsp[8:12])
        if self.status == 0x0000:
            print "Returned %s" % STATUS[self.status]
            return False
        elif self.status in STATUS:
            print "Returned %s" % STATUS[self.status]
        else:
            print "Returned Unrecognized error %d (0x%08x)" % (self.status, self.status)
        return True

    def parse_replay(self, rsp):
        if self.returned_status(rsp):
            return False

        # Get Command
        command = unpack_uint(rsp[:2])
        print "Command %d (0x%02x)" % (command, command)

        if command == COMMAND['register_session']:
            self.session = unpack_dint(rsp[4:8])
            print "COMMAND[register_session] Handle = %d (0x%04x)" % (self.session, self.session)
            self.session_registered = True
        elif command == COMMAND['list_identity']:
            print "COMMAND[ist_identity] item count %d" % unpack_uint(rsp[24:28])
            # print_bytes(rsp[28:])
        elif command == COMMAND['list_services']:
            print "COMMAND[list_services]  item count %d" % unpack_uint(rsp[24:28])
            # print_bytes(rsp[28:])
        elif command == COMMAND['list_interfaces']:
            print "COMMAND[list_interfaces]  item count %d" % unpack_uint(rsp[24:28])
            # print_bytes(rsp[28:])
        elif command == COMMAND['send_rr_data']:
            print "COMMAND[send_rr_data]  item count %d" % unpack_uint(rsp[24:28])
            # print_bytes(rsp[28:])
            print "Read =", unpack_dint(rsp[-4:])
            print "Read =", unpack_uint(rsp[-2:])
        else:
            print "Command %d (0x%02x) unknown or not implemented" % (command, command)

            return False
        print_info(rsp)
        return True

    def build_header(self, command, length):
        """
        build the encapsulated message header which is a 24 bytes fixed length.
        The header includes the command and the length of the optional data portion
        """
        h = pack_uint(command)          # Command UINT
        h += pack_uint(length)          # Length UINT
        h += pack_dint(self.session)    # Session Handle UDINT
        h += pack_dint(self.status)     # Status UDINT
        h += self.context               # Sender Context 8 bytes
        h += pack_dint(self.option)     # Option UDINT
        return h

    def nop(self):
        msg = self.build_header(COMMAND['nop'], 0)
        self.__sock.send(msg)

    def list_identity(self):
        msg = self.build_header(COMMAND['list_identity'], 0)
        self.send(msg)
        # parse the response
        self.parse_replay(self.__sock.receive())

    def list_services(self):
        msg = self.build_header(COMMAND['list_services'], 0)
        self.send(msg)
        # parse the response
        self.parse_replay(self.__sock.receive())

    def list_interfaces(self):
        msg = self.build_header(COMMAND['list_interfaces'], 0)
        self.send(msg)
        # parse the response
        self.parse_replay(self.__sock.receive())

    def register_session(self):
        msg = self.build_header(COMMAND['register_session'], 4)
        msg += pack_uint(self.protocol_version)
        msg += pack_uint(0)
        print_bytes(msg)
        self.__sock.send(msg)

        # parse the response
        self.parse_replay(self.__sock.receive())

        return self.session

    def send_rr_data(self):
        if self.session_registered:
            msg = self.build_header(COMMAND['send_rr_data'], 0)
            msg += pack_dint(0)     # Interface Handle shall be 0 for CIP
            msg += pack_uint(0)     # timeout
            self.send(msg)
            # parse the response
            self.parse_replay(self.__sock.receive())
        else:
            print "session not registered yet"

    def send_rr_data(self, tag):
        if self.session_registered:

            tag_length = len(tag)
            request_path = "\x91" + chr(tag_length)

            print "request_path =", list(request_path)

            request_path_length = tag_length + 2

            for char in tag:
                request_path += char
            print "request_path =", list(request_path)

            if tag_length % 2:
                # add pad byte because length must be word-aligned
                request_path += '\x00'
                request_path_length += 1
            print "request_path =", list(request_path)

            mr = '\x4c'     # Request Service
            mr += chr(request_path_length/2)   # Request Length
            print "mr =", list(mr)
            mr += request_path     # Request Path
            print "mr =", list(mr)
            mr += '\x01\x00' # \x01\x00\x01\x01'
            print "mr =", list(mr)

            msg = self.build_header(COMMAND['send_rr_data'], len(mr) + 16 )
            msg += pack_dint(0)         # Interface Handle shall be 0 for CIP
            msg += pack_uint(10)        # timeout
            msg += pack_uint(2)         # Item count this field should be 2
            msg += pack_uint(0)         # Address Type ID This field should be o indicating  UCMM message
            msg += pack_uint(0)         # Address Length should be 0 since UCMM  use the NULL address item
            msg += pack_uint(178)       # Data Type ID x00b2 or 178 in decimal
            msg += pack_uint(len(mr))
            msg += mr

            print "msg =", list(msg)

            self.send(msg)
            # parse the response
            #print "Received =", list(self.__sock.receive())
            self.parse_replay(self.__sock.receive())

        else:
            print "session not registered yet"
            return None

    def unregister_session(self):
        msg = self.build_header(COMMAND['unregister_session'], 0)
        self.__sock.send(msg)
        self.session = 0

    def send(self, msg):
        return self.__sock.send(msg)

    def receive(self, msg):
        return self.__sock.receive(msg)

    def open(self, ip_address):
        # handle the socket layer
        if not self.connection_opened:
            self.__sock.connect(ip_address, self.port)
            self.connection_opened = True
            return True
        return False

    def close(self):
        if self.session != 0:
            self.unregister_session()
        self.__sock.close()
        self.__sock = None
        self.session = 0
        self.connection_opened = False