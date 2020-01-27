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
]


@pytest.mark.parametrize('tag_name, data_type, value', atomic_tests)
def test_atomic_writes(plc, tag_name, data_type, value):
    result = plc.write((tag_name, value))
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type
