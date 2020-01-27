import pytest
from pycomm3 import LogixDriver
import os


SLOT = int(os.environ['slot'])
IP_ADDR = os.environ['ip']


@pytest.fixture(scope='module', autouse=True)
def plc():
    with LogixDriver(IP_ADDR, slot=SLOT) as plc_:
        yield plc_
