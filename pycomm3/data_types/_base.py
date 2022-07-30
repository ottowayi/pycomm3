# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Ian Ottoway <ian@ottoway.dev>
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
from __future__ import annotations

from dataclasses import Field, astuple, dataclass, field, fields, make_dataclass
from inspect import isclass
from io import BytesIO
from struct import calcsize, pack, unpack
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Literal,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args, Protocol, overload, Iterable,
)

from ..exceptions import BufferEmptyError, DataError
import builtins

_BufferType = Union[BytesIO, bytes]

__all__ = (
    'DataType',
    'is_datatype',
    'StructType',
)


def _repr(buffer: _BufferType) -> str:
    if isinstance(buffer, BytesIO):
        return repr(buffer.getvalue())
    else:
        return repr(buffer)


def _get_bytes(buffer: _BufferType, length: int) -> bytes:
    if isinstance(buffer, bytes):
        return buffer[:length]

    return buffer.read(length)


def _as_stream(buffer: _BufferType) -> BytesIO:
    if isinstance(buffer, bytes):
        return BytesIO(buffer)
    return buffer


class _DataTypeMeta(type):
    def __repr__(cls):
        return cls.__name__


#: The Python type that the :class:`DataType` implements
PyType = TypeVar('PyType')
_DataType = TypeVar('_DataType', bound='DataType')


class DataType(Generic[PyType], metaclass=_DataTypeMeta):
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

    __encoded_value__: bytes = b''
    size: int = 0

    def __new__(cls: type[_DataType], value: PyType, *args, **kwargs) -> _DataType:
        return super().__new__(cls, value, *args, **kwargs)  # type: ignore

    def __bytes__(self) -> bytes:
        return self.__encoded_value__

    @classmethod
    def encode(cls: type[_DataType], value: PyType, *args, **kwargs) -> bytes:
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
    def _encode(cls: type[_DataType], value: PyType, *args, **kwargs) -> bytes:
        ...

    @classmethod
    def decode(cls: type[_DataType], buffer: _BufferType) -> _DataType:
        """
        Deserializes a Python object from the ``buffer`` of ``bytes``

        .. note::
            Any subclass overriding this method must catch any exception and re-raise as a :class:`DataError`.
            Except ``BufferEmptyErrors`` they must be re-raised as such, array decoding relies on this.
        """
        try:
            stream = _as_stream(buffer)
            return cls._decode(stream)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f"Error unpacking {_repr(buffer)} as {cls.__name__}") from err

    @classmethod
    def _decode(cls: type[_DataType], stream: BytesIO) -> _DataType:
        ...

    @classmethod
    def _stream_read(cls, stream: BytesIO, size: int) -> bytes:
        """
        Reads `size` bytes from `stream`.
        Raises `BufferEmptyError` if stream returns no data.
        """
        if not (data := stream.read(size)):
            raise BufferEmptyError()
        return data


ArrayElementType = TypeVar('ArrayElementType', bound=DataType)
ArrayLengthType = TypeVar('ArrayLengthType', Type['IntDataType'], int, None, 'builtins.ellipsis', )

_ArrayType = TypeVar('_ArrayType', bound='ArrayType')
# # Type for DataTypes that may be used in arguments, either DataType classes or instances
# DataTypeType = Union[DataType, Type[DataType]]


def is_datatype(obj: Any, typ=DataType) -> bool:
    """
    Returns True if ``obj`` is an instance or subclass of ``typ``, False otherwise
    """
    if isclass(obj):
        return issubclass(obj, typ)
    else:
        return isinstance(obj, typ)


class _ArrayMetaMixin(type):
    """
    Allows a data type to create arrays using brackets: DINT[5] -> Array(DINT, 5)
    """

    def __getitem__(cls: type[ArrayElementType], item: ArrayLengthType) -> type[ArrayType]:  # type: ignore
        class Array(ArrayType):
            element_type: type[ArrayElementType] = cls
            length: ArrayLengthType = item

        return Array


class _ElementaryDataTypeMeta(_DataTypeMeta):
    def __new__(mcs, name, bases, classdict):
        klass = super().__new__(mcs, name, bases, classdict)
        base_type, *_ = get_args(klass.__orig_bases__[0])
        klass._base_type = base_type
        if not klass.size and klass._format:
            klass.size = calcsize(klass._format)

        return klass


