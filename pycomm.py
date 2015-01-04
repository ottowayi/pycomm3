from eip import Eip
from cip import Cip
from cip_const import *



if __name__ == '__main__':
    c = Cip()
    c.open('192.168.1.10')
    # c.register_session()
    # c.list_identity()
    # c.list_interfaces()
    # c.send_rr_data("TotalCount")
    # c.list_services()
    # c.list_identity()
    c.read_tag('TotalCount')
    # c.read_tag('ctrl_aComplex[0].bVal')
    c.close()

