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


import reprlib
from dataclasses import Field, dataclass, field, fields, make_dataclass, astuple
from enum import IntEnum
from inspect import isclass
from io import BytesIO
from itertools import chain
from struct import calcsize, pack, unpack
from typing import (
    Any, Generic, Optional, TypeVar, Union, Type, ClassVar, Dict, Tuple, get_args, Sequence, cast,
    Iterable, Literal, overload
)
from collections import abc
from ..exceptions import BufferEmptyError, DataError

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

    def __bytes__(self) -> bytes:
        return self.__encoded_value__

    @classmethod
    def encode(cls, value: PyType, *args, **kwargs) -> bytes:
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
    def _encode(cls, value: PyType, *args, **kwargs) -> bytes:
        ...

    @classmethod
    def decode(cls, buffer: _BufferType) -> _DataType:
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
    def _decode(cls, stream: BytesIO) -> _DataType:
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


# Type for DataTypes that may be used in arguments, either DataType classes or instances
DataTypeType = Union[DataType, Type[DataType]]


def is_datatype(obj: DataTypeType, typ=DataType) -> bool:
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
    def __getitem__(cls: ArrayElementType, item: ArrayLengthType) -> type[ArrayType]:
        class Array(ArrayType[cls]):
            element_type: ArrayElementType = cls
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
    """
    """


ElementaryType = TypeVar('ElementaryType', bound='ElementaryDataType')


class ElementaryDataType(DataType[PyType], metaclass=_ElementaryDataTypeMeta):
    """
    Type that represents a single primitive value in CIP.
    """

    code: int = 0x00  #: CIP data type identifier
    size: int = 0  #: size of type in bytes
    _format: str = ""

    # keeps track of all subclasses using the cip type code
    _codes: dict[int, type[ElementaryDataType]] = {}

    def __new__(cls, value: PyType, *args, **kwargs) -> ElementaryType:
        try:
            obj = super().__new__(cls, value, *args, **kwargs)
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
    def _encode(cls, value: PyType, *args, **kwargs) -> bytes:
        return pack(cls._format, value)

    @classmethod
    def _decode(cls, stream: BytesIO) -> ElementaryType:
        data = cls._stream_read(stream, cls.size)
        return cls(unpack(cls._format, data)[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._base_type.__repr__(self)})'


class IntDataType(ElementaryDataType[int], int, metaclass=_ArrayableElementaryDataTypeMeta):
    ...


_BT = TypeVar('_BT', bound='BoolDataType')


class BoolDataType(ElementaryDataType[bool], int, metaclass=_ArrayableElementaryDataTypeMeta):
    def __new__(cls, value: int, *args, **kwargs) -> _BT:
        val = True if value else False
        return super().__new__(cls, val, *args, **kwargs)

    @classmethod
    def _encode(cls, value: bool, *args, **kwargs) -> Literal[b"\x00", b"\xFF"]:
        # don't inline to keep pycharm's type checker happy
        if value:
            return b"\xFF"
        else:
            return b"\x00"

    @classmethod
    def _decode(cls, stream: BytesIO) -> _BT:
        data = cls._stream_read(stream, cls.size)
        return cls(data[0])


class FloatDataType(ElementaryDataType[float], float, metaclass=_ArrayableElementaryDataTypeMeta):
    ...


_StrT = TypeVar('_StrT', bound='StringDataType')


class StringDataType(ElementaryDataType[str], str, metaclass=_ArrayableElementaryDataTypeMeta):
    """
    Base class for any string type
    """

    len_type: type[IntDataType] = None  #: data type of the string length
    encoding: str = 'iso-8859-1'

    @classmethod
    def _encode(cls, value: str , *args, **kwargs) -> bytes:
        return cls.len_type.encode(len(value)) + value.encode(cls.encoding)

    @classmethod
    def _decode(cls, stream: BytesIO) -> _StrT:
        str_len = cls.len_type.decode(stream)
        if str_len == 0:
            return cls("")
        str_data = cls._stream_read(stream, str_len)

        return cls(str_data.decode(cls.encoding))


class BytesDataType(ElementaryDataType[bytes], bytes, metaclass=_ArrayableElementaryDataTypeMeta):
    """
    Base type for placeholder bytes.
    """

    @classmethod
    def _encode(cls, value: bytes, *args, **kwargs) -> bytes:
        return value[: cls.size] if cls.size != -1 else value[:]

    @classmethod
    def _decode(cls, stream: BytesIO) -> BytesDataType:
        data = cls._stream_read(stream, cls.size)
        return cls(data)


