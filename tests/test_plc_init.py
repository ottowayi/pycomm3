from pycomm3 import LogixDriver
import os


PATH = os.environ['PLCPATH']


def test_connect_init_none():
    with LogixDriver(PATH, init_info=False, init_tags=False) as plc:
        assert plc.name is None
        assert not plc.info
        assert plc.connected
        assert plc._session != 0


def test_connect_init_info():
    with LogixDriver(PATH, init_info=True, init_tags=False) as plc:
        # assert plc.name == 'PLCA'
        assert plc.info['vendor'] == 'Rockwell Automation/Allen-Bradley'
        assert plc.info['keyswitch'] == 'REMOTE RUN'
        # assert plc.info['name'] == 'testing'
        # assert plc.name == 'testing'


def test_connect_init_tags():
    with LogixDriver(PATH, init_info=False, init_tags=True) as plc:
        assert len(plc.tags) > 0
        assert isinstance(plc.tags, dict)

