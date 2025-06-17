from re import I
from typing import ClassVar
from pycomm3.data_types import USINT, STRING, UINT, UDINT, BOOL
from pycomm3.protocols.cip import CIPObject, CIPAttribute, service
from pycomm3.util import IntEnumX


class SymbolType(IntEnumX):
    """
    +---------+------------+----------+-------------+
    | Struct  | Array Dims | Reserved |  Type Info. |
    +=========+=====+======+==========+=============+
    |   15    |  14 |  13  |    12    |  11 - 0     |
    +---------+-----+------+----------+-------------+
    """

    mask_struct_bit = 0b1000_0000_0000_0000
    atomic = 0
    struct = mask_struct_bit
    mask_array_bits = 0b0110_0000_0000_0000
    array_dim0 = 0
    array_dim1 = 0b0010_0000_0000_0000
    array_dim2 = 0b0100_0000_0000_0000
    array_dim3 = 0b0110_0000_0000_0000


class Symbol(CIPObject):
    class_code = 0x6B

    uid = CIPAttribute(id=8, data_type=UDINT, class_attr=True)

    name = CIPAttribute(id=1, data_type=STRING)
    data_type = CIPAttribute(id=2, data_type=UINT)
    address = CIPAttribute(id=3, data_type=UDINT)
    object_address = CIPAttribute(id=5, data_type=UDINT)
    software_control = CIPAttribute(id=6, data_type=UDINT)
    element_size = CIPAttribute(id=7, data_type=UINT)
    array_dimensions = CIPAttribute(id=8, data_type=UDINT[3])
    safety_flag = CIPAttribute(id=9, data_type=BOOL)
    ppd_control = CIPAttribute(id=10, data_type=USINT)
    constant_indicator = CIPAttribute(id=11, data_type=USINT)

    @service(id=USINT(0x4C))
    @classmethod
    def read_tag(cls): ...

    @service(id=USINT(0x52))
    @classmethod
    def read_tag_fragmented(cls): ...

    @service(id=USINT(0x4D))
    @classmethod
    def write_tag(cls): ...

    @service(id=USINT(0x53))
    @classmethod
    def write_tag_fragmented(cls): ...
