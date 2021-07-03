# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
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


from typing import NamedTuple, Any, Optional
from reprlib import repr as _r


__all__ = ["Tag"]


class Tag(NamedTuple):
    tag: str  #: tag name of tag read/written or request name (generic message)
    value: Any  #: value read/written, may be ``None`` on error
    type: Optional[str] = None  #: data type of tag
    error: Optional[str] = None  #: error message if unsuccessful, else ``None``

    def __bool__(self):
        """
        ``True`` if both ``value`` is not ``None`` and ``error`` is ``None``, ``False`` otherwise
        """
        return self.value is not None and self.error is None

    def __str__(self):
        return f"{self.tag}, {_r(self.value)}, {self.type}, {self.error}"

    def __repr__(self):
        return f"{self.__class__.__name__}(tag={self.tag!r}, value={self.value!r}, type={self.type!r}, error={self.error!r})"
