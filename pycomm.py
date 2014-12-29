from eip import Eip
from time import sleep

if __name__ == '__main__':
    c = Eip()

    c.open('192.168.1.10')
    c.register_session()
    c.list_identity()
    c.list_interfaces()
    c.list_services()
    c.unregister_session()
    c.close()
