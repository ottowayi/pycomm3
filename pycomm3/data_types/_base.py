import types

from enum import EnumMeta, Enum
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
    Union,
    Literal,
)


from pycomm3.exceptions import BufferEmptyError, DataError
from pycomm3.util import DataclassMeta
from types import EllipsisType, UnionType

type ArrayableT = (
    StructType
    | ElementaryDataType[int]
    | ElementaryDataType[float]
    | ElementaryDataType[bool]
    | ElementaryDataType[str]
    | ElementaryDataType[bytes]
)
type ElementaryPyType = int | float | bool | str | bytes
type ArrayLenT = None | type[ElementaryDataType[int]] | int | EllipsisType
type BufferT = BytesIO | bytes


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


class DataType[T](metaclass=_DataTypeMeta):
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

    def __new__(cls, *args, **kwargs):
        if super().__new__ is object.__new__:
            return super().__new__(cls)
        return super().__new__(cls, *args, **kwargs)

    def __bytes__(self) -> bytes:
        return self.__class__.encode(self)

    @classmethod
    def encode(cls, value: Self | T, *args, **kwargs) -> bytes:
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
    def _encode(cls, value: Self | T, *args, **kwargs) -> bytes: ...

    @classmethod
    def decode(cls, buffer: BufferT) -> Self:
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
    def _decode(cls, stream: BytesIO) -> Self: ...

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


class _ElementaryDataTypeMeta(_DataTypeMeta):
    code: int
    size: int
    _format: str
    _base_type: type[ElementaryPyType]
    _codes: dict[int, type]

    def __new__(mcs, name, bases, classdict):
        klass = super().__new__(mcs, name, bases, classdict)

        if cls_args := get_args(klass.__orig_bases__[0]):  # type: ignore
            klass._base_type = cls_args[0]

        if not klass.size and klass._format:
            klass.size = calcsize(klass._format)

        if klass.code:
            klass._codes[klass.code] = klass

        return klass


class ElementaryDataType[T: ElementaryPyType](DataType[T], metaclass=_ElementaryDataTypeMeta):
    """
    Type that represents a single primitive value in CIP.
    """

    code: int = 0x00  #: CIP data type identifier
    size: int = 0  #: size of type in bytes
    _format: str = ""
    _base_type: type[T]

    # keeps track of all subclasses using the cip type code
    _codes: dict[int, type[T]] = {}

    def __new__(cls, value, *args, **kwargs):
        try:
            obj = super().__new__(cls, value, *args, **kwargs)  # type: ignore
        except Exception as err:
            raise DataError(f"invalid value for {cls}: {value!r}") from err

        # encode at the same time we create the object, removes the need for validation
        # since if it can be encoded, it's valid.
        obj.__encoded_value__ = cls.encode(value, *args, **kwargs)
        return obj

    def __bytes__(self) -> bytes:
        return self.__encoded_value__

    # @classmethod
    # def encode(cls, value: Self, *args, **kwargs) -> bytes:
    #     return super().encode(value, *args)

    @classmethod
    def _encode(cls, value: Self | T, *args, **kwargs) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls, stream: BytesIO):
        data = cls._stream_read(stream, cls.size)
        return cls(unpack(cls._format, data)[0])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._base_type.__repr__(self)})"  # noqa # type: ignore


def _process_typehint(typ, _field):
    if isclass(typ) and issubclass(typ, DataType):
        return typ

    field_type = None
    origin = get_origin(typ)
    if origin is Annotated:
        _type, *extra = get_args(typ)
        _type_origin = get_origin(_type)
        if isclass(_type_origin) and issubclass(_type_origin, ArrayType):
            element_type, ary_len = get_args(_type)
            if get_origin(element_type) is type:
                element_type, *_ = get_args(element_type)
            if not isclass(element_type) or not issubclass(element_type, DataType):
                raise DataError("Annotated array types must have a type[DataType] for the element type (1st) arg")  # fmt: skip
            if ary_len is int:
                _ary_len = next(iter(extra), None)
                if not isinstance(_ary_len, int):
                    raise DataError("Annotated arrays using ArrayType[*, int] must provide an int for the next annotated arg")  # fmt: skip
                ary_len = _ary_len
            field_type = array(cast(type[ArrayableT], element_type), ary_len)
        else:
            if not isclass(_type) or not issubclass(_type, DataType):
                raise DataError(f"Annotated types must provide a DataType for the first arg: {_field.name}")
            field_type = _type

    elif isclass(origin) and issubclass(origin, ArrayType):
        # handles 'x: ArrayType[y, z]' case
        field_type = array(*get_args(typ))

    return field_type


