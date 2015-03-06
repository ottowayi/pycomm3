pycomm
======
pycomm is a package that includes a collection of modules used to communicate with PLCs.
At the moment the first module in the package is ab_comm. 

Test
----
The library is currently test on Python 2.6, 2.7, 3.2, 3.3 and 3.4.

[![Build Status](https://travis-ci.org/ruscito/pycomm.svg?branch=master)](https://travis-ci.org/ruscito/pycomm)

Setup
-------
The package can be installed from GitHub:

::
    git clone https://github.com/ruscito/pycomm.git
    cd pycomm
    sudo python setup.py install
    
    
    
ab_comm
-------
ab_comm is a module that contains a set of classes used to interface Rockwell PLCs using Ethernet/IP protocol.
The module ClxDriver can be used to communicate with Compactlogix, Controllogix and Micrologix PLCs. I tried to follow 
CIP specifications volume 1 and 2 as well as [Rockwell Automation Publication 1756-PM020-EN-P - November 2012] 
(http://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm020_-en-p.pdf). 

See the following snippet for usage information:
 
::    
    
    from pycomm.ab_comm.clx import Driver as ClxDriver
       
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



The Future
----------
This package is under development. The module _ab_comm.clx_ is not completed yet, but stable enough to read and write
multiple atomic or structured tags. Other drivers will be added in the future.


Thanks
------
Couple of people and projects on the internet inspired _ab_comm.clx_ driver. Among this I would like to thank mr 
_Lynn Lins_ for providing helpful suggestions and code snippets, and [tuxeip project](https://code.google.com/p/tuxeip/).
 
License
-------
pycomm is distributed under the MIT License
  