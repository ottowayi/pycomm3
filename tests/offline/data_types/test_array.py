from pycomm3.data_types import DINT, SINT, INT, StructType, STRING, array
from pycomm3.data_types._base import ArrayType
import pytest
from pycomm3.exceptions import DataError


def test_array_classes():
    assert issubclass(DINT[4], ArrayType)
    assert DINT[4].element_type is DINT
    assert DINT[4].length == 4
    assert DINT[SINT].length is SINT
    assert DINT[...].length is Ellipsis

    assert DINT[4].size == DINT.size * 4

    with pytest.raises(DataError):
        x = DINT[...].size

    with pytest.raises(DataError):
        x = DINT[INT].size

    assert DINT[1] == DINT[1]
    assert DINT[1] != DINT[2]
    assert DINT[None] == DINT[...]
    assert DINT[10] != INT[10]
    assert DINT[...] != INT[...]

    assert DINT[...] is DINT[...] is array(DINT, None)


elementary_tests = [
    (DINT, 1, [1], bytes(DINT(1))),
    (STRING, 1, ["hello there"], bytes(STRING("hello there"))),
    (DINT, 3, [1, 2, 3], bytes(DINT(1)) + bytes(DINT(2)) + bytes(DINT(3))),
]


@pytest.mark.parametrize("typ, length, values, encoded", elementary_tests)
def test_array_elementary(typ, length, values, encoded):
    ary_type = typ[length]
    ary = ary_type(values)

    assert bytes(ary) == encoded
    assert ary_type.decode(encoded) == ary


def test_array_slicing():
    ary = DINT[10](range(10))
    assert ary[:4] == DINT[4](range(4))
    assert bytes(ary[:4]) == bytes(DINT[4](range(4)))

    ary[5:] = [0, 0, 0, 0, 0]
    assert ary == DINT[10]([0, 1, 2, 3, 4, 0, 0, 0, 0, 0])
    assert bytes(ary[5:]) == bytes(DINT(0)) * 5
    assert ary[:2].size == DINT.size * 2


def test_array_struct():
    class S1(StructType):
        x: DINT = 0
        y: STRING = "xyz"
        z: DINT[...] = DINT[3]([1, 2, 3])

    ary = S1[3]([S1(), S1(), S1()])
    assert ary[0].x == 0
    assert bytes(ary) == bytes(S1()) * 3
    ary[1].z[0] = -1
    assert ary[1] == S1(z=[-1, 2, 3])
    assert bytes(ary) != (bytes(S1()) * 3)
    assert bytes(ary) == bytes(S1()) + bytes(S1(z=[-1, 2, 3])) + bytes(S1())
