import struct, re
from collections import defaultdict
from autologging import logged
from types import GeneratorType
from functools import wraps
from . import DataError, Tag
from .base import Base
from .clx import LogixDriver
from .bytes_ import (pack_dint, pack_uint, pack_udint, pack_usint, unpack_usint, unpack_uint, unpack_dint, unpack_udint,
                     UNPACK_DATA_FUNCTION, PACK_DATA_FUNCTION, DATA_FUNCTION_SIZE)
from .const import (SUCCESS, EXTENDED_SYMBOL, ENCAPSULATION_COMMAND, DATA_TYPE, BITS_PER_INT_TYPE,
                    REPLY_INFO, TAG_SERVICES_REQUEST, PADDING_BYTE, ELEMENT_ID, DATA_ITEM, ADDRESS_ITEM,
                    CLASS_ID, CLASS_CODE, INSTANCE_ID, INSUFFICIENT_PACKETS, REPLY_START, BASE_TAG_BIT,
                    MULTISERVICE_READ_OVERHEAD, MULTISERVICE_WRITE_OVERHEAD, MIN_VER_INSTANCE_IDS, REQUEST_PATH_SIZE,
                    VENDORS, PRODUCT_TYPES, KEYSWITCH, TAG_SERVICES_REPLY, get_service_status, get_extended_status,
                    TEMPLATE_MEMBER_INFO_LEN, EXTERNAL_ACCESS, STRUCTURE_READ_REPLY, DATA_TYPE_SIZE)


re_bit = re.compile(r'(?P<base>^.*)\.(?P<bit>([0-2][0-9])|(3[01])|[0-9])$')


def with_forward_open(func):
    def wrapped(self, *args, **kwargs):
        if not self.forward_open():
            self.__log.warning("Target did not connected. read_tag will not be executed.")
            raise DataError("Target did not connected. read_tag will not be executed.")
        return func(self, *args, **kwargs)

    return wrapped


class LogixDriver2(LogixDriver):
    """
    This Ethernet/IP client is based on Rockwell specification. Please refer to the link below for details.

    http://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf

    The following services have been implemented:
        - Read Tag Service (0x4c)
        - Read Tag Fragment Service (0x52)
        - Write Tag Service (0x4d)
        - Write Tag Fragment Service (0x53)
        - Multiple Service Packet (0x0a)
        - Read Modify Write Tag (0xce)

    The client has been successfully tested with the following PLCs:
        - CompactLogix 5330ERM
        - CompactLogix 5370
        - ControlLogix 5572 and 1756-EN2T Module

"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @with_forward_open
    def read(self, *tags):
        # if not self.forward_open():
        #     self.__log.warning("Target did not connected. read_tag will not be executed.")
        #     raise DataError("Target did not connected. read_tag will not be executed.")
        # tags_to_read = {}  # tag: return size (including array elements)
        # tags_requested = defaultdict(list)  # base tag: (members requested, array elements)
        # results = []
        # for tag in tags:
        #     tmp = self._parse_tag_read_request(tag)
        #     if tmp is None:
        #         results.append(Tag(tag, None, None, error='Invalid tag path, request not sent'))
        #     else:
        #         base, tag, return_size, elements = tmp  # {x} stripped from tag already if it exists
        #         if base not in tags_to_read:
        #             tags_to_read[base] = return_size * elements
        #         tags_requested[base].append((tag, elements))
        for tag in tags:
            request = self.new_request('read_tag')
            # request.add(
            #     bytes([TAG_SERVICES_REQUEST['Read Tag']]),
            #     self.create_tag_rp(tag),
            #     pack_uint(1)
            # )
            request.add(tag, tag_info=self._tags[tag])
            response = request.send()
            for k, v in response.value.items():
                print(f'{k} = {v}')


    def _parse_tag_read_request(self, tag: str):
        try:
            if tag.endswith('}') and '{' in tag:
                # elements = int(tag[tag.find('{')+1:-1])
                tag, _tmp = tag.split('{')
                elements = int(_tmp[:-1])
            else:
                elements = 1

            base, *attrs = tag.split('.')
            return_size = self._lookup_tag_value_size(base, attrs)

            return base, tag, return_size, elements

        except Exception as err:
            # something went wrong parsing the tag path
            # don't care what, just return None
            return None

    def _lookup_tag_value_size(self, base, attrs):

        def _recurse_attrs(attrs, tag_data):
            cur, *remain = attrs
            data_type = tag_data[cur]['data_type']
            if not len(remain):
                if isinstance(data_type, str):
                    size = DATA_TYPE_SIZE[data_type]
                    array_len = tag_data[cur].get('array') or 1
                    return size * array_len
                else:
                    return data_type['template']['structure_size']
            else:
                return _recurse_attrs(remain, data_type['internal_tags'])

        tag_data = self._tags[base]
        if tag_data['tag_type'] == 'atomic':
            return DATA_TYPE_SIZE[tag_data['data_type']]
        elif not len(attrs):
            return tag_data['udt']['template']['structure_size']
        else:
            return _recurse_attrs(attrs, tag_data['udt']['internal_tags'])