class _ArrayableElementaryDataTypeMeta(_ElementaryDataTypeMeta, _ArrayMetaMixin):
    """ """


_ElementaryType = TypeVar('_ElementaryType', bound='ElementaryDataType')
ElmPyType = TypeVar('ElmPyType', int, float, bool, str, bytes)


class ElementaryDataType(DataType[ElmPyType], metaclass=_ElementaryDataTypeMeta):
    """
    Type that represents a single primitive value in CIP.
    """

    code: int = 0x00  #: CIP data type identifier
    size: int = 0  #: size of type in bytes
    _format: str = ""
    _base_type: type[ElmPyType]

    # keeps track of all subclasses using the cip type code
    _codes: dict[int, type[ElementaryDataType]] = {}

    def __new__(cls: type[_ElementaryType], value: ElmPyType, *args, **kwargs) -> _ElementaryType:
        try:
            obj = super().__new__(cls, value, *args, **kwargs)  # type: ignore
        except Exception as err:
            raise DataError(f'invalid value for {cls}: {value!r}') from err

        # encode at the same time we create the object, removes the need for validation
        # since if it can be encoded, it's valid.
        obj.__encoded_value__ = cls.encode(value, *args, **kwargs)
        return obj

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.code:
            cls._codes[cls.code] = cls

    @classmethod
    def _encode(cls, value: ElmPyType, *args, **kwargs) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls: type[_ElementaryType], stream: BytesIO) -> _ElementaryType:
        data = cls._stream_read(stream, cls.size)
        return cls(unpack(cls._format, data)[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._base_type.__repr__(self)})'  # type: ignore


class IntDataType(ElementaryDataType[int], int, metaclass=_ArrayableElementaryDataTypeMeta):
    ...


_BT = TypeVar('_BT', bound='BoolDataType')


class BoolDataType(ElementaryDataType[bool], int, metaclass=_ArrayableElementaryDataTypeMeta):
    def __new__(cls, value: int, *args, **kwargs):
        return super().__new__(cls, True if value else False, *args, **kwargs)  # type: ignore

    @classmethod
    def _encode(cls, value: bool, *args, **kwargs) -> Literal[b"\x00", b"\xFF"]:
        # don't inline to keep pycharm's type checker happy
        if value:
            return b"\xFF"
        else:
            return b"\x00"

    @classmethod
    def _decode(cls: type[_BT], stream: BytesIO) -> _BT:
        data = cls._stream_read(stream, cls.size)
        return cls(data[0])


class FloatDataType(ElementaryDataType[float], float, metaclass=_ArrayableElementaryDataTypeMeta):
    ...


_StringType = TypeVar('_StringType', bound='StringDataType')


class StringDataType(ElementaryDataType[str], str, metaclass=_ArrayableElementaryDataTypeMeta):  # type: ignore
    """
    Base class for any string type
    """

    len_type: type[IntDataType]  #: data type of the string length
    encoding: str = 'iso-8859-1'

    @classmethod
    def _encode(cls: type[_StringType], value: str, *args, **kwargs) -> bytes:
        return cls.len_type.encode(len(value)) + value.encode(cls.encoding)

    @classmethod
    def _decode(cls: type[_StringType], stream: BytesIO) -> _StringType:
        str_len: IntDataType = cls.len_type.decode(stream)
        if str_len == 0:
            return cls("")
        str_data = cls._stream_read(stream, str_len)

        return cls(str_data.decode(cls.encoding))


_BytesType = TypeVar('_BytesType', bound='BytesDataType')


class BytesDataType(ElementaryDataType[bytes], bytes, metaclass=_ArrayableElementaryDataTypeMeta):  # type: ignore
    """
    Base type for placeholder bytes.
    """

    @classmethod
    def _encode(cls: type[_BytesType], value: bytes, *args, **kwargs) -> bytes:
        return value[: cls.size] if cls.size != -1 else value[:]

    @classmethod
    def _decode(cls: type[_BytesType], stream: BytesIO) -> _BytesType:
        data = cls._stream_read(stream, cls.size)
        return cls(data)


_BitsType = TypeVar('_BitsType', bound='BitArrayType')