class BitArrayType(IntDataType):
    bits: tuple[int]

    def __new__(cls, value: int | Sequence[int], *args, **kwargs) -> DataType[int]:
        try:
            if not isinstance(value, int):
                value = cls._from_bits(value)
        except Exception as err:
            raise DataError(f'invalid value for {cls}: {value!r}')
        obj = super().__new__(cls, value)
        return obj

    def __init__(self, *args, **kwargs) -> None:
        self.bits = self._to_bits(self)

    @classmethod
    def _encode(cls, value: int | Sequence[Any], *args, **kwargs) -> bytes:
        if not isinstance(value, int):
            value = cls._from_bits(value)

        return super()._encode(value)

    @classmethod
    def _to_bits(cls, value: int) -> tuple[int]:
        return tuple((value >> idx) & 1 for idx in range(cls.size * 8))

    @classmethod
    def _from_bits(cls, value: Sequence[int]) -> int:
        if len(value) != (8 * cls.size):
            raise DataError(f"{cls.__name__} requires exactly {cls.size * 8} elements, got: {len(value)}")
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


class _StructMeta(_DataTypeMeta, _ArrayMetaMixin):
    def __new__(mcs, name: str, bases: tuple, clsdict: dict) -> type[StructType]:
        cls = super().__new__(mcs, name, bases, clsdict)
        klass = cast(dataclass, dataclass(cls))

        _fields = fields(klass)
        klass._members = {_field.name: _field.type for _field in _fields}
        klass._attributes = {_field.name: _field.type for _field in _fields if not _field.metadata.get('reserved', False)}

        return klass

    @property
    def size(cls) -> int:
        return sum(typ.size for typ in cls._members.values())


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

    #: complete list of all members inside the struct
    _members: ClassVar[dict[str, type[DataType]]] = {}
    #: mapping of _user_ members of the struct to their type,
    #: excluding reserved or private members not meant for users to interact with
    _attributes: ClassVar[dict[str, type[DataType]]] = {}

    def __post_init__(self) -> None:
        self.__encoded_value__ = self.encode(self)

    def __setattr__(self, key: str, value: PyType) -> None:
        if key != '__encoded_value__':
            if key not in self.__class__._members:
                raise AttributeError(f'{key!r} is not an attribute of struct {self.__class__.__name__}')
            if not isinstance(value, typ := self.__class__._members[key]):
                try:
                    value = typ(value)
                except Exception as err:
                    raise DataError(f'Type conversion error for attribute {key!r}') from err
                self.__encoded_value__ = b''

        super().__setattr__(key, value)

    def __bytes__(self) -> bytes:
        if not self.__encoded_value__:
            self.__encoded_value__ = self.__class__.encode(self)

        return self.__encoded_value__

    @classmethod
    def _encode(cls, value: StructType, *args, **kwargs) -> bytes:
        return b''.join(bytes(attr) for attr in astuple(cast(dataclass, value)))

    @classmethod
    def _decode(cls: type[StructType], stream: BytesIO) -> StructType:
        values = {name: typ.decode(stream) for name, typ in cls._members.items()}
        return cast(dataclass, cls)(**values)

    @staticmethod
    def attr(*, reserved: bool = False, **kwargs) -> Field:
        return field(
            metadata={
                **kwargs,
                'reserved': reserved,
            }
        )

    @staticmethod
    def create(name: str, members: StructCreateMembersType) -> type[StructType]:
        _fields = []
        member: tuple
        for i, member in enumerate(members):
            if len(member) == 2:
                _name, typ = member
                _field = None
            else:
                _name, typ, _field = member

            if not _name:
                _name = f'_reserved_attr{i}'
                if _field is None:
                    _field = StructType.attr(reserved=True)

            _fields.append((_name, typ, _field))

        struct_class: type[StructType] = make_dataclass(  # noqa
            cls_name=name,
            fields=_fields,
            bases=(StructType, ),
        )

        return struct_class


class _ArrayReprMeta(_DataTypeMeta):
    def __repr__(cls: "ArrayType") -> str:
        if cls.length in (Ellipsis, None):
            return f"{cls.element_type}[...]"

        return f"{cls.element_type}[{cls.length!r}]"

    # __str__ = __repr__


