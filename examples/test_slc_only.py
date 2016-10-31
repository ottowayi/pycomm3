__author__ = 'agostino'

from pycomm.ab_comm.slc import Driver as SlcDriver
import logging

if __name__ == '__main__':
    logging.basicConfig(
        filename="SlcDriver.log",
        format="%(levelname)-10s %(asctime)s %(message)s",
        level=logging.DEBUG
    )
    c = SlcDriver()
    if c.open('192.168.1.15'):

        while 1:
            try:
                print c.read_tag('S:1/5')
                print c.read_tag('S:60', 2)

                print c.write_tag('N7:0', [-30, 32767, -32767])
                print c.write_tag('N7:0', 21)
                print c.read_tag('N7:0', 10)

                print c.write_tag('F8:0', [3.1, 4.95, -32.89])
                print c.write_tag('F8:0', 21)
                print c.read_tag('F8:0', 3)

                print c.write_tag('B3:100', [23, -1, 4, 9])
                print c.write_tag('B3:100', 21)
                print c.read_tag('B3:100', 4)

                print c.write_tag('T4:3.PRE', 431)
                print c.read_tag('T4:3.PRE')
                print c.write_tag('C5:0.PRE', 501)
                print c.read_tag('C5:0.PRE')
                print c.write_tag('T4:3.ACC', 432)
                print c.read_tag('T4:3.ACC')
                print c.write_tag('C5:0.ACC', 502)
                print c.read_tag('C5:0.ACC')

                c.write_tag('T4:2.EN', 0)
                c.write_tag('T4:2.TT', 0)
                c.write_tag('T4:2.DN', 0)
                print c.read_tag('T4:2.EN', 1)
                print c.read_tag('T4:2.TT', 1)
                print c.read_tag('T4:2.DN',)

                c.write_tag('C5:0.CU', 1)
                c.write_tag('C5:0.CD', 0)
                c.write_tag('C5:0.DN', 1)
                c.write_tag('C5:0.OV', 0)
                c.write_tag('C5:0.UN', 1)
                c.write_tag('C5:0.UA', 0)
                print c.read_tag('C5:0.CU')
                print c.read_tag('C5:0.CD')
                print c.read_tag('C5:0.DN')
                print c.read_tag('C5:0.OV')
                print c.read_tag('C5:0.UN')
                print c.read_tag('C5:0.UA')

                c.write_tag('B3:100', 1)
                print c.read_tag('B3:100')

                c.write_tag('B3/3955', 1)
                print c.read_tag('B3/3955')

                c.write_tag('N7:0/2', 1)
                print c.read_tag('N7:0/2')

                print c.write_tag('O:0.0/4', 1)
                print c.read_tag('O:0.0/4')
            except Exception as e:
                print e
                pass
    c.close()
