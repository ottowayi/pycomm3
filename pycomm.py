from ab_comm import ClxDriver
import logging
import cip_const

if __name__ == '__main__':
    print (cip_const.EXTEND_CODES[5][1])
    c = ClxDriver()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    v = c.read_tag('Counts')
    print v
    if v is not None:
        c.write_tag('Counts', 23, 'INT')
    c.close()
    logging.shutdown()

