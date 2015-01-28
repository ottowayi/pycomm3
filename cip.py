_version__ = "$Revision$"
# $Source$

from cip_base import *


class TagList:
    def __init__(self):
        self.tagList = []

    def add_tag(self, t):
        self.tagList.append(t)


class Cip:
    def __init__(self):
        self.__version__ = '0.1'
        self.__sock = Socket(None)
        self.session = 0
        self.context = '_pycomm_'
        self.protocol_version = 1
        self.general_status = 0
        self.extend_status = 0
        self.option = 0
        self.port = 0xAF12
        self.connection_opened = False
        self._replay = None
        self._message = None
        self.cid = '\x27\x04\x19\x71'
        self.csn = '\x27\x04'
        self.vid = '\x09\x10'
        self.vsn = '\x09\x10\x19\x71'
        self.target_cid = pack_dint(0)


    def get_address_type(self):
        """
            Address Type Id  Position start 8 chars after Encapsulation HEADER (size 24)
            Address Type Id is UINT type
        :return:
        """
        return unpack_uint(self._replay[32:34])

    def service_replayed(self):
        """
            Replay Service 16 chars after Encapsulation HEADER (size 24)
            Replay Service 1 byte long
        :return:
        """
        return ord(self._replay[40])

    def get_extended_status(self):
        """
            Extended Status is  3 byte  after Replay Service
            Replay Service 1 byte long
        :return:
        """
        if ord(self._replay[43]) == 0:
            # no extend_status
            return 0
        else:
            # Extended status should be 2 byte
            self.extend_status = unpack_uint(self._replay[44:45])
        return self.extend_status

    def is_replay_ok(self):
        if self._replay is None:
            return False

        if unpack_dint(self._replay[8:12]) == SUCCESS:
            return True
        else:
            print (er)
            return False


    def parse(self):
        if self._replay is None:
            return False

        replay_status = unpack_dint(self._replay[8:12])
        if replay_status != SUCCESS:
            if replay_status in STATUS.keys():
                print "Returned %s" % STATUS[replay_status]
            else:
                print "Returned Unrecognized error %d (0x%08x)" % (replay_status, replay_status)
            return False

        # Get Command
        command = self._replay[:2]

        if command == ENCAPSULATION_COMMAND['register_session']:
            self.session = unpack_dint(self._replay[4:8])
            print 'Session Registered:'
            print_bytes(pack_dint(self.session))
        elif command == ENCAPSULATION_COMMAND['list_identity']:
            pass
        elif command == ENCAPSULATION_COMMAND['list_services']:
            pass
        elif command == ENCAPSULATION_COMMAND['list_interfaces']:
            pass
        elif command == ENCAPSULATION_COMMAND['send_rr_data']:
            pass

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
        h = command                     # Command UINT
        h += pack_uint(length)          # Length UINT
        h += pack_dint(self.session)    # Session Handle UDINT
        h += pack_dint(0)               # Status UDINT
        h += self.context               # Sender Context 8 bytes
        h += pack_dint(self.option)     # Option UDINT
        return h

    def nop(self):
        self._message = self.build_header(ENCAPSULATION_COMMAND['nop'], 0)
        self.send()

    def list_identity(self):
        self._message = self.build_header(ENCAPSULATION_COMMAND['list_identity'], 0)
        self.send()
        self.receive()
        self.parse()

    def register_session(self):
        self._message = self.build_header(ENCAPSULATION_COMMAND['register_session'], 4)
        self._message += pack_uint(self.protocol_version)
        self._message += pack_uint(0)
        self.send()
        self.receive()
        self.parse()
        return self.session

    def un_register_session(self):
        self._message = self.build_header(ENCAPSULATION_COMMAND['unregister_session'], 0)
        self.send()
        self.session = None

    def send_rr_data(self, msg):
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_rr_data"], len(msg))
        self._message += msg
        print_bytes(self._message)
        self.send()
        self.receive()

    def send_unit_data(self, msg):
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_unit_data"], len(msg))
        self._message += msg
        print_bytes(self._message)
        self.send()
        self.receive()

    @staticmethod
    def build_common_cpf(message_type, message, addr_type, addr_data=None, timeout=0):
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

    def forward_open(self, backplane=1, cpu_slot=0, rpi=5000):
        if self.session == 0:
            print "Session not registered yet."
            return None

        forward_open_msg = [
            FORWARD_OPEN,
            pack_sint(2),
            CLASS_ID["8-bit"],
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_ID["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            self.target_cid,
            self.cid,
            self.csn,
            self.vid,
            self.vsn,
            TIMEOUT_MULTIPLIER,
            '\x00\x00\x00',
            pack_dint(rpi*1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            pack_dint(rpi*1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            TRANSPORT_CLASS,  # Transport Class
            CONNECTION_SIZE['Backplane'],
            pack_sint(backplane),
            pack_sint(cpu_slot),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_sint(1)
        ]
        # forward_open_msg = ''.join(forward_open_msg)
        self.send_rr_data(Cip.build_common_cpf(DATA_ITEM['Unconnected'],
                                               ''.join(forward_open_msg),
                                               ADDRESS_ITEM['Null'],
                                               timeout=1))

    def read(self, backplane=1, cpu_slot=0, rpi=5000):
        self.forward_open()
        print_bytes(self._replay)
        tag = 'Counts'
        # Exit if replay is not  valid
        if self._replay is None:
            print 'forward_open without reply'
            return False

        # Exit if send_rr_data returned error
        if unpack_dint(self._replay[8:12]) != SUCCESS:
            print 'send_rr_data reply error'
            return False

        # Exit if  forward_open replay returned error
        if unpack_sint(self._replay[42:43]) != SUCCESS:
            print 'forward_open reply error'
            return False

        self.target_cid = self._replay[44:48]

        print_bytes(self.target_cid)

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
        message_request = [
            pack_uint(2),
            chr(TAG_SERVICES_REQUEST['Read Tag']),   # the Request Service
            chr(len(rp) / 2),               # the Request Path Size length in word
            rp,                             # the request path
            pack_uint(1),                    # Add the number of tag to read
            chr(TAG_SERVICES_REQUEST['Read Tag']),   # the Request Service
            chr(len(rp) / 2),               # the Request Path Size length in word
            rp,                             # the request path
            pack_uint(1),                    # Add the number of tag to read
        ]

        self.send_unit_data(Cip.build_common_cpf(DATA_ITEM['Connected'],
                                                 ''.join(message_request),
                                                 ADDRESS_ITEM['Connection Based'],
                                                 addr_data=self.target_cid))

        print_bytes(self._replay)

    def read_tag(self, tag, time_out=10):
        """
        From Rockwell Automation Publication 1756-PM020C-EN-P - November 2012:
        The Read Tag Service reads the data associated with the tag specified in the path.
            1) Any data that fits into the reply packet is returned, even if it does not all fit.
            2) If all the data does not fit into the packet, the error 0x06 is returned along
            with the data.
            3) When reading a two or three dimensional array of data, all dimensions
            must be specified.
            4) When reading a BOOL tag, the values returned for 0 and 1 are 0 and 0xFF,
            respectively.

        :param tag: The tag to read
        :param time_out: Operation Timeout
        :return: the tag value or None if any error
        """
        # TO DO: add control tag's validity
        self._replay = None
        self.forward_open()


    def _get_symbol_object_instances(self, instance=0, time_out=10):
        """
        When a tag is created, an instance of the Symbol class (Class ID 0x6B) is created
        inside the controller. The name of the tag is stored in attribute 1 of the instance.
        The data type of the tag is stored in attribute 2(*).

        We send this Message Request to get the list of tags name and type in the controller.

        (*) From Rockwell Automation Publication 1756-PM020C-EN-P - November 2012

        :param instance: The instance to retrieve. First time will be 0
        :param time_out: Operation Timeout
        :return: the message composed or None if any error
        """
        if self.session == 0:
            print "Session not registered yet."
            return None

        # Creating the Message Request Packet
        mr = [
            # Request Service
            chr(TAG_SERVICES_REQUEST['Get Instance Attribute List']),
            # the Request Path Size length in word
            chr(3),
            # Request Path ( 20 6B 25 00 Instance )
            CLASS_ID["8-bit"],       # Class id = 20 from spec 0x20
            CLASS_CODE["Symbol Object"],  # Logical segment: Symbolic Object 0x6B
            INSTANCE_ID["16-bit"],   # Instance Segment: 16 Bit instance 0x25
            '\x00',                       # Add pad byte because total length of Request path must be word-aligned
            pack_uint(instance),          # The instance
            # Request Data
            pack_uint(2),   # Number of attributes to retrieve
            pack_uint(1),   # Attribute 1: Symbol name
            pack_uint(2)    # Attribute 2: Symbol type
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
        self._message = self.build_header(ENCAPSULATION_COMMAND['send_rr_data'],
                                          len(command_specific_data)) + command_specific_data

        # Debug
        print_info(self._message)

        # Send the UCMM Request
        self.send()

        # Get replay
        self.receive()

    def send(self):
        try:
            self.__sock.send(self._message)
        except SocketError, e:
            print 'Error {%s} during {%s}'.format(e, 'send')
            return False

        return True

    def receive(self):
        try:
            self._replay = self.__sock.receive()
        except SocketError, e:
            print 'Error {%s} during {%s}'.format(e, 'receive')
            self._replay = None
            return False

        return True

    def open(self, ip_address):
        # handle the socket layer
        if not self.connection_opened:
            try:
                self.__sock.connect(ip_address, self.port)
                self.connection_opened = True
                self.register_session()
                return True
            except SocketError, e:
                print 'Error {%s} during {%s}'.format(e, 'open')

        return False

    def close(self):
        if self.session != 0:
            self.un_register_session()
        self.__sock.close()
        self.__sock = None
        self.session = 0
        self.connection_opened = False