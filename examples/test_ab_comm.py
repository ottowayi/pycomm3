import logging

from pycomm.ab_comm.clx import Driver as ClxDriver

logging.basicConfig(
    #filename="pycomm.log",
    level=logging.WARNING,
    format="%(levelname)-10s %(asctime)s %(message)s"
)

if __name__ == '__main__':

    c = ClxDriver()
    if c.open('192.168.1.10'):

        print(c.read_tag('Counts'))
        print(c.read_tag(['ControlWord']))
        print(c.read_tag(['parts', 'ControlWord', 'Counts']))

        print(c.write_tag(('Counts', 26, 'INT')))
        print(c.write_tag([('Counts', 26, 'INT')]))
        print(c.write_tag([('Counts', 26, 'INT'), ('ControlWord', 30, 'DINT'), ('parts', 31, 'DINT')]))

        c.close()
