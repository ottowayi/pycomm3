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
        assert plc.info['name'] == plc.name
        assert plc.info['vendor'] == 'Rockwell Automation/Allen-Bradley'
        assert plc.info['keyswitch'] == 'REMOTE RUN'
        assert 'modules' not in plc.info
        assert 'tasks' not in plc.info
        assert 'programs' not in plc.info


def test_connect_init_tags():
    with LogixDriver(PATH) as plc:
        assert len(plc.tags) > 0
        assert isinstance(plc.tags, dict)
        assert 'Pycomm3_Testing' in plc.info['programs']

        assert plc.tags == {tag['tag_name']: tag for tag in plc.get_tag_list()}

