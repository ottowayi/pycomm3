import pytest
from pycomm3 import LogixDriver, SLCDriver
import os


@pytest.fixture(scope="session", autouse=True)
def plc():
    with LogixDriver(os.environ["PLCPATH"]) as plc_:
        yield plc_


@pytest.fixture(scope="session", autouse=True)
def slc():
    with SLCDriver(os.environ["SLCPATH"]) as slc_:
        yield slc_
