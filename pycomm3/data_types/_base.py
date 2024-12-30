from __future__ import annotations

import builtins
import dataclasses
from collections.abc import MutableMapping, Mapping
from dataclasses import Field, astuple, dataclass, field, fields, make_dataclass
from inspect import isclass
from io import BytesIO
from struct import calcsize, pack, unpack
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Literal,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    overload,
    TYPE_CHECKING,
    Optional,
    get_origin,
    get_type_hints,
)

from typing_extensions import dataclass_transform, TypeAlias, Annotated

from pycomm3.exceptions import BufferEmptyError, DataError
from pycomm3.util import DataclassMeta

if TYPE_CHECKING:
    from types import EllipsisType
else:
    EllipsisType = type(...)

BufferT: TypeAlias = Union[BytesIO, bytes]
ArrayLenT: TypeAlias = Optional[
    Union[
        Type["ElementaryDataType[int]"],
        int,
        EllipsisType,
    ]
]


def buff_repr(buffer: BufferT) -> str:
    if isinstance(buffer, BytesIO):
        return repr(buffer.getvalue())
    else:
        return repr(buffer)


def get_bytes(buffer: BufferT, length: int) -> bytes:
    if isinstance(buffer, bytes):
        return buffer[:length]

    return buffer.read(length)


def as_stream(buffer: BufferT) -> BytesIO:
    if isinstance(buffer, bytes):
        return BytesIO(buffer)
    return buffer


# if TYPE_CHECKING:
#     MT = TypeVar('MT', bound='_DataTypeMeta')
#     DT = TypeVar('DT', bound='DataType')
#     LT = TypeVar('LT', bound=ArrayLenT)
#
#     class _DataTypeMeta(type, Generic[LT]):
#         def __new__(mcs: type[MT], *args, **kwargs) -> type[DT]: ...
#         def __getitem__(cls: MT, item: LT) -> ArrayType[DT, LT]:
#
#
#
# else:
class _DataTypeMeta(type):
    def __repr__(cls):
        return cls.__name__


class _ArrayMetaMixin(type):
    def __getitem__(cls, item):
        return array(cls, item)


DT = TypeVar("DT", bound="DataType")


class DataType(metaclass=_DataTypeMeta):
    """
    Base class to represent a CIP data type.
    Instances of a type are only used when defining the
    members of a structure.

    Each type class provides ``encode`` / ``decode`` class methods.
    If overriding them, they must catch any unhandled exception
    and raise a :class:`DataError` from it. For ``decode``, ``BufferEmptyError``
    should be reraised immediately without modification.
    The buffer empty error is needed for decoding arrays of
    unknown length.  Typically, for custom types, overriding the
    private ``_encode``/``_decode`` methods are sufficient. The private
    methods do not need to do any exception handling if using the
    base public methods.  For ``_decode`` use the private ``_stream_read``
    method instead of ``stream.read``, so that ``BufferEmptyError`` exceptions are
    raised appropriately.
    """

    __encoded_value__: bytes = b""
    size: int = 0

    # def __new__(cls, *args, **kwargs):
    #     return super().__new__(cls, *args, **kwargs)

    def __bytes__(self) -> bytes:
        return self.__class__.encode(self)

    @classmethod
    def encode(cls: type[DT], value: DT, *args, **kwargs) -> bytes:
        """
        Serializes a Python object ``value`` to ``bytes``.

        .. note::
            Any subclass overriding this method must catch any exception and re-raise a :class:`DataError`
        """
        try:
            return cls._encode(value, *args, **kwargs)
        except Exception as err:
            raise DataError(f"Error packing {value!r} as {cls.__name__}") from err

    @classmethod
    def _encode(cls: type[DT], value: DT, *args, **kwargs) -> bytes: ...

    @classmethod
    def decode(cls: type[DT], buffer: BufferT) -> DT:
        """
        Deserializes a Python object from the ``buffer`` of ``bytes``

        .. note::
            Any subclass overriding this method must catch any exception and re-raise as a :class:`DataError`.
            Except ``BufferEmptyErrors`` they must be re-raised as such, array decoding relies on this.
        """
        try:
            stream = as_stream(buffer)
            return cls._decode(stream)
        except BufferEmptyError:
            raise
        except Exception as err:
            raise DataError(f"Error unpacking {buff_repr(buffer)} as {cls.__name__}") from err

    @classmethod
    def _decode(cls: type[DT], stream: BytesIO) -> DT: ...

    @classmethod
    def _stream_read(cls, stream: BytesIO, size: int) -> bytes:
        """
        Reads `size` bytes from `stream`.
        Raises `BufferEmptyError` if stream returns no data.
        """
        if not (data := stream.read(size)):
            raise BufferEmptyError()
        return data


