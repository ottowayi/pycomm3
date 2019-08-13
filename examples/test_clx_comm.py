from pycomm3.clx import CLXDriver as ClxDriver
import logging

from time import sleep


if __name__ == '__main__':

    logging.basicConfig(
        filename="ClxDriver.log",
        format="%(levelname)-10s %(asctime)s %(message)s",
        level=logging.DEBUG
    )
    c = ClxDriver()

    print c['port']
    print c.__version__


    if c.open('172.16.2.161'):
        while 1:
            try:
                print(c.read_tag(['ControlWord']))
                print(c.read_tag(['parts', 'ControlWord', 'Counts']))

                print(c.write_tag('Counts', -26, 'INT'))
                print(c.write_tag(('Counts', 26, 'INT')))
                print(c.write_tag([('Counts', 26, 'INT')]))
                print(c.write_tag([('Counts', -26, 'INT'), ('ControlWord', -30, 'DINT'), ('parts', 31, 'DINT')]))
                sleep(1)
            except Exception as e:
                c.close()
                print e
                pass

        # To read an array
        r_array = c.read_array("TotalCount", 1750)
        for tag in r_array:
            print (tag)

        c.close()
