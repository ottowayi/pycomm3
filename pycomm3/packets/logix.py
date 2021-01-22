import logging
from itertools import tee, zip_longest
from reprlib import repr as _r
from typing import Dict, Any

from .ethernetip import SendUnitDataRequestPacket, SendUnitDataResponsePacket
from .util import parse_read_reply, make_write_data_tag, make_write_data_bit, get_service_status, get_extended_status

from ..bytes_ import Pack, Unpack
from ..cip import CLASS_TYPE, INSTANCE_TYPE, DataType, ClassCode, Services
from ..const import INSUFFICIENT_PACKETS, STRUCTURE_READ_REPLY, SUCCESS
from ..exceptions import RequestError


class TagServiceResponsePacket(SendUnitDataResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    tag_service = None

    def __init__(self, request: 'TagServiceRequestPacket', raw_data: bytes = None):
        self.tag = request.tag
        self.elements = request.elements
        self.tag_info = request.tag_info
        super().__init__(request, raw_data)


class TagServiceRequestPacket(SendUnitDataRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    response_class = TagServiceResponsePacket

    def __init__(self, tag: str, elements: int, tag_info: Dict[str, Any], request_id: int):
        super().__init__()
        self.tag = tag
        self.elements = elements
        self.tag_info = tag_info
        self.request_id = request_id


class ReadTagServiceResponsePacket(TagServiceResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'ReadTagServiceRequestPacket', raw_data: bytes = None):
        self.value = None
        self.data_type = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        try:
            super()._parse_reply()
            if self.is_valid():
                self.value, self.data_type = parse_read_reply(self.data, self.tag_info, self.elements)
            else:
                self.value, self.data_type = None, None
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.data_type!r}, {_r(self.value)}, {self.service_status!r})'


class ReadTagServiceRequestPacket(TagServiceRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'read'
    response_class = ReadTagServiceResponsePacket
    tag_service = Services.read_tag

    def __init__(self, tag: str, elements: int, tag_info: Dict[str, Any], request_id: int, request_path: bytes,):
        super().__init__(tag, elements, tag_info, request_id)
        self.request_path = request_path

        if request_path is None:
            self.error = 'Invalid Tag Request Path'

        self.add(
            self.tag_service,
            request_path,
            Pack.uint(self.elements),
        )


class ReadTagFragmentedServiceResponsePacket(ReadTagServiceResponsePacket):
    # TODO
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, request: 'ReadTagFragmentedServiceRequestPacket', raw_data: bytes = None):
        self.value = None
        self.data_type = None
        self._value_bytes = None
        super().__init__(request, raw_data)

    def _parse_reply(self):
        super()._parse_reply()
        if self.data[:2] == STRUCTURE_READ_REPLY:
            self._value_bytes = self.data[4:]
            self._data_type = self.data[:4]
        else:
            self._value_bytes = self.data[2:]
            self._data_type = self.data[:2]

    def parse_bytes(self):
        try:
            if self.is_valid():
                self.value, self.data_type = parse_read_reply(self._data_type + self._value_bytes,
                                                          self._request.tag_info, self._request.elements)
            else:
                self.value, self.data_type = None, None
        except Exception as err:
            self.__log.exception('Failed parsing reply data')
            self.value = None
            self._error = f'Failed to parse reply - {err}'

    def __repr__(self):
        return f'{self.__class__.__name__}(raw_data={_r(self.raw)})'

    __str__ = __repr__


class ReadTagFragmentedServiceRequestPacket(ReadTagServiceRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'read'
    response_class = ReadTagFragmentedServiceResponsePacket
    tag_service = Services.read_tag_fragmented

    def send(self):
        # TODO: determine best approach here, will probably require more work in the
        #       driver send method to handle the fragmenting
        if not self.error:
            offset = 0
            responses = []
            while offset is not None:
                self._msg.extend([Services.read_tag_fragmented,
                                  self.request_path,
                                  Pack.uint(self.elements),
                                  Pack.dint(offset)])
                self._send(self.build_request())
                self.__log.debug(f'Sent: {self!r} (offset={offset})')
                reply = self._receive()
                response = ReadTagFragmentedServiceResponsePacket(reply, self.tag_info, self.elements)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                if response.service_status == INSUFFICIENT_PACKETS:
                    offset += len(response.bytes_)
                    self._msg = [Pack.uint(self._driver._sequence)]
                else:
                    offset = None
            if all(responses):
                final_response = responses[-1]
                final_response.bytes_ = b''.join(resp.bytes_ for resp in responses)
                final_response.parse_bytes()
                self.__log.debug(f'Reassembled Response: {final_response!r}')
                return final_response

        failed_response = ReadTagServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        self.__log.debug(f'Reassembled Response: {failed_response!r}')
        return failed_response

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self.tag!r}, elements={self.elements!r})'