class BitArrayType(IntDataType):
    bits: tuple[int, ...]

    def __new__(cls: type[_BitsType], value: int | Sequence[int], *args, **kwargs) -> _BitsType:
        try:
            if not isinstance(value, int):
                value = cls._from_bits(value)
        except Exception as err:
            raise DataError(f'invalid value for {cls}: {value!r}')
        obj = super().__new__(cls, value)  # type: ignore
        return obj

    def __init__(self, *args, **kwargs) -> None:
        self.bits = self._to_bits(self)

    @classmethod
    def _encode(cls: type[_BitsType], value: int | Sequence[Any], *args, **kwargs) -> bytes:
        if not isinstance(value, int):
            value = cls._from_bits(value)

        return super()._encode(value)

    @classmethod
    def _to_bits(cls: type[_BitsType], value: int) -> tuple[int, ...]:
        return tuple((value >> idx) & 1 for idx in range(cls.size * 8))

    @classmethod
    def _from_bits(cls: type[_BitsType], value: Sequence[int]) -> int:
        if len(value) != (8 * cls.size):
            raise DataError(
                f"{cls.__name__} requires exactly {cls.size * 8} elements, got: {len(value)}"
            )
        _value = 0
        for i, val in enumerate(value):
            if val:
                _value |= 1 << i

        return _value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.bits!r})'


class DerivedDataType(DataType[PyType]):
    """
    Base type for types composed of :class:`ElementaryDataType`
    """

    def __eq__(self, other):
        try:
            if isinstance(other, DerivedDataType):
                return self.__encoded_value__ == other.__encoded_value__
        except Exception:  # noqa
            ...

        return False

# def __dataclass_transform__(
#     *,
#     eq_default: bool = True,
#     order_default: bool = False,
#     kw_only_default: bool = False,
#     field_specifiers: Tuple[Union[type, Callable[..., Any]], ...] = (()),
# ) -> Callable[[_T], _T]:
#     # If used within a stub file, the following implementation can be
#     # replaced with "...".
#     return lambda a: a


_StructType = TypeVar('_StructType', bound='StructType')


class _StructMeta(_DataTypeMeta, _ArrayMetaMixin):
    def __new__(mcs: type[_StructMeta], name: str, bases: tuple, clsdict: dict) -> type[_StructType]:
        cls: _StructMeta = super().__new__(mcs, name, bases, clsdict)
        klass: type[_StructType] = dataclass(cast(type[_StructType], cls))

        _fields = fields(klass)
        klass._members = {_field.name: _field.type for _field in _fields}
        klass._attributes = {
            _field.name: _field.type
            for _field in _fields
            if not _field.metadata.get('reserved', False)
        }

        return klass

    @property
    def size(cls) -> int:
        return sum(typ.size for typ in cls._members.values())  # type: ignore


StructValuesType = Union[Dict[str, DataType], Sequence[DataType]]
StructCreateMembersType = Sequence[
    Union[
        Tuple[str, Type[DataType]],
        Tuple[str, Type[DataType], Field],
    ]
]


class StructType(DerivedDataType, metaclass=_StructMeta):
    """
    Base type for a structure
    """

    #: map of all members inside the struct and their types
    _members: ClassVar[dict[str, type[DataType]]] = {}
    #: mapping of _user_ members of the struct to their type,
    #: excluding reserved or private members not meant for users to interact with
    _attributes: ClassVar[dict[str, type[DataType]]] = {}

    def __new__(cls: type[_StructType], *args, **kwargs) -> _StructType:
        return super().__new__(cls, *args, **kwargs)

    def __post_init__(self) -> None:
        self.__encoded_value__ = self.encode(self)

    def __setattr__(self: _StructType, key: str, value: DataType | PyType) -> None:
        if key != '__encoded_value__':
            if key not in self.__class__._members:  # noqa
                raise AttributeError(
                    f'{key!r} is not an attribute of struct {self.__class__.__name__}'
                )
            if not isinstance(value, typ := self.__class__._members[key]): # noqa
                try:
                    value = typ(value)
                except Exception as err:
                    raise DataError(f'Type conversion error for attribute {key!r}') from err
                self.__encoded_value__ = b''

        super().__setattr__(key, value)

    def __bytes__(self: _StructType) -> bytes:
        if not self.__encoded_value__:
            self.__encoded_value__ = self.__class__.encode(self)

        return self.__encoded_value__

    @classmethod
    def _encode(cls: type[StructType], value: _StructType, *args, **kwargs) -> bytes:
        return b''.join(bytes(attr) for attr in astuple(value))

    @classmethod
    def _decode(cls: type[_StructType], stream: BytesIO) -> _StructType:
        values = {name: typ.decode(stream) for name, typ in cls._members.items()}
        return cls(**values)

    @staticmethod
    def attr(*, reserved: bool = False, **kwargs) -> Field:
        return field(
            metadata={
                **kwargs,
                'reserved': reserved,
            }
        )

    @staticmethod
    def create(name: str, members: StructCreateMembersType) -> type[_StructType]:
        _fields = []
        member: tuple[str, type[DataType]] | tuple[str, type[DataType], Field]
        for i, member in enumerate(members):
            if len(member) == 2:
                _name, typ = cast(tuple[str, type[DataType]], member)
                _field = None
            else:
                _name, typ, _field = cast(tuple[str, type[DataType], Field], member)

            if not _name:
                _name = f'_reserved_attr{i}'
                if _field is None:
                    _field = StructType.attr(reserved=True)

            _fields.append((_name, typ, _field))

        struct_class: type[_StructType] = make_dataclass(  # noqa
            cls_name=name,
            fields=_fields,
            bases=(StructType,),
        )

        return struct_class


