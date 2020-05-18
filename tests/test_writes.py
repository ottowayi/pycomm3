from math import isclose
import pytest
from itertools import chain
from . import tag_only

atomic_tests = [  # (tag name, data type, value)

    # atomic tags
    ('DINT2', 'DINT', 100_000_000),
    ('SINT2', 'SINT', -128),
    ('INT2', 'INT', 256),
    ('REAL2', 'REAL', 25.2),
    ('BOOL3', 'BOOL', False),
    ('BOOL4', 'BOOL', True),
    ('STRING3', 'STRING', 'A test for writing to a string'),
    ('Program:Pycomm3_Testing._dint2', 'DINT', 111),
    ('Program:Pycomm3_Testing._real2', 'REAL', 222.22),
    ('Program:Pycomm3_Testing._string2', 'STRING', 'Hello World!'),

    # arrays
    ('SINT_ARY2{3}', 'SINT[3]', [1, 2, 3]),
    ('INT_ARY2[1]{5}', 'INT[5]', [255, 254, 253, 252, 251]),
    ('STRING_ARY2[0]{5}', 'STRING[5]', 'A B C D E'.split()),


    # bits of integers
    ('DINT3.0', 'BOOL', True),
    ('DINT3.31', 'BOOL', True),
    ('INT1.8', 'BOOL', True),
    ('INT1.15', 'BOOL', False),
    ('SINT1.2', 'BOOL', True),
    ('SINT1.7', 'BOOL', False),

    # boolean array tests
    ('bool_ary2[0]', 'BOOL', True),
    ('bool_ary2[3]', 'BOOL', True),
    ('bool_ary2[32]', 'BOOL', False),
    ('bool_ary2[63]', 'BOOL', True),

    # structure elements
    ('TestAOI2_1.OutputDINT', 'DINT', 1234_5678),
    ('TestAOI2_1._bool', 'BOOL', True),
    ('TestAOI2_1._counters[0].DN', 'BOOL', True),
    ('TestAOI2_1._counters[1].PRE', 'DINT', 1000),
    ('TestAOI2_1._strings[0]', 'STRING20', 'Hello World!'),
    ('TestAOI2_1._bools[0]', 'BOOL', True),
    ('Program:Pycomm3_Testing._udt2.bool', 'BOOL', True),
    ('Program:Pycomm3_Testing._udt2.dint', 'DINT', 11),
]


@pytest.mark.parametrize('tag_name, data_type, value', atomic_tests)
def test_atomic_writes(plc, tag_name, data_type, value):
    result = plc.write((tag_name, value))
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type
