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


import pythoncom
from .clx import LogixDriver

CLSID = '{7038d3a1-1ac4-4522-97d5-4c5a08a29906}'


class LogixDriverCOMServer(LogixDriver):
    _reg_clsctx_ = pythoncom.CLSCTX_LOCAL_SERVER
    _public_methods_ = ['open', 'close', 'read_tag', 'write_tag', 'read_string', 'write_string',
                        'read_array', 'write_array', 'get_plc_info', 'get_plc_name', 'get_tag_list']
    _readonly_attrs_ = ['tags', 'info', 'description']
    _public_attrs_ = ['ip_address', 'slot', 'large_packets', ] + _readonly_attrs_

    _reg_clsid_ = CLSID
    _reg_desc_ = 'Pycomm3 - Python Ethernet/IP ControlLogix Library COM Server'
    _reg_progid_ = 'Pycomm3.COMServer'

    def __init__(self):
        super().__init__(ip_address="0.0.0.0", init_info=False, init_tags=False)

    @property
    def ip_address(self):
        return self.attribs.get('ip address')

    @ip_address.setter
    def ip_address(self, value):
        self.attribs['ip address'] = value

    @property
    def slot(self):
        return self.attribs.get('cpu slot')

    @slot.setter
    def slot(self, value):
        self.attribs['cpu slot'] = value

    @property
    def large_packets(self):
        return self['extended forward open']

    @large_packets.setter
    def large_packets(self, value):
        self['extended forward open'] = value
