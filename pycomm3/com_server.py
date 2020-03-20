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

raise NotImplementedError('COMServer implementation is incomplete')


import pythoncom
from pycomm3 import LogixDriver, Tag

CLSID = '{7038d3a1-1ac4-4522-97d5-4c5a08a29906}'


class COMTag(Tag):
    _public_attrs_ = ['name', 'value', 'type', 'error']
    _readonly_attrs_ = _public_attrs_


class LogixDriverCOMServer:
    _reg_clsctx_ = pythoncom.CLSCTX_LOCAL_SERVER
    _public_methods_ = ['open', 'close', 'read_tag', 'write', ] #'get_plc_info', 'get_plc_name', 'get_tag_list']
    _readonlu_attrs_ = []
    _public_attrs_ = []
    # _readonly_attrs_ = ['tags', 'info', 'name']
    # _public_attrs_ = ['path', 'large_packets', 'init_tags', 'init_program_tags' ] + _readonly_attrs_

    _reg_clsid_ = CLSID
    _reg_desc_ = 'Pycomm3 - Python Ethernet/IP ControlLogix Library COM Server'
    _reg_progid_ = 'Pycomm3.COMServer'

    def __init__(self):
        self.plc: LogixDriver = None

    def open(self, path, init_tags=True, init_program_tags=False, init_info=True):
        self.plc = LogixDriver(path, init_tags=init_tags, init_program_tags=init_program_tags, init_info=init_info)
        self.plc.open()

    def close(self):
        self.plc.close()

    def read(self, tag):
        result = self.plc.read(tag)
        return result.value if result else None

    def write(self, *tag_values):
        return self.plc.write(*tag_values)


def register_COM_server():
    import sys
    if '--register' in sys.argv or '--unregister' in sys.argv:
        import win32com.server.register
        win32com.server.register.UseCommandLine(LogixDriverCOMServer)


if __name__ == '__main__':
    register_COM_server()