def _process_fields(cls: "_StructMeta") -> ...:
    _fields = fields(cls)  # noqa
    _type_hints = get_type_hints(cls, include_extras=True)
    cls._dataclass_fields = {}
    cls._members = {}
    cls._attributes = {}
    cls._array_length_attributes = {}
    cls._size_ref = None

    for _field in _fields:
        cls._dataclass_fields[_field.name] = _field
        typ = _type_hints.get(_field.name)
        metadata = _field.metadata or {}

        if isclass(typ) and issubclass(typ, DataType):
            field_type = typ
        elif (origin := get_origin(typ)) is not None:
            if origin in (UnionType, Union):
                _type, *_ = get_args(typ)
            else:
                _type = typ
            field_type = _process_typehint(_type, _field)
        else:
            raise DataError(f"Unsupported annotation for struct field: {_field.name}")

        if field_type is None:
            raise DataError(f"Failed to determine type (unsupported annotation) for field: {_field.name}")
        cls._members[_field.name] = field_type
        if not metadata.get("reserved"):
            cls._attributes[_field.name] = field_type
        if len_ref := metadata.get("len_ref"):
            if not issubclass(field_type, (ArrayType, BYTES)):
                raise DataError(f"Fields with 'len_ref' must be Arrays: {_field.name}")
            if len_ref[0] not in cls._members:
                raise DataError(f"Invalid 'len_ref', {len_ref[0]} is not a previous member of the struct")
            cls._array_length_attributes[_field.name] = len_ref
        if size_ref := metadata.get("size_ref"):
            if cls._size_ref is not None:
                raise DataError(f"'size_ref' already defined for struct field: {cls._size_ref[0]}")
            cls._size_ref = _field.name, size_ref


def _default_ref_callable(value: DataType | int) -> int:
    return value  # type: ignore