ArrayElementType = TypeVar('ArrayElementType', bound=DataType)
ArrayLengthType = Union[Type[IntDataType], int, None, type(Ellipsis)]


class ArrayType(DerivedDataType[Sequence[ArrayElementType]], metaclass=_ArrayReprMeta):
    """
    Base type for an array
    """

    element_type: type[ArrayElementType] = None
    length: ArrayLengthType = None

    def __init__(self, value: Sequence[ArrayElementType]) -> None:
        if isinstance(self.length, int):
            try:
                val_len = len(value)
            except Exception as err:
                raise DataError('invalid value for array, must support len()') from err
            else:
                if val_len != self.length:
                    raise DataError(f'Array length error: expected {self.length} items, received {len(value)}')

        self._array = [self._convert_element(v) for v in value]

    def _convert_element(self, value) -> ArrayElementType:
        if not isinstance(value, self.element_type):  # noqa - PyCharm Issue: PY-32860
            try:
                value = self.element_type(value)
            except Exception as err:
                raise DataError(f'Error converting element:') from err

        return value

    def __len__(self):
        return len(self._array)

    def __getitem__(self, item):
        return self._array[item]

    def __setitem__(self, item, value):
        if isinstance(item, slice):
            self._array[item] = (self._convert_element(v) for v in value)
        else:
            self._array[item] = self._convert_element(value)
        self.__encoded_value__ = b''

    def __bytes__(self) -> bytes:
        if not self.__encoded_value__:
            self.__encoded_value__ = self.__class__.encode(self._array)

        return self.__encoded_value__

    @classmethod
    def _encode(cls, value: ArrayType, *args, **kwargs) -> bytes:
        encoded_elements = b''.join(bytes(x) for x in value._array)
        if value.length in IntDataType.__subclasses__():
            return bytes(value.length(len(value))) + encoded_elements

        return encoded_elements
        # _length = length or cls.length
        # if isinstance(_length, int):
        #     if len(values) != _length:
        #         raise DataError(f"Not enough values to encode array of {cls.element_type}[{_length}]")
        #
        #     _len = _length
        # else:
        #     _len = len(values)
        #
        # try:
        #     # if is_datatype(cls.element_type, BytesDataType):
        #     #     if not isinstance(values, (bytes, bytearray)):
        #     #         raise DataError('BytesDataType value must be a bytes/bytearray object')
        #     #     return values[:_len]
        #     #
        #     # if is_datatype(cls.element_type, BitArrayType):
        #     #     chunk_size = cls.element_type.size * 8
        #     #     _len = len(values) // chunk_size
        #     #     values = [values[i : i + chunk_size] for i in range(0, len(values), chunk_size)]
        #
        #     return b"".join(cls.element_type.encode(v) for v in values)
        # except Exception as err:
        #     raise DataError(f"Error packing {reprlib.repr(values)} into {cls.element_type}[{_length}]") from err

    @classmethod
    def _decode_all(cls, stream) -> list[ArrayElementType]:
        # if issubclass(cls.element_type, BytesDataType):
        #     return cls._stream_read(stream, -1)

        _array = []
        while True:
            try:
                _array.append(cls.element_type.decode(stream))
            except BufferEmptyError:
                break
        return _array

    @classmethod
    def decode(cls, buffer: _BufferType, length: Optional[int] = None) -> ArrayType:
        _length = length or cls.length
        try:
            stream = _as_stream(buffer)
            if _length in {None, Ellipsis}:
                return cls(cls._decode_all(stream))

            if is_datatype(_length, DataType):
                _len = _length.decode(stream)
            else:
                _len = _length

            # if is_datatype(cls.element_type, BytesDataType):
            #     return cls(cls._stream_read(stream, _len))

            _val = [cls.element_type.decode(stream) for _ in range(_len)]

            # if is_datatype(cls.element_type, BitArrayType):
            #     return list(chain.from_iterable(_val))

            return cls(_val)
        except Exception as err:
            if isinstance(err, BufferEmptyError):
                raise
            else:
                raise DataError(f"Error unpacking into {cls.element_type}[{_length}] from {_repr(buffer)}") from err

    def __repr__(self):
        return f'{self.__class__!r}({self._array!r})'
