from pycomm3 import LogixDriver2
import os
from math import isclose
import pytest

SLOT = int(os.environ['slot'])
IP_ADDR = os.environ['ip']


@pytest.fixture(scope='module', autouse=True)
def plc_connection():
    with LogixDriver2(IP_ADDR, slot=SLOT) as plc:
        yield plc


tests = [
    ('DINT1', (20, 'DINT')),
    ('SINT1', (5, 'SINT')),
    ('INT1', (256, 'INT')),
    ('STRING1', ('A Test String', 'STRING')),
    ('bool1', (False, 'BOOL'))
]


@pytest.mark.parametrize('tag_name,expected', tests)
def test_single_reads(plc_connection, tag_name, expected):
    value, data_type = expected
    result = plc_connection.read(tag_name)
    assert result
    assert result.tag == tag_name
    assert result.value == value
    assert result.type == data_type
