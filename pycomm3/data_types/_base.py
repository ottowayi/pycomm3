import types
from collections.abc import MutableMapping, Mapping
from dataclasses import Field, astuple, dataclass, field, fields, make_dataclass
from inspect import isclass
from io import BytesIO
from struct import calcsize, pack, unpack
from typing import (
    Any,
    ClassVar,
    Generic,
    Type,
    TypeVar,
    cast,
    get_args,
    overload,
    Optional,
    get_origin,
    get_type_hints,
    Sequence,
    TypeAlias,
    dataclass_transform,
    Annotated,
    Self,
    Callable,
    TYPE_CHECKING,
)

from pycomm3.exceptions import BufferEmptyError, DataError
from pycomm3.util import DataclassMeta
from types import EllipsisType


BufferT: TypeAlias = BytesIO | bytes
ArrayLenT: TypeAlias = None | Type["ElementaryDataType[int]"] | int | EllipsisType


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


class _DataTypeMeta(type):
    def __repr__(cls):
        return cls.__name__


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

    @classmethod
    def _stream_peek(cls, stream: BytesIO, size: int) -> bytes:
        return stream.getvalue()[stream.tell() : stream.tell() + size]


def is_datatype(obj: Any, typ=DataType) -> bool:
    """
    Returns True if ``obj`` is an instance or subclass of ``typ``, False otherwise
    """
    if isclass(obj):
        return issubclass(obj, typ)
    else:
        return isinstance(obj, typ)


ElementaryPyType: TypeAlias = int | float | bool | str | bytes

EDT = TypeVar("EDT", bound="ElementaryDataType")
ET = TypeVar("ET", int, float, bool, str, bytes)
EVT: TypeAlias = EDT | ET


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


class _ArrayMetaMixin[T: type[DataType], LT: ArrayLenT](type):
    def __getitem__(cls: T, item: LT) -> "ArrayType[T, LT]":
        return array(cls, item)


def _process_fields(cls: "type[StructType]") -> ...:
    _fields = fields(cls)  # noqa
    _type_hints = get_type_hints(cls, include_extras=True)
    cls._dataclass_fields = {}
    cls._members = {}
    cls._attributes = {}
    cls._array_length_attributes = {}

    for _field in _fields:
        cls._dataclass_fields[_field.name] = _field
        typ = _type_hints.get(_field.name)
        metadata = _field.metadata or {}
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

            elif isclass(origin) and issubclass(origin, ArrayType):
                # handles 'x: ArrayType[y, z]' case
                field_type = array(*get_args(typ))
        else:
            raise DataError(f"Unsupported annotation for struct field: {_field.name}")

        if field_type is None:
            raise DataError(f"Failed to determine type (unsupported annotation) for field: {_field.name}")
        cls._members[_field.name] = field_type
        if not metadata.get("reserved"):
            cls._attributes[_field.name] = field_type
        if len_ref := metadata.get("len_ref"):
            cls._array_length_attributes[_field.name] = len_ref


def _default_len_ref_callable(value: DataType) -> int:
    return value  # type: ignore


def attr(
    default: DataType | None = None,
    init: bool = True,
    reserved: bool = False,
    len_ref: str | tuple[str, Callable[[DataType], int]] | None = None,
):
    """
    Customize behavior of struct attributes (and their underlying dataclass fields)

    default: Default value for the attribute when creating the object, will be overwritten with decoded value when
             instance created using decode(). `None` is not a valid default value for fields, unlike in regular dataclasses.
             `None` means the attribute must be provided when creating the object.

    init: Whether the attribute can be provided when creating the struct. If False, then the attribute
          will not be set on the instance automatically and must be done manually in __post_init__.
          Value will be overwritten with decoded value after instance is created using decode()
    reserved: Whether the attribute is reserved. If True, the attribute will not be _user facing_ and implies `init=True`.
    len_ref: Used for ArrayType attributes whose length is determined by another attribute and used when decoding the
             struct whole. The attribute should be type hinted as `Array[...]` as well. This parameter must be
             the name of the length attribute or a tuple of the name and a 1-arg callable that accepts the value of the
             length attribute and returns an int.  The length attribute must be defined before the array as well, since
             it needs to be decoded before the array can be.
    """
    field_kwargs = dict(init=True if reserved else init, metadata={"reserved": reserved})
    if default is not None:
        field_kwargs["default"] = default
    if len_ref is not None and isinstance(len_ref, str):
        len_ref = len_ref, _default_len_ref_callable
    field_kwargs["metadata"]["len_ref"] = len_ref

    return field(**field_kwargs)


