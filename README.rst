pycomm
======
pycomm is a package that includes a collection of modules used to communicate with PLCs.
At the moment the first module in the package is ab_comm.

Test
~~~~
The library is currently test on Python 2.6, 2.7.

.. image:: https://travis-ci.org/ruscito/pycomm.svg?branch=master
    :target: https://travis-ci.org/ruscito/pycomm

Setup
~~~~~
The package can be installed from

GitHub:
::

    git clone https://github.com/ruscito/pycomm.git
    cd pycomm
    sudo python setup.py install


PyPi:
::

    pip install pycomm

ab_comm
~~~~~~~
ab_comm is a module that contains a set of classes used to interface Rockwell PLCs using Ethernet/IP protocol.
The "clx" class can be used to communicate with Compactlogix, Controllogix PLCs
The "slc" can be used to communicate with Micrologix or SLC PLCs

I tried to followCIP specifications volume 1 and 2 as well as `Rockwell Automation Publication 1756-PM020-EN-P - November 2012`_ .

.. _Rockwell Automation Publication 1756-PM020-EN-P - November 2012: http://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf

See the following snippet for communication with a Controllogix PLC:

::

    from pycomm.ab_comm.clx import Driver as ClxDriver
    import logging


    if __name__ == '__main__':
        logging.basicConfig(
            filename="ClxDriver.log",
            format="%(levelname)-10s %(asctime)s %(message)s",
            level=logging.DEBUG
        )
        c = ClxDriver()

        if c.open('172.16.2.161'):

            print(c.read_tag(['ControlWord']))
            print(c.read_tag(['parts', 'ControlWord', 'Counts']))

            print(c.write_tag('Counts', -26, 'INT'))
            print(c.write_tag(('Counts', 26, 'INT')))
            print(c.write_tag([('Counts', 26, 'INT')]))
            print(c.write_tag([('Counts', -26, 'INT'), ('ControlWord', -30, 'DINT'), ('parts', 31, 'DINT')]))

            # To read an array
            r_array = c.read_array("TotalCount", 1750)
            for tag in r_array:
                print (tag)


            # To read string
            c.write_string('TEMP_STRING', 'my_value')
            c.read_string('TEMP_STRING')

            # reset tha array to all 0
            w_array = []
            for i in xrange(1750):
                w_array.append(0)
            c.write_array("TotalCount", w_array, "SINT")

            c.close()




See the following snippet for communication with a  Micrologix PLC:


::

    from pycomm.ab_comm.slc import Driver as SlcDriver
    import logging


    if __name__ == '__main__':
        logging.basicConfig(
            filename="SlcDriver.log",
            format="%(levelname)-10s %(asctime)s %(message)s",
            level=logging.DEBUG
        )
        c = SlcDriver()
        if c.open('172.16.2.160'):

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

        c.close()


The Future
~~~~~~~~~~
This package is under development.
The modules _ab_comm.clx_ and _ab_comm.slc_ are completed at  moment but other drivers will be added in the future.

Thanks
~~~~~~
Thanks to patrickjmcd_ for the help with the Direct Connections and thanks in advance to anyone for feedback and suggestions.

.. _patrickjmcd: https://github.com/patrickjmcd

License
~~~~~~~
pycomm is distributed under the MIT License