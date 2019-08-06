import pythoncom
from .clx import CLXDriver

CLSID = '{7038d3a1-1ac4-4522-97d5-4c5a08a29906}'


class CLXDriverCOMServer(CLXDriver):
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
