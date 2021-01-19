"""Response Class and function tests.

It is borderline impossible to cover the responses with tests due to
extremely high cyclomatic complexity in the methods and functions here.

https://www.sonarsource.com/docs/CognitiveComplexity.pdf
https://en.wikipedia.org/wiki/Cyclomatic_complexity#Definition
"""
from pycomm3.packets.responses import get_extended_status, parse_read_reply_struct


def test_unknown_status_size_if_not_branch():
    TEST_MESSAGE = b'\xFF\xFF'
    EXPECTED_RESULT = 'Extended Status Size Unknown'
    assert EXPECTED_RESULT == get_extended_status(TEST_MESSAGE, 0)

def test_no_ext_status_on_lookup_error():
    EXPECTED_RESULT = 'No Extended Status'
    assert EXPECTED_RESULT == get_extended_status(b'\x00\x00', 0)

def test_parse_read_reply_struct_with_no_attributes_returns_empty_dict():
    result = parse_read_reply_struct([0], {
        'internal_tags': {
            'parsed_tag_name': {
                'data_type': 'BOOL',
                'offset': 0,
                'tag_type': 'atomic'
            }
        },
        'attributes': []
    })
    assert result == {}

    