def attr[T](
    default: T | None = None,
    init: bool = True,
    reserved: bool = False,
    len_ref: str | tuple[str, Callable[[int], int]] | None = None,
    size_ref: bool | Callable[[int], int] = False,
    **kwargs,
) -> Any | T:
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
    size_ref: Indicates the field contains the size (byte count) for all the fields following it. Only one field can
              be a `size_ref` and cannot be used with `len_ref`.  The field can either be `True` or a 1-arg callable
              that accepts the size as an int for the following fields and returns an int.
    """
    if (size_ref or len_ref) and reserved:
        raise DataError("Cannot specify both reserved=True and size_ref/len_ref")
    if size_ref and len_ref:
        raise DataError("Cannot specify both size_ref and len_ref")
    if reserved and not init:
        raise DataError("Cannot specify both reserved=True and init=False")
    if size_ref:
        init = False
    field_kwargs: dict[str, Any] = dict(init=init, metadata={"reserved": reserved})
    if default is not None:
        field_kwargs["default"] = default
    if len_ref is not None and isinstance(len_ref, str):
        len_ref = len_ref, _default_ref_callable
    field_kwargs["metadata"]["len_ref"] = len_ref
    if size_ref and isinstance(size_ref, bool):
        size_ref = _default_ref_callable
    field_kwargs["metadata"]["size_ref"] = size_ref

    return field(**field_kwargs, **kwargs)


@dataclass_transform(field_specifiers=(attr,))
class _StructMeta(DataclassMeta, _DataTypeMeta):
    _members: dict[str, type[DataType]]
    _attributes: dict[str, type[DataType]]
    _dataclass_fields: dict[str, Field]
    _array_length_attributes: dict[str, tuple[str, Callable[[DataType], int]]]
    _size_ref: tuple[str, Callable[[DataType], int]] | None

    def __new__(mcs, name: str, bases: tuple, cls_dict: dict):
        repr = True
        if any(getattr(b, "__field_descriptions__", None) for b in bases) or cls_dict.get("__field_descriptions__"):
            repr = False
        cls = super().__new__(mcs, name, bases, cls_dict, repr=repr)
        _process_fields(cls)
        return cls

    @property
    def size(cls) -> int:
        return sum(sz for typ in cls._members.values() if (sz := typ.size) != -1)


type StructValuesType = dict[str, DataType] | Sequence[DataType]
type StructCreateMembersType = Sequence[tuple[str, type[DataType]] | tuple[str, type[DataType], Field]]


@dataclass_transform(field_specifiers=(attr,))
class StructType(DataType, metaclass=_StructMeta):
    """
    Base type for a structure
    """

    # -- Set by metaclass, for doing cool shit automatically --
    #: map of all members inside the struct and their types
    _members: ClassVar[dict[str, type[DataType]]]
    #: mapping of _user_ members of the struct to their type,
    #: excluding reserved or private members not meant for users to interact with
    _attributes: ClassVar[dict[str, type[DataType]]]
    #: map of field names to dataclass Field objects, to avoid having to call fields() all the time
    _dataclass_fields: ClassVar[dict[str, Field]]
    #: map of array field names to the field name that is the source of the length of the array
    _array_length_attributes: ClassVar[dict[str, tuple[str, Callable[[DataType], int]]]]
    _size_ref: ClassVar[tuple[str, Callable[[int], int]] | None]
    __field_descriptions__: ClassVar[dict[str, dict[DataType | None, str]]] = {}

    def __post_init__(self, *args, **kwargs) -> None:
        for member, typ in self._members.items():
            if issubclass(typ, (StructType, ArrayType)):
                getattr(self, member).__parent_struct__ = (self, member)

        self.__initialized__ = True
        self._update_size_ref()

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.__parent_struct__ = None
        self.__parent_array__ = None
        self.__encoded_fields__ = dict()
        self.__initialized__ = False
        return self

    def __class_getitem__(cls, item: ArrayLenT) -> type["ArrayType[type[Self], ArrayLenT]"]:
        return array(cls, item)

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("__") and key.endswith("__"):
            return super().__setattr__(key, value)

        if key not in self.__class__._members:
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
                setattr(self, len_ref[0], len(value))  # type: ignore
        except Exception as err:
            raise DataError(f"Error updating length attribute for array attribute {key!r}") from err

        try:
            self.__encoded_fields__[key] = bytes(value)  # type: ignore
        except Exception as err:
            raise DataError(f"Error encoding attribute {key!r}") from err
        super().__setattr__(key, value)

        if issubclass(typ, (StructType, ArrayType)):
            value.__parent_struct__ = (self, key)  # type: ignore

        if self.__parent_struct__ is not None:  # type: ignore
            parent, my_name = self.__parent_struct__  # type: ignore
            parent.__setattr__(my_name, self)

        if self.__parent_array__ is not None:  # type: ignore
            parent, my_index = self.__parent_array__  # type: ignore
            parent._encoded_array[my_index] = bytes(self)  # noqa

        if self._size_ref is not None and key != self._size_ref[0]:
            self._update_size_ref()

    def _update_size_ref(self) -> None:
        if self._size_ref is None or not self.__initialized__:
            return
        ref_name, ref_func = self._size_ref
        member_list = list(self._members)
        following_members = member_list[member_list.index(ref_name) + 1 :]
        new_size = ref_func(sum(len(self.__encoded_fields__[m]) for m in following_members))  # type: ignore
        self.__setattr__(ref_name, new_size)

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
        return b"".join(value.__encoded_fields__[attr_name] for attr_name in cls._members)  # type: ignore

    @classmethod
    def _decode(cls: type[Self], stream: BytesIO) -> Self:
        values: dict[str, DataType] = {}
        for name, typ in cls._members.items():
            if len_ref := cls._array_length_attributes.get(name):
                _ref, _func = len_ref
                typ = cast(type[ArrayType[type[ArrayableT], int]], typ)
                _array = array(typ.element_type, _func(values[_ref]))
                value = _array.decode(stream)
            else:
                value = typ.decode(stream)
            values[name] = value

        post_init_vars = {name: val for name, val in values.items() if not cls._dataclass_fields[name].init}
        init_vars = {k: v for k, v in values.items() if k not in post_init_vars}
        instance = cls(**init_vars)
        for name, val in post_init_vars.items():
            setattr(instance, name, val)
        return instance

    @staticmethod
    def create(name: str, members: StructCreateMembersType) -> type["StructType"]:
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

        struct_class = make_dataclass(cls_name=name, fields=_fields, bases=(StructType,))

        return struct_class

    def __field_reprs__(self):
        for name in self._members:
            value = getattr(self, name)
            if name in self.__field_descriptions__:
                desc = self.__field_descriptions__[name].get(
                    value, self.__field_descriptions__[name].get(None, "UNKNOWN")
                )
                yield f"{name}: {desc!r} = {value}"
            else:
                yield f"{name}={value}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(self.__field_reprs__())})"


class _ArrayMeta(_DataTypeMeta):
    element_type: type[ArrayableT]
    length: ArrayLenT

    def __repr__(cls) -> str:
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

    def __eq__(self, other) -> bool:
        try:
            return self.element_type == other.element_type and self.length == other.length
        except Exception:
            return False


def array[ET: ArrayableT, LT: ArrayLenT](element_type: type[ET], length: LT) -> type["ArrayType[type[ET], LT]"]:
    """
    Creates an array type of `length` elements of `element_type`
    """
    _type: type[ET] = element_type
    _len = length
    if _len is None:
        _len = ...

    class Array(ArrayType[type[ET], LT]):
        element_type = _type
        length = _len

    return Array


class ArrayType[ElementT: type[ArrayableT], LenT: ArrayLenT](DataType, metaclass=_ArrayMeta):
    """
    Base type for an array
    """

    element_type: ElementT
    length: LenT

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.__parent_struct__ = None  # type: ignore
        return self

    def __init__(self: Self, value: Sequence) -> None:
        if isinstance(self.length, int):
            try:
                val_len = len(value)
            except Exception as err:
                raise DataError("invalid value for array, must support len()") from err
            else:
                if val_len != self.length:
                    raise DataError(f"Array length error: expected {self.length} items, received {len(value)}")

        self._array = [self._convert_element(v) for v in value]
        if issubclass(self.element_type, StructType):
            for i, obj in enumerate(self._array):
                obj.__parent_array__ = (self, i)  # type: ignore
        self._encoded_array = [bytes(x) for x in self._array]

    @property
    def size(self) -> int:  # pyright: ignore [reportIncompatibleVariableOverride]
        if isclass(self.length) and issubclass(self.length, DataType):
            return self.length.size + len(self._array) * self.element_type.size
        else:
            return len(self._array) * self.element_type.size

    def _convert_element(self, value):
        if not isinstance(value, self.element_type):
            try:
                val = self.element_type(value)  # pyright: ignore [reportCallIssue]
            except Exception as err:
                raise DataError("Error converting element:") from err
        else:
            val = value
        return val

    def __hash__(self):
        return hash((self.length, self.element_type, self._array))

    def __len__(self) -> int:
        return len(self._array)

    @overload
    def __getitem__(self, item: int) -> ArrayableT: ...

    @overload
    def __getitem__(self, item: slice) -> "ArrayType[type[ArrayableT], int]": ...

    def __getitem__(self, item):
        if isinstance(item, slice):
            items = self._array[item]
            return array(self.element_type, len(items))(items)

        return self._array[item]

    def __setitem__(self, item: int | slice, value) -> None:
        try:
            if isinstance(item, slice):
                self._array[item] = (self._convert_element(v) for v in value)
                self._encoded_array[item] = (bytes(x) for x in self._array[item])
            else:
                self._array[item] = self._convert_element(value)
                self._encoded_array[item] = bytes(self._array[item])

            if self.__parent_struct__ is not None:  # type: ignore
                parent, my_name = self.__parent_struct__  # type: ignore
                parent.__setattr__(my_name, self)
                ...
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
        encoded_elements = b"".join(value._encoded_array)
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
                _len = cls.length.decode(stream)
            else:
                _len = cls.length

            _val = [cls.element_type.decode(stream) for _ in range(cast(int, _len))]

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


class Array[ET: ArrayableT, LT: ArrayLenT](Sequence[ET]):
    def __class_getitem__(cls, item: type[ET] | tuple[type[ET], LT]) -> type[ArrayType[type[ET], LT]]:
        element_type: type[ET]
        len_type: LT
        if isinstance(item, tuple):
            element_type, len_type = item
        else:
            element_type, len_type = item, ...  # type: ignore
        return array(element_type, len_type)


class BYTES(ElementaryDataType[bytes], bytes, metaclass=_ElementaryDataTypeMeta):  # type: ignore
    """
    Base type for placeholder bytes, sized to `size`. if `size` is -1, then unlimited

    ignore comment b/c decode() method incompatible w/ bytes.decode(), but it's supposed to be
    b/c we're overriding the bytes behavior to return BYTES not str
    """

    size: int = -1
    _int_type: type[ElementaryDataType[int]] | None = None

    # so this type can pretend to be an array sometimes
    element_type: type["BYTES"]  # set below
    length: None = None

    def __new__(cls, value: bytes | int, *args, **kwargs):
        if isinstance(value, int):
            value = bytes([value])
        value = value[: cls.size] if cls.size != -1 else value[:]
        return super().__new__(cls, value, *args, **kwargs)

    def __class_getitem__(cls, item: int | EllipsisType | type[ElementaryDataType[int]]) -> type["BYTES"]:
        size = item if isinstance(item, int) else -1
        _int_type = item if not isinstance(item, (int, EllipsisType)) else None
        klass = type("BYTES", (cls,), {"size": size, "_int_type": _int_type})
        return klass

    @classmethod
    def _encode(cls, value: bytes, *args, **kwargs) -> bytes:
        val = value[: cls.size] if cls.size != -1 else value
        if cls._int_type is not None:
            val = bytes(cls._int_type(len(value))) + value
        return val

    @classmethod
    def _decode(cls, stream: BytesIO) -> Self:
        if cls._int_type is not None:
            size = cast(int, cls._int_type.decode(stream))
        else:
            size = cls.size
        data = cls._stream_read(stream, size)
        return cls(data)

    def __getitem__(self, item) -> bytes:  # type: ignore
        if isinstance(item, int):
            return super().__getitem__(slice(item, item + 1))

        return super().__getitem__(item)

    def __repr__(self) -> str:
        if self._int_type is not None:
            size = self._int_type.__name__
        else:
            size = "..." if self.size == -1 else self.size
        return f"{self.__class__.__name__}[{size}]({self})"


BYTES.element_type = BYTES