def is_datatype(obj: Any, typ=DataType) -> bool:
    """
    Returns True if ``obj`` is an instance or subclass of ``typ``, False otherwise
    """
    if isclass(obj):
        return issubclass(obj, typ)
    else:
        return isinstance(obj, typ)


ElementaryPyType: TypeAlias = Union[int, float, bool, str, bytes]

EDT = TypeVar("EDT", bound="ElementaryDataType")
ET = TypeVar("ET", int, float, bool, str, bytes)
EVT: TypeAlias = Union[EDT, ET]


class _ElementaryDataTypeMeta(_DataTypeMeta):
    def __new__(mcs, name, bases, classdict):
        klass = super().__new__(mcs, name, bases, classdict)

        if cls_args := get_args(klass.__orig_bases__[0]):
            klass._base_type = cls_args[0]
        if not klass.size and klass._format:
            klass.size = calcsize(klass._format)

        if klass.code:
            klass._codes[klass.code] = klass

        return klass


class ElementaryDataType(DataType, Generic[ET], metaclass=_ElementaryDataTypeMeta):
    """
    Type that represents a single primitive value in CIP.
    """

    code: int = 0x00  #: CIP data type identifier
    size: int = 0  #: size of type in bytes
    _format: str = ""
    _base_type: type[ET]

    # keeps track of all subclasses using the cip type code
    _codes: dict[int, type[ET]] = {}

    def __new__(cls: type[EDT], value: EVT, *args, **kwargs) -> EDT:
        try:
            obj = super().__new__(cls, value, *args, **kwargs)
        except Exception as err:
            raise DataError(f"invalid value for {cls}: {value!r}") from err

        # encode at the same time we create the object, removes the need for validation
        # since if it can be encoded, it's valid.
        obj.__encoded_value__ = cls.encode(value, *args, **kwargs)
        return obj

    def __bytes__(self) -> bytes:
        return self.__encoded_value__

    @classmethod
    def encode(cls: type[EDT], value: EVT, *args, **kwargs) -> bytes:
        return super().encode(value, *args)

    @classmethod
    def _encode(cls, value: EVT, *args, **kwargs) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls: type[EDT], stream: BytesIO) -> EDT:
        data = cls._stream_read(stream, cls.size)
        return cls(unpack(cls._format, data)[0])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._base_type.__repr__(self)})"  # noqa


def struct_attr(*, reserved: bool = False, **kwargs) -> Field:
    return field(
        metadata={
            **kwargs,
            "reserved": reserved,
        }
    )


SDT = TypeVar("SDT", bound="StructType")


class _StructFieldMarker:
    """
    base class for any special markers that can be added to annotated fields in a struct type
    """


RESERVED = _StructFieldMarker()


def _process_fields(cls: "type[_StructMeta]") -> ...:
    _fields = fields(cls)  # noqa
    _type_hints = get_type_hints(cls, include_extras=True)
    cls._struct_fields = {}
    cls._members = {}
    cls._attributes = {}

    for _field in _fields:
        typ = _type_hints.get(_field.name)
        is_reserved = False
        field_type = None
        if isclass(typ) and issubclass(typ, DataType):
            field_type = typ
        elif (origin := get_origin(typ)) is not None:
            if origin is Annotated:
                _type, *extra = get_args(typ)
                _type_origin = get_origin(_type)
                if isclass(_type_origin) and issubclass(_type_origin, ArrayType):
                    element_type, ary_len = get_args(_type)
                    if not isclass(element_type) or not issubclass(element_type, DataType):
                        raise DataError("Annotated array types must have a type[DataType] for the element type (1st) arg")  # fmt: skip
                    if ary_len is int:
                        _ary_len = next(iter(extra), None)
                        if not isinstance(_ary_len, int):
                            raise DataError("Annotated arrays using ArrayType[*, int] must provide an int for the next annotated arg")  # fmt: skip
                        ary_len = _ary_len
                    field_type = array(element_type, ary_len)
                else:
                    if not isclass(_type) or not issubclass(_type, DataType):
                        raise DataError(f"Annotated types must provide a DataType for the first arg: {_field.name}")
                    field_type = _type
                # handle extras
                if RESERVED in extra:
                    is_reserved = True

            elif isclass(origin) and issubclass(origin, ArrayType):
                # handles 'x: ArrayType[y, z]' case
                field_type = array(*get_args(typ))
        else:
            raise DataError(f"Unsupported annotation for struct field: {_field.name}")

        if field_type is None:
            raise DataError(f"Failed to determine type (unsupported annotation) for field: {_field.name}")
        cls._members[_field.name] = field_type
        if not is_reserved:
            cls._attributes[_field.name] = field_type


