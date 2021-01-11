from itertools import chain
from time import sleep

import pytest

from tests import tag_only
from . import BASE_ATOMIC_TESTS, BASE_ATOMIC_ARRAY_TESTS, BASE_STRUCT_TESTS

all_write_tests = list(chain.from_iterable((
    [(f'write{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_TESTS],
    [(f'Program:pycomm3.write_prog{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_TESTS],
    [(f'write{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS],
    [(f'Program:pycomm3.write_prog{tag}', dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS],
    [(f'write{tag}', dt, val) for tag, dt, val in BASE_STRUCT_TESTS],
    [(f'Program:pycomm3.write_prog{tag}', dt, val) for tag, dt, val in BASE_STRUCT_TESTS],
)))


@pytest.mark.parametrize('tag_name, data_type, value', all_write_tests)
def test_writes(plc, tag_name, data_type, value):
    result = plc.write((tag_name, value))
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type

    assert result == plc.read(tag_name)  # read the same tag and make sure it matches


def test_multi_write(plc):
    """
    Read all the test tags in a single read() call instead of individually
    """
    tags = [(tag, value) for (tag, _, value) in all_write_tests]
    results = plc.write(*tags)
    assert len(results) == len(all_write_tests)

    for result, (tag, typ, value) in zip(results, all_write_tests):
        assert result
        assert result.error is None
        assert result.tag == tag_only(tag)
        assert result.type == typ
        assert result.value == value

