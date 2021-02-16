"""Tests for the logix_driver.py file.

The Logix Driver is beholden to the CIPDriver interface. Only tests
which bind it to that interface should be allowed here. Tests binding
to another interface such as Socket are an anti-pattern.

There are quite a few methods in the LogixDriver which are difficult to
read or test due to both code clarity issues and it being inconvenient.

Also the vast majority of methods are private, I think that private 
methods should not be tested directly, but rather, their effects on
public methods should be tested.

pytest --cov=pycomm3 --cov-branch tests/offline/
----------- coverage: platform linux, python 3.8.1-final-0 -----------
Name                           Stmts   Miss Branch BrPart  Cover
----------------------------------------------------------------
pycomm3/logix_driver.py                   798    718    346      0     7%

We're currently at 7% test coverage, I would like to increase that to >=50%
and then continue to do so for the rest of the modules.
"""
from unittest import mock

import pytest

from pycomm3.cip_driver import CIPDriver
from pycomm3.const import MICRO800_PREFIX, SUCCESS
from pycomm3.exceptions import CommError, PycommError, RequestError
from pycomm3.logix_driver import LogixDriver, writable_value
from pycomm3.packets import RequestPacket, ResponsePacket
from pycomm3.socket_ import Socket
from pycomm3.tag import Tag
from pycomm3.custom_types import ModuleIdentityObject

CONNECT_PATH = '192.168.1.100/1'

IDENTITY_CLX_V20 = {'vendor': 'Rockwell Automation/Allen-Bradley',
                'product_type': 'Programmable Logic Controller', 'product_code': 89,
                'revision': {'major': 20, 'minor': 0},
                'status': b'00', 'serial': '00000000',
                'product_name': '1756-L55'}

IDENTITY_CLX_V21 = {'vendor': 'Rockwell Automation/Allen-Bradley',
                'product_type': 'Programmable Logic Controller', 'product_code': 89,
                'revision': {'major': 21, 'minor': 0},
                'status': b'00', 'serial': '00000000',
                'product_name': '1756-L62'}

IDENTITY_CLX_V32 = {'vendor': 'Rockwell Automation/Allen-Bradley',
                'product_type': 'Programmable Logic Controller', 'product_code': 89,
                'revision': {'major': 32, 'minor': 0},
                'status': b'00', 'serial': '00000000',
                'product_name': '1756-L85'}

PLC_INFOS = [
    {'vendor': 'Honeywell Inc.',
     'product_type': 'Limit Switch',
     'product_code': 0x03,
     'revision': {'major': 12, 'minor': 34},
     'status': b'\x01\x02',
     'serial': 'c00fa09b',
     'product_name': 'Test-Product-1'},


]


def test_info():
    encoded = ModuleIdentityObject.encode(PLC_INFOS[0])
    assert encoded
    decoded = ModuleIdentityObject.decode(encoded)
    assert decoded == PLC_INFOS[0]


@pytest.mark.parametrize('identity', [IDENTITY_CLX_V20, IDENTITY_CLX_V21, IDENTITY_CLX_V32])
def test_logix_init_for_version_support_instance_ids_large_connection(identity):
    with mock.patch.object(LogixDriver, '_list_identity') as mock_identity, \
         mock.patch.object(LogixDriver, 'get_plc_info') as mock_get_info, \
         mock.patch.object(LogixDriver, 'get_plc_name') as mock_get_name:

        mock_identity.return_value = identity
        mock_get_info.return_value = identity  # this is the ListIdentity response
                                               # not the same as module idenity, but
                                               # has all the fields needed for the test

        plc = LogixDriver(CONNECT_PATH)
        plc._initialize_driver(False, False)

        assert plc._micro800 is False
        assert plc._cfg['use_instance_ids'] == (identity['revision']['major'] >= 21)
        assert mock_get_info.called
        assert mock_get_name.called

def test_logix_init_micro800_avoids_plc_name():
    with mock.patch.object(LogixDriver, 'open'), \
            mock.patch.object(LogixDriver, 'get_plc_info'), \
            mock.patch.object(LogixDriver, 'get_plc_name') as mock_name, \
            mock.patch.object(CIPDriver, '_list_identity') as mock_identity:
        mock_identity.return_value = {'product_name': MICRO800_PREFIX}
        LogixDriver(CONNECT_PATH, init_info=True, init_tags=False)
    assert not mock_name.called


def test_logix_init_calls_get_tag_list_if_init_tags():
    with mock.patch.object(LogixDriver, 'open'), \
            mock.patch.object(LogixDriver, 'get_tag_list') as mock_tag:
        LogixDriver(CONNECT_PATH, init_info=False, init_tags=True)
    assert mock_tag.called