@dataclass_transform(field_specifiers=(Field, field, struct_attr))
class _StructMeta(DataclassMeta, _ArrayMetaMixin, _DataTypeMeta):
    _members: dict[str, type[DataType]]
    _attributes: dict[str, type[DataType]]

    def __new__(mcs: type[_StructMeta], name: str, bases: tuple, clsdict: dict) -> type[SDT]:
        cls: type[SDT] = super().__new__(mcs, name, bases, clsdict)
        # _fields = fields(cls)
        # _type_hints = get_type_hints(cls, include_extras=True)
        # cls._members = {_field.name: _field_type(_type_hints.get(_field.name)) for _field in _fields}
        # cls._attributes = {_field.name: _field.type for _field in _fields if not _field.metadata.get("reserved", False)}
        _process_fields(cls)
        return cls

    @property
    def size(cls: _StructMeta) -> int:
        return sum(typ.size for typ in cls._members.values())


StructValuesType = Union[Dict[str, DataType], Sequence[DataType]]
StructCreateMembersType = Sequence[
    Union[
        Tuple[str, Type[DataType]],
        Tuple[str, Type[DataType], Field],
    ]
]


@dataclass_transform(field_specifiers=(Field, field, struct_attr))
class StructType(DataType, metaclass=_StructMeta):
    """
    Base type for a structure
    """

    #: map of all members inside the struct and their types
    _members: ClassVar[dict[str, type[DataType]]] = {}
    #: mapping of _user_ members of the struct to their type,
    #: excluding reserved or private members not meant for users to interact with
    _attributes: ClassVar[dict[str, type[DataType]]] = {}

    attr = struct_attr

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __setattr__(self: SDT, key: str, value: Any) -> None:
        if key not in self.__class__._members:  # noqa
            raise AttributeError(f"{key!r} is not an attribute of struct {self.__class__.__name__}")
        if not isinstance(value, typ := self.__class__._members[key]):
            try:
                if issubclass(typ, StructType):
                    value = typ(**cast(Mapping[str, Any], value))
                else:
                    value = typ(value)
            except Exception as err:
                raise DataError(f"Type conversion error for attribute {key!r}") from err

        super().__setattr__(key, value)

    def __iter__(self):
        yield from ((m, self[m]) for m in self._members)

    def __getitem__(self, item: str) -> SDT:
        if item not in self.__class__._members:
            raise DataError(f"Invalid member name: {item}")

        return getattr(self, item)

    def __setitem__(self, item: str, value: Any) -> None:
        if item not in self.__class__._members:
            raise DataError(f"Invalid member name: {item}")

        setattr(self, item, value)

    def keys(self):
        return self.__class__._members.keys()

    def __bytes__(self: SDT) -> bytes:
        return self.__class__.encode(self)

    @classmethod
    def _encode(cls: type[SDT], value: SDT, *args, **kwargs) -> bytes:
        return b"".join(bytes(getattr(value, attr_name)) for attr_name in cls._members)

    @classmethod
    def _decode(cls: type[SDT], stream: BytesIO) -> SDT:
        values = {name: typ.decode(stream) for name, typ in cls._members.items()}
        return cls(**values)

    @staticmethod
    def create(name: str, members: StructCreateMembersType) -> type[SDT]:
        _fields = []
        member: tuple[str, type[DataType]] | tuple[str, type[DataType], Field]
        for i, member in enumerate(members):
            if len(member) == 2:
                _name, typ = cast(Tuple[str, Type[DataType]], member)
                _field = None
            else:
                _name, typ, _field = cast(Tuple[str, Type[DataType], Field], member)

            if not _name:
                _name = f"_reserved_attr{i}"
                if _field is None:
                    _field = StructType.attr(reserved=True)

            _fields.append((_name, typ, _field))

        struct_class: type[SDT] = make_dataclass(
            cls_name=name,
            fields=_fields,
            bases=(StructType,),
        )

        return struct_class


ArrayElementType = TypeVar("ArrayElementType", bound=DataType)
ArrayLengthType = TypeVar("ArrayLengthType", bound=ArrayLenT)


_ArrayType = TypeVar("_ArrayType", bound="ArrayType")


