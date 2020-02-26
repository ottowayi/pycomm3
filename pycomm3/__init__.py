# -*- coding: utf-8 -*-
#
# const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
# Copyright (c) 2019 Ian Ottoway <ian@ottoway.dev>
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

__version_info__ = (0, 4, 2)
__version__ = '.'.join(f'{x}' for x in __version_info__)

from typing import NamedTuple, Any, Union, Optional


class PycommError(Exception):
    ...


class CommError(PycommError):
    ...


class DataError(PycommError):
    ...


class RequestError(PycommError):
    ...


def _mkstr(value):
    """If value is a string, return it wrapped in quotes, else just return the value (like for repr's)"""
    return f"'{value}'" if isinstance(value, str) else value


class Tag(NamedTuple):
    tag: str
    value: Any
    type: Optional[str] = None
    error: Optional[str] = None

    def __bool__(self):
        return self.value is not None and self.error is None

    def __str__(self):
        return f'{self.tag}, {self.value}, {self.type}, {self.error}'

    def __repr__(self):
        return f"{self.__class__.__name__}(tag={_mkstr(self.tag)}, value={_mkstr(self.value)}, " \
               f"type={_mkstr(self.type)}, error={_mkstr(self.error)})"


from .clx import LogixDriver
from .slc import SLCDriver