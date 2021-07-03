"""Tests for the SLCDriver

The methods and functions in the slc_driver.py file are extraordinarily
difficult to test.
"""

from pycomm3.const import SLC_REPLY_START, SUCCESS
from pycomm3.packets import ResponsePacket, SendUnitDataResponsePacket, RequestPacket, SendUnitDataRequestPacket
from pycomm3.cip_driver import CIPDriver
from unittest import mock

import pytest
from pycomm3.exceptions import ResponseError, RequestError

from pycomm3.slc_driver import SLCDriver, _parse_read_reply
from pycomm3.tag import Tag

CONNECT_PATH = '192.168.1.100/1'



def test_slc__read_tag_raises_requesterror_for_none():
    driver = SLCDriver(CONNECT_PATH)

    with mock.patch('pycomm3.slc_driver.parse_tag', return_value=None):
        with pytest.raises(RequestError):
            driver._read_tag(None)


def test_slc__read_tag_returns_tag():
    TEST_PARSED_TAG = {
        'file_type': 'N',
        'file_number': '1',
        'element_number': '1',
        'pos_number': '1',
        'address_field': 2,
        'element_count': 1,
        'tag': 'Dummy Parsed Tag'
    }
    RESPONSE_PACKET = ResponsePacket(RequestPacket(), b'\x00')
    driver = SLCDriver(CONNECT_PATH)

    with mock.patch('pycomm3.slc_driver.parse_tag', return_value=TEST_PARSED_TAG), \
         mock.patch.object(SLCDriver, 'send') as mock_send:
        mock_send.return_value = RESPONSE_PACKET
        assert type(driver._read_tag("Anything at all")) == Tag


def test_slc_get_processor_type_returns_none_if_falsy_response():
    driver = SLCDriver(CONNECT_PATH)
    RESPONSE_PACKET = SendUnitDataResponsePacket(SendUnitDataRequestPacket(driver._sequence), b'\x00')

    with mock.patch.object(SLCDriver, 'send') as mock_send, \
         mock.patch.object(CIPDriver, '_forward_open'):
        mock_send.return_value = RESPONSE_PACKET
        assert driver.get_processor_type() is None


def test_slc_get_processor_type_returns_none_if_parsing_exception():
    driver = SLCDriver(CONNECT_PATH)
    EXPECTED_TYPE = None

    with mock.patch.object(SLCDriver, 'send') as mock_send, \
         mock.patch.object(CIPDriver, '_forward_open'), \
         mock.patch.object(ResponsePacket, '_parse_reply'):
        RESPONSE_PACKET = SendUnitDataResponsePacket(SendUnitDataRequestPacket(driver._sequence), b'\x00')
        RESPONSE_PACKET.command = "Something"
        RESPONSE_PACKET.command_status = SUCCESS
        
        mock_send.return_value = RESPONSE_PACKET
        assert EXPECTED_TYPE == driver.get_processor_type()


def test__parse_read_reply_raises_dataerror_if_exception():
    driver = SLCDriver(CONNECT_PATH)

    with pytest.raises(ResponseError):
        _parse_read_reply('bad', 'data')
