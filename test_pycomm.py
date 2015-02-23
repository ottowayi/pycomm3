__author__ = 'agostino'
from ab_comm import ClxDriver
from pycomm import setup_logging

import logging


if __name__ == '__main__':
    setup_logging()
    c = ClxDriver()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    print(c.read_tag(['parts', 'ControlWord', 'Counts']))
    print(c.read_tag(['parts']))
    print(c.read_tag('Counts'))
    c.write_tag('Counts', 25, 'INT')
    c.close()
    logging.shutdown()