"""Tests for the logix_driver.py file.

There are quite a few methods in the CIPDriver which are difficult to
read or test due to both code clarity and complexity issues. As well as
there being no way to control the execution of many of the private
methods through the public API. This has lead to testing of quite a few
private API methods to achieve an acceptable test coverage.
"""
from logging import exception
from pycomm3.const import SUCCESS
from pycomm3.packets import RegisterSessionResponsePacket, ResponsePacket, GenericConnectedResponsePacket
from pycomm3.packets import GenericConnectedRequestPacket, GenericUnconnectedRequestPacket, RegisterSessionRequestPacket, RequestPacket, UnRegisterSessionRequestPacket
import socket
from unittest import mock

import pytest
from pycomm3.cip_driver import CIPDriver
from pycomm3.exceptions import CommError, ResponseError, PycommError
from pycomm3.socket_ import Socket
from pycomm3.tag import Tag

CONNECT_PATH = '192.168.1.100/1'

def test_cip_get_module_info_raises_data_error_if_response_falsy():
    with mock.patch.object(CIPDriver, 'generic_message') as mock_generic_message:
        mock_generic_message.return_value = False
        with pytest.raises(ResponseError):
            driver = CIPDriver(CONNECT_PATH)
            driver.get_module_info(1)

        assert mock_generic_message.called

def test_get_module_info_returns_expected_identity_dict():
    EXPECTED_DICT = {
        'vendor': 'Rockwell Automation/Allen-Bradley', # uint 1 for Rockwell Automation/Allen-Bradley
        'product_type': 'Residual Gas Analyzer', # uint 0x1E for 'Residual Gas Analyzer'
        'product_code': 1, # uint
        'version_major': 1, # int
        'version_minor': 1, # int
        'revision': '1.1', # int, int
        'serial': '00000001', # udint
        'device_type': 'This is a test',
        'status': '0000000100000001', # uint
        'state': 'Major Unrecoverable Fault', # uint 5 Major Unrecoverable Fault
    }
    RESPONSE_BYTES = b"\x01\x00\x1E\x00\x01\x00\x01\x01\x01\x01\x01\x00\x00\x00" + \
        len(EXPECTED_DICT['device_type']).to_bytes(1, 'little') + \
        bytes(EXPECTED_DICT['device_type'], 'ascii') + int(5).to_bytes(4, 'little')
    RESPONSE_TAG = Tag("Dummy_tag", RESPONSE_BYTES, type=None, error=None)
    with mock.patch.object(CIPDriver, 'generic_message') as mock_generic_message:
        mock_generic_message.return_value = RESPONSE_TAG
        driver = CIPDriver(CONNECT_PATH)
        actual_response = driver.get_module_info(1)
        assert actual_response == EXPECTED_DICT

import itertools
viable_methods = ['_forward_close', '_un_register_session']
viable_exceptions = Exception.__subclasses__() + PycommError.__subclasses__()
param_values = list(itertools.product(viable_methods, viable_exceptions))
@pytest.mark.parametrize(['mock_method', 'exception'], param_values)
def test_close_raises_commerror_on_any_exception(mock_method, exception):
    """Raise a CommError if any CIPDriver methods raise exception.
    
    There are two CIPDriver methods called within close:
        CIPDriver._forward_close()
        CIPDriver._un_register_session()

    If those internal methods change, this test will break. I think
    that's acceptable and any changes to this method should make the
    author very aware that they have changed this method.
    """
    with mock.patch.object(CIPDriver, mock_method) as mock_method:
        mock_method.side_effect = exception
        with pytest.raises(CommError):
            driver = CIPDriver(CONNECT_PATH)
            driver.close()

def test_close_raises_no_error_on_sucessful_run():
    with mock.patch.object(UnRegisterSessionRequestPacket, 'send') as mock_send, \
         mock.patch.object(Socket, 'close') as mock_close:
        mock_send.return_value = True
        mock_close.return_value = None

        try:
            driver = CIPDriver(CONNECT_PATH, **{'session': 0, 'socket': Socket()})
            driver.close()
        except PycommError:
            pytest.fail('Unexpected exception')

