__author__ = "Agostino Ruscito <ruscito@gmail.com>"
__status__ = "testing"
__version__ = "0.1"
__date__ = "01 01 2015"

import logging

from cip.cip_base import *


class Driver(object):

    logger = logging.getLogger('ClxDriver')

    def __init__(self):
        self.__version__ = '0.1'
        self.__sock = Socket(None)
        self.session = 0
        self.connection_opened = False
        self._replay = None
        self._message = None
        self.target_cid = None
        self.target_is_connected = False
        self.tag_list = []
        self._sequence = 1
        self._last_instance = 0
        self._more_packets_available = False
        self.attribs = {'context': '_pycomm_', 'protocol version': 1, 'rpi': 5000, 'port': 0xAF12, 'timeout': 10,
                        'backplane': 1, 'cpu slot': 0, 'option': 0, 'cid': '\x27\x04\x19\x71', 'csn': '\x27\x04',
                        'vid': '\x09\x10', 'vsn': '\x09\x10\x19\x71'}

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

    def build_header(self, command, length):
        """
        build the encapsulated message header which is a 24 bytes fixed length.
        The header includes the command and the length of the optional data portion
        """
        h = command                                 # Command UINT
        h += pack_uint(length)                      # Length UINT
        h += pack_dint(self.session)                # Session Handle UDINT
        h += pack_dint(0)                           # Status UDINT
        h += self.attribs['context']                # Sender Context 8 bytes
        h += pack_dint(self.attribs['option'])      # Option UDINT
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
        self._message += pack_uint(self.attribs['protocol version'])
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

    def _parse_tag_list(self, start_tag_ptr, status):
        tags_returned = self._replay[start_tag_ptr:]
        tags_returned_length = len(tags_returned)
        idx = 0
        instance = 0
        while idx < tags_returned_length:
            instance = unpack_dint(tags_returned[idx:idx+4])
            idx += 4
            tag_length = unpack_uint(tags_returned[idx:idx+2])
            idx += 2
            tag_name = tags_returned[idx:idx+tag_length]
            idx += tag_length
            symbol_type = unpack_uint(tags_returned[idx:idx+2])
            idx += 2
            self.tag_list.append((instance, tag_name, symbol_type))

        if status == SUCCESS:
            self._last_instance = -1
        elif status == 0x06:
            self._last_instance = instance + 1
        else:
            self.logger.warning('unknown status during _parse_tag_list')


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
                if unpack_sint(self._replay[40:41]) == I_TAG_SERVICES_REPLAY["Get Instance Attribute List"]:
                    self._parse_tag_list(44, status)
                    return True
                if status != SUCCESS:
                    self.logger.warning('send_rr_data reply status {0}: {1}'.format(
                        "{:0>2x} ".format(ord(self._replay[42:43])),
                        SERVICE_STATUS[status]))
                    self.logger.warning(get_extended_status(self._replay, 42))
                    return False

            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = unpack_sint(self._replay[48:49])
                if unpack_sint(self._replay[46:47]) == I_TAG_SERVICES_REPLAY["Get Instance Attribute List"]:
                    self._parse_tag_list(50, status)
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
            return False

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
            pack_sint(self.attribs['backplane']),
            pack_sint(self.attribs['cpu slot']),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_sint(1)
        ]

        if self.send_rr_data(
                build_common_packet_format(DATA_ITEM['Unconnected'], ''.join(forward_open_msg), ADDRESS_ITEM['UCMM'],)):
            self.target_cid = self._replay[44:48]
            self.target_is_connected = True
            self.logger.info("The target is connected end returned CID %s" % print_bytes_line(self.target_cid))
            self.logger.debug('forward_open >>>')
            return True
        self.logger.warning('forward_open returning False>>>')
        return False

    def forward_close(self):
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
            self.attribs['csn'],
            self.attribs['vid'],
            self.attribs['vsn'],
            CONNECTION_SIZE['Backplane'],
            '\x00',     # Reserved
            pack_sint(self.attribs['backplane']),
            pack_sint(self.attribs['cpu slot']),
            CLASS_ID["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_ID["8-bit"],
            pack_sint(1)
        ]
        if self.send_rr_data(
                build_common_packet_format(DATA_ITEM['Unconnected'], ''.join(forward_close_msg), ADDRESS_ITEM['UCMM'])):
            self.target_is_connected = False
            self.logger.debug('forward_close >>>')
            return True
        self.logger.warning('forward_close returning False>>>')
        return False

    def read_tag(self, tag):
        """ read_tag

        """
        multi_requests = False
        if isinstance(tag, list):
            multi_requests = True

        self.logger.debug('>>> read_tag')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        if not self.target_is_connected:
            self.logger.debug('target not connected yet. Will execute a forward_open to connect')
            if not self.forward_open():
                self.logger.warning("Target did not connected")
                return None

        if multi_requests:
            rp_list = []
            for t in tag:
                rp = create_tag_rp(t, multi_requests=True)
                if rp is None:
                    self.logger.warning('Cannot create tag {0} request packet. Read not executed'.format(tag))
                    return None
                else:
                    rp_list.append(chr(TAG_SERVICES_REQUEST['Read Tag']) + rp + pack_uint(1))
            message_request = build_multiple_service(rp_list, self._get_sequence())

        else:
            rp = create_tag_rp(tag)
            if rp is None:
                self.logger.warning('Cannot create tag {0} request packet. Read not executed'.format(tag))
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(self._get_sequence()),
                    chr(TAG_SERVICES_REQUEST['Read Tag']),  # the Request Service
                    chr(len(rp) / 2),                       # the Request Path Size length in word
                    rp,                                     # the request path
                    pack_uint(1)
                ]

        self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self.target_cid,
            ))

        if multi_requests:
            return parse_multi_request(self._replay, tag, 'READ')
        else:
            # Get the data type
            data_type = unpack_uint(self._replay[50:52])
            try:
                self.logger.debug('read_tag {0}={1} >>>'.format(
                    tag,
                    UNPACK_DATA_FUNCTION[I_DATA_TYPE[data_type]](self._replay[52:]))
                )
                return UNPACK_DATA_FUNCTION[I_DATA_TYPE[data_type]](self._replay[52:]), I_DATA_TYPE[data_type]
            except LookupError:
                self.logger.warning('read_tag data type unknown>>>')
                return None

    def write_tag(self, tag, value=None, typ=None):
        """ write_tag

        """
        multi_requests = False
        if isinstance(tag, list):
            multi_requests = True

        self.logger.debug('>>> write_tag')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        if not self.target_is_connected:
            if not self.forward_open():
                self.logger.warning("Target did not connected")
                return None

        if multi_requests:
            rp_list = []
            tag_to_remove = []
            idx = 0
            for name, value, typ in tag:
                # Create the request path to wrap the tag name
                rp = create_tag_rp(name, multi_requests=True)
                if rp is None:
                    self.logger.warning('Cannot create tag {0} request packet. Read not executed'.format(tag))
                    return None
                else:
                    try:    # Trying to add the rp to the request path list
                        val = PACK_DATA_FUNCTION[typ](value)
                        rp_list.append(
                            chr(TAG_SERVICES_REQUEST['Write Tag'])
                            + rp
                            + pack_uint(S_DATA_TYPE[typ])
                            + pack_uint(1)
                            + val
                        )
                        idx += 1
                    except (LookupError, struct.error) as e:
                        self.logger.warning('Tag:{0} type:{1} removed from write list. Error:{2}'.format(name, typ, e))
                        # The tag in idx position need to be removed from the rp list because has some kind of error
                        tag_to_remove.append(idx)

            # Remove the tags that have not been inserted in the request path list
            for position in tag_to_remove:
                del tag[position]
            # Create the message request
            message_request = build_multiple_service(rp_list, self._get_sequence())

        else:
            name, value, typ = tag
            rp = create_tag_rp(name)
            if rp is None:
                self.logger.warning('Cannot create tag {0} request packet. Write not executed'.format(tag))
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(self._get_sequence()),
                    chr(TAG_SERVICES_REQUEST["Write Tag"]),   # the Request Service
                    chr(len(rp) / 2),               # the Request Path Size length in word
                    rp,                             # the request path
                    pack_uint(S_DATA_TYPE[typ]),    # data type
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
            )
        )

        self.logger.debug('write_tag >>>')
        if multi_requests:
            return parse_multi_request(self._replay, tag, 'WRITE')
        else:
            return ret_val

    def get_tag_list(self):
        """ _get_symbol_object_instances

        """
        self.logger.debug('>>> get_tag_list')
        if self.session == 0:
            self.logger.warning("Session not registered yet.")
            return None

        if not self.target_is_connected:
            self.logger.debug('target not connected yet. Will execute a forward_open to connect')
            if not self.forward_open():
                self.logger.warning("Target did not connected")
                return None

        self._last_instance = 0

        while self._last_instance != -1:

            # Creating the Message Request Packet

            message_request = [
                pack_uint(self._get_sequence()),
                chr(TAG_SERVICES_REQUEST['Get Instance Attribute List']),
                # the Request Path Size length in word
                chr(3),
                # Request Path ( 20 6B 25 00 Instance )
                CLASS_ID["8-bit"],       # Class id = 20 from spec 0x20
                CLASS_CODE["Symbol Object"],  # Logical segment: Symbolic Object 0x6B
                INSTANCE_ID["16-bit"],   # Instance Segment: 16 Bit instance 0x25
                '\x00',
                pack_uint(self._last_instance),          # The instance
                # Request Data
                pack_uint(2),   # Number of attributes to retrieve
                pack_uint(1),   # Attribute 1: Symbol name
                pack_uint(2)    # Attribute 2: Symbol type
            ]

            self.send_unit_data(
                build_common_packet_format(
                    DATA_ITEM['Connected'],
                    ''.join(message_request),
                    ADDRESS_ITEM['Connection Based'],
                    addr_data=self.target_cid,
                ))

        self.logger.debug('get_tag_list >>>')
        return self.tag_list

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

    def open(self, ip_address):
        self.logger.debug('>>> open %s' % ip_address)
        # handle the socket layer
        if not self.connection_opened:
            try:
                self.__sock.connect(ip_address, self.attribs['port'])
                self.connection_opened = True
                if self.register_session() is None:
                    self.logger.warning("Session not registered")
                    self.logger.debug('open >>>')
                    return False
                self.logger.debug('open >>>')
                return True
            except Exception as e:
                self.logger.error('Error {0} during {1}'.format(e, 'open'), exc_info=True)
                self.logger.debug('open >>>')
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