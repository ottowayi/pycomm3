__author__ = 'agostino'

from pycomm.ab_comm.slc import Driver as SlcDriver

if __name__ == '__main__':
    c = SlcDriver(True, 'delete_slc.log')
    if c.open('172.16.2.160'):
        print c.read_tag('O:0.0', 6)
        print c.read_tag('T4:2.PRE', 2)
        print c.read_tag('B3:0')
        print c.read_tag('F8:0')
        print c.read_tag('N7:0')
        print c.write_tag('N7:0', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        print c.write_tag('F8:1', 3.0)
        print c.write_tag('T4:2.PRE', 1000)
        #print c.write_tag('B3:0', 12)
        print c.read_tag('N7:0', 10)
        print c.read_tag('B3:0')
        print c.read_tag('F8:0', 2)
        #print c.read_tag('T4:2.PRE')
    c.close()
