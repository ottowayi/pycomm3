from pycomm.ab_comm.clx import Driver as ClxDriver

from time import sleep


if __name__ == '__main__':

    c = ClxDriver(True, 'ClxDriver.log')

    print c['port']
    print c.__version__

    if c.open('172.16.2.161'):
        while 1:
            try:
                #if not c.is_connected():
                #    print "retry to open"
                #    #c.close()
                #    print "closed"
                #    c.open('172.16.2.161')

                print(c.read_tag(['ControlWord']))
                print(c.read_tag(['parts', 'ControlWord', 'Counts']))

                print(c.write_tag('Counts', -26, 'INT'))
                print(c.write_tag(('Counts', 26, 'INT')))
                print(c.write_tag([('Counts', 26, 'INT')]))
                print(c.write_tag([('Counts', -26, 'INT'), ('ControlWord', -30, 'DINT'), ('parts', 31, 'DINT')]))
                sleep(1)
            except Exception as e:
                err = c.get_status()
                c.close()
                print err
                pass

        # To read an array
        r_array = c.read_array("TotalCount", 1750)
        for tag in r_array:
            print (tag)

        c.close()
