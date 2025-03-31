from typing import Sequence

import pytest

from pycomm3 import USINT, DataError, UDINT, SHORT_STRING
from pycomm3.data_types import StructType, UINT, SINT, DINT, STRING, ArrayType, attr, Annotated, Array
from dataclasses import asdict


def test_struct_simple():
    class S1(StructType):
        x: UINT
        y: SINT
        z: DINT

    assert S1.size == sum((UINT.size, SINT.size, DINT.size))

    s1 = S1(1, 2, 3)

    assert s1.x.__class__ is UINT
    assert s1.x == 1
    assert s1.x == UINT(1)
    assert dict(s1) == {"x": UINT(1), "y": SINT(2), "z": DINT(3)}
    assert dict(s1) == {**s1}
    assert bytes(s1) == bytes(UINT(1)) + bytes(SINT(2)) + bytes(DINT(3))
    s1.x = 100
    assert bytes(s1) == bytes(UINT(100)) + bytes(SINT(2)) + bytes(DINT(3))


def test_nested_struct():
    class S1(StructType):
        x: DINT
        y: DINT
        z: STRING

    class S2(StructType):
        a: S1
        b: DINT

    s2 = S2(S1(1, 2, "Hello"), 100)

    assert s2.a.x == 1
    assert s2.a.x.__class__ is DINT
    assert asdict(s2) == {
        "a": {"x": 1, "y": 2, "z": "Hello"},
        "b": 100,
    }
    assert asdict(s2) == asdict(S2(**asdict(s2)))
    assert bytes(s2) == b"\x01\x00\x00\x00\x02\x00\x00\x00\x05\x00Hello\x64\x00\x00\x00"
    s2.a = S1(3, 4, "Hi")
    assert s2.a.z == "Hi"
    assert bytes(s2) == b"\x03\x00\x00\x00\x04\x00\x00\x00\x02\x00Hi\x64\x00\x00\x00"
    s2.a.z = "Bye"
    assert bytes(s2) == b"\x03\x00\x00\x00\x04\x00\x00\x00\x03\x00Bye\x64\x00\x00\x00"


class S1(StructType):
    x: DINT
    y: STRING


def test_struct_array_member():
    class S1(StructType):
        x: DINT
        y: STRING

    class S2(StructType):
        a: UINT[USINT]
        b: Annotated[ArrayType[S1, int], 3]
        c: Annotated[SINT[3], "not used"]

    s2 = S2([1, 2, 3], [S1(10, "a"), S1(20, "b"), S1(30, "c")], [1, 2, 3])

    assert s2.a[0] == 1
    assert bytes(s2) == (
        b"\x03\x01\x00\x02\x00\x03\x00"
        b"\x0a\x00\x00\x00\x01\x00a\x14\x00\x00\x00\x01\x00b\x1e\x00\x00\x00\x01\x00c\x01\x02\x03"
    )

    s2.a = [4, 5, 6]
    assert bytes(s2) == (
        b"\x03\x04\x00\x05\x00\x06\x00"
        b"\x0a\x00\x00\x00\x01\x00a\x14\x00\x00\x00\x01\x00b\x1e\x00\x00\x00\x01\x00c\x01\x02\x03"
    )

    # retest with better type hinting
    class S3(StructType):
        a: UINT | int
        b: Array[UINT, USINT] | Sequence[UINT | int]
        c: Annotated[ArrayType[UINT, int], 3] | Sequence[UINT | int]

    s3 = S3(1, [2, 2, 2], [4, 4, 4])
    assert s3.a == 1
    assert type(s3.a) is UINT
    assert bytes(s3) == b"\x01\x00\x03\x02\x00\x02\x00\x02\x00\x04\x00\x04\x00\x04\x00"
    s3.b = [1, 2]
    assert bytes(s3) == b"\x01\x00\x02\x01\x00\x02\x00\x04\x00\x04\x00\x04\x00"
    _s3 = S3.decode(b"\x01\x00\x02\x01\x00\x02\x00\x04\x00\x04\x00\x04\x00")
    assert _s3 == s3


def test_struct_missing_args():
    class S1(StructType):
        x: DINT
        y: STRING[4]
        z: SINT

    with pytest.raises(TypeError):
        S1(4, ["a", "b", "c", "d"])

    with pytest.raises(DataError):
        S1(2, ["a", "b", "c"], 0)

    class S2(StructType):
        a: S1
        b: DINT

    with pytest.raises(TypeError):
        S2({"x": 6, "y": "abcd", "z": 9})

    with pytest.raises(DataError):
        S2(S1(x=6, y="000", z=6), 6)


def test_struct_reserved_field():
    class S1(StructType):
        x: DINT
        _: UINT = attr(reserved=True, default=2)
        y: DINT

    assert S1._members == {"x": DINT, "_": UINT, "y": DINT}
    assert S1._attributes == {"x": DINT, "y": DINT}
    assert bytes(S1(1, 3)) == b"\x01\x00\x00\x00\x02\x00\x03\x00\x00\x00"


def test_struct_array_len_ref():
    class S1(StructType):
        x: USINT
        count: UINT = attr(init=False)
        items: USINT[...] = attr(len_ref="count")
        z: UDINT = 3

    s = S1(1, [])
    assert s.count == 0
    assert asdict(s) == {"x": USINT(1), "count": UINT(0), "items": USINT[...]([]), "z": UDINT(3)}
    assert bytes(s) == b"\x01\x00\x00\x03\x00\x00\x00"

    s.items = [1, 2, 3]
    assert s.count == 3
    assert bytes(s) == b"\x01\x03\x00\x01\x02\x03\x03\x00\x00\x00"

    class S2(StructType):
        x: USINT
        count: UINT = attr(init=False)
        items: USINT[...] = attr(len_ref=("count", lambda x: x * 2, lambda x: x // 2))
        z: UDINT = 3

    s2 = S2(1, [])
    assert s2.count == 0
    assert asdict(s2) == {"x": USINT(1), "count": UINT(0), "items": USINT[...]([]), "z": UDINT(3)}
    assert bytes(s2) == b"\x01\x00\x00\x03\x00\x00\x00"

    s2.items = [1, 2, 3, 4]
    assert s2.count == 2
    assert bytes(s2) == b"\x01\x02\x00\x01\x02\x03\x04\x03\x00\x00\x00"
    assert S2.decode(b"\x01\x02\x00\x01\x02\x03\x04\x03\x00\x00\x00") == s2


def test_struct_size_ref():
    class S1(StructType):
        x: USINT | int
        z: Array[USINT, UINT] | Sequence[int]

    class S2(StructType):
        a: DINT | int
        struct_size: UINT = attr(size_ref=True)
        b: SHORT_STRING | str
        s: S1

    s1 = S1(1, [1, 1])
    s2 = S2(0, "", s1)
    assert s2.struct_size == 6
    assert bytes(s2) == b"\x00\x00\x00\x00\x06\x00\x00\x01\x02\x00\x01\x01"
    s2.b = "hello there!"
    assert s2.struct_size == 18
    s2.s.z = [1, 2, 3]
    assert s2.struct_size == 19
    assert bytes(s2) == b"\x00\x00\x00\x00\x13\x00\x0chello there!\x01\x03\x00\x01\x02\x03"
    assert S2.decode(b"\x00\x00\x00\x00\x13\x00\x0chello there!\x01\x03\x00\x01\x02\x03") == S2(
        0, "hello there!", S1(1, [1, 2, 3])
    )

    # TODO: test callable size ref
