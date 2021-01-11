import pytest
from pycomm3.cip_base import parse_connection_path
from pycomm3 import RequestError

_simple_path = ('192.168.1.100', b'\x01\x01\x00')
_simple_paths = [
    '192.168.1.100',
    '192.168.1.100/0',
    r'192.168.1.100\0',
    '192.168.1.100/bp/0',
    '192.168.1.100/backplane/0',
    r'192.168.1.100\bp\0',
    r'192.168.1.100\backplane\0'
]

_route_path = ('192.168.1.100', b'\t\x01\x01\x12\x0b10.11.12.13\x00\x01\x00')
_route_paths = [
    '192.168.1.100/backplane/1/enet/10.11.12.13/bp/0',
    r'192.168.1.100\backplane\1\enet\10.11.12.13\bp\0'
]

path_tests = [
    *[(p, _simple_path) for p in _simple_paths],
    *[(p, _route_path) for p in _route_paths],
]


@pytest.mark.parametrize('path, expected_output', path_tests)
def test_plc_path(path, expected_output):
    assert parse_connection_path(path) == expected_output


_bad_paths = [
    '192',
    '192.168',
    '192.168.1',
    '192.168.1.1.100',
    '300.1.1.1',
    '1.300.1.1',
    '1.1.300.1',
    '1.1.1.300',
    '192.168.1.100/Z',
    'bp/0',
    '192.168.1.100/backplan/1',
    '192.168.1.100/backplane/1/10.11.12.13/bp/0'
]

@pytest.mark.parametrize('path', _bad_paths)
def test_bad_plc_paths(path):
    with pytest.raises(RequestError):
        parse_connection_path(path)