class WriteTagServiceResponsePacket(TagServiceResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')


class WriteTagServiceRequestPacket(TagServiceRequestPacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'write'
    response_class = WriteTagServiceResponsePacket
    tag_service = Services.write_tag

    def __init__(self, tag: str, elements: int, tag_info: Dict[str, Any], request_id: int, request_path, value, bits_write=None):
        super().__init__(tag, elements, tag_info, request_id)
        self.value = None
        self.data_type = None

        if request_path is None:
            self.error = 'Invalid Tag Request Path'

        else:
            if bits_write:
                request_path = make_write_data_bit(tag_info, value, request_path)
                data_type = 'BOOL'
            else:
                request_path, data_type = make_write_data_tag(tag_info, value, elements, request_path)

            super().add(
                request_path,
            )
            self.data_type = data_type

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self.tag!r}, value={_r(self.value)}, elements={self.elements!r})'


class WriteTagFragmentedServiceResponsePacket(WriteTagServiceResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')


class WriteTagFragmentedServiceRequestPacket(WriteTagServiceRequestPacket):
    #TODO
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'write'
    response_class = WriteTagFragmentedServiceResponsePacket
    tag_service = Services.write_tag_fragmented

    def __init__(self, tag: str, elements: int, tag_info: Dict[str, Any], request_id: int, request_path, value):
        super().__init__(tag, elements, tag_info, request_id, request_path, value)
        self.request_path = request_path
        self.segment_size = None
        self.data_type = tag_info['data_type_name']

        try:
            if tag_info['tag_type'] == 'struct':
                self._packed_type = STRUCTURE_READ_REPLY + Pack.uint(
                    tag_info['data_type']['template']['structure_handle'])
            else:
                self._packed_type = Pack.uint(DataType[self.data_type])

            if self.request_path is None:
                self.error = 'Invalid Tag Request Path'
        except Exception as err:
            self.__log.exception('Failed adding request')
            self.error = err

    def send(self):
        if not self.error:
            responses = []
            segment_size = self._driver.connection_size - (len(self.request_path) + len(self._packed_type)
                                                           + 9)  # 9 = len of other stuff in the path

            pack_func = Pack[self.data_type] if self.tag_info['tag_type'] == 'atomic' else lambda x: x
            segments = (self.value[i: i +segment_size]
                        for i in range(0, len(self.value), segment_size))

            offset = 0
            elements_packed = Pack.uint(self.elements)

            for i, segment in enumerate(segments, start=1):
                segment_bytes = b''.join(pack_func(s) for s in segment) if not isinstance(segment, bytes) else segment
                self._msg.extend((
                    Services.write_tag_fragmented,
                    self.request_path,
                    self._packed_type,
                    elements_packed,
                    Pack.dint(offset),
                    segment_bytes
                ))

                self._send(self.build_request())
                self.__log.debug(f'Sent: {self!r} (part={i} offset={offset})')
                reply = self._receive()
                response = WriteTagFragmentedServiceResponsePacket(reply)
                self.__log.debug(f'Received: {response!r}')
                responses.append(response)
                offset += len(segment_bytes)
                self._msg = [Pack.uint(self._driver._sequence), ]

            if all(responses):
                final_response = responses[-1]
                self.__log.debug(f'Reassembled Response: {final_response!r}')
                return final_response

        failed_response = WriteTagFragmentedServiceResponsePacket()
        failed_response._error = self.error or 'One or more fragment responses failed'
        self.__log.debug(f'Reassembled Response: {failed_response!r}')
        return failed_response


class MultiServiceResponsePacket(SendUnitDataResponsePacket):
    __log = logging.getLogger(f'{__module__}.{__qualname__}')

    def __init__(self, raw_data: bytes = None, tags=None, *args, **kwargs):
        self.tags = tags
        self.values = None
        self.request_statuses = None
        super().__init__(raw_data, *args, **kwargs)

    def _parse_reply(self):
        super()._parse_reply()
        num_replies = Unpack.uint(self.data)
        offset_data = self.data[2:2 + 2 * num_replies]
        offsets = (Unpack.uint(offset_data[i:i+2]) for i in range(0, len(offset_data), 2))
        start, end = tee(offsets)  # split offsets into start/end indexes
        next(end)   # advance end by 1 so 2nd item is the end index for the first item
        reply_data = [self.data[i:j] for i, j in zip_longest(start, end)]
        values = []

        for data, tag in zip(reply_data, self.tags):
            service = data[0:1]
            service_status = data[2]
            tag['service_status'] = service_status
            if service_status != SUCCESS:
                tag['error'] = f'{get_service_status(service_status)} - {get_extended_status(data, 2)}'

            if Services.get(Services.from_reply(service)) == Services.read_tag:
                if service_status == SUCCESS:
                    value, dt = parse_read_reply(data[4:], tag['tag_info'], tag['elements'])
                else:
                    value, dt = None, None

                values.append(value)
                tag['value'] = value
                tag['data_type'] = dt
            else:
                tag['value'] = None
                tag['data_type'] = None

        self.values = values

    def __repr__(self):
        return f'{self.__class__.__name__}(values={_r(self.values)}, error={self.error!r})'


class MultiServiceRequestPacket(SendUnitDataRequestPacket):
    # TODO:  this class should wrap the other tag request packets
    #        the add method should take other requests instead of builing them itself
    __log = logging.getLogger(f'{__module__}.{__qualname__}')
    type_ = 'multi'
    response_class = MultiServiceResponsePacket

    def __init__(self, driver):
        super().__init__(driver)
        self.tags = []
        self._msg.extend((
            Services.multiple_service_request,  # the Request Service
            Pack.usint(2),  # the Request Path Size length in word
            CLASS_TYPE["8-bit"],
            ClassCode.message_router,
            INSTANCE_TYPE["8-bit"],
            b'\x01',  # Instance 1
        ))
        self._message = None
        self._msg_errors = None

    @property
    def message(self) -> bytes:
        return self._message

    def build_message(self, tags):
        rp_list, errors = [], []
        for tag in tags:
            if tag['rp'] is None:
                errors.append(f'Unable to create request path {tag["tag"]}')
            else:
                rp_list.append(tag['rp'])

        offset = len(rp_list) * 2 + 2
        offsets = []
        for rp in rp_list:
            offsets.append(Pack.uint(offset))
            offset += len(rp)

        msg = self._msg + [Pack.uint(len(rp_list))] + offsets + rp_list
        return b''.join(msg)

    def add_read(self, tag, request_path, elements, tag_info, request_id):
        # TODO: maybe instead of these methods, the multi-packet uses multiple normal ReadRequests
        #       and combines them as needed
        if request_path is not None:
            rp = Services.read_tag + request_path + Pack.uint(elements)
            _tag = {
                'tag': tag,
                'elements': elements,
                'tag_info': tag_info,
                'rp': rp,
                'service': 'read',
                'request_id': request_id
            }
            message = self.build_message(self.tags + [_tag])
            if len(message) < self._driver.connection_size:
                self._message = message
                self.tags.append(_tag)
                return True
            else:
                return False
        else:
            self.__log.error(f'Failed to create request path for {tag}')
            raise RequestError('Failed to create request path')

    def add_write(self, tag, request_path, value, elements, tag_info, request_id, bits_write=None):
        if request_path is not None:
            if bits_write:
                data_type = tag_info['data_type']
                request_path = make_write_data_bit(tag_info, value, request_path)
            else:
                request_path, data_type = make_write_data_tag(tag_info, value, elements, request_path)

            _tag = {'tag': tag, 'elements': elements, 'tag_info': tag_info, 'rp': request_path, 'service': 'write',
                    'value': value, 'data_type': data_type, 'request_id': request_id}

            message = self.build_message(self.tags + [_tag])
            if len(message) < self._driver.connection_size:
                self._message = message
                self.tags.append(_tag)
                return True
            else:
                return False

        else:
            self.__log.error(f'Failed to create request path for {tag}')
            raise RequestError('Failed to create request path')

    def send(self):
        if not self._msg_errors:
            request = self.build_request()
            self._send(request)
            self.__log.debug(f'Sent: {self!r}')
            reply = self._receive()
            response = MultiServiceResponsePacket(reply, tags=self.tags)
        else:
            self.error = f'Failed to create request path for: {", ".join(self._msg_errors)}'
            response = MultiServiceResponsePacket()
            response._error = self.error

        self.__log.debug(f'Received: {response!r}')
        return response





