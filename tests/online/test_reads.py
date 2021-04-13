from itertools import chain

import pytest

from tests import tag_only
from . import BASE_ATOMIC_TESTS, BASE_ATOMIC_ARRAY_TESTS, BASE_STRUCT_TESTS, _bool_array


all_read_tests = list(chain.from_iterable((
    [(f'read{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_TESTS],
    [(f'Program:pycomm3.read_prog{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_TESTS],
    [(f'read{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS],
    [(f'Program:pycomm3.read_prog{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS],
    [(f'read{tag}', dt, val) for tag, dt, val in BASE_STRUCT_TESTS],
    [(f'Program:pycomm3.read_prog{tag}', dt, val) for tag, dt, val in BASE_STRUCT_TESTS],

)))


@pytest.mark.parametrize('tag_name, data_type, value', all_read_tests)
def test_reads(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type
    assert result.value == value


@pytest.mark.parametrize('tag_name, data_type, value', (
    ('read_bool_ary1[1]{32}', 'BOOL[32]', _bool_array[1:33]),
    ('read_bool_ary1[32]{32}', 'BOOL[32]', _bool_array[32:64]),
    ('read_bool_ary1[32]{64}', 'BOOL[64]', _bool_array[32:]),
    ('read_bool_ary1[10]{80}', 'BOOL[80]', _bool_array[10:90]),
))
def test_bool_array_reads(plc, tag_name, data_type, value):
    result = plc.read(tag_name)
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type
    assert result.value == value


def test_multi_read(plc):
    """
    Read all the test tags in a single read() call instead of individually
    """
    tags = [tag for (tag, _, __) in all_read_tests]
    results = plc.read(*tags)
    assert len(results) == len(all_read_tests)

    for result, (tag, typ, value) in zip(results, all_read_tests):
        assert result
        assert result.error is None
        assert result.tag == tag_only(tag)
        assert result.type == typ
        assert result.value == value


def test_duplicate_tags_in_request(plc):
    tags = [
        'read_dint_max.0', 'read_dint_max.1', 'read_int_max', 'read_bool1', 'read_int_max'
    ]

    results = plc.read(*tags, *tags)

    result_tags = [r.tag for r in results]

    assert result_tags == tags * 2
    assert all(results)