@dataclass_transform(field_specifiers=(Field, field, attr))
class _StructMeta(DataclassMeta, _ArrayMetaMixin, _DataTypeMeta):
    def __new__(mcs: Self, name: str, bases: tuple, cls_dict: dict) -> type[Self]:
        cls: type[Self] = super().__new__(mcs, name, bases, cls_dict)
        _process_fields(cls)
        return cls

    @property
    def size(cls: Self) -> int:
        return sum(sz for typ in cls._members.values() if (sz := typ.size) != -1)


type StructValuesType = dict[str, DataType] | Sequence[DataType]
type StructCreateMembersType = Sequence[tuple[str, type[DataType]] | tuple[str, type[DataType], Field]]


@dataclass_transform(field_specifiers=(Field, field, attr))
class StructType(DataType, metaclass=_StructMeta):
    """
    Base type for a structure
    """

    #: map of all members inside the struct and their types
    _members: ClassVar[dict[str, type[DataType]]] = {}
    #: mapping of _user_ members of the struct to their type,
    #: excluding reserved or private members not meant for users to interact with
    _attributes: ClassVar[dict[str, type[DataType]]] = {}
    #: map of field names to dataclass Field objects, to avoid having to call fields() all the time
    _dataclass_fields: ClassVar[dict[str, Field]] = {}
    #: map of array field names to the field name that is the source of the length of the array
    _array_length_attributes: ClassVar[dict[str, tuple[str, Callable[[DataType], int]]]] = {}

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __setattr__(self: Self, key: str, value: Any) -> None:
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
        try:
            if len_ref := self._array_length_attributes.get(key):
                setattr(self, len_ref[0], len(value))
        except Exception as err:
            raise DataError(f"Error updating length attribute for array attribute {key!r}") from err
        super().__setattr__(key, value)

    def __iter__(self):
        yield from ((m, self[m]) for m in self._members)

    def __getitem__(self, item: str) -> Self:
        if item not in self.__class__._members:
            raise DataError(f"Invalid member name: {item}")

        return getattr(self, item)

    def __setitem__(self, item: str, value: Any) -> None:
        if item not in self.__class__._members:
            raise DataError(f"Invalid member name: {item}")

        setattr(self, item, value)

    def keys(self):
        return self.__class__._members.keys()

    def __bytes__(self: Self) -> bytes:
        return self.__class__.encode(self)

    @classmethod
    def _encode(cls: type[Self], value: Self, *args, **kwargs) -> bytes:
        return b"".join(bytes(getattr(value, attr_name)) for attr_name in cls._members)

    @classmethod
    def _decode(cls: type[Self], stream: BytesIO) -> Self:
        values: dict[str, DataType] = {}
        for name, typ in cls._members.items():
            if len_ref := cls._array_length_attributes.get(name):
                typ: ArrayType
                _ref, _func = len_ref
                _array = array(typ.element_type, _func(values[_ref]))
                value = _array.decode(stream)
            else:
                value = typ.decode(stream)
            values[name] = value

        post_init_vars = {name: val for name, val in values.items() if not cls._dataclass_fields[name].init}
        instance = cls(**{k: v for k, v in values if k not in post_init_vars})
        for name, val in post_init_vars.items():
            setattr(instance, name, val)
        return instance

    @staticmethod
    def create[T: type[StructType]](name: str, members: StructCreateMembersType) -> T:
        _fields = []
        member: tuple[str, type[DataType]] | tuple[str, type[DataType], Field]
        for i, member in enumerate(members):
            if len(member) == 2:
                _name, typ = cast(tuple[str, type[DataType]], member)
                _field = None
            else:
                _name, typ, _field = cast(tuple[str, type[DataType], Field], member)

            if not _name:
                _name = f"_reserved_attr{i}_"
                if _field is None:
                    _field = attr(reserved=True)
                else:
                    _field.metadata = types.MappingProxyType({**(_field.metadata or {}), "reserved": True})

            _fields.append((_name, typ, _field))

        struct_class: type[T] = cast(type[T], make_dataclass(cls_name=name, fields=_fields, bases=(StructType,)))

        return struct_class


