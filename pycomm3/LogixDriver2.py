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
from .packets.requests import writable_value


re_bit = re.compile(r'(?P<base>^.*)\.(?P<bit>([0-2][0-9])|(3[01])|[0-9])$')


def with_forward_open(func):
    def wrapped(self, *args, **kwargs):
        if not self.forward_open():
            msg = f'Target did not connected. {func.__name__} will not be executed.'
            self.__log.warning(msg)
            raise DataError(msg)
        return func(self, *args, **kwargs)

    return wrapped


class LogixDriver2(LogixDriver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @with_forward_open
    def read(self, *tags):

        parsed_requests = self._parse_requested_tags(tags)
        requests = self._read__build_requests(parsed_requests)
        read_results = self._send_requests(requests)

        results = []

        for tag in tags:
            try:
                request_data = parsed_requests[tag]
                result = read_results[(request_data['plc_tag'], request_data['elements'])]
                if request_data.get('bit') is None:
                    results.append(result)
                else:
                    if result:
                        typ, bit = request_data['bit']
                        if typ == 'bit':
                            val = bool(result.value & (1 << bit))
                        else:
                            val = result.value[bit % 32]
                        results.append(Tag(tag, val, 'BOOL'))
                    else:
                        results.append(Tag(tag, None, None, result.error))
            except Exception as err:
                results.append(Tag(tag, None, None, f'Invalid tag request - {err}'))

        if len(tags) > 1:
            return results
        else:
            return results[0]

    def _read__build_requests(self, parsed_tags):
        requests = []
        response_size = 0
        current_request = self.new_request('multi_request')
        requests.append(current_request)
        tags_in_requests = set()
        for tag, tag_data in parsed_tags.items():
            if tag_data.get('error') is None and (tag_data['plc_tag'], tag_data['elements'])not in tags_in_requests:
                tags_in_requests.add((tag_data['plc_tag'], tag_data['elements']))
                return_size = _tag_return_size(tag_data['tag_info']) * tag_data['elements']
                if return_size > self.connection_size:
                    _request = self.new_request('read_tag_fragmented')
                    _request.add(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                    requests.append(_request)
                else:
                    try:
                        if response_size + return_size < self.connection_size:
                            if current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info']):
                                response_size += return_size
                            else:
                                response_size = return_size
                                current_request = self.new_request('multi_request')
                                current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                                requests.append(current_request)
                        else:
                            response_size = return_size
                            current_request = self.new_request('multi_request')
                            current_request.add_read(tag_data['plc_tag'], tag_data['elements'], tag_data['tag_info'])
                            requests.append(current_request)
                    except RequestError:
                        self.__log.exception(f'Failed to build request for {tag} - skipping')
                        continue

        return requests

    @with_forward_open
    def write(self, *tags_values):
        tags = (tag for (tag, value) in tags_values)
        parsed_requests = self._parse_requested_tags(tags)

        normal_tags = set()
        bit_tags = set()

        for tag, value in tags_values:
            parsed_requests[tag]['value'] = value

            if parsed_requests[tag].get('bit') is None:
                normal_tags.add(tag)
            else:
                bit_tags.add(tag)

        requests = self._write__build_requests(parsed_requests)
        write_results = self._send_requests(requests)
        results = []
        for tag, _ in tags_values:
            try:
                request_data = parsed_requests[tag]
                result = write_results[(request_data['plc_tag'], request_data['elements'])]
                results.append(result)
            except Exception as err:
                results.append(Tag(tag, None, None, f'Invalid tag request - {err}'))

        if len(tags_values) > 1:
            return results
        else:
            return results[0]

    def _write__build_requests(self, parsed_tags):
        requests = []
        current_request = self.new_request('multi_request')
        requests.append(current_request)

        tags_in_requests = set()
        for tag, tag_data in parsed_tags.items():
            if tag_data.get('error') is None and (tag_data['plc_tag'], tag_data['elements'])not in tags_in_requests:
                tags_in_requests.add((tag_data['plc_tag'], tag_data['elements']))
                _val = writable_value(tag_data['value'], tag_data['elements'], tag_data['tag_info']['data_type'])

                if len(_val) > self.connection_size:
                    _request = self.new_request('write_tag_fragmented')
                    _request.add(tag_data['plc_tag'], tag_data['value'], tag_data['elements'], tag_data['tag_info'])
                    requests.append(_request)
                else:
                    try:
                        if not current_request.add_write(tag_data['plc_tag'], tag_data['value'], tag_data['elements'], tag_data['tag_info']):
                            current_request = self.new_request('multi_request')
                            requests.append(current_request)
                            current_request.add_write(tag_data['plc_tag'], tag_data['value'], tag_data['elements'], tag_data['tag_info'])

                    except RequestError:
                        self.__log.exception(f'Failed to build request for {tag} - skipping')
                        continue

        return requests

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

    def _parse_requested_tags(self, tags):
        requests = {}
        for tag in tags:
            parsed = {}
            try:
                plc_tag, bit, elements, tag_info = self._parse_tag_request(tag)
            except RequestError as err:
                parsed['error'] = str(err)
            else:
                parsed['plc_tag'] = plc_tag
                parsed['bit'] = bit
                parsed['elements'] = elements
                parsed['tag_info'] = tag_info
            finally:
                requests[tag] = parsed
        return requests

    def _parse_tag_request(self, tag: str):
        try:
            if tag.endswith('}') and '{' in tag:
                tag, _tmp = tag.split('{')
                elements = int(_tmp[:-1])
            else:
                elements = 1

            bit = None

            base, *attrs = tag.split('.')
            if len(attrs) and attrs[-1].isdigit():
                _bit = attrs.pop(-1)
                bit = ('bit', int(_bit))
                if not len(attrs):
                    tag = base
                else:
                    tag = f"{base}.{''.join(attrs)}"

            tag_info = self._get_tag_info(base, attrs)

            if tag_info['data_type'] == 'DWORD' and elements == 1:
                _tag, idx = _get_array_index(tag)
                tag = f'{_tag}[{idx // 32}]'
                bit = ('bool_array', idx)
                elements = 1

            return tag, bit, elements, tag_info

        except Exception as err:
            # something went wrong parsing the tag path
            raise RequestError('Failed to parse tag read request', tag)

    @staticmethod
    def _send_requests(requests):

        def _mkkey(t=None, r=None):
            if t is not None:
                return t['tag'], t['elements']
            else:
                return r.tag, r.elements

        results = {}

        for request in requests:
            try:
                response = request.send()
            except Exception as err:
                if request.type_ != 'multi':
                    results[_mkkey(r=request)] = Tag(request.tag, None, None, str(err))
                else:
                    for tag in request.tags:
                        results[_mkkey(t=tag)] = Tag(tag['tag'], None, None, str(err))
            else:
                if request.type_ != 'multi':
                    if response:
                        results[_mkkey(r=request)] = Tag(request.tag,
                                                         response.value if request.type_ == 'read' else request.value,
                                                         response.data_type if request.type_ == 'read' else request.data_type)
                    else:
                        results[_mkkey(r=request)] = Tag(request.tag, None, None, response.error)
                else:
                    for tag in response.tags:
                        if tag['service_status'] == SUCCESS:
                            results[_mkkey(t=tag)] = Tag(tag['tag'], tag['value'], tag['data_type'])
                        else:
                            results[_mkkey(t=tag)] = Tag(tag['tag'], None, None,
                                                         tag.get('error', 'Unknown Service Error'))
        return results


def _strip_array(tag):
    if '[' in tag:
        return tag[:tag.find('[')]
    return tag


def _get_array_index(tag):
    if tag.endswith(']') and '[' in tag:
        tag, _tmp = tag.split('[')
        idx = int(_tmp[:-1])
    else:
        idx = 0

    return tag, idx


def _tag_return_size(tag_info):
    if tag_info['tag_type'] == 'atomic':
        size = DATA_TYPE_SIZE[tag_info['data_type']]
    else:
        size = tag_info['udt']['template']['structure_size']

    return size