def test_logix_context_manager_calls_open_and_close():
    with mock.patch.object(LogixDriver, 'open') as mock_open, \
            mock.patch.object(LogixDriver, 'close') as mock_close:
        with LogixDriver(CONNECT_PATH, init_info=False, init_tags=False):
            pass

        assert mock_open.called
        assert mock_close.called


def test__exit__returns_false_on_commerror():
    ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
    assert False == ld.__exit__(None, None, None)  # Exit with no exception


def test__exit__returns_true_on_no_error_and_no_exc_type():
    with mock.patch.object(LogixDriver, 'close'):
        ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
        assert True == ld.__exit__(None, None, None)


def test__exit__returns_false_on_no_error_and_exc_type():
    with mock.patch.object(LogixDriver, 'close'):
        ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
        assert False == ld.__exit__('Some Exc Type', None, None)


def test__repr___ret_str():
    ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
    assert str == type(ld.__repr__())


def test_default_logix_tags_are_empty_dict():
    """Show that LogixDriver tags are an empty dict on init."""
    ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
    assert ld.tags == dict()


def test_logix_connected_false_on_init_with_false_init_params():
    ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
    assert ld.connected == False


def test_logix_writeable_value_raises_requesterror_on_value_mismatch():
    with pytest.raises(RequestError):
        writable_value({
            'value': 'Hello',
            'elements': 1,
            'tag_info': {
                'data_type': 'WORD'
            }
        })


def test_clx_writeable_value_returns_bytes_if_bytes():
    TEST_PARSED_TAG = {'value': b'some bytes'}
    assert TEST_PARSED_TAG['value'] == writable_value(TEST_PARSED_TAG)


def test_clx_get_plc_time_sends_packet():
    with mock.patch.object(RequestPacket, 'send') as mock_send, \
            mock.patch('pycomm3.cip_base.with_forward_open'):
        ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
        ld.get_plc_time()
        assert mock_send.called


def test_clx_set_plc_time_sends_packet():
    with mock.patch.object(RequestPacket, 'send') as mock_send, \
            mock.patch('pycomm3.cip_base.with_forward_open'):
        ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
        ld.set_plc_time()
        assert mock_send.called


EXAMPLE_TAG = {
    'tag_info': {
        'tag_type': 'atomic',
        'data_type': 'bool'
    },
    'elements': 15
}


def test__tag_return_size_returns_int():
    assert type(_tag_return_size(EXAMPLE_TAG)) == int


def test__tag_return_size_returns_correct_size_for_bool():
    assert _tag_return_size(EXAMPLE_TAG) == 15


@pytest.mark.skip(reason="""tag parsing is extremely complex, and it's \
nearly impossible to test this without also reverse-engineering it""")
def test__get_tag_list_returns_expected_user_tags():
    EXPECTED_USER_TAGS = [{
        'tag_type': 'struct',  # bit 15 is a 1
        'instance_id': 1,
        'tag_name': b"\x00\x01",
        'symbol_type': "",
        'symbol_address': "",
        'symbol_object_address': "",
        'software_control': "",
        'external_access': "",
        'dimensions': ["", "", ""]
    }]

    TEST_RESPONSE = ResponsePacket()
    # 0 -> 4 are the 'instance', dint
    # 4 -> 6 is the 'tag_length', uint, used internally
    # 8 -> 'tag_length' is 'tag_name'
    # 8+tag_length -> 10+tag_length is 'symbol_type' uint
    # 10+tag_length -> 14+tag_length is 'symbol_address' udint
    # 14+tag_length -> 18+tag_length is 'symbol_object_address' udint
    # 18+tag_length -> 22+tag_length is 'software_control' udint
    # 'dim1', 'dim2' and 'dim3' are the next 12 bytes, udint
    TEST_RESPONSE.data = \
        b"\x00\x00\x00\x01" + \
        b"\x00\x01" + \
        b"\x00\x01" + \
        b"\x00\x00\x00\x00\x00\x10"
    TEST_RESPONSE.command = "Something"
    TEST_RESPONSE.command_status = SUCCESS

    ld = LogixDriver(CONNECT_PATH, init_info=False, init_tags=False)
    with mock.patch.object(RequestPacket, 'send') as mock_send, \
            mock.patch.object(CIPDriver, '_forward_open'), \
            mock.patch.object(LogixDriver, '_parse_instance_attribute_list'):
        mock_send.return_value = TEST_RESPONSE
        actual_tags = ld.get_tag_list()
    assert EXPECTED_USER_TAGS == actual_tags
