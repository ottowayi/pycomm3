from ._core_types import IntDataType, FloatDataType

# fmt: off
__all__ = (
    "SINT", "INT", "DINT", "LINT", "USINT", "UINT", "UDINT", "ULINT",
    "SINT_BE", "INT_BE", "DINT_BE", "LINT_BE", "USINT_BE", "UINT_BE", "UDINT_BE", "ULINT_BE",
    "REAL","LREAL"
)
# fmt: on


class SINT(IntDataType):
    """
    Signed 8-bit integer
    """

    code = 0xC2  #: 0xC2
    _format = "<b"


class INT(IntDataType):
    """
    Signed 16-bit integer
    """

    code = 0xC3  #: 0xC3
    _format = "<h"


class DINT(IntDataType):
    """
    Signed 32-bit integer
    """

    code = 0xC4  #: 0xC4
    _format = "<i"


class LINT(IntDataType):
    """
    Signed 64-bit integer
    """

    code = 0xC5  #: 0xC5
    _format = "<q"


class USINT(IntDataType):
    """
    Unsigned 8-bit integer
    """

    code = 0xC6  #: 0xC6
    _format = "<B"


class UINT(IntDataType):
    """
    Unsigned 16-bit integer
    """

    code = 0xC7  #: 0xC7
    _format = "<H"


class UDINT(IntDataType):
    """
    Unsigned 32-bit integer
    """

    code = 0xC8  #: 0xC8
    _format = "<I"


class ULINT(IntDataType):
    """
    Unsigned 64-bit integer
    """

    code = 0xC9  #: 0xC9
    _format = "<Q"


class REAL(FloatDataType):
    """
    32-bit floating point
    """

    code = 0xCA  #: 0xCA
    _format = "<f"


class LREAL(FloatDataType):
    """
    64-bit floating point
    """

    code = 0xCB  #: 0xCB
    _format = "<d"


#
# Big-Endian Integer Variations
#


class SINT_BE(IntDataType):
    """
    Signed 8-bit integer, big-endian
    """

    _format = ">b"


class INT_BE(IntDataType):
    """
    Signed 16-bit integer, big-endian
    """

    _format = ">h"


class DINT_BE(IntDataType):
    """
    Signed 32-bit integer, big-endian
    """

    _format = ">i"


class LINT_BE(IntDataType):
    """
    Signed 64-bit integer, big-endian
    """

    _format = ">q"


class USINT_BE(IntDataType):
    """
    Unsigned 8-bit integer, big-endian
    """

    _format = ">B"


class UINT_BE(IntDataType):
    """
    Unsigned 16-bit integer, big-endian
    """

    _format = ">H"


class UDINT_BE(IntDataType):
    """
    Unsigned 32-bit integer, big-endian
    """

    _format = ">I"


class ULINT_BE(IntDataType):
    """
    Unsigned 64-bit integer, big-endian
    """

    _format = ">Q"
