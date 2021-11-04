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


"""
Various utility functions.
"""

from typing import Tuple


def strip_array(tag: str) -> str:
    """
    Strip off the array portion of the tag

    'tag[100]' -> 'tag'

    """
    if "[" in tag:
        return tag[: tag.find("[")]
    return tag


def get_array_index(tag: str) -> Tuple[str, int]:
    """
    Return tag name and array index from a 1-dim tag request

    'tag[100]' -> ('tag', 100)
    """
    if tag.endswith("]") and "[" in tag:
        tag, _tmp = tag.rsplit("[", maxsplit=1)
        idx = int(_tmp[:-1])
    else:
        idx = None

    return tag, idx


def cycle(stop, start=0):
    val = start
    while True:
        if val > stop:
            val = start

        yield val
        val += 1
