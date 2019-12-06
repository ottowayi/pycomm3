from pycomm3 import LogixDriver
import os
from math import isclose

SLOT = int(os.environ['slot'])
IP_ADDR = os.environ['ip']

atomic_tests = [
        # tag name, value, error, type
        ('bool_1', False, 'BOOL'),
        ('bool_2', True, 'BOOL'),
        ('dint_1', -2_147_483_648, 'DINT'),
        ('dint_2', 2_147_483_647, 'DINT'),
        ('dint_3', 0, 'DINT'),
        ('int_1', -32_768, 'INT'),
        ('int_2', 32_767, 'INT'),
        ('int_3', 0, 'INT'),
        ('sint_1', -128, 'SINT'),
        ('sint_2', 127, 'SINT'),
        ('sint_3', 0, 'SINT'),
        ('real_1', 1234.5678, 'REAL'),
        ('real_2', 0.00123, 'REAL'),
        ('real_3', 0, 'REAL'),
        ('doesnt_exist', None, None)
    ]


def _run_test_single_reads(init_tags, large_packets):
    with LogixDriver(IP_ADDR, slot=SLOT, init_tags=init_tags, init_info=True, large_packets=large_packets) as plc:
        for name, value, type in atomic_tests:
            tag = plc.read_tag(name)
            assert tag.tag == name, f'{name} - tag'
            if isinstance(value, float):
                assert isclose(tag.value, value, rel_tol=1e-4)
            else:
                assert tag.value == value, f'{name} - value'
            assert tag.type == type, f'{name} - type'
            if value is None:
                assert tag.error, f'{name} - error'
                assert not tag, f'{name} - __bool__'
            else:
                assert tag, f'{name} - __bool__'
                assert tag.error is None, f'{name} - error'


def _run_test_multi_reads(init_tags, large_packets, tests=None):
    if tests is None:
        tests = atomic_tests

    with LogixDriver(IP_ADDR, slot=SLOT, init_tags=init_tags, init_info=True, large_packets=large_packets) as plc:
        tags = plc.read_tag(test[0] for test in tests)
        assert len(tests) == len(tags), 'returns as many tags as read'

        for tag, (name, value, typ) in zip(tags, tests):
            assert tag.tag == name, f'{name} - tag'
            if isinstance(value, float):
                assert isclose(tag.value, value, rel_tol=1e-4)
            else:
                assert tag.value == value, f'{name} - value'
            assert tag.type == typ, f'{name} - type'
            if value is None:
                assert not tag, f'{name} - __bool__'
                assert tag.error, f'{name} - error'
            else:
                assert tag, f'{name} - __bool__'
                assert tag.error is None, f'{name} - error'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  single reads
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def test_single_atomic_reads_symbolic_names_standard_packets():
    _run_test_single_reads(init_tags=False, large_packets=False)


def test_single_atomic_reads_symbolic_ids_standard_packets():
    _run_test_single_reads(init_tags=True, large_packets=False)


def test_single_atomic_reads_symbolic_names_large_packets():
    _run_test_single_reads(init_tags=False, large_packets=True)


def test_single_atomic_reads_symbolic_ids_large_packets():
    _run_test_single_reads(init_tags=True, large_packets=False)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  multi reads
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def test_multi_atomic_reads_symbolic_names_standard_packets():
    _run_test_multi_reads(init_tags=False, large_packets=False)


def test_multi_atomic_reads_symbolic_ids_standard_packets():
    _run_test_multi_reads(init_tags=True, large_packets=False)


def test_multi_atomic_reads_symbolic_names_large_packets():
    _run_test_multi_reads(init_tags=False, large_packets=True)


def test_multi_atomic_reads_symbolic_ids_large_packets():
    _run_test_multi_reads(init_tags=True, large_packets=True)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  multi-packet multi reads
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def test_multi_atomic_reads_symbolic_names_standard_packets_multi_request():
    _run_test_multi_reads(init_tags=False, large_packets=False, tests=atomic_tests*10)


def test_multi_atomic_reads_symbolic_ids_standard_packets_multi_request():
    _run_test_multi_reads(init_tags=True, large_packets=False, tests=atomic_tests*10)


def test_multi_atomic_reads_symbolic_names_large_packets_multi_request():
    _run_test_multi_reads(init_tags=False, large_packets=True, tests=atomic_tests*10)


def test_multi_atomic_reads_symbolic_ids_large_packets_multi_request():
    _run_test_multi_reads(init_tags=True, large_packets=True, tests=atomic_tests*10)
