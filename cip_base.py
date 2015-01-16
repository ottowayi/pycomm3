import struct
import socket
from cip_const import *


class ProtocolError(Exception):
    pass


class SocketError(Exception):
    pass


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
            raise SocketError("Socket timeout during connection.")

    def send(self, msg, timeout=0):
        if timeout != 0:
            self.sock.settimeout(timeout)
        total_sent = 0
        while total_sent < len(msg):
            try:
                sent = self.sock.send(msg[total_sent:])
                if sent == 0:
                    raise SocketError("socket connection broken.")
                total_sent += sent
            except socket.error:
                raise SocketError("socket connection broken.")
        return total_sent

    def receive(self, timeout):
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
                    raise SocketError("socket connection broken.")
                if one_shot:
                    data_size = int(struct.unpack('<H', chunk[2:4])[0])  # Length
                    msg_len = HEADER_SIZE + data_size
                    one_shot = False

                chunks.append(chunk)
                bytes_recd += len(chunk)
            except socket.error, e:
                raise SocketError(e)
        return ''.join(chunks)

    def close(self):
        self.sock.close()
