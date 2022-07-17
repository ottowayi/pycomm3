import pytest

from pycomm3.data_types import (
    DINT,
    INT,
    LINT,
    LREAL,
    REAL,
    SINT,
    UDINT,
    UINT,
    ULINT,
    USINT,
    BYTE,
    WORD,
    DWORD,
    LWORD,
    BOOL,
)
from pycomm3.exceptions import DataError

i8_range = (-128, 127)
u8_range = (0, 255)
i16_range = (-32_768, 32_767)
u16_range = (0, 65_535)
i32_range = (-(2**31), (2**31) - 1)
u32_range = (0, (2**32) - 1)
i64_range = (-(2**63), (2**63) - 1)
u64_range = (0, (2**64) - 1)
shared = (0, 1, 31, 32, 69, 100)

int_value_tests = [
    *((SINT, x) for x in (*i8_range, *shared)),
    *((USINT, x) for x in (*u8_range, *shared)),
    *((BYTE, x) for x in (*u8_range, *shared)),
    *((INT, x) for x in (*i16_range, *shared)),
    *((UINT, x) for x in (*u16_range, *shared)),
    *((WORD, x) for x in (*u16_range, *shared)),
    *((DINT, x) for x in (*i32_range, *shared)),
    *((UDINT, x) for x in (*u32_range, *shared)),
    *((DWORD, x) for x in (*u32_range, *shared)),
    *((LINT, x) for x in (*i64_range, *shared)),
    *((ULINT, x) for x in (*u64_range, *shared)),
    *((LWORD, x) for x in (*u64_range, *shared)),
]


@pytest.mark.parametrize('typ, value', int_value_tests)
def test_int_types(typ, value):
    encoded = typ.encode(value)
    decoded = typ.decode(encoded)
    assert len(encoded) == typ.size
    assert isinstance(encoded, bytes)
    assert encoded == typ(value).__encoded_value__
    assert decoded == value
    assert isinstance(decoded, typ)


int_range_tests = [
    (SINT, i8_range),
    (USINT, u8_range),
    (BYTE, u8_range),
    (INT, i16_range),
    (UINT, u16_range),
    (WORD, u16_range),
    (DINT, i32_range),
    (UDINT, u32_range),
    (DWORD, u32_range),
    (LINT, i64_range),
    (ULINT, u64_range),
    (LWORD, u64_range),
]


@pytest.mark.parametrize('typ, rng', int_range_tests)
def test_int_out_of_range(typ, rng):
    min, max = rng

    with pytest.raises(DataError):
        typ(min - 1)

    with pytest.raises(DataError):
        typ(max + 1)


float_value_tests = [
    (REAL, 0.00),
    (REAL, 1.23456),
    (REAL, 1_234_567.00009),
    (REAL, -0.00789),
    (REAL, -1234.5),
    (LREAL, 0.00),
    (LREAL, 1.23456),
    (LREAL, 1_234_567.00009),
    (LREAL, -0.00789),
    (LREAL, -1234.5),
]


@pytest.mark.parametrize('typ, value', float_value_tests)
def test_float_types(typ, value):
    encoded = typ.encode(value)
    decoded = typ.decode(encoded)
    assert len(encoded) == typ.size
    assert isinstance(encoded, bytes)
    assert encoded == typ(value).__encoded_value__
    assert decoded == pytest.approx(value)
    assert isinstance(decoded, typ)


unsupported_values = [
    'abc',
    [0, 1, 2],
    b'\x00\x01\x03\x04',
    object(),
    {'1': 2},
]

invalid_type_tests = [
    (typ, val)
    for val in unsupported_values
    for typ in [
        DINT,
        INT,
        LINT,
        LREAL,
        REAL,
        SINT,
        UDINT,
        UINT,
        ULINT,
        USINT,
        BYTE,
        WORD,
        DWORD,
        LWORD,
    ]
]


@pytest.mark.parametrize('typ, value', invalid_type_tests)
def test_invalid_values(typ, value):
    with pytest.raises(DataError):
        typ(value)


bit_array_tests = [
    (BYTE, 0, (0,) * 8),
    (BYTE, u8_range[1], (1,) * 8),
    (BYTE, 1, (1, 0, 0, 0, 0, 0, 0, 0)),
    (WORD, 0, (0,) * 16),
    (WORD, u16_range[1], (1,) * 16),
    (WORD, 1, (1, *(0 for _ in range(15)))),
    (DWORD, 0, (0,) * 32),
    (DWORD, u32_range[1], (1,) * 32),
    (DWORD, 1, (1, *(0 for _ in range(31)))),
    (LWORD, 0, (0,) * 64),
    (LWORD, u64_range[1], (1,) * 64),
    (LWORD, 1, (1, *(0 for _ in range(63)))),
]


@pytest.mark.parametrize('typ, value, bits', bit_array_tests)
def test_bit_arrays(typ, value, bits):
    assert typ(value).bits == bits
    assert typ(bits) == value


bool_tests = [
    *((x, True) for x in (True, 1, -1, 1_000_000)),
    *((x, False) for x in (False, 0)),
]


@pytest.mark.parametrize('val, bool_', bool_tests)
def test_bool(val, bool_):
    if bool_:
        assert BOOL(val)
    else:
        assert not BOOL(val)
    assert BOOL(val) == bool_
    assert bool(BOOL(val)) is bool_
    assert bytes(BOOL(val)) == (b'\xFF' if bool_ else b'\x00')
