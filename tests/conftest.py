import pytest
from pycomm3 import LogixDriver2
import os


SLOT = int(os.environ['slot'])
IP_ADDR = os.environ['ip']


@pytest.fixture(scope='module', autouse=True)
def plc():
    with LogixDriver2(IP_ADDR, slot=SLOT) as plc_:
        yield plc_