class _ArrayReprMeta(_DataTypeMeta):
    def __repr__(cls: _ArrayType) -> str:  # type: ignore
        if cls.length in (Ellipsis, None):
            return f"{cls.element_type}[...]"

        return f"{cls.element_type}[{cls.length!r}]"


class ArrayType(Generic[ArrayElementType, ArrayLengthType], DerivedDataType, metaclass=_ArrayReprMeta):
    """
    Base type for an array
    """

    element_type: type[ArrayElementType]
    length: ArrayLengthType

    def __init__(self: _ArrayType, value: Sequence[ArrayElementType | PyType]) -> None:
        if isinstance(self.length, int):
            try:
                val_len = len(value)
            except Exception as err:
                raise DataError('invalid value for array, must support len()') from err
            else:
                if val_len != self.length:
                    raise DataError(
                        f'Array length error: expected {self.length} items, received {len(value)}'
                    )

        self._array: list[ArrayElementType] = [self._convert_element(v) for v in value]

    def _convert_element(self, value: PyType) -> ArrayElementType:
        if not isinstance(value, self.element_type):  # noqa - PyCharm Issue: PY-32860
            try:
                val = self.element_type(value)
            except Exception as err:
                raise DataError(f'Error converting element:') from err
        else:
            val = value
        return val

    def __len__(self: _ArrayType) -> int:
        return len(self._array)

    @overload
    def __getitem__(self: _ArrayType, item: int) -> ArrayElementType: ...

    @overload
    def __getitem__(self: _ArrayType, item: slice) -> list[ArrayElementType]: ...

    def __getitem__(self: _ArrayType, item: int | slice) -> ArrayElementType | list[ArrayElementType]:
        return self._array[item]

    def __setitem__(self: _ArrayType, item: int | slice, value: PyType | Iterable[PyType]) -> None:
        try:
            if isinstance(item, slice):

                self._array[item] = (self._convert_element(v) for v in cast(Iterable[PyType], value))
            else:
                self._array[item] = self._convert_element(value)
        except Exception as err:
            raise DataError(f'Failed to set item') from err

        self.__encoded_value__ = b''

    def __bytes__(self: _ArrayType) -> bytes:
        if not self.__encoded_value__:
            self.__encoded_value__ = self.__class__.encode(self)

        return self.__encoded_value__

    @classmethod
    def _encode(cls: type[_ArrayType], value: _ArrayType, *args, **kwargs) -> bytes:
        encoded_elements = b''.join(bytes(x) for x in value._array)
        if value.length in IntDataType.__subclasses__():
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
    def decode(cls: type[_ArrayType], buffer: _BufferType) -> _ArrayType:
        try:
            stream = _as_stream(buffer)
            if cls.length in {None, Ellipsis}:
                return cls(cls._decode_all(stream))

            if is_datatype(cls.length, DataType):
                _len = cls.length.decode(stream)
            else:
                _len = cls.length

            _val = [cls.element_type.decode(stream) for _ in range(_len)]

            return cls(_val)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(
                    f"Error unpacking into {cls.element_type}[{cls.length}] from {_repr(buffer)}"
                ) from err

    def __repr__(self):
        return f'{self.__class__!r}({self._array!r})'
