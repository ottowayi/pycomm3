__author__ = 'agostino'
from ab_comm import ClxDriver
from pycomm import setup_logging

import logging


if __name__ == '__main__':
    setup_logging()
    c = ClxDriver()
    # c.open('192.168.1.10')
    c.open('172.16.20.100')
    # print(c.read_tag(['parts', 'ControlWord', 'Counts', 'pippo_1[39].rVal']))
    print(c.read_tag(['ControlWords']))
    # print(c.read_tag('Counts'))
    # print(c.write_tag([('Counts', 26, 'INT'), ('ControlWord', 26, 'DINT'), ('parts', 26, 'DINT')]))
    # print(c.write_tag('Counts', 26, 'INT'))
    # tags = c.get_tag_list()
    #if tags is not None:
    #    for tag in tags:
    #        print (tag)
    c.close()
    logging.shutdown()