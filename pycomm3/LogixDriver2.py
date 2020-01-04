import struct, re
from collections import defaultdict
from autologging import logged
from types import GeneratorType
from functools import wraps
from . import DataError, Tag, RequestError
from .base import Base
from .clx import LogixDriver
from .bytes_ import (pack_dint, pack_uint, pack_udint, pack_usint, unpack_usint, unpack_uint, unpack_dint, unpack_udint,
                     UNPACK_DATA_FUNCTION, PACK_DATA_FUNCTION, DATA_FUNCTION_SIZE)
from .const import (SUCCESS, EXTENDED_SYMBOL, ENCAPSULATION_COMMAND, DATA_TYPE, BITS_PER_INT_TYPE, SERVICE_STATUS,
                    REPLY_INFO, TAG_SERVICES_REQUEST, PADDING_BYTE, ELEMENT_ID, DATA_ITEM, ADDRESS_ITEM,
                    CLASS_ID, CLASS_CODE, INSTANCE_ID, INSUFFICIENT_PACKETS, REPLY_START, BASE_TAG_BIT,
                    MULTISERVICE_READ_OVERHEAD, MULTISERVICE_WRITE_OVERHEAD, MIN_VER_INSTANCE_IDS, REQUEST_PATH_SIZE,
                    VENDORS, PRODUCT_TYPES, KEYSWITCH, TAG_SERVICES_REPLY, get_service_status, get_extended_status,
                    TEMPLATE_MEMBER_INFO_LEN, EXTERNAL_ACCESS, STRUCTURE_READ_REPLY, DATA_TYPE_SIZE)
from pprint import pprint


re_bit = re.compile(r'(?P<base>^.*)\.(?P<bit>([0-2][0-9])|(3[01])|[0-9])$')


def with_forward_open(func):
    def wrapped(self, *args, **kwargs):
        if not self.forward_open():
            self.__log.warning("Target did not connected. read_tag will not be executed.")
            raise DataError("Target did not connected. read_tag will not be executed.")
        return func(self, *args, **kwargs)

    return wrapped


class LogixDriver2(LogixDriver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @with_forward_open
    def read(self, *tags):
        # first, go thru all tags and generate request objects for them,
        # pre-populate the results with any failed requests,
        # also, return actual tag names (e.g. minus the {array} len)
        requests, results, _tags = self._read_build_requests(tags)

        for request in requests:
            try:
                response = request.send()
            except Exception as err:
                if request.single:
                    results[request.request_num] = Tag(request.tag, None, None, str(err))
                else:
                    for tag in request.tags:
                        results[tag['request_num']] = Tag(tag['tag'], None, None, str(err))
            else:
                if request.single:
                    if response:
                        results[request.request_num] = Tag(request.tag, response.value, response.data_type, None)
                    else:
                        results[request.request_num] = Tag(request.tag, None, None, response.error)
                else:
                    for tag in response.tags:
                        if tag['service_status'] == SUCCESS:
                            results[tag['request_num']] = Tag(tag['tag'], tag['value'], tag['data_type'])
                        else:
                            results[tag['request_num']] = Tag(tag['tag'], None, None,
                                                              tag.get('error', 'Unknown Service Error'))

        if len(tags) == 1:
            return results[0]
        else:
            return [results[i] for i in range(len(tags))]

    def _read_build_requests(self, tags):
        requests = []
        results = {}
        current_request = None
        request_size, response_size = 0, 0
        tags_ = []

        for i, tag in enumerate(tags):
            try:
                tag, base, elements, tag_data = self._parse_tag_read_request(tag)
                tags_.append(tag)
            except RequestError as err:
                results[i] = Tag(tag, None, None, str(err))
            else:
                return_size = _tag_return_size(tag_data) * elements
                if return_size > self.connection_size:
                    _request = self.new_request('read_tag_fragmented')
                    _request.add(tag, elements, tag_data, i)
                    requests.append(_request)
                else:
                    if current_request is None:
                        request_size, response_size = 0, 0
                        current_request = self.new_request('multi_request')
                        requests.append(current_request)

                    if response_size + return_size < self.connection_size:
                        if current_request.add_read(tag, elements, tag_data, i):
                            continue
                        else:
                            request_size, response_size = 0, 0
                            current_request = self.new_request('multi_request')
                            requests.append(current_request)

        return requests, results, tags_

    def _parse_tag_read_request(self, tag: str):
        try:
            if tag.endswith('}') and '{' in tag:
                # elements = int(tag[tag.find('{')+1:-1])
                tag, _tmp = tag.split('{')
                elements = int(_tmp[:-1])
            else:
                elements = 1

            base, *attrs = tag.split('.')
            tag_data = self._get_tag_info(base, attrs)

            return tag, base, elements, tag_data

        except Exception as err:
            # something went wrong parsing the tag path
            raise RequestError('Failed to parse tag read request', tag)

    def _get_tag_info(self, base, attrs):

        def _recurse_attrs(attrs, data):
            cur, *remain = attrs
            if not len(remain):
                return data[_strip_array(cur)]
            else:
                return _recurse_attrs(remain, data[cur]['data_type']['internal_tags'])

        try:
            data = self._tags[_strip_array(base)]
            if not len(attrs):
                return data
            else:
                return _recurse_attrs(attrs, data['udt']['internal_tags'])

        except Exception as err:
            self.__log.exception(f'Failed to lookup tag data for {base}, {attrs}')
            raise

def _strip_array(tag):
    if '[' in tag:
        return tag[:tag.find('[')]
    return tag



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

def _tag_return_size(tag_info):
    if tag_info['tag_type'] == 'atomic':
        size = DATA_TYPE_SIZE[tag_info['data_type']]
    else:
        size = tag_info['udt']['template']['structure_size']

    return size
