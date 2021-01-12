# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Ian Ottoway <ian@ottoway.dev>
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

__all__ = ['EnumMap', ]


class MapMeta(type):

    def __new__(cls, name, bases, classdict):
        enumcls = super().__new__(cls, name, bases, classdict)

        # get all non-private attributes
        members = {
            key: value for key, value in classdict.items()
            if not key.startswith('_') and not isinstance(value, (classmethod, staticmethod))
        }

        # also add uppercase keys for each member (if they're not already lowercase)
        lower_members = {key.lower(): value for key, value in members.items() if key.lower() not in members}

        # invert members to a value->key dict
        value_map = {value: key.lower() for key, value in members.items()}

        # merge 3 previous dicts to get member lookup dict
        enumcls._members_ = {**members, **lower_members, **value_map}

        # lookup by value only return CAPS keys if attribute set
        _only_caps = enumcls.__dict__.get('_return_caps_only_')
        enumcls._return_caps_only_ = _only_caps

        return enumcls

    def __getitem__(self, item):
        val = self._members_.__getitem__(_key(item))
        if self._return_caps_only_ and isinstance(val, str):
            val = val.upper()
        return val

    def get(cls, item, default=None):

        val = cls._members_.get(_key(item), default)

        if cls._return_caps_only_ and isinstance(val, str):
            val = val.upper()
        return val

    def __contains__(self, item):
        return self._members_.__contains__(item.lower() if isinstance(item, (str, bytes)) else item)


def _key(item):
    if isinstance(item, str):
        return item.lower()
    elif isinstance(item, bytes):
        return item
    else:
        return item


class EnumMap(metaclass=MapMeta):
    """
    A simple enum-like class that allows dict-like __getitem__() and get() lookups.
    __getitem__() and get() are case-insensitive and bidirectional

    example:

    class TestEnum(Pycomm3EnumMap):
        x = 100

    >>> TestEnum.x
    100
    >>> TestEnum['X']
    100
    >>> TestEnum[100]
    x

    Note: this class is really only to be used internally, it doesn't cover anything more than simple subclasses
    (as in attributes only, don't add methods except for classmethods)
    It's really just to provide dict-like item access with enum-like attributes.

    """
    ...