class _ArrayMeta(_DataTypeMeta):
    element_type: type[DataType]
    length: ArrayLenT

    def __repr__(cls: Self) -> str:
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

    def __eq__(self: Self, other) -> bool:
        try:
            return self.element_type == other.element_type and self.length == other.length
        except Exception:
            return False


def array[ET: type[DataType], LT: ArrayLenT](element_type: type[ET], length: LT) -> type["ArrayType[ET, LT]"]:
    _type, _len = element_type, length
    if _len is None:
        _len = ...

    class Array(ArrayType[ET, LT]):
        element_type = _type
        length = _len

    return Array


class ArrayType[ElementT: DataType, LenT: ArrayLenT](DataType, metaclass=_ArrayMeta):
    """
    Base type for an array
    """

    element_type: type[ElementT]
    length: LenT

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self: Self, value: Sequence) -> None:
        if isinstance(self.length, int):
            try:
                val_len = len(value)
            except Exception as err:
                raise DataError("invalid value for array, must support len()") from err
            else:
                if val_len != self.length:
                    raise DataError(f"Array length error: expected {self.length} items, received {len(value)}")

        self._array: list[ElementT] = [self._convert_element(v) for v in value]

    @property
    def size(self) -> int:
        if isclass(self.length) and issubclass(self.length, DataType):
            return self.length.size + len(self._array) * self.element_type.size
        else:
            return len(self._array) * self.element_type.size

    def _convert_element(self, value) -> ElementT:
        if not isinstance(value, self.element_type):
            try:
                val = self.element_type(value)
            except Exception as err:
                raise DataError(f"Error converting element:") from err
        else:
            val = value
        return val

    def __hash__(self):
        return hash((self.length, self.element_type, self._array))

    def __len__(self) -> int:
        return len(self._array)

    @overload
    def __getitem__(self, item: int) -> ElementT: ...

    @overload
    def __getitem__(self, item: slice) -> list[ElementT]: ...

    def __getitem__(self, item: int | slice) -> ElementT | list[ElementT]:
        if isinstance(item, slice):
            items = self._array[item]
            return self.element_type[len(items)](items)

        return self._array[item]

    def __setitem__(self, item: int | slice, value) -> None:
        try:
            if isinstance(item, slice):
                self._array[item] = (self._convert_element(v) for v in value)
            else:
                self._array[item] = self._convert_element(value)
        except Exception as err:
            raise DataError("Failed to set item") from err

    def __bytes__(self) -> bytes:
        return self.__class__.encode(self)

    def __eq__(self, other):
        try:
            return self._array == other._array  # noqa
        except Exception:  # noqa
            return False

    @classmethod
    def _encode(cls, value: Self, *args, **kwargs) -> bytes:
        encoded_elements = b"".join(bytes(x) for x in value._array)
        if isclass(value.length) and issubclass(value.length, DataType):
            return bytes(value.length(len(value))) + encoded_elements

        return encoded_elements

    @classmethod
    def _decode_all(cls, stream: BytesIO) -> list[ElementT]:
        _array = []
        while True:
            try:
                _array.append(cls.element_type.decode(stream))
            except BufferEmptyError:
                break
        return _array

    @classmethod
    def decode(cls, buffer: BufferT) -> Self:
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
