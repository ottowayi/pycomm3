"""Tests for bytes_ functionality.

Almost all of these tests are based on executing the function and using
the results as the expected value. These are works-as-I-found-it tests,
not exhibits-expected-behavior-tests.
"""
import pytest
from pycomm3.bytes_ import (
    print_bytes_msg,
    _encode_pccc_ascii,
    _encode_pccc_string
)


def test_print_bytes_msg_returns_expected_output_for_msg():
    """Existing behavior test for print_bytes_message.
    
    This test just validates that the behavior as-is in the code at the
    time the test was added.
    """
    TEST_MESSAGE = b'This is a message'
    EXPECTED_RESPONSE = '\n(0000) 54 68 69 73 20 69 73 20 61 20 \n(0010) 6d 65 73 73 61 67 65 '
    assert EXPECTED_RESPONSE == print_bytes_msg(TEST_MESSAGE)

@pytest.mark.parametrize(
    ['trial_input', 'expected_response'],
    [('A', b' A'), ('AB', b'BA')]
)
def test__encode_pccc_ascii_returns_expected_output_for_string(trial_input, expected_response):
    assert expected_response == _encode_pccc_ascii(trial_input)

def test__encode_pccc_ascii_raises_valueerror_on_strlen_gt_two():
    with pytest.raises(ValueError):
        _encode_pccc_ascii("ABC")