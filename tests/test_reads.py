from math import isclose
import pytest
from itertools import chain
from . import tag_only


atomic_tests = [  # (tag name, data type, value)

    # atomic tags
    ('DINT1', 'DINT', 20),
    ('SINT1', 'SINT', 5),
    ('INT1', 'INT', 256),
    ('REAL1', 'REAL', 100.001),
    ('BOOL1', 'BOOL', False),
    ('Program:Pycomm3_Testing._dint1', 'DINT', 111),
    ('Program:Pycomm3_Testing._real1', 'REAL', 222.22),

    # bits of integers
    ('DINT1.0', 'BOOL', False),
    ('DINT1.31', 'BOOL', False),
    ('INT1.8', 'BOOL', True),
    ('INT1.15', 'BOOL', False),
    ('SINT1.2', 'BOOL', True),
    ('SINT1.7', 'BOOL', False),

    # single array elements
    ('DINT_ARY1[99]', 'DINT', 99000),
    ('INT_ARY1[10]', 'INT', 100),
    ('SINT_ARY1', 'SINT', 0),  # no element == first element
    ('SINT_ARY1[4]', 'SINT', 4),
    ('REAL_ARY1[0]', 'REAL', .001),
    ('REAL_ARY1[6]', 'REAL', 0.0),

    # multiple array elements
    ('DINT_ARY1[10]{3}', 'DINT[3]', [10000, 11000, 12000]),
    ('INT_ARY1[1]{10}', 'INT[10]', [i*10 for i in range(1, 11)]),
    ('SINT_ARY1[4]{3}', 'SINT[3]', [4, 5, 6]),
    ('REAL_ARY1[2]{2}', 'REAL[2]', [.1, 1.0]),

    ('DINT_ARY1{100}', 'DINT[100]', [i*1000 for i in range(100)]),
    ('INT_ARY1{15}', 'INT[15]', [i*10 for i in range(15)]),
    ('SINT_ARY1{10}', 'SINT[10]', list(range(10))),

    # elements from a structure
    ('SimpleUDT1_1.bool', 'BOOL', True),
    ('SimpleUDT1_1.sint', 'SINT', 100),
    ('SimpleUDT1_1.int', 'INT', -32768),
    ('SimpleUDT1_1.dint', 'DINT', -1),
    ('Program:Pycomm3_Testing._udt1.sint', 'SINT', 1),
    ('Program:Pycomm3_Testing._udt1.int', 'INT', 2),
    ('Program:Pycomm3_Testing._udt1.dint', 'DINT', 3),

    # boolean array tests
    ('bool_ary1[0]', 'BOOL', True),
    ('bool_ary1[1]', 'BOOL', False),
    ('bool_ary1[32]', 'BOOL', False),
    ('bool_ary1[95]', 'BOOL', True),
    ('bool_ary1{3}', 'BOOL[96]', list(chain((i % 2 == 0 for i in range(16)), (True for i in range(16)),
                                            (False for i in range(63)), (True,)))),

    # strings, technically structures, but value is similar to atomic types
    ('STRING1', 'STRING', 'A Test String °'),
    ('STRING2', 'STRING', ''),
    ('STRING20_1', 'STRING20', 'x'*20),
    ('LongString1', 'STR_480', 'A 480 char string.'),
    ('STRING_ARY1{5}', 'STRING[5]', 'first Second THIRD FoUrTh 5th'.split()),
    ('STRING20_ARY1{10}', 'STRING20[10]', [f'{i}' * 20 for i in range(10)]),
    ('Program:Pycomm3_Testing._string1', 'STRING', 'A program scoped string'),

]


@pytest.mark.parametrize('tag_name, data_type, value', atomic_tests)
def test_atomic_reads(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type

    if 'REAL' in data_type:
        if isinstance(value, list):
            assert all(isclose(rval, val, rel_tol=1e-4) for rval, val in zip(result.value, value))
        else:
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
        assert result.tag == tag_only(tag)
        # assert result.type == typ
        if 'REAL' in typ:
            if isinstance(value, list):
                assert all(isclose(rval, val, rel_tol=1e-4) for rval, val in zip(result.value, value))
            else:
                assert isclose(result.value, value, rel_tol=1e-4)
        else:
            assert result.value == value


@pytest.mark.parametrize('tag_name, data_type, value', struct_tests)
def test_udt_read(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type

    for val in value:
        read_val = result.value.get(val)
        assert read_val is not None
        if data_type == 'REAL':
            assert isclose(read_val, value[val], rel_tol=1e-4)
        else:
            assert read_val == value[val]



