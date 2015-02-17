__author__ = "Agostino Ruscito <ruscito@gmail.com>"
__status__ = "testing"
__version__ = "0.1"
__date__ = "01 01 2015"

from cip_base import *
import logging


class ClxDriver(object):
    logger = logging.getLogger('ClxDriver')

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
        self.target_cid = None
        self.target_is_connected = False
        self._sequence = 1
        self.backplane = 1
        self.cpu_slot = 0
        self.rpi = 5000
        self._more_packets_available = False

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

    def register_session(self):
        self.logger.debug('>>> register_session')
        if self.session:
            self.logger.warn('Session already registered')
            return self.session

        self._message = self.build_header(ENCAPSULATION_COMMAND['register_session'], 4)
        self._message += pack_uint(self.protocol_version)
        self._message += pack_uint(0)
        self.send()
        self.receive()
        if self._check_replay():
            self.session = unpack_dint(self._replay[4:8])
            self.logger.debug('register_session (session =%s) >>>' % print_bytes_line(self._replay[4:8]))
            return self.session
        self.logger.warn('Leaving register_session (session =None) >>>')
        return None

    def un_register_session(self):
        self._message = self.build_header(ENCAPSULATION_COMMAND['unregister_session'], 0)
        self.send()
        self.session = None

    def send_rr_data(self, msg):
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_rr_data"], len(msg))
        self._message += msg
        self.send()
        self.receive()
        return self._check_replay()

    def send_unit_data(self, msg):
        self._message = self.build_header(ENCAPSULATION_COMMAND["send_unit_data"], len(msg))
        self._message += msg
        self.send()
        self.receive()
        return self._check_replay()

    def _get_sequence(self):
        if self._sequence < 65535:
            self._sequence += 1
        else:
            self._sequence = 1
        return self._sequence

    def _check_replay(self):
        """ _check_replay

        """
        try:
            if self._replay is None:
                self.logger.warning('%s without reply' % REPLAY_INFO[unpack_dint(self._message[:2])])
                return False
            # Get the type of command
            typ = unpack_uint(self._replay[:2])

            # Encapsulation status check
            if unpack_dint(self._replay[8:12]) != SUCCESS:
                self.logger.warning('%s reply error' % REPLAY_INFO[typ])
                self.logger.warning('{0} reply status:{1}'.format(
                    REPLAY_INFO[typ],
                    SERVICE_STATUS[unpack_dint(self._replay[8:12])]
                ))
                return False

            # Command Specific Status check
            if typ == unpack_uint(ENCAPSULATION_COMMAND["send_rr_data"]):
                status = unpack_sint(self._replay[42:43])
                if status == INSUFFICIENT_PACKETS:
                    self._more_packets_available = True
                    return True

                if status != SUCCESS:
                    self.logger.warning('send_rr_data reply status {0}: {1}'.format(
                        "{:0>2x} ".format(ord(self._replay[42:43])),
                        SERVICE_STATUS[status]))
                    self.logger.warning(get_extended_status(self._replay, 42))
                    return False

            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = unpack_sint(self._replay[48:49])
                if status == INSUFFICIENT_PACKETS:
                    self._more_packets_available = True
                    return True
                if status != SUCCESS:
                    self.logger.debug(print_bytes_msg(self._replay))
                    self.logger.warning('send_unit_data reply status {0}: {1}'.format(
                        "{:0>2x} ".format(ord(self._replay[48:49])),
                        SERVICE_STATUS[status]))
                    self.logger.warning(get_extended_status(self._replay, 48))
                    return False

        except LookupError:
            self.logger.warning('LookupError inside _check_replay')
        return True

    def forward_open(self):
        self.logger.debug('>>> forward_open')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
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
            pack_dint(0),
            self.cid,
            self.csn,
            self.vid,
            self.vsn,
            TIMEOUT_MULTIPLIER,
            '\x00\x00\x00',
            pack_dint(self.rpi*1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            pack_dint(self.rpi*1000),
            pack_uint(CONNECTION_PARAMETER['Default']),
            TRANSPORT_CLASS,  # Transport Class
            CONNECTION_SIZE['Backplane'],
            pack_sint(self.backplane),
            pack_sint(self.cpu_slot),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_sint(1)
        ]

        if self.send_rr_data(
                build_common_packet_format(
                        DATA_ITEM['Unconnected'],
                        ''.join(forward_open_msg),
                        ADDRESS_ITEM['Null'],
                        timeout=1
                )):
            self.target_cid = self._replay[44:48]
            self.target_is_connected = True
            self.logger.info("The target is connected end returned CID %s" % print_bytes_line(self.target_cid))
            self.logger.debug('forward_open >>>')
            return True
        self.logger.warning('forward_open returning False>>>')
        return False

    def forward_close(self, backplane=1, cpu_slot=0):
        self.logger.debug('>>> forward_close')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        forward_close_msg = [
            FORWARD_CLOSE,
            pack_sint(2),
            CLASS_ID["8-bit"],
            CLASS_CODE["Connection Manager"],  # Volume 1: 5-1
            INSTANCE_ID["8-bit"],
            CONNECTION_MANAGER_INSTANCE['Open Request'],
            PRIORITY,
            TIMEOUT_TICKS,
            self.csn,
            self.vid,
            self.vsn,
            CONNECTION_SIZE['Backplane'],
            '\x00',     # Reserved
            pack_sint(backplane),
            pack_sint(cpu_slot),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_sint(1)
        ]
        if self.send_rr_data(
                build_common_packet_format(
                        DATA_ITEM['Unconnected'],
                        ''.join(forward_close_msg),
                        ADDRESS_ITEM['Null'],
                        timeout=1
                )):
            self.target_is_connected = False
            self.logger.debug('forward_close >>>')
            return True
        self.logger.warning('forward_close returning False>>>')
        return False


    def read_tag(self, tag):
        """ read_tag

        """
        self.logger.debug('>>> read_tag')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        if not self.target_is_connected:
            self.logger.debug('target not connected yet. Will execute a forward_open to connect')
            if not self.forward_open():
                self.logger.warning("Target did not connected")
                return None

        rp = create_tag_rp(tag)

        if rp is None:
            self.logger.warning('Cannot create tag {0} request packet. Read not executed'.format(tag))
            return None

        # Creating the Message Request Packet
        message_request = [
            pack_uint(self._get_sequence()),
            chr(TAG_SERVICES_REQUEST['Read Tag']),  # the Request Service
            chr(len(rp) / 2),                       # the Request Path Size length in word
            rp,                                     # the request path
            pack_uint(1),                           # Add the number of tag to read
        ]

        if self.send_unit_data(
                build_common_packet_format(
                    DATA_ITEM['Connected'],
                    ''.join(message_request),
                    ADDRESS_ITEM['Connection Based'],
                    addr_data=self.target_cid,
                    timeout=1
                )):
            # Get the data type
            for key, value in DATA_TYPE.iteritems():
                if value == unpack_uint(self._replay[50:52]):
                    self.logger.debug('read_tag {0}={1} >>>'.format(tag, UNPACK_DATA_FUNCTION[key](self._replay[52:])))
                    return UNPACK_DATA_FUNCTION[key](self._replay[52:]), key
            self.logger.warning('read_tag returned none because data type is unknown>>>')
            return None
        else:
            self.logger.warning('read_tag returned None >>>')
            return None

    def write_tag(self, tag, value, typ):
        """ write_tag

        """
        self.logger.debug('>>> write_tag')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        if not self.target_is_connected:
            if not self.forward_open():
                self.logger.warning("Target did not connected")
                return None

        rp = create_tag_rp(tag)

        if rp is None:
            self.logger.warning('Cannot create tag {0} request packet. Read not executed'.format(tag))
            return None

        # Creating the Message Request Packet
        message_request = [
            pack_uint(self._get_sequence()),
            chr(TAG_SERVICES_REQUEST["Write Tag"]),   # the Request Service
            chr(len(rp) / 2),               # the Request Path Size length in word
            rp,                             # the request path
            pack_uint(DATA_TYPE[typ]),    # data type
            pack_uint(1),                    # Add the number of tag to write
            PACK_DATA_FUNCTION[typ](value)
        ]
        self.logger.debug('writing tag:{0} value:{1} type:{2}'.format(tag, value, typ))
        ret_val = self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self.target_cid,
                timeout=1
            )
        )
        self.logger.debug('write_tag >>>')
        return ret_val

    def _get_symbol_object_instances(self, instance=0, time_out=10):
        """ _get_symbol_object_instances

        """
        if self.session == 0:
            print("Session not registered yet.")
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

        # Send the UCMM Request
        self.send()

        # Get replay
        self.receive()

    def send(self):
        try:
            self.logger.debug(print_bytes_msg(self._message,  'SEND --------------'))
            self.__sock.send(self._message)
        except SocketError as e:
            self.logger.error('Error {0} during {1}'.format(e, 'send'), exc_info=True)
            return False

        return True

    def receive(self):
        try:
            self._replay = self.__sock.receive()
            self.logger.debug(print_bytes_msg(self._replay, 'RECEIVE -----------'))
        except SocketError as e:
            self.logger.error('Error {0} during {1}'.format(e, 'receive'), exc_info=True)
            self._replay = None
            return False

        return True

    def open(self, ip_address, backplane=1, cpu_slot=0, rpi=5000):
        self.logger.debug('>>> open %s' % ip_address)
        # handle the socket layer
        self.backplane = backplane
        self.cpu_slot = cpu_slot
        self.rpi = rpi
        if not self.connection_opened:
            try:
                self.__sock.connect(ip_address, self.port)
                self.connection_opened = True
                if self.register_session() is None:
                    self.logger.warning("Session not registered")
                    self.logger.debug('open >>>')
                    return False
                self.logger.debug('open >>>')
                return True
            except SocketError as e:
                self.logger.error('Error {0} during {1}'.format(e, 'open'), exc_info=True)
        return False

    def close(self):
        self.logger.debug('>>> close')
        if self.target_is_connected:
            self.forward_close()
        if self.session != 0:
            self.un_register_session()
        self.__sock.close()
        self.__sock = None
        self.session = 0
        self.connection_opened = False
        self.logger.debug('close >>>')