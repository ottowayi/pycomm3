from cip import Cip
import logging
import ab_cip_const

if __name__ == '__main__':
    print (ab_cip_const.EXTEND_CODES[5][1])
    c = Cip()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    v = c.read_tag('Counts')
    print v
    if v is not None:
        c.write_tag('Counts', 23, 'DINT')
    c.close()
    logging.shutdown()

