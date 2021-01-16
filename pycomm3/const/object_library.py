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

from ..map import EnumMap


class ConnectionManagerInstance(EnumMap):
    open_request = b'\x01'
    open_format_rejected = b'\x02'
    open_resource_rejected = b'\x03'
    open_other_rejected = b'\x04'
    close_request = b'\x05'
    close_format_request = b'\x06'
    close_other_request = b'\x07'
    connection_timeout = b'\x08'








class ClassCode(EnumMap):
    identity_object = b'\x01'
    message_router = b'\x02'
    symbol_object = b'\x6b'
    template_object = b'\x6c'
    connection_manager = b'\x06'
    program_name = b'\x64'  # Rockwell KB# 23341
    wall_clock_time = b'\x8b'  # Micro800 CIP client messaging quick start
    tcpip = b'\xf5'
    ethernet_link = b'\xf6'
    modbus_serial_link = b'\x46'
    file_object = b'\x37'
