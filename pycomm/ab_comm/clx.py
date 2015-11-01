# -*- coding: utf-8 -*-
#
# clx.py - Ethernet/IP Client for Rockwell PLCs
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
from pycomm.cip.cip_base import *
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Driver(Base):
    """
    This Ethernet/IP client is based on Rockwell specification. Please refer to the link below for details.

    http://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf

    The following services have been implemented:
        - Read Tag Service (0x4c)
        - Read Tag Fragment Service (0x52)
        - Write Tag Service (0x4d)
        - Write Tag Fragment Service (0x53)
        - Multiple Service Packet (0x0a)

    The client has been successfully tested with the following PLCs:
        - CompactLogix 5330ERM
        - CompactLogix 5370
        - ControlLogix 5572 and 1756-EN2T Module

"""    

    def __init__(self):
        super(Driver, self).__init__()

        self._buffer = {}
        self._get_template_in_progress = False
        self.__version__ = '0.2'

    def get_last_tag_read(self):
        """ Return the last tag read by a multi request read

        :return: A tuple (tag name, value, type)
        """
        return self._last_tag_read

    def get_last_tag_write(self):
        """ Return the last tag write by a multi request write

        :return: A tuple (tag name, 'GOOD') if the write was successful otherwise (tag name, 'BAD')
        """
        return self._last_tag_write

    def _parse_instance_attribute_list(self, start_tag_ptr, status):
        """ extract the tags list from the message received

        :param start_tag_ptr: The point in the message string where the tag list begin
        :param status: The status of the message receives
        """
        tags_returned = self._reply[start_tag_ptr:]
        tags_returned_length = len(tags_returned)
        idx = 0
        instance = 0
        count = 0
        try:
            while idx < tags_returned_length:
                instance = unpack_dint(tags_returned[idx:idx+4])
                idx += 4
                tag_length = unpack_uint(tags_returned[idx:idx+2])
                idx += 2
                tag_name = tags_returned[idx:idx+tag_length]
                idx += tag_length
                symbol_type = unpack_uint(tags_returned[idx:idx+2])
                idx += 2
                count += 1
                self._tag_list.append({'instance_id': instance,
                                       'tag_name': tag_name,
                                       'symbol_type': symbol_type})
        except Exception as e:
            raise DataError(e)

        if status == SUCCESS:
            self._last_instance = -1
        elif status == 0x06:
            self._last_instance = instance + 1
        else:
            self._status = (1, 'unknown status during _parse_tag_list')
            self._last_instance = -1

    def _parse_structure_makeup_attributes(self, start_tag_ptr, status):
        """ extract the tags list from the message received

        :param start_tag_ptr: The point in the message string where the tag list begin
        :param status: The status of the message receives
        """
        self._buffer = {}

        if status != SUCCESS:
            self._buffer['Error'] = status
            return

        attribute = self._reply[start_tag_ptr:]
        idx = 4
        try:
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                self._buffer['object_definition_size'] = unpack_dint(attribute[idx:idx + 4])
            else:
                self._buffer['Error'] = 'object_definition Error'
                return

            idx += 6
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                self._buffer['structure_size'] = unpack_dint(attribute[idx:idx + 4])
            else:
                self._buffer['Error'] = 'structure Error'
                return

            idx += 6
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                self._buffer['member_count'] = unpack_uint(attribute[idx:idx + 2])
            else:
                self._buffer['Error'] = 'member_count Error'
                return

            idx += 4
            if unpack_uint(attribute[idx:idx + 2]) == SUCCESS:
                idx += 2
                self._buffer['structure_handle'] = unpack_uint(attribute[idx:idx + 2])
            else:
                self._buffer['Error'] = 'structure_handle Error'
                return

            return self._buffer

        except Exception as e:
            raise DataError(e)

    def _parse_template(self, start_tag_ptr, status):
        """ extract the tags list from the message received

        :param start_tag_ptr: The point in the message string where the tag list begin
        :param status: The status of the message receives
        """
        tags_returned = self._reply[start_tag_ptr:]
        bytes_received = len(tags_returned)

        self._buffer += tags_returned

        if status == SUCCESS:
            self._get_template_in_progress = False

        elif status == 0x06:
            self._byte_offset += bytes_received
        else:
            self._status = (1, 'unknown status {0} during _parse_template'.format(status))
            self.logger.warning(self._status)
            self._last_instance = -1

    def _parse_fragment(self, start_ptr, status):
        """ parse the fragment returned by a fragment service.

        :param start_ptr: Where the fragment start within the replay
        :param status: status field used to decide if keep parsing or stop
        """
        try:
            data_type = unpack_uint(self._reply[start_ptr:start_ptr+2])
            fragment_returned = self._reply[start_ptr+2:]
        except Exception as e:
            raise DataError(e)

        fragment_returned_length = len(fragment_returned)
        idx = 0

        while idx < fragment_returned_length:
            try:
                typ = I_DATA_TYPE[data_type]
                if self._output_raw:
                    value = fragment_returned[idx:idx+DATA_FUNCTION_SIZE[typ]]
                else:
                    value = UNPACK_DATA_FUNCTION[typ](fragment_returned[idx:idx+DATA_FUNCTION_SIZE[typ]])
                idx += DATA_FUNCTION_SIZE[typ]
            except Exception as e:
                raise DataError(e)
            if self._output_raw:
                self._tag_list += value
            else:
                self._tag_list.append((self._last_position, value))
                self._last_position += 1

        if status == SUCCESS:
            self._byte_offset = -1
        elif status == 0x06:
            self._byte_offset += fragment_returned_length
        else:
            self._status = (2, 'unknown status during _parse_fragment')
            self._byte_offset = -1

    def _parse_multiple_request_read(self, tags):
        """ parse the message received from a multi request read:

        For each tag parsed, the information extracted includes the tag name, the value read and the data type.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50
        try:
            number_of_service_replies = unpack_uint(self._reply[offset:offset+2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(self._reply[position:position+2])
                general_status = unpack_usint(self._reply[start+2:start+3])

                if general_status == 0:
                    data_type = unpack_uint(self._reply[start+4:start+6])
                    value_begin = start + 6
                    value_end = value_begin + DATA_FUNCTION_SIZE[I_DATA_TYPE[data_type]]
                    value = self._reply[value_begin:value_end]
                    self._last_tag_read = (tags[index], UNPACK_DATA_FUNCTION[I_DATA_TYPE[data_type]](value),
                                           I_DATA_TYPE[data_type])
                else:
                    self._last_tag_read = (tags[index], None, None)

                tag_list.append(self._last_tag_read)

            return tag_list
        except Exception as e:
            raise DataError(e)

    def _parse_multiple_request_write(self, tags):
        """ parse the message received from a multi request writ:

        For each tag parsed, the information extracted includes the tag name and the status of the writing.
        Those information are appended to the tag list as tuple

        :return: the tag list
        """
        offset = 50
        position = 50
        try:
            number_of_service_replies = unpack_uint(self._reply[offset:offset+2])
            tag_list = []
            for index in range(number_of_service_replies):
                position += 2
                start = offset + unpack_uint(self._reply[position:position+2])
                general_status = unpack_usint(self._reply[start+2:start+3])

                if general_status == 0:
                    self._last_tag_write = (tags[index] + ('GOOD',))
                else:
                    self._last_tag_write = (tags[index] + ('BAD',))

                tag_list.append(self._last_tag_write)
            return tag_list
        except Exception as e:
            raise DataError(e)

    def _check_reply(self):
        """ check the replayed message for error

        """
        self._more_packets_available = False
        try:
            if self._reply is None:
                self._status = (3, '%s without reply' % REPLAY_INFO[unpack_dint(self._message[:2])])
                return False
            # Get the type of command
            typ = unpack_uint(self._reply[:2])

            # Encapsulation status check
            if unpack_dint(self._reply[8:12]) != SUCCESS:
                self._status = (3, "{0} reply status:{1}".format(REPLAY_INFO[typ],
                                                                 SERVICE_STATUS[unpack_dint(self._reply[8:12])]))
                return False

            # Command Specific Status check
            if typ == unpack_uint(ENCAPSULATION_COMMAND["send_rr_data"]):
                status = unpack_usint(self._reply[42:43])
                if status != SUCCESS:
                    self._status = (3, "send_rr_data reply:{0} - Extend status:{1}".format(
                        SERVICE_STATUS[status], get_extended_status(self._reply, 42)))
                    return False
                else:
                    return True
            elif typ == unpack_uint(ENCAPSULATION_COMMAND["send_unit_data"]):
                status = unpack_usint(self._reply[48:49])
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Read Tag Fragmented"]:
                    self._parse_fragment(50, status)
                    return True
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Get Instance Attributes List"]:
                    self._parse_instance_attribute_list(50, status)
                    return True
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Get Attributes"]:
                    self._parse_structure_makeup_attributes(50, status)
                    return True
                if unpack_usint(self._reply[46:47]) == I_TAG_SERVICES_REPLY["Read Template"] and \
                        self._get_template_in_progress:
                    self._parse_template(50, status)
                    return True
                if status == 0x06:
                    self._status = (3, "Insufficient Packet Space")
                    self._more_packets_available = True
                elif status != SUCCESS:
                    self._status = (3, "send_unit_data reply:{0} - Extend status:{1}".format(
                        SERVICE_STATUS[status], get_extended_status(self._reply, 48)))
                    return False
                else:
                    return True

            return True
        except Exception as e:
            raise DataError(e)

    def read_tag(self, tag):
        """ read tag from a connected plc

        Possible combination can be passed to this method:
                - ('Counts') a single tag name
                - (['ControlWord']) a list with one tag or many
                - (['parts', 'ControlWord', 'Counts'])

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :return: None is returned in case of error otherwise the tag list is returned
        """
        multi_requests = False
        if isinstance(tag, list):
            multi_requests = True

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (6, "Target did not connected. read_tag will not be executed.")
                self.logger.warning(self._status)
                raise DataError("Target did not connected. read_tag will not be executed.")

        if multi_requests:
            rp_list = []
            for t in tag:
                rp = create_tag_rp(t, multi_requests=True)
                if rp is None:
                    self._status = (6, "Cannot create tag {0} request packet. read_tag will not be executed.".format(tag))
                    raise DataError("Cannot create tag {0} request packet. read_tag will not be executed.".format(tag))
                else:
                    rp_list.append(chr(TAG_SERVICES_REQUEST['Read Tag']) + rp + pack_uint(1))
            message_request = build_multiple_service(rp_list, Base._get_sequence())

        else:
            rp = create_tag_rp(tag)
            if rp is None:
                self._status = (6, "Cannot create tag {0} request packet. read_tag will not be executed.".format(tag))
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(Base._get_sequence()),
                    chr(TAG_SERVICES_REQUEST['Read Tag']),  # the Request Service
                    chr(len(rp) / 2),                       # the Request Path Size length in word
                    rp,                                     # the request path
                    pack_uint(1)
                ]

        if self.send_unit_data(
                build_common_packet_format(
                    DATA_ITEM['Connected'],
                    ''.join(message_request),
                    ADDRESS_ITEM['Connection Based'],
                    addr_data=self._target_cid,
                )) is None:
            raise DataError("send_unit_data returned not valid data")

        if multi_requests:
            return self._parse_multiple_request_read(tag)
        else:
            # Get the data type
            data_type = unpack_uint(self._reply[50:52])
            try:
                return UNPACK_DATA_FUNCTION[I_DATA_TYPE[data_type]](self._reply[52:]), I_DATA_TYPE[data_type]
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
        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (7, "Target did not connected. read_tag will not be executed.")
                self.logger.warning(self._status)
                raise DataError("Target did not connected. read_tag will not be executed.")

        self._byte_offset = 0
        self._last_position = 0
        self._output_raw = raw

        if self._output_raw:
            self._tag_list = ''
        else:
            self._tag_list = []
        while self._byte_offset != -1:
            rp = create_tag_rp(tag)
            if rp is None:
                self._status = (7, "Cannot create tag {0} request packet. read_tag will not be executed.".format(tag))
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(Base._get_sequence()),
                    chr(TAG_SERVICES_REQUEST["Read Tag Fragmented"]),  # the Request Service
                    chr(len(rp) / 2),                                  # the Request Path Size length in word
                    rp,                                                # the request path
                    pack_uint(counts),
                    pack_dint(self._byte_offset)
                ]

            if self.send_unit_data(
                    build_common_packet_format(
                        DATA_ITEM['Connected'],
                        ''.join(message_request),
                        ADDRESS_ITEM['Connection Based'],
                        addr_data=self._target_cid,
                    )) is None:
                raise DataError("send_unit_data returned not valid data")

        return self._tag_list

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
            - INT'
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
        multi_requests = False
        if isinstance(tag, list):
            multi_requests = True

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (8, "Target did not connected. write_tag will not be executed.")
                self.logger.warning(self._status)
                raise DataError("Target did not connected. write_tag will not be executed.")

        if multi_requests:
            rp_list = []
            tag_to_remove = []
            idx = 0
            for name, value, typ in tag:
                # Create the request path to wrap the tag name
                rp = create_tag_rp(name, multi_requests=True)
                if rp is None:
                    self._status = (8, "Cannot create tag{0} req. packet. write_tag will not be executed".format(tag))
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
                        self._status = (8, "Tag:{0} type:{1} removed from write list. Error:{2}.".format(name, typ, e))

                        # The tag in idx position need to be removed from the rp list because has some kind of error
                        tag_to_remove.append(idx)

            # Remove the tags that have not been inserted in the request path list
            for position in tag_to_remove:
                del tag[position]
            # Create the message request
            message_request = build_multiple_service(rp_list, Base._get_sequence())

        else:
            if isinstance(tag, tuple):
                name, value, typ = tag
            else:
                name = tag

            rp = create_tag_rp(name)
            if rp is None:
                self._status = (8, "Cannot create tag {0} request packet. write_tag will not be executed.".format(tag))
                logger.warning(self._status)
                return None
            else:
                # Creating the Message Request Packet
                message_request = [
                    pack_uint(Base._get_sequence()),
                    chr(TAG_SERVICES_REQUEST["Write Tag"]),   # the Request Service
                    chr(len(rp) / 2),               # the Request Path Size length in word
                    rp,                             # the request path
                    pack_uint(S_DATA_TYPE[typ]),    # data type
                    pack_uint(1),                    # Add the number of tag to write
                    PACK_DATA_FUNCTION[typ](value)
                ]

        ret_val = self.send_unit_data(
            build_common_packet_format(
                DATA_ITEM['Connected'],
                ''.join(message_request),
                ADDRESS_ITEM['Connection Based'],
                addr_data=self._target_cid,
            )
        )

        if multi_requests:
            return self._parse_multiple_request_write(tag)
        else:
            if ret_val is None:
                raise DataError("send_unit_data returned not valid data")
            return ret_val

    def write_array(self, tag, data_type, values, raw=False):
        """ write array of atomic data type from a connected plc

        At the moment there is not a strong validation for the argument passed. The user should verify
        the correctness of the format passed.

        :param tag: the name of the tag to read
        :param data_type: the type of tag to write
        :param values: the array of values to write, if raw: the frame with bytes
        :param raw: indicates that the values are given as raw values (hex)
        """
        if not isinstance(values, list):
            self._status = (9, "A list of tags must be passed to write_array.")
            logger.warning(self._status)
            raise DataError("A list of tags must be passed to write_array.")

        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (9, "Target did not connected. write_array will not be executed.")
                logger.warning(self._status)
                raise DataError("Target did not connected. write_array will not be executed.")

        array_of_values = ""
        byte_size = 0
        byte_offset = 0

        for i, value in enumerate(values):
            if raw:
                array_of_values += value
            else:
                array_of_values += PACK_DATA_FUNCTION[data_type](value)
            byte_size += DATA_FUNCTION_SIZE[data_type]

            if byte_size >= 450 or i == len(values)-1:
                # create the message and send the fragment
                rp = create_tag_rp(tag)
                if rp is None:
                    self._status = (9, "Cannot create tag {0} request packet. \
                        write_array will not be executed.".format(tag))
                    return None
                else:
                    # Creating the Message Request Packet
                    message_request = [
                        pack_uint(Base._get_sequence()),
                        chr(TAG_SERVICES_REQUEST["Write Tag Fragmented"]),  # the Request Service
                        chr(len(rp) / 2),                                   # the Request Path Size length in word
                        rp,                                                 # the request path
                        pack_uint(S_DATA_TYPE[data_type]),                  # Data type to write
                        pack_uint(len(values)),                             # Number of elements to write
                        pack_dint(byte_offset),
                        array_of_values                                     # Fragment of elements to write
                    ]
                    byte_offset += byte_size

                if self.send_unit_data(
                        build_common_packet_format(
                            DATA_ITEM['Connected'],
                            ''.join(message_request),
                            ADDRESS_ITEM['Connection Based'],
                            addr_data=self._target_cid,
                        )) is None:
                    raise DataError("send_unit_data returned not valid data")
                array_of_values = ""
                byte_size = 0

    def _get_instance_attribute_list_service(self):
        """ Step 1: Finding user-created controller scope tags in a Logix5000 controller

        This service returns instance IDs for each created instance of the symbol class, along with a list
        of the attribute data associated with the requested attribute
        """
        try:
            if not self._target_is_connected:
                if not self.forward_open():
                    self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                    logger.warning(self._status)
                    raise DataError("Target did not connected. get_tag_list will not be executed.")

            self._last_instance = 0

            self._get_template_in_progress = True
            while self._last_instance != -1:

                # Creating the Message Request Packet

                message_request = [
                    pack_uint(Base._get_sequence()),
                    chr(TAG_SERVICES_REQUEST['Get Instance Attributes List']),  # STEP 1
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

                if self.send_unit_data(
                        build_common_packet_format(
                            DATA_ITEM['Connected'],
                            ''.join(message_request),
                            ADDRESS_ITEM['Connection Based'],
                            addr_data=self._target_cid,
                        )) is None:
                    raise DataError("send_unit_data returned not valid data")

            self._get_template_in_progress = False

        except Exception as e:
            raise DataError(e)

    def _get_structure_makeup(self, instance_id):
        """
        get the structure makeup for a specific structure
        """
        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                logger.warning(self._status)
                raise DataError("Target did not connected. get_tag_list will not be executed.")

        message_request = [
            pack_uint(self._get_sequence()),
            chr(TAG_SERVICES_REQUEST['Get Attributes']),
            chr(3),                         # Request Path ( 20 6B 25 00 Instance )
            CLASS_ID["8-bit"],              # Class id = 20 from spec 0x20
            CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
            INSTANCE_ID["16-bit"],          # Instance Segment: 16 Bit instance 0x25
            '\x00',
            pack_uint(instance_id),
            pack_uint(4),  # Number of attributes
            pack_uint(4),  # Template Object Definition Size UDINT
            pack_uint(5),  # Template Structure Size UDINT
            pack_uint(2),  # Template Member Count UINT
            pack_uint(1)   # Structure Handle We can use this to read and write UINT
        ]

        if self.send_unit_data(
                build_common_packet_format(DATA_ITEM['Connected'],
                                           ''.join(message_request), ADDRESS_ITEM['Connection Based'],
                                           addr_data=self._target_cid,)) is None:
            raise DataError("send_unit_data returned not valid data")

        return self._buffer

    def _read_template(self, instance_id, object_definition_size):
        """ get a list of the tags in the plc

        """
        if not self._target_is_connected:
            if not self.forward_open():
                self._status = (10, "Target did not connected. get_tag_list will not be executed.")
                logger.warning(self._status)
                raise DataError("Target did not connected. get_tag_list will not be executed.")

        self._byte_offset = 0
        self._buffer = ""
        self._get_template_in_progress = True

        try:
            while self._get_template_in_progress:

                # Creating the Message Request Packet

                message_request = [
                    pack_uint(self._get_sequence()),
                    chr(TAG_SERVICES_REQUEST['Read Template']),
                    chr(3),                         # Request Path ( 20 6B 25 00 Instance )
                    CLASS_ID["8-bit"],              # Class id = 20 from spec 0x20
                    CLASS_CODE["Template Object"],  # Logical segment: Template Object 0x6C
                    INSTANCE_ID["16-bit"],          # Instance Segment: 16 Bit instance 0x25
                    '\x00',
                    pack_uint(instance_id),
                    pack_dint(self._byte_offset),  # Offset
                    pack_uint(((object_definition_size * 4)-23) - self._byte_offset)
                ]

                if not self.send_unit_data(
                        build_common_packet_format(DATA_ITEM['Connected'], ''.join(message_request),
                                                   ADDRESS_ITEM['Connection Based'], addr_data=self._target_cid,)):
                    raise DataError("send_unit_data returned not valid data")

            self._get_template_in_progress = False
            return self._buffer

        except Exception as e:
            raise DataError(e)

    def _isolating_user_tag(self):
        try:
            lst = self._tag_list
            self._tag_list = []
            for tag in lst:
                    if tag['tag_name'].find(':') != -1 or tag['tag_name'].find('__') != -1:
                        continue
                    if tag['symbol_type'] & 0b0001000000000000:
                        continue
                    dimension = (tag['symbol_type'] & 0b0110000000000000) >> 13

                    if tag['symbol_type'] & 0b1000000000000000 :
                        template_instance_id = tag['symbol_type'] & 0b0000111111111111
                        tag_type = 'struct'
                        data_type = 'user-created'
                        self._tag_list.append({'instance_id': tag['instance_id'],
                                               'template_instance_id': template_instance_id,
                                               'tag_name': tag['tag_name'],
                                               'dim': dimension,
                                               'tag_type': tag_type,
                                               'data_type': data_type,
                                               'template': {},
                                               'udt': {}})
                    else:
                        tag_type = 'atomic'
                        datatype = tag['symbol_type'] & 0b0000000011111111
                        data_type = I_DATA_TYPE[datatype]
                        if datatype == 0xc1:
                            bit_position = (tag['symbol_type'] & 0b0000011100000000) >> 8
                            self._tag_list.append({'instance_id': tag['instance_id'],
                                                   'tag_name':  tag['tag_name'],
                                                   'dim': dimension,
                                                   'tag_type': tag_type,
                                                   'data_type': data_type,
                                                   'bit_position' : bit_position})
                        else:
                            self._tag_list.append({'instance_id': tag['instance_id'],
                                                   'tag_name':  tag['tag_name'],
                                                   'dim': dimension,
                                                   'tag_type': tag_type,
                                                   'data_type': data_type})
        except Exception as e:
            raise DataError(e)

    def _parse_udt_raw(self, tag):
        try:
            buff = self._read_template(tag['template_instance_id'], tag['template']['object_definition_size'])
            member_count = tag['template']['member_count']
            names = buff.split('\00')
            lst = []

            tag['udt']['name'] = 'Not an user defined structure'
            for name in names:
                if len(name) > 1:

                    if name.find(';') != -1:
                        tag['udt']['name'] = name[:name.find(';')]
                    elif name.find('ZZZZZZZZZZ') != -1:
                        continue
                    elif name.isalpha():
                        lst.append(name)
                    else:
                        continue
            tag['udt']['internal_tags'] = lst

            type_list = []

            for i in xrange(member_count):
                # skip member 1

                if i != 0:
                    array_size = unpack_uint(buff[:2])
                    try:
                        data_type = I_DATA_TYPE[unpack_uint(buff[2:4])]
                    except Exception:
                        data_type = "None"

                    offset = unpack_dint(buff[4:8])
                    type_list.append((array_size, data_type, offset))

                buff = buff[8:]

            tag['udt']['data_type'] = type_list
        except Exception as e:
            raise DataError(e)

    def get_tag_list(self):
        self._tag_list = []
        # Step 1
        self._get_instance_attribute_list_service()

        # Step 2
        self._isolating_user_tag()

        # Step 3
        for tag in self._tag_list:
            if tag['tag_type'] == 'struct':
                tag['template'] = self._get_structure_makeup(tag['template_instance_id'])

        for idx, tag in enumerate(self._tag_list):
            # print (tag)
            if tag['tag_type'] == 'struct':
                self._parse_udt_raw(tag)

        # Step 4

        return self._tag_list




