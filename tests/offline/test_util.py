from pycomm3.util import strip_array, get_array_index

TEST_TAG = "This is a tag"


def test_strip_array_removes_data_past_left_bracket():
    TEST_ARRAY = "[123]"
    assert TEST_TAG == strip_array(TEST_TAG + TEST_ARRAY)


def test_strip_array_with_no_array_returns_tag():
    assert TEST_TAG == strip_array(TEST_TAG)


def test_get_array_index_returns_0_idx_with_no_array():
    EXPECTED = (TEST_TAG, None)
    assert EXPECTED == get_array_index(TEST_TAG)


def test_get_array_index_returns_index_value():
    TEST_ARRAY = "[123]"
    EXPECTED = (TEST_TAG, 123)
    assert EXPECTED == get_array_index(TEST_TAG + TEST_ARRAY)
