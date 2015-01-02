_version__ = "$Revision$"
# $Source$

from cip_const import *
from cip_base import *


class Cip:
    def __init__(self):
        self.__version__ = '0.1'
        self.__sock = Socket(None)
        self.session = 0
        self.context = '_pycomm_'
        self.protocol_version = 1
        self.status = 0
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

    def register_session(self):
        msg = self.build_header(COMMAND['register_session'], 4)
        msg += pack_uint(self.protocol_version)
        msg += pack_uint(0)
        print_bytes(msg)
        self.__sock.send(msg)

        # parse the response
        self.parse_replay(self.__sock.receive())

        return self.session

    def unregister_session(self):
        msg = self.build_header(COMMAND['unregister_session'], 0)
        self.__sock.send(msg)
        self.session = 0

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

    def read_tag(self, tag):
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

    def send(self, msg):
        return self.__sock.send(msg)

    def receive(self, msg):
        return self.__sock.receive(msg)

    def open(self, ip_address):
        # handle the socket layer
        if not self.connection_opened:
            self.__sock.connect(ip_address, self.port)
            self.connection_opened = True
            self.register_session()
            return True
        return False

    def close(self):
        if self.session != 0:
            self.unregister_session()
        self.__sock.close()
        self.__sock = None
        self.session = 0
        self.connection_opened = False