def test_close_raises_commerror_on_socket_close_exception():
    with mock.patch.object(Socket, 'close') as mock_close:
        mock_close.side_effect = Exception
        with pytest.raises(CommError):
            driver = CIPDriver(CONNECT_PATH, **{'session': 0, 'socket': Socket()})
            driver.close()

def test_close_calls_socket_close_if_socket():
    with mock.patch.object(Socket, 'close') as mock_close:
        try:
            driver = CIPDriver(CONNECT_PATH, **{'session': 0, 'socket': Socket()})
            driver.close()
        except Exception:
            pass
        assert mock_close.called

def test_open_raises_commerror_on_connect_fail():
    with mock.patch.object(Socket, 'connect') as mock_connect:
        mock_connect.side_effect = Exception
        driver = CIPDriver(CONNECT_PATH)
        with pytest.raises(CommError):
            driver.open()

def test_open_returns_false_if_register_session_falsy():
    with mock.patch.object(Socket, 'connect'), \
         mock.patch.object(CIPDriver, '_register_session') as mock_register:
        mock_register.return_value = None
        driver = CIPDriver(CONNECT_PATH)
        assert not driver.open()

def test_open_returns_true_if_register_session_truthy():
    with mock.patch.object(Socket, 'connect'), \
         mock.patch.object(CIPDriver, '_register_session') as mock_register:
        mock_register.return_value = 1
        driver = CIPDriver(CONNECT_PATH)
        assert driver.open()

def test_generic_message_builds_req_with_no_route_path():
    EXPECTED_CALL_ARGS = {
        'service': 1,
        'class_code': 1,
        'instance': 1,
        'attribute': 1,
        'request_data': b'\x00',
        'data_format': [('blah', 1)],
    }
    RESPONSE_PACKET = GenericConnectedResponsePacket(
        data_format=EXPECTED_CALL_ARGS['data_format']
    )

    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(GenericConnectedRequestPacket, 'build') as mock_build, \
         mock.patch.object(RequestPacket, 'send') as mock_send, \
         mock.patch.object(CIPDriver, '_forward_open'):
        mock_send.return_value = RESPONSE_PACKET  # Fake response
        driver = CIPDriver(CONNECT_PATH, **{'session': 1, 'socket': Socket()})
        result = driver.generic_message(
            service=EXPECTED_CALL_ARGS['service'],
            class_code=EXPECTED_CALL_ARGS['class_code'],
            instance=EXPECTED_CALL_ARGS['instance'],
            attribute=EXPECTED_CALL_ARGS['attribute'],
            request_data=EXPECTED_CALL_ARGS['request_data'],
            data_type=EXPECTED_CALL_ARGS['data_format']
        )
        mock_build.assert_called_once_with(**EXPECTED_CALL_ARGS)

def test_generic_message_returns_tag():
    RESPONSE_PACKET = GenericConnectedResponsePacket(data_format=[('blah', 1)])

    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(GenericConnectedRequestPacket, 'build') as mock_build, \
         mock.patch.object(RequestPacket, 'send') as mock_send, \
         mock.patch.object(CIPDriver, '_forward_open'):
        mock_send.return_value = RESPONSE_PACKET  # Fake response
        driver = CIPDriver(CONNECT_PATH, **{'session': 1, 'socket': Socket()})
        result = driver.generic_message(
            service=1,
            class_code=1,
            instance=1
        )
        assert isinstance(result, Tag)