class _ArrayMeta(_DataTypeMeta):
    element_type: type[DataType]
    length: ArrayLenT

    def __repr__(cls: _ArrayType) -> str:  # type: ignore
        if cls is ArrayType:
            return ArrayType.__name__
        if cls.length in (Ellipsis, None):
            return f"{cls.element_type}[...]"

        return f"{cls.element_type}[{cls.length!r}]"

    def __hash__(cls):
        return hash(type(cls))

    @property
    def size(cls) -> int:
        if (
            cls.length in {None, Ellipsis}  # fmt: skip
            or (isclass(cls.length) and issubclass(cls.length, DataType))
        ):
            raise DataError("cannot determine dynamic array sizes before instantiation")
        else:
            return cast(int, cls.length) * cls.element_type.size

    def __eq__(self: type[_ArrayType], other) -> bool:  # type: ignore
        try:
            return self.element_type == other.element_type and self.length == other.length
        except Exception:
            return False


_ET = TypeVar("_ET", bound=DataType)
_LT = TypeVar("_LT", bound=ArrayLenT)


def array(element_type: type[_ET], length: _LT) -> type[ArrayType[_ET, _LT]]:
    _type, _len = element_type, length
    if _len is None:
        _len = ...

    class Array(ArrayType[_ET, _LT]):
        element_type = _type
        length = _len

    return Array


class ArrayType(DataType, Generic[ArrayElementType, ArrayLengthType], metaclass=_ArrayMeta):
    """
    Base type for an array
    """

    element_type: type[ArrayElementType]
    length: ArrayLengthType

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self: _ArrayType, value: Sequence) -> None:
        if isinstance(self.length, int):
            try:
                val_len = len(value)
            except Exception as err:
                raise DataError("invalid value for array, must support len()") from err
            else:
                if val_len != self.length:
                    raise DataError(f"Array length error: expected {self.length} items, received {len(value)}")

        self._array: list[ArrayElementType] = [self._convert_element(v) for v in value]

    @property
    def size(self) -> int:  # type: ignore
        if isclass(self.length) and issubclass(self.length, DataType):
            return self.length.size + len(self._array) * self.element_type.size  # type: ignore
        else:
            return len(self._array) * self.element_type.size

    def _convert_element(self, value) -> ArrayElementType:
        if not isinstance(value, self.element_type):  # noqa - PyCharm Issue: PY-32860
            try:
                val = self.element_type(value)
            except Exception as err:
                raise DataError(f"Error converting element:") from err
        else:
            val = value
        return val

    def __hash__(self):
        return hash((self.length, self.element_type, self._array))

    def __len__(self: _ArrayType) -> int:
        return len(self._array)

    @overload
    def __getitem__(self: _ArrayType, item: int) -> ArrayElementType: ...

    @overload
    def __getitem__(self: _ArrayType, item: slice) -> list[ArrayElementType]: ...

    def __getitem__(self: _ArrayType, item: int | slice) -> ArrayElementType | list[ArrayElementType]:
        if isinstance(item, slice):
            items = self._array[item]
            return self.element_type[len(items)](items)

        return self._array[item]

    def __setitem__(self: _ArrayType, item: int | slice, value) -> None:
        try:
            if isinstance(item, slice):
                self._array[item] = (self._convert_element(v) for v in value)
            else:
                self._array[item] = self._convert_element(value)
        except Exception as err:
            raise DataError(f"Failed to set item") from err

    def __bytes__(self: _ArrayType) -> bytes:
        return self.__class__.encode(self)

    def __eq__(self, other):
        try:
            return self._array == other._array  # noqa
        except Exception:  # noqa
            return False

    @classmethod
    def _encode(cls: type[_ArrayType], value: _ArrayType, *args, **kwargs) -> bytes:
        encoded_elements = b"".join(bytes(x) for x in value._array)
        if isclass(value.length) and issubclass(value.length, DataType):
            return bytes(value.length(len(value))) + encoded_elements

        return encoded_elements

    @classmethod
    def _decode_all(cls: type[_ArrayType], stream: BytesIO) -> list[ArrayElementType]:
        _array = []
        while True:
            try:
                _array.append(cls.element_type.decode(stream))
            except BufferEmptyError:
                break
        return _array

    @classmethod
    def decode(cls: type[_ArrayType], buffer: BufferT) -> _ArrayType:
        try:
            stream = as_stream(buffer)
            if cls.length in {None, Ellipsis}:
                return cls(cls._decode_all(stream))

            if isclass(cls.length) and issubclass(cls.length, ElementaryDataType):
                _len = cast(int, cls.length.decode(stream))
            else:
                _len = cls.length

            _val = [cls.element_type.decode(stream) for _ in range(_len)]

            return cls(_val)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(
                    f"Error unpacking into {cls.element_type}[{cls.length}] from {buff_repr(buffer)}"
                ) from err

    def __repr__(self):
        return f"{self.__class__!r}({self._array!r})"
