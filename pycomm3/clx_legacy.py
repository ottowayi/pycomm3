import struct
from collections import defaultdict
from types import GeneratorType

from . import DataError, Tag, CommError
from .bytes_ import (pack_dint, pack_uint, pack_udint, pack_usint, unpack_usint, unpack_uint, unpack_dint,
                     UNPACK_DATA_FUNCTION, PACK_DATA_FUNCTION, DATA_FUNCTION_SIZE, print_bytes_msg)
from .clx import LogixDriver
from .const import (SUCCESS, EXTENDED_SYMBOL, ENCAPSULATION_COMMAND, DATA_TYPE, BITS_PER_INT_TYPE,
                    REPLY_INFO, TAG_SERVICES_REQUEST, PADDING_BYTE, ELEMENT_TYPE, DATA_ITEM, ADDRESS_ITEM,
                    CLASS_TYPE, CLASS_CODE, INSTANCE_TYPE, INSUFFICIENT_PACKETS, REPLY_START, MULTISERVICE_READ_OVERHEAD,
                    MULTISERVICE_WRITE_OVERHEAD, TAG_SERVICES_REPLY, get_service_status, get_extended_status)


class LogixDriverLegacy(LogixDriver):

    def _send(self, message):
        """
        socket send
        :return: true if no error otherwise false
        """
        try:
            if self.debug:
                self.__log.debug(print_bytes_msg(message, '>>> SEND >>>'))
            self._sock.send(message)
        except Exception as e:
            raise CommError(e)

    def _receive(self):
        """
        socket receive
        :return: reply data
        """
        try:
            reply = self._sock.receive()
        except Exception as e:
            raise CommError(e)
        else:
            if self.debug:
                self.__log.debug(print_bytes_msg(reply, '<<< RECEIVE <<<'))
            return reply

    def _create_tag_rp(self, tag):
        """ Creates a request pad

        It returns the request packed wrapped around the tag passed.
        If any error it returns none
        """
        tags = tag.split('.')
        if tags:
            base, *attrs = tags

            if self.use_instance_ids and base in self.tags:
                rp = [CLASS_TYPE['8-bit'],
                      CLASS_CODE['Symbol Object'],
                      INSTANCE_TYPE['16-bit'], b'\x00',
                      pack_uint(self.tags[base]['instance_id'])]
            else:
                base_tag, index = self._find_tag_index(base)
                base_len = len(base_tag)
                rp = [EXTENDED_SYMBOL,
                      pack_usint(base_len),
                      base_tag]
                if base_len % 2:
                    rp.append(PADDING_BYTE)
                if index is None:
                    return None
                else:
                    rp += index

            for attr in attrs:
                attr, index = self._find_tag_index(attr)
                tag_length = len(attr)
                # Create the request path
                attr_path = [EXTENDED_SYMBOL,
                             pack_usint(tag_length),
                             attr]
                # Add pad byte because total length of Request path must be word-aligned
                if tag_length % 2:
                    attr_path.append(PADDING_BYTE)
                # Add any index
                if index is None:
                    return None
                else:
                    attr_path += index
                rp += attr_path

            # At this point the Request Path is completed,
            request_path = b''.join(rp)
            request_path = bytes([len(request_path) // 2]) + request_path

            return request_path

        return None

    def _check_reply(self, reply):
        """ check the replayed message for error

            return the status error if unsuccessful, else None
        """
        try:
            if reply is None:
                return f'{REPLY_INFO[unpack_dint(reply[:2])]} without reply'
            # Get the type of command
            typ = unpack_uint(reply[:2])

            # Encapsulation status check
            if unpack_dint(reply[8:12]) != SUCCESS:
                return get_service_status(unpack_dint(reply[8:12]))

            # Command Specific Status check
            if typ == unpack_uint(ENCAPSULATION_COMMAND["send_rr_data"]):
                status = unpack_usint(reply[42:43])
                if status != SUCCESS:
                    return f"send_rr_data reply:{get_service_status(status)} - " \
                           f"Extend status:{get_extended_status(reply, 42)}"
                else:
                    return None
            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                service = reply[46]
                status = _unit_data_status(reply)
                # return None
                if status == INSUFFICIENT_PACKETS and service in (TAG_SERVICES_REPLY['Read Tag'],
                                                                  TAG_SERVICES_REPLY['Multiple Service Packet'],
                                                                  TAG_SERVICES_REPLY['Read Tag Fragmented'],
                                                                  TAG_SERVICES_REPLY['Write Tag Fragmented'],
                                                                  TAG_SERVICES_REPLY['Get Instance Attributes List'],
                                                                  TAG_SERVICES_REPLY['Get Attributes']):
                    return None
                if status == SUCCESS:
                    return None

                return f"send_unit_data reply:{get_service_status(status)} - " \
                       f"Extend status:{get_extended_status(reply, 48)}"

        except Exception as e:
            raise DataError(e)

    def read_tag(self, *tags):
        """ read tag from a connected plc

        Possible combination can be passed to this method:
                - ('Counts') a single tag name
                - (['ControlWord']) a list with one tag or many
                - (['parts', 'ControlWord', 'Counts'])

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :return: None is returned in case of error otherwise the tag list is returned
        """

        if not self._forward_open():
            self.__log.warning("Target did not connected. read_tag will not be executed.")
            raise DataError("Target did not connected. read_tag will not be executed.")

        if len(tags) == 1:
            if isinstance(tags[0], (list, tuple, GeneratorType)):
                return self._read_tag_multi(tags[0])
            else:
                return self._read_tag_single(tags[0])
        else:
            return self._read_tag_multi(tags)

    def _read_tag_multi(self, tags):
        tag_bits = defaultdict(list)
        rp_list, tags_read = [[]], [[]]
        request_len = 0
        for tag in tags:
            tag, bit = self._prep_bools(tag, 'BOOL', bits_only=True)
            read = bit is None or tag not in tag_bits
            if bit is not None:
                tag_bits[tag].append(bit)
            if read:
                rp = self._create_tag_rp(tag)
                if rp is None:
                    raise DataError(f"Cannot create tag {tag} request packet. read_tag will not be executed.")
                else:
                    tag_req_len = len(rp) + MULTISERVICE_READ_OVERHEAD
                    if tag_req_len + request_len >= self.connection_size:
                        rp_list.append([])
                        tags_read.append([])
                        request_len = 0
                    rp_list[-1].append(bytes([TAG_SERVICES_REQUEST['Read Tag']]) + rp + b'\x01\x00')
                    tags_read[-1].append(tag)
                    request_len += tag_req_len

        replies = []
        for req_list, tags_ in zip(rp_list, tags_read):
            message_request = self.build_multiple_service(req_list, self._sequence())
            msg = self.build_common_packet_format(DATA_ITEM['Connected'], b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'], addr_data=self._target_cid, )
            print(msg)
            success, reply = self.send_unit_data(msg)
            if not success:
                raise DataError(f"send_unit_data returned not valid data - {reply}")

            replies += self._parse_multiple_request_read(reply, tags_, tag_bits)
        return replies

    def _read_tag_single(self, tag):
        tag, bit = self._prep_bools(tag, 'BOOL', bits_only=True)
        rp = self._create_tag_rp(tag)
        if rp is None:
            self.__log.warning(f"Cannot create tag {tag} request packet. read_tag will not be executed.")
            return None
        else:
            # Creating the Message Request Packet
            message_request = [
                pack_uint(self._sequence()),
                bytes([TAG_SERVICES_REQUEST['Read Tag']]),  # the Request Service
                # bytes([len(rp) // 2]),  # the Request Path Size length in word
                rp,  # the request path
                b'\x01\x00',
            ]
        request = self.build_common_packet_format(DATA_ITEM['Connected'], b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'], addr_data=self._target_cid, )
        success, reply = self.send_unit_data(request)

        if success:
            data_type = unpack_uint(reply[50:52])
            typ = DATA_TYPE[data_type]
            try:
                value = UNPACK_DATA_FUNCTION[typ](reply[52:])
                if bit is not None:
                    value = bool(value & (1 << bit)) if bit < BITS_PER_INT_TYPE[typ] else None
                return Tag(tag, value, typ)
            except Exception as e:
                raise DataError(e)
        else:
            return Tag(tag, None, None, reply)

    @staticmethod
    def _parse_multiple_request_read(reply, tags, tag_bits=None):
        """ parse the message received from a multi request read:

        For each tag parsed, the information extracted includes the tag name, the value read and the data type.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50
        tag_bits = tag_bits or {}
        try:
            number_of_service_replies = unpack_uint(reply[offset:offset + 2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(reply[position:position + 2])
                general_status = unpack_usint(reply[start + 2:start + 3])
                tag = tags[index]
                if general_status == SUCCESS:
                    typ = DATA_TYPE[unpack_uint(reply[start + 4:start + 6])]
                    value_begin = start + 6
                    value_end = value_begin + DATA_FUNCTION_SIZE[typ]
                    value = UNPACK_DATA_FUNCTION[typ](reply[value_begin:value_end])
                    if tag in tag_bits:
                        for bit in tag_bits[tag]:
                            val = bool(value & (1 << bit)) if bit < BITS_PER_INT_TYPE[typ] else None
                            tag_list.append(Tag(f'{tag}.{bit}', val, 'BOOL'))
                    else:
                        tag_list.append(Tag(tag, value, typ))
                else:
                    tag_list.append(Tag(tag, None, None, get_service_status(general_status)))

            return tag_list
        except Exception as e:
            raise DataError(e)

    def read_array(self, tag, counts, raw=False):
        """ read array of atomic data type from a connected plc

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :param tag: the name of the tag to read
        :param counts: the number of element to read
        :param raw: the value should output as raw-value (hex)
        :return: None is returned in case of error otherwise the tag list is returned
        """

        if not self._target_is_connected and not self._forward_open():
            self.__log.warning("Target did not connected. read_tag will not be executed.")
            raise DataError("Target did not connected. read_tag will not be executed.")

        offset = 0
        last_idx = 0
        tags = b'' if raw else []

        while offset != -1:
            rp = self._create_tag_rp(tag)
            if rp is None:
                self.__log.warning(f"Cannot create tag {tag} request packet. read_tag will not be executed.")
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(self._sequence()),
                    bytes([TAG_SERVICES_REQUEST["Read Tag Fragmented"]]),  # the Request Service
                    # bytes([len(rp) // 2]),  # the Request Path Size length in word
                    rp,  # the request path
                    pack_uint(counts),
                    pack_dint(offset)
                ]
            msg = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                  b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'],
                                                  addr_data=self._target_cid, )
            success, reply = self.send_unit_data(msg)
            if not success:
                raise DataError(f"send_unit_data returned not valid data - {reply}")

            last_idx, offset = self._parse_fragment(reply, last_idx, offset, tags, raw)

        return tags

    def _parse_fragment(self, reply, last_idx, offset, tags, raw=False):
        """ parse the fragment returned by a fragment service."""

        try:
            status = _unit_data_status(reply)
            data_type = unpack_uint(reply[REPLY_START:REPLY_START + 2])
            fragment_returned = reply[REPLY_START + 2:]
        except Exception as e:
            raise DataError(e)

        fragment_returned_length = len(fragment_returned)
        idx = 0
        while idx < fragment_returned_length:
            try:
                typ = DATA_TYPE[data_type]
                if raw:
                    value = fragment_returned[idx:idx + DATA_FUNCTION_SIZE[typ]]
                else:
                    value = UNPACK_DATA_FUNCTION[typ](fragment_returned[idx:idx + DATA_FUNCTION_SIZE[typ]])
                idx += DATA_FUNCTION_SIZE[typ]
            except Exception as e:
                raise DataError(e)
            if raw:
                tags += value
            else:
                tags.append((last_idx, value))
                last_idx += 1

        if status == SUCCESS:
            offset = -1
        elif status == 0x06:
            offset += fragment_returned_length
        else:
            self.__log.warning('{0}: {1}'.format(get_service_status(status), get_extended_status(reply, 48)))
            offset = -1

        return last_idx, offset

    @staticmethod
    def _prep_bools(tag, typ, bits_only=True):
        """
        if tag is a bool and a bit of an integer, returns the base tag and the bit value,
        else returns the tag name and None

        """
        if typ != 'BOOL':
            return tag, None
        if not bits_only and tag.endswith(']'):
            try:
                base, idx = tag[:-1].rsplit(sep='[', maxsplit=1)
                idx = int(idx)
                base = f'{base}[{idx // 32}]'
                return base, idx
            except Exception:
                return tag, None
        else:
            try:
                base, bit = tag.rsplit('.', maxsplit=1)
                bit = int(bit)
                return base, bit
            except Exception:
                return tag, None

    @staticmethod
    def _dword_to_boolarray(tag, bit):
        base, tmp = tag.rsplit(sep='[', maxsplit=1)
        i = int(tmp[:-1])
        return f'{base}[{(i * 32) + bit}]'

    def _write_tag_multi_write(self, tags):
        rp_list = [[]]
        tags_added = [[]]
        request_len = 0
        for name, value, typ in tags:
            name, bit = self._prep_bools(name, typ, bits_only=False)  # check if bool & if bit of int or bool array
            # Create the request path to wrap the tag name
            rp = self._create_tag_rp(name, multi_requests=True)
            if rp is None:
                self.__log.warning(f"Cannot create tag {tags} req. packet. write_tag will not be executed")
                return None
            else:
                try:
                    if bit is not None:  # then it is a boolean array
                        rp = self._create_tag_rp(name, multi_requests=True)
                        request = bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]]) + rp
                        request += b''.join(self._make_write_bit_data(bit, value, bool_ary='[' in name))
                        if typ == 'BOOL' and name.endswith(']'):
                            name = self._dword_to_boolarray(name, bit)
                        else:
                            name = f'{name}.{bit}'
                    else:
                        request = (bytes([TAG_SERVICES_REQUEST["Write Tag"]]) +
                                   rp +
                                   pack_uint(DATA_TYPE[typ]) +
                                   b'\x01\x00' +
                                   PACK_DATA_FUNCTION[typ](value))

                    tag_req_len = len(request) + MULTISERVICE_WRITE_OVERHEAD
                    if tag_req_len + request_len >= self.connection_size:
                        rp_list.append([])
                        tags_added.append([])
                        request_len = 0
                    rp_list[-1].append(request)
                    request_len += tag_req_len
                except (LookupError, struct.error) as e:
                    self.__warning(f"Tag:{name} type:{typ} removed from write list. Error:{e}.")

                    # The tag in idx position need to be removed from the rp list because has some kind of error
                else:
                    tags_added[-1].append((name, value, typ))

        # Create the message request
        replies = []
        for req_list, tags_ in zip(rp_list, tags_added):
            message_request = self.build_multiple_service(req_list, self._sequence())
            msg = self.build_common_packet_format(DATA_ITEM['Connected'],
                                                  b''.join(message_request),
                                                  ADDRESS_ITEM['Connection Based'],
                                                  addr_data=self._target_cid, )
            success, reply = self.send_unit_data(msg)
            if success:
                replies += self._parse_multiple_request_write(tags_, reply)
            else:
                raise DataError(f"send_unit_data returned not valid data - {reply}")
        return replies

    def _write_tag_single_write(self, tag, value, typ):
        name, bit = self._prep_bools(tag, typ,
                                     bits_only=False)  # check if we're writing a bit of a integer rather than a BOOL

        rp = self._create_tag_rp(name)
        if rp is None:
            self.__log.warning(f"Cannot create tag {tag} request packet. write_tag will not be executed.")
            return None
        else:
            # Creating the Message Request Packet
            message_request = [
                pack_uint(self._sequence()),
                bytes([TAG_SERVICES_REQUEST["Read Modify Write Tag"]
                       if bit is not None else TAG_SERVICES_REQUEST["Write Tag"]]),
                # bytes([len(rp) // 2]),  # the Request Path Size length in word
                rp,  # the request path
            ]
            if bit is not None:
                try:
                    message_request += self._make_write_bit_data(bit, value, bool_ary='[' in name)
                except Exception as err:
                    raise DataError(f'Unable to write bit, invalid bit number {repr(err)}')
            else:
                message_request += [
                    pack_uint(DATA_TYPE[typ]),  # data type
                    pack_uint(1),  # Add the number of tag to write
                    PACK_DATA_FUNCTION[typ](value)
                ]
            request = self.build_common_packet_format(DATA_ITEM['Connected'], b''.join(message_request),
                                                      ADDRESS_ITEM['Connection Based'], addr_data=self._target_cid)
            success, reply = self.send_unit_data(request)
            return Tag(tag, value, typ, None if success else reply)

    @staticmethod
    def _make_write_bit_data(bit, value, bool_ary=False):
        or_mask, and_mask = 0x00000000, 0xFFFFFFFF

        if bool_ary:
            mask_size = 4
            bit = bit % 32
        else:
            mask_size = 1 if bit < 8 else 2 if bit < 16 else 4

        if value:
            or_mask |= (1 << bit)
        else:
            and_mask &= ~(1 << bit)

        return [pack_uint(mask_size), pack_udint(or_mask)[:mask_size], pack_udint(and_mask)[:mask_size]]

    @staticmethod
    def _parse_multiple_request_write(tags, reply):
        """ parse the message received from a multi request writ:

        For each tag parsed, the information extracted includes the tag name and the status of the writing.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50

        try:
            number_of_service_replies = unpack_uint(reply[offset:offset + 2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(reply[position:position + 2])
                general_status = unpack_usint(reply[start + 2:start + 3])
                error = None if general_status == SUCCESS else get_service_status(general_status)
                tag_list.append(Tag(*tags[index], error))
            return tag_list
        except Exception as e:
            raise DataError(e)

    def write_tag(self, tag, value=None, typ=None):
        """ write tag/tags from a connected plc

        Possible combination can be passed to this method:
                - ('tag name', Value, data type)  as single parameters or inside a tuple
                - ([('tag name', Value, data type), ('tag name2', Value, data type)]) as array of tuples

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        The type accepted are:
            - BOOL
            - SINT
            - INT
            - DINT
            - REAL
            - LINT
            - BYTE
            - WORD
            - DWORD
            - LWORD

        :param tag: tag name, or an array of tuple containing (tag name, value, data type)
        :param value: the value to write or none if tag is an array of tuple or a tuple
        :param typ: the type of the tag to write or none if tag is an array of tuple or a tuple
        :return: None is returned in case of error otherwise the tag list is returned
        """

        if not self._target_is_connected and not self._forward_open():
            self.__log.warning("Target did not connected. write_tag will not be executed.")
            raise DataError("Target did not connected. write_tag will not be executed.")

        if isinstance(tag, (list, tuple, GeneratorType)):
            return self._write_tag_multi_write(tag)
        else:
            if isinstance(tag, tuple):
                name, value, typ = tag
            else:
                name = tag
            return self._write_tag_single_write(name, value, typ)

    def write_array(self, tag, values, data_type, raw=False):
        """ write array of atomic data type from a connected plc
        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.
        :param tag: the name of the tag to read
        :param data_type: the type of tag to write
        :param values: the array of values to write, if raw: the frame with bytes
        :param raw: indicates that the values are given as raw values (hex)
        """

        if not isinstance(values, list):
            self.__log.warning("A list of tags must be passed to write_array.")
            raise DataError("A list of tags must be passed to write_array.")

        if not self._target_is_connected and not self._forward_open():
            self.__log.warning("Target did not connected. write_array will not be executed.")
            raise DataError("Target did not connected. write_array will not be executed.")

        array_of_values = b''
        byte_size = 0
        byte_offset = 0

        for i, value in enumerate(values):
            array_of_values += value if raw else PACK_DATA_FUNCTION[data_type](value)
            byte_size += DATA_FUNCTION_SIZE[data_type]

            if byte_size >= 450 or i == len(values) - 1:
                # create the message and send the fragment
                rp = self._create_tag_rp(tag)
                if rp is None:
                    self.__log.warning(f"Cannot create tag {tag} request packet write_array will not be executed.")
                    return None
                else:
                    # Creating the Message Request Packet
                    message_request = [
                        pack_uint(self._sequence()),
                        bytes([TAG_SERVICES_REQUEST["Write Tag Fragmented"]]),  # the Request Service
                        bytes([len(rp) // 2]),  # the Request Path Size length in word
                        rp,  # the request path
                        pack_uint(DATA_TYPE[data_type]),  # Data type to write
                        pack_uint(len(values)),  # Number of elements to write
                        pack_dint(byte_offset),
                        array_of_values  # Fragment of elements to write
                    ]
                    byte_offset += byte_size

                msg = self.build_common_packet_format(
                    DATA_ITEM['Connected'],
                    b''.join(message_request),
                    ADDRESS_ITEM['Connection Based'],
                    addr_data=self._target_cid,
                )

                success, reply = self.send_unit_data(msg)
                if not success:
                    raise DataError(f"send_unit_data returned not valid data - {reply}")

                array_of_values = b''
                byte_size = 0
        return True

    def write_string(self, tag, value, size=82):
        """
            Rockwell define different string size:
                STRING  STRING_12   STRING_16   STRING_20   STRING_40   STRING_8
            by default we assume size 82 (STRING)
        """
        data_tag = ".".join((tag, "DATA"))
        len_tag = ".".join((tag, "LEN"))

        # create an empty array
        data_to_send = [0] * size
        for idx, val in enumerate(value):
            try:
                unsigned = ord(val)
                data_to_send[idx] = unsigned - 256 if unsigned > 127 else unsigned
            except IndexError:
                break

        str_len = len(value)
        if str_len > size:
            str_len = size

        result_len = self.write_tag(len_tag, str_len, 'DINT')
        result_data = self.write_array(data_tag, data_to_send, 'SINT')
        return result_data and result_len

    def read_string(self, tag, str_len=None):
        data_tag = f'{tag}.DATA'
        if str_len is None:
            len_tag = f'{tag}.LEN'
            tmp = self.read_tag(len_tag)
            length, _ = tmp or (None, None)
        else:
            length = str_len

        if length:
            values = self.read_array(data_tag, length)
            if values:
                _, values = zip(*values)
                chars = ''.join(chr(v + 256) if v < 0 else chr(v) for v in values)
                string, *_ = chars.split('\x00', maxsplit=1)
                return string
        return None

    def _check_reply(self, reply):
        raise NotImplementedError("The method has not been implemented")

    def nop(self):
        """ No replay command

        A NOP provides a way for either an originator or target to determine if the TCP connection is still open.
        """
        message = self.build_header(ENCAPSULATION_COMMAND['nop'], 0)
        self._send(message)

    def send_unit_data(self, message):
        """ SendUnitData send encapsulated connected messages.

        :param message: The message to be send to the target
        :return: the replay received from the target
        """
        msg = self.build_header(ENCAPSULATION_COMMAND["send_unit_data"], len(message))
        msg += message
        self._send(msg)
        reply = self._receive()
        status = self._check_reply(reply)
        return (True, reply) if status is None else (False, status)

    def build_header(self, command, length):
        """ Build the encapsulate message header

        The header is 24 bytes fixed length, and includes the command and the length of the optional data portion.

         :return: the header
        """
        try:
            h = command
            h += pack_uint(length)  # Length UINT
            h += pack_dint(self._session)  # Session Handle UDINT
            h += pack_dint(0)  # Status UDINT
            h += self.attribs['context']  # Sender Context 8 bytes
            h += pack_dint(self.attribs['option'])  # Option UDINT
            return h
        except Exception as e:
            raise CommError(e)

    @staticmethod
    def create_tag_rp(tag, multi_requests=False):
        """ Create tag Request Packet

        It returns the request packed wrapped around the tag passed.
        If any error it returns none
        """
        tags = tag.encode().split(b'.')
        rp = []
        index = []
        for tag in tags:
            add_index = False
            # Check if is an array tag
            if b'[' in tag:
                # Remove the last square bracket
                tag = tag[:len(tag) - 1]
                # Isolate the value inside bracket
                inside_value = tag[tag.find(b'[') + 1:]
                # Now split the inside value in case part of multidimensional array
                index = inside_value.split(b',')
                # Flag the existence of one o more index
                add_index = True
                # Get only the tag part
                tag = tag[:tag.find(b'[')]
            tag_length = len(tag)

            # Create the request path
            rp.append(EXTENDED_SYMBOL)  # ANSI Ext. symbolic segment
            rp.append(bytes([tag_length]))  # Length of the tag

            # Add the tag to the Request path
            rp += [bytes([char]) for char in tag]
            # Add pad byte because total length of Request path must be word-aligned
            if tag_length % 2:
                rp.append(PADDING_BYTE)
            # Add any index
            if add_index:
                for idx in index:
                    val = int(idx)
                    if val <= 0xff:
                        rp.append(ELEMENT_TYPE["8-bit"])
                        rp.append(pack_usint(val))
                    elif val <= 0xffff:
                        rp.append(ELEMENT_TYPE["16-bit"])
                        rp.append(pack_uint(val))
                    elif val <= 0xfffffffff:
                        rp.append(ELEMENT_TYPE["32-bit"])
                        rp.append(pack_dint(val))
                    else:
                        # Cannot create a valid request packet
                        return None

        # At this point the Request Path is completed,
        if multi_requests:
            request_path = bytes([len(rp) // 2]) + b''.join(rp)
        else:
            request_path = b''.join(rp)
        return request_path

    @staticmethod
    def build_common_packet_format(message_type, message, addr_type, addr_data=None, timeout=10):
        """ build_common_packet_format

        It creates the common part for a CIP message. Check Volume 2 (page 2.22) of CIP specification  for reference
        """
        msg = pack_dint(0)  # Interface Handle: shall be 0 for CIP
        msg += pack_uint(timeout)  # timeout
        msg += pack_uint(2)  # Item count: should be at list 2 (Address and Data)
        msg += addr_type  # Address Item Type ID

        if addr_data is not None:
            msg += pack_uint(len(addr_data))  # Address Item Length
            msg += addr_data
        else:
            msg += b'\x00\x00'  # Address Item Length
        msg += message_type  # Data Type ID
        msg += pack_uint(len(message))  # Data Item Length
        msg += message
        return msg

    @staticmethod
    def build_multiple_service(rp_list, sequence=None):
        mr = [
            bytes([TAG_SERVICES_REQUEST["Multiple Service Packet"]]),  # the Request Service
            pack_usint(2),  # the Request Path Size length in word
            CLASS_TYPE["8-bit"],
            CLASS_CODE["Message Router"],
            INSTANCE_TYPE["8-bit"],
            b'\x01',  # Instance 1
            pack_uint(len(rp_list))  # Number of service contained in the request
        ]
        if sequence is not None:
            mr.insert(0, pack_uint(sequence))
        # Offset calculation
        offset = (len(rp_list) * 2) + 2
        for index, rp in enumerate(rp_list):
            mr.append(pack_uint(offset))  # Starting offset
            offset += len(rp)

        mr += rp_list
        return mr

    @staticmethod
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
        number_of_service_replies = unpack_uint(message[offset:offset + 2])
        tag_list = []
        for index in range(number_of_service_replies):
            position += 2
            start = offset + unpack_uint(message[position:position + 2])
            general_status = unpack_usint(message[start + 2:start + 3])

            if general_status == 0:
                if typ == "READ":
                    data_type = unpack_uint(message[start + 4:start + 6])
                    try:
                        value_begin = start + 6
                        value_end = value_begin + DATA_FUNCTION_SIZE[DATA_TYPE[data_type]]
                        value = message[value_begin:value_end]
                        tag_list.append((tags[index],
                                         UNPACK_DATA_FUNCTION[DATA_TYPE[data_type]](value),
                                         DATA_TYPE[data_type]))
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


def _unit_data_status(reply):
    return unpack_usint(reply[48:49])

