
from pycomm3.cip_base import CIPDriver
from unittest import mock

import pytest
from pycomm3.const import DataType
from pycomm3.exceptions import CommError, PycommError, RequestError
from pycomm3.packets import (
    RequestPacket,
    ReadTagFragmentedServiceRequestPacket,
    WriteTagFragmentedServiceRequestPacket,
    MultiServiceRequestPacket,
    request_path,
    make_write_data_tag,
    make_write_data_bit
)
from pycomm3.packets import (
    ReadTagServiceResponsePacket
)
from pycomm3.packets import RequestTypes

CONNECT_PATH = '192.168.1.100/1'

def test_send_raises_commerror_with_no_plc():
    packet = RequestPacket(None)
    with mock.patch.object(RequestPacket, '_build_request'):
        with pytest.raises(CommError):
            packet.send()


packet_classes = RequestPacket.__subclasses__()
@pytest.mark.parametrize('packet_cls', packet_classes)
def test_send_returns_appropriate_response_type(packet_cls):
    driver = CIPDriver(CONNECT_PATH, sequence=1)
    packet = packet_cls(driver)
    with mock.patch.object(RequestPacket, '_build_request'), \
         mock.patch.object(RequestPacket, '_send'), \
         mock.patch.object(RequestPacket, '_receive'):
        response = packet.send()
        assert isinstance(response, packet.response_class)

packet_classes = RequestPacket.__subclasses__()
@pytest.mark.parametrize('packet_cls', packet_classes)
def test_send_calls__send_and__receive(packet_cls):
    driver = CIPDriver(CONNECT_PATH)
    packet = packet_cls(driver)
    with mock.patch.object(RequestPacket, '_build_request'), \
         mock.patch.object(RequestPacket, '_send') as mock_send, \
         mock.patch.object(packet_cls, '_receive') as mock_receive:
        packet.send()
        assert mock_send.called
        assert mock_receive.called

def test_ReadTagFragmentedServiceRequestPacket_returns_expected_response_if_error():
    driver = CIPDriver(CONNECT_PATH)
    packet = ReadTagFragmentedServiceRequestPacket(driver)
    packet.error = "Some Error"

    expected_response = ReadTagServiceResponsePacket()
    expected_response._error = packet.error
    result = packet.send()
    assert str(result) == str(expected_response)

def test_default_WriteTagFragmentedServiceRequestPacket_attributes():
    driver = CIPDriver(CONNECT_PATH)
    packet = WriteTagFragmentedServiceRequestPacket(driver)
    assert packet.tag is None
    assert packet.value is None
    assert packet.elements is None
    assert packet.tag_info is None
    assert packet.request_path is None
    assert packet.data_type is None
    assert packet.segment_size is None
    assert packet.request_id is None
    assert packet._packed_type is None

def test_default_WriteTagFragmentedServiceRequestPacket_add_exception_sets_error():
    driver = CIPDriver(CONNECT_PATH)
    packet = WriteTagFragmentedServiceRequestPacket(driver)
    packet.add(1, 1, 1, 1, 1, 1)
    assert packet.error is not None

def test_MultiServiceRequestPacket_add_read_none_request_path_raises_requesterror():
    driver = CIPDriver(CONNECT_PATH)
    packet = MultiServiceRequestPacket(driver)
    with pytest.raises(RequestError):
        packet.add_read(1, None, 1, 1, 1)

def test_MultiServiceRequestPacket_add_write_none_request_path_raises_requesterror():
    driver = CIPDriver(CONNECT_PATH)
    packet = MultiServiceRequestPacket(driver)
    with pytest.raises(RequestError):
        packet.add_write(1, None, 1, 1, 1, 1)

def test__make_write_data_tag_raises_requesterror_if_value_not_bytes():
    with pytest.raises(RequestError):
        _make_write_data_tag({
            'tag_type': 'struct',
            'data_type': None
        }, None, None, None)

def test__make_write_data_tag_raises_requesterror_if_type_not_struct_and_unknown_data_type():
    with pytest.raises(RequestError):
        _make_write_data_tag({
            'tag_type': 'not a struct',
            'data_type': 'Not a real data type'
        }, None, None, None)

def test__make_write_data_tag_returns_bytestring_and_data_type():
    DATA_TYPE = 'bool'
    result_bytes, result_dt = _make_write_data_tag({
        'tag_type': 'not a struct',
        'data_type': DATA_TYPE
    }, b'', 1, b'')
    assert type(result_bytes) == bytes
    assert result_dt == DATA_TYPE

def test__make_write_data_bit_raises_requesterror_if_mask_size_none():
    with pytest.raises(RequestError):
        _make_write_data_bit({
            'data_type': 'totally invalid datatype'
        }, 'useless value', 'useless request path')

def test__make_write_data_bit_returns_bytes_if_valid_data_type():
    result = _make_write_data_bit({
        'data_type': 'bool'
    }, (1,  1), b'useless request path')

    assert type(result) == bytes
