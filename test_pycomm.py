__author__ = 'agostino'


from ab_comm import ClxDriver
import logging


if __name__ == '__main__':
    c = ClxDriver()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    v = c.read_tag('Counts')
    print v
    if v is not None:
        c.write_tag('Counts', 23, 'INT')
    c.close()
    logging.shutdown()