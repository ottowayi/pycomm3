import pytest
from pycomm3 import LogixDriver, SLCDriver
import os


PATH = os.environ['PLCPATH']
SLC_PATH = os.environ['SLCPATH']


@pytest.fixture(scope='session', autouse=True)
def plc():
    with LogixDriver(PATH) as plc_:
        yield plc_


@pytest.fixture(scope='session', autouse=True)
def slc():
    with SLCDriver(SLC_PATH) as slc_:
        yield slc_
