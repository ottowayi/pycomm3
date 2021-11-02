import pytest

from pycomm3 import RequestError
from tests import tag_only
from . import BASE_ATOMIC_TESTS, BASE_ATOMIC_ARRAY_TESTS, BASE_STRUCT_TESTS, _bool_array


all_write_tests = [
    *[(f"write{tag}", dt, val) for tag, dt, val in BASE_ATOMIC_TESTS if "aoi" not in tag],
    *[(f"Program:pycomm3.write_prog{tag}", dt, val) for tag, dt, val in BASE_ATOMIC_TESTS if "aoi" not in tag],
    *[(f"write{tag}", dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS if "aoi" not in tag],
    *[(f"Program:pycomm3.write_prog{tag}", dt, val) for tag, dt, val in BASE_ATOMIC_ARRAY_TESTS if "aoi" not in tag],
    *[(f"write{tag}", dt, val) for tag, dt, val in BASE_STRUCT_TESTS if "aoi" not in tag],
    *[(f"Program:pycomm3.write_prog{tag}", dt, val) for tag, dt, val in BASE_STRUCT_TESTS if "aoi" not in tag],
]


@pytest.mark.parametrize("tag_name, data_type, value", all_write_tests)
def test_writes(plc, tag_name, data_type, value):
    result = plc.write((tag_name, value))
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type

    assert result == plc.read(tag_name)  # read the same tag and make sure it matches


@pytest.mark.parametrize(
    "tag_name, data_type, value",
    (
        ("write_bool_ary1[0]{32}", "BOOL[32]", _bool_array[:32]),
        ("write_bool_ary1[32]{32}", "BOOL[32]", _bool_array[32:64]),
        ("write_bool_ary1[32]{64}", "BOOL[64]", _bool_array[32:]),
    ),
)
def test_bool_array_writes(plc, tag_name, data_type, value):
    result = plc.write((tag_name, value))
    assert result
    assert result.error is None
    assert result.tag == tag_only(tag_name)
    assert result.type == data_type

    assert result == plc.read(tag_name)  # read the same tag and make sure it matches


def test_bool_array_invalid_writes(plc):
    result = plc.write("write_bool_ary1[1]{2}", [True, False])
    assert not result


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


# def _nested_dict_to_lists(src):
#     if isinstance(src, dict):
#         return [
#             _nested_dict_to_lists(value) if isinstance(value, dict) else value
#             for key, value in src.items()
#         ]
#     return src
#
#
# #
# # writing tags by value no longer supported
# # keeping here in case it is added back in the future
# struct_values_list_tests = [
#     *[(f'write{tag}', dt, _nested_dict_to_lists(val))
#       for tag, dt, val in BASE_STRUCT_TESTS if isinstance(val, dict)],
#
#     *[(f'Program:pycomm3.write_prog{tag}', dt, _nested_dict_to_lists(val))
#       for tag, dt, val in BASE_STRUCT_TESTS if isinstance(val, dict)],
# ]
#
#
# @pytest.mark.parametrize('tag_name, data_type, value', struct_values_list_tests)
# def test_struct_write_value_as_list(plc, tag_name, data_type, value):
#     """
#     verify that writing structures using nested lists works as well as dictionaries
#     """
#     result = plc.write((tag_name, value))
#     assert result
#
#     read_value = plc.read(tag_name).value
#     result = plc.write((tag_name, read_value))
#     assert result
#     assert plc.read(tag_name).value == read_value


def test_duplicate_tags_in_request(plc):
    tags = [
        ("write_int_max.0", True),
        ("write_int_max.1", False),
        ("write_int_max", 32_767),
        ("write_int_min", -32_768),
        ("write_bool_ary1[1]", False),
    ]

    results = plc.write(*tags, *tags)

    request_tags = [tag for tag, value in tags] * 2
    result_tags = [r.tag for r in results]

    assert result_tags == request_tags
    assert all(results)
