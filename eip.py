__version__ = "$Revision$"
# $Source$

import socket
import struct
from multiprocessing import Process, Event
from time import sleep

COMMAND = {"nop": 0x00,
               "list_targets": 0x01,
               "list_services": 0x04,
               "list_identity": 0x63,
               "list_interfaces": 0x64,
               "register_session": 0x65,
               "unregister_session": 0x66,
               "send_rr_data": 0x6F,
               "send_unit_data": 0x70}

STATUS = {0x0000: "0x0000: Success",
          0x0001: "0x0001: Unsupported Command",
          0x0002: "0x0002: No Resources to Process",
          0x0003: "0x0003: Poorly Formed/Bad Data Attached",
          0x0064: "0x0064: Invalid Session",
          0x0065: "0x0065: Request was Invalid Length",
          0x0069: "0x0069: Unsupported Protocol Version"}

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
                sent = self.sock.send(msg[total_sent:])
                if sent == 0:
                    raise RuntimeError("socket connection broken")
                total_sent += sent
            return total_sent

        def receive(self):
            msg_len = 28
            chunks = []
            bytes_recd = 0
            one_shot = True
            while bytes_recd < msg_len:
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

    def returned_error(self, rsp):
        self.status = unpack_dint(rsp[8:12])
        if self.status == 0x0000:
            return False
        elif self.status == 0x0001:
            error = STATUS[0x0001]
        elif self.status == 0x0002:
            error = STATUS[0x0002]
        elif self.status == 0x0003:
            error = STATUS[0x0003]
        elif self.status == 0x0064:
            error = STATUS[0x0064]
        elif self.status == 0x0065:
            error = STATUS[0x0065]
        elif self.status == 0x0069:
            error = STATUS[0x0069]
        else:
            error = "Unrecognized error %d (0x%08x)" % (self.status, self.status)
        print "Returned %s" % error
        return True

    def parse_replay(self, rsp):
        if self.returned_error(rsp):
            return False

        # Get Command
        command = unpack_uint(rsp[:2])
        print "Command %d (0x%02x)" % (command, command)

        if command == COMMAND['register_session']:
            self.session = unpack_dint(rsp[4:8])
            print "New Session Handle = %d (0x%04x)" % (self.session, self.session)
            self.session_registered = True
        elif command == COMMAND['list_identity']:
            print "item count %d" % unpack_uint(rsp[24:28])

            print_bytes(rsp[28:])
        else:
            print "Command %d (0x%02x) unknown or not implemented" % (command, command)
            return False

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
        print_info(msg)
        self.send(msg)
        # parse the response
        self.parse_replay(self.__sock.receive())

    def register_session(self):
        msg = self.build_header(COMMAND['register_session'], 4)
        msg += pack_uint(self.protocol_version)
        msg += pack_uint(0)
        self.__sock.send(msg)

        # parse the response
        self.parse_replay(self.__sock.receive())

        return self.session

    def unregister_session(self):
        msg = self.build_header(COMMAND['unregister_session'], 0)
        self.__sock.send(msg)

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