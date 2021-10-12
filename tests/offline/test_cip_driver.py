"""Tests for the logix_driver.py file.

There are quite a few methods in the CIPDriver which are difficult to
read or test due to both code clarity and complexity issues. As well as
there being no way to control the execution of many of the private
methods through the public API. This has lead to testing of quite a few
private API methods to achieve an acceptable test coverage.
"""
import itertools
from unittest import mock

import pytest

from pycomm3 import (
    PADDED_EPATH,
    UDINT,
    CIPDriver,
    CommError,
    DataError,
    PortSegment,
    PycommError,
    RequestError,
    ResponseError,
    parse_connection_path,
)
from pycomm3.socket_ import Socket

from . import Mocket

CONNECT_PATH = "192.168.1.100"


_simple_path = (
    "192.168.1.100",
    [
        PortSegment("bp", 0),
    ],
)
_simple_paths = [
    "192.168.1.100/bp/0",
    "192.168.1.100/backplane/0",
    r"192.168.1.100\bp\0",
    r"192.168.1.100\backplane\0",
]

_route_path = (
    "192.168.1.100",
    [
        PortSegment(port="backplane", link_address=1),
        PortSegment(port="enet", link_address="10.11.12.13"),
        PortSegment(port="bp", link_address=0),
    ],
)
_route_paths = [
    "192.168.1.100/backplane/1/enet/10.11.12.13/bp/0",
    r"192.168.1.100\backplane\1\enet\10.11.12.13\bp\0",
]

path_tests = [
    *[(p, _simple_path) for p in _simple_paths],
    *[(p, _route_path) for p in _route_paths],
    ("192.168.1.100", ("192.168.1.100", [])),
]


@pytest.mark.parametrize("path, expected_output", path_tests)
def test_plc_path(path, expected_output):
    assert parse_connection_path(path) == expected_output


auto_slot_path_tests = [
    ("192.168.1.100", _simple_path),
    ("192.168.1.100/0", _simple_path),
    (r"192.168.1.100\0", _simple_path),
]


@pytest.mark.parametrize("path, expected_output", auto_slot_path_tests)
def test_plc_path_auto_slot(path, expected_output):
    assert parse_connection_path(path, auto_slot=True) == expected_output


_bad_paths = [
    "192",
    "192.168",
    "192.168.1",
    "192.168.1.1.100",
    "300.1.1.1",
    "1.300.1.1",
    "1.1.300.1",
    "1.1.1.300",
    "192.168.1.100/Z",
    "bp/0",
    "192.168.1.100/backplan/1",
    "192.168.1.100/backplane/1/10.11.12.13/bp/0",
]


@pytest.mark.parametrize("path", _bad_paths)
def test_bad_plc_paths(path):
    with pytest.raises(
        (DataError, RequestError),
    ):
        ip, segments = parse_connection_path(path)
        PADDED_EPATH.encode(segments, length=True)


def test_cip_get_module_info_raises_response_error_if_response_falsy():
    with mock.patch.object(CIPDriver, "generic_message") as mock_generic_message:
        mock_generic_message.return_value = False
        with pytest.raises(ResponseError):
            driver = CIPDriver(CONNECT_PATH)
            driver.get_module_info(1)

        assert mock_generic_message.called


def test_get_module_info_returns_expected_identity_dict():
    EXPECTED_DICT = {
        "vendor": "Rockwell Automation/Allen-Bradley",
        "product_type": "Programmable Logic Controller",
        "product_code": 89,
        "revision": {"major": 20, "minor": 19},
        "status": b"`0",
        "serial": "c00fa09b",
        "product_name": "1769-L23E-QBFC1 LOGIX5323E-QBFC1",
    }

    RESPONSE_BYTES = (
        b"o\x00C\x00\x02\x13\x02\x0b\x00\x00\x00\x00_pycomm_\x00\x00\x00\x00\x00\x00\x00\x00\n"
        b"\x00\x02\x00\x00\x00\x00\x00\xb2\x003\x00\x81\x00\x00\x00\x01\x00\x0e\x00Y\x00\x14\x13"
        b"`0\x9b\xa0\x0f\xc0 1769-L23E-QBFC1 LOGIX5323E-QBFC1"
    )

    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket(RESPONSE_BYTES)
    actual_response = driver.get_module_info(1)
    assert actual_response == EXPECTED_DICT


