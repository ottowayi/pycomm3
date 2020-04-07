from pycomm3 import LogixDriver


def write_single():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.write(('DINT2', 100_000_000))


def write_multiple():
    with LogixDriver('10.61.50.4/10') as plc:
        return plc.write(('REAL2', 25.2), ('STRING3', 'A test for writing to a string.'))
