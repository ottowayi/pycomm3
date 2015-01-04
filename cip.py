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
        self._replay = None

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

    def get_address_type(self):
        return self._replay[ADDRESS_TYPE:ADDRESS_TYPE+2]

    def get_general_status(self):
        return ord(self._replay[OFFSET_MESSAGE_REQUEST+2:OFFSET_MESSAGE_REQUEST+3])

    def get_extended_status(self):
        return ord(self._replay[OFFSET_MESSAGE_REQUEST+4:])

    def returned_status(self):
        self.status = unpack_dint(self._replay[8:12])
        if self.status == 0x0000:
            return False
        elif self.status in STATUS:
            print "Returned %s" % STATUS[self.status]
        else:
            print "Returned Unrecognized error %d (0x%08x)" % (self.status, self.status)
        return True

    def parse_replay(self):
        if self._replay is None:
            return False

        if self.returned_status():
            return False

        # Get Command
        command = unpack_uint(self._replay[:2])

        if command == COMMAND['register_session']:
            self.session = unpack_dint(self._replay[4:8])
            self.session_registered = True
        elif command == COMMAND['list_identity']:
            pass
        elif command == COMMAND['list_services']:
            pass
        elif command == COMMAND['list_interfaces']:
            pass
        elif command == COMMAND['send_rr_data']:
            if unpack_uint(self.get_address_type()) == UCMM['Address Type ID']:
                # Is UCMM
                if self.get_general_status() != SUCCESS:
                    print SERVICE_STATUS[self.get_general_status()]

            print list(self._replay[OFFSET_MESSAGE_REQUEST:])
            print "Read =", unpack_dint(self._replay[-4:])
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
        self.send(msg)
        # parse the response
        self.parse_replay(self.__sock.receive())

    def register_session(self):
        msg = self.build_header(COMMAND['register_session'], 4)
        msg += pack_uint(self.protocol_version)
        msg += pack_uint(0)
        self.send(msg)

        self.receive()
        # parse the response
        self.parse_replay()

        return self.session

    def unregister_session(self):
        msg = self.build_header(COMMAND['unregister_session'], 0)
        self.send(msg)
        self.session = 0

    def read_tag(self, tag, time_out=10):
        # TO DO: add control tag's validity
        if self.session_registered:
            tag_length = len(tag)

            # Create the request path
            rp = [
                EXTENDED_SYMBOL,            # ANSI Ext. symbolic segment
                chr(tag_length)             # Length of the tag
            ]

            # Add the tag to the Request path
            for char in tag:
                rp.append(char)

            # Add pad byte because total length of Request path must be word-aligned
            if tag_length % 2:
                rp.append('\x00')

            # At this point the Request Path is completed,
            rp = ''.join(rp)

            # Creating the Message Request Packet
            mr = [
                chr(SERVICES_REQUEST['Read Tag']),  # the Request Service
                chr(len(rp) / 2),           # the Request Path Size length in word
                rp,                         # the request path
                pack_uint(1)                # Add the number of tag to read
            ]

            # join the the list
            packet = ''.join(mr)

            # preparing the head of the Command Specific data
            head = [
                pack_dint(UCMM['Interface Handle']),    # The Interface Handle: should be 0
                pack_uint(time_out),                    # Timeout
                pack_uint(UCMM['Item Count']),          # Item Count: should be 2
                pack_uint(UCMM['Address Type ID']),     # Address Type ID: should be 0
                pack_uint(UCMM['Address Length']),      # Address Length: should be 0
                pack_uint(UCMM['Data Type ID']),        # Data Type ID: should be 0x00b2 or 178
                pack_uint(len(packet))                  # Length of the MR request packet
            ]

            # Command Specific Data is composed by head and packet
            command_specific_data = ''.join(head) + packet

            # Now put together Encapsulation Header and Command Specific Data
            msg = self.build_header(COMMAND['send_rr_data'], len(command_specific_data)) + command_specific_data

            # Debug
            print_info(msg)

            # Send the UCMM Request
            self.send(msg)

            # Get replay
            self.receive()

            # parse the response
            self.parse_replay()

        else:
            print "session not registered yet"
            return None

    def send(self, msg):
        self.__sock.send(msg)
        return True

    def receive(self):
        self._replay = self.__sock.receive()
        return True

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