viable_methods = ["_forward_close", "_un_register_session"]
viable_exceptions = Exception.__subclasses__() + PycommError.__subclasses__()
param_values = list(itertools.product(viable_methods, viable_exceptions))


@pytest.mark.parametrize(["mock_method", "exception"], param_values)
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
            driver._target_is_connected = True
            driver._session = 1
            driver.close()


def test_context_manager_calls_open_close():
    with mock.patch.object(CIPDriver, "open") as mock_close, mock.patch.object(
        CIPDriver, "close"
    ) as mock_open:
        with CIPDriver(CONNECT_PATH) as driver:
            ...
        assert mock_open.called
        assert mock_close.called


def test_context_manager_calls_open_close_with_exception():
    with mock.patch.object(CIPDriver, "open") as mock_close, mock.patch.object(
        CIPDriver, "close"
    ) as mock_open:
        try:
            with CIPDriver(CONNECT_PATH) as driver:
                x = 1 / 0
        except Exception:
            ...
        assert mock_open.called
        assert mock_close.called


def test_close_raises_no_error_on_close_with_registered_session():
    driver = CIPDriver(CONNECT_PATH)
    driver._session = 1
    driver._sock = Mocket()
    driver.close()


def test_close_raises_commerror_on_socket_close_exception():
    with mock.patch.object(Socket, "close") as mock_close:
        mock_close.side_effect = Exception
        with pytest.raises(CommError):
            driver = CIPDriver(CONNECT_PATH)
            driver._sock = Socket()
            driver.close()


def test_close_calls_socket_close_if_socket():
    with mock.patch.object(Mocket, "close") as mock_close:
        driver = CIPDriver(CONNECT_PATH)
        driver._sock = Mocket()
        driver.close()
        assert mock_close.called


def test_open_raises_commerror_on_connect_fail():
    with mock.patch.object(Socket, "connect") as mock_connect:
        mock_connect.side_effect = Exception
        driver = CIPDriver(CONNECT_PATH)
        with pytest.raises(CommError):
            driver.open()


def test_open_returns_false_if_register_session_falsy():
    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket()
    assert not driver.open()


def test_open_returns_true_if_register_session_truthy():
    with mock.patch.object(CIPDriver, "_register_session") as mock_register:
        mock_register.return_value = 1
        driver = CIPDriver(CONNECT_PATH)
        driver._sock = Mocket()
        assert driver.open()


def test__forward_close_returns_false_if_no_response():
    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket()
    driver._session = 1
    assert not driver._forward_close()


def test__forward_close_returns_true_if_response():
    driver = CIPDriver(CONNECT_PATH)
    driver._session = 1
    response = (
        b"o\x00\x1e\x00\x02\x16\x02\x0b\x00\x00\x00\x00_pycomm_"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\n\x00\x02\x00\x00\x00"
        b"\x00\x00\xb2\x00\x0e\x00\xce\x00\x00\x00'\x04\t\x10\xd6\x9c\x06=\x00\x00"
    )
    driver._sock = Mocket(response)
    assert driver._forward_close()


def test__forward_close_raises_commerror_if_session_zero():
    driver = CIPDriver(CONNECT_PATH)
    with pytest.raises(CommError):
        driver._forward_close()


@pytest.mark.parametrize("conf_session", range(1, 100))
def test__register_session_returns_configured_session(conf_session):
    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket(bytes(4) + UDINT.encode(conf_session) + bytes(20))
    assert conf_session == driver._register_session()


def test__register_session_returns_none_if_no_response():
    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket()
    assert driver._register_session() is None


def test__forward_open_returns_true_if_already_connected():
    driver = CIPDriver(CONNECT_PATH)
    driver._target_is_connected = True
    assert driver._forward_open()


def test__forward_open_returns_false_if_falsy_response():
    driver = CIPDriver(CONNECT_PATH)
    driver._sock = Mocket()
    driver._session = 1
    assert not driver._forward_open()


def test__forward_open_raises_commerror_if_session_is_zero():
    driver = CIPDriver(CONNECT_PATH)
    with pytest.raises(CommError):
        driver._forward_open()
