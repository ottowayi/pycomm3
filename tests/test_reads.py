from pycomm3 import LogixDriver2
import os
from math import isclose
import pytest
from itertools import chain

SLOT = int(os.environ['slot'])
IP_ADDR = os.environ['ip']


@pytest.fixture(scope='module', autouse=True)
def plc():
    with LogixDriver2(IP_ADDR, slot=SLOT) as plc_:
        yield plc_


def _tag_only(tag):
    if '{' in tag:
        return tag[:tag.find('{')]
    else:
        return tag


atomic_tests = [  # (tag name, value, data type)
    ('DINT1', 'DINT', 20),
    ('SINT1', 'SINT', 5),
    ('INT1', 'INT', 256),
    ('STRING1', 'STRING', 'A Test String'),
    ('STRING2', 'STRING', ''),
    ('BOOL1', 'BOOL', False),
    ('DINT1.0', 'BOOL', False),
    ('SINT1.2', 'BOOL', True),
    ('SINT1.7', 'BOOL', False),
    ('INT1.8', 'BOOL', True),
    ('INT1.13', 'BOOL', False),
    ('REAL1', 'REAL', 100.001),
    ('SINT_ARY1[0]', 'SINT', 0),
    ('SINT_ARY1[4]', 'SINT', 4),
    ('INT_ARY1[10]', 'INT', 100),
    ('DINT_ARY1[99]', 'DINT', 99000),
    ('SINT_ARY1{10}', 'SINT[10]', list(range(10))),
    ('INT_ARY1{15}', 'INT[15]', [i*10 for i in range(15)]),
    ('DINT_ARY1{100}', 'DINT[100]', [i*1000 for i in range(100)]),
    ('SINT_ARY1[4]{3}', 'SINT[3]', [4, 5, 6]),
    ('INT_ARY1[1]{10}', 'INT[10]', [i*10 for i in range(1, 11)]),
    ('STRING_ARY1{5}', 'STRING[5]', 'first Second THIRD FoUrTh 5th'.split()),
    ('STRING20_ARY1{10}', 'STRING20[10]', [f'{i}' * 20 for i in range(10)]),
    ('REAL_ARY1[0]', 'REAL', .001),
    ('REAL_ARY1[6]', 'REAL', 0.0),
    ('SimpleUDT1_1.bool', 'BOOL', True),
    ('SimpleUDT1_1.sint', 'SINT', 100),
    ('SimpleUDT1_1.int', 'INT', -32768),
    ('SimpleUDT1_1.dint', 'DINT', -1),
    ('bool_ary1{3}', 'DWORD[3]', list(chain((i % 2 == 0 for i in range(16)), (True for i in range(16)),
                                            (False for i in range(63)), (True,)))),
    ('bool_ary1[0]', 'BOOL', True),
    ('bool_ary1[1]', 'BOOL', False),
    ('bool_ary1[32]', 'BOOL', False),
    ('bool_ary1[95]', 'BOOL', True),
]


@pytest.mark.parametrize('tag_name, data_type, value', atomic_tests)
def test_atomic_reads(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == _tag_only(tag_name)
    assert result.type == data_type

    if 'REAL' in data_type:
        assert isclose(result.value, value, rel_tol=1e-4)
    else:
        assert result.value == value


struct_tests = [  # tag name, (data type, value)
    ('SimpleUDT1_1', 'SimpleUDT1', {'dint': -1, 'sint': 100, 'int': -32768, 'bool': True}),
    ('TIMER1', 'TIMER', {'PRE': 30000, 'ACC': 30200, 'TT': True, 'EN': False, 'DN': True})
]


def test_multi_read(plc):
    tags = [tag for (tag, _, __) in atomic_tests]
    results = plc.read(*tags)
    assert len(results) == len(atomic_tests)
    for result, (tag, typ, value) in zip(results, atomic_tests):
        assert result.tag == _tag_only(tag)
        # assert result.type == typ
        if 'REAL' in typ:
            assert isclose(result.value, value, rel_tol=1e-4)
        else:
            assert result.value == value


@pytest.mark.parametrize('tag_name, data_type, value', struct_tests)
def test_udt_read(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == _tag_only(tag_name)
    assert result.type == data_type

    for val in value:
        read_val = result.value.get(val)
        assert read_val is not None
        if data_type == 'REAL':
            assert isclose(read_val, value[val], rel_tol=1e-4)
        else:
            assert read_val == value[val]



