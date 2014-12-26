from eip import Eip
from time import sleep

if __name__ == '__main__':
    c = Eip()

    c.open('192.168.1.10')
    c.register_session()
    c.list_identity()
    run = True
    while run:
        try:
            c.nop()
            sleep(1)
        except (KeyboardInterrupt, SystemExit):
            run = False
    c.close()
