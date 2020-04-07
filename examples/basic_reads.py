from pycomm3 import LogixDriver


def read_single():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('DINT1')


def read_multiple():
    tags = ['DINT1', 'SINT1', 'REAL1']
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read(*tags)


def read_array():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('DINT_ARY1{5}')


def read_array_slice():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('DINT_ARY1[50]{5}')


def read_strings():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('STRING1', 'STRING_ARY1[2]{2}')


def read_udt():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('SimpleUDT1_1')


def read_timer():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.read('TIMER1')