def test_generic_message_builds_req_with_route_path_bytes():
    EXPECTED_CALL_ARGS = {
        'service': 1,
        'class_code': 1,
        'instance': 1,
        'attribute': 1,
        'request_data': b'\x00',
        'data_format': [('blah', 1)],
        'route_path': b'\x00',
        'unconnected_send': False
    }
    RESPONSE_PACKET = GenericConnectedResponsePacket(
        data_format=EXPECTED_CALL_ARGS['data_format']
    )

    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(GenericUnconnectedRequestPacket, 'build') as mock_build, \
         mock.patch.object(RequestPacket, 'send') as mock_send, \
         mock.patch.object(CIPDriver, '_forward_open'):
        mock_send.return_value = RESPONSE_PACKET  # Fake response
        driver = CIPDriver(CONNECT_PATH, **{'session': 1, 'socket': Socket()})
        driver.generic_message(
            service=EXPECTED_CALL_ARGS['service'],
            class_code=EXPECTED_CALL_ARGS['class_code'],
            instance=EXPECTED_CALL_ARGS['instance'],
            attribute=EXPECTED_CALL_ARGS['attribute'],
            request_data=EXPECTED_CALL_ARGS['request_data'],
            data_type=EXPECTED_CALL_ARGS['data_format'],
            route_path=EXPECTED_CALL_ARGS['route_path'],
            unconnected_send=EXPECTED_CALL_ARGS['unconnected_send'],
            connected=False  # Send us down the route_path code path.
        )
        mock_build.assert_called_once_with(**EXPECTED_CALL_ARGS)

def test__forward_close_returns_false_if_no_response():
    with mock.patch.object(CIPDriver, 'generic_message') as mock_message:
        mock_message.return_value = Tag('Falsy_Tag', None, None, None)
        driver = CIPDriver(CONNECT_PATH, **{'session': 1})
        assert not driver._forward_close()

def test__forward_close_returns_true_if_response():
    with mock.patch.object(CIPDriver, 'generic_message') as mock_message:
        mock_message.return_value = Tag('Truthy_Tag', 'Some Response', None, None)
        driver = CIPDriver(CONNECT_PATH, **{'session': 1})
        assert driver._forward_close()

def test__forward_close_raises_commerror_if_session_zero():
    with mock.patch.object(CIPDriver, 'generic_message') as mock_message:
        mock_message.return_value = Tag('Falsy_Tag', None, None, None)
        driver = CIPDriver(CONNECT_PATH, **{'session': 0})
        with pytest.raises(CommError):
            driver._forward_close()

@pytest.mark.parametrize('conf_session', range(1, 100))
def test__register_session_returns_configured_session(conf_session):
    driver = CIPDriver(CONNECT_PATH, **{'session': conf_session})
    with mock.patch.object(RequestPacket, 'send'):
        assert conf_session == driver._register_session()

def test__register_session_returns_none_if_no_response():
    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(RequestPacket, 'send') as mock_send:
        mock_send.return_value = False
        assert driver._register_session() is None

@pytest.mark.parametrize('conf_session', range(1, 100))
def test__register_session_returns_session_from_response(conf_session):
    RESPONSE_PACKET = RegisterSessionResponsePacket()
    RESPONSE_PACKET.session = conf_session
    RESPONSE_PACKET.command = "Bogus Command"
    RESPONSE_PACKET.command_status = SUCCESS

    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(RequestPacket, 'send') as mock_send:
        mock_send.return_value = RESPONSE_PACKET
        assert conf_session == driver._register_session()


def test__forward_open_returns_true_if_already_connected():
    driver = CIPDriver(CONNECT_PATH)
    driver._target_is_connected = True
    assert driver._forward_open()

def test__forward_open_returns_false_if_falsy_response():
    driver = CIPDriver(CONNECT_PATH)
    with mock.patch.object(CIPDriver, 'generic_message') as mock_message:
        mock_message.return_value = Tag('Falsy_Tag', None, None, None)
        assert not driver._forward_open()

def test__forward_open_raises_commerror_if_session_is_zero():
    driver = CIPDriver(CONNECT_PATH, session=0)
    with pytest.raises(CommError):
        driver._forward_open()
