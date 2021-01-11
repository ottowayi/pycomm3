import pytest
from pycomm3 import LogixDriver
import os


PATH = os.environ['PLCPATH']


@pytest.fixture(scope='session', autouse=True)
def plc():
    with LogixDriver(PATH, init_program_tags=True) as plc_:
        yield plc_
