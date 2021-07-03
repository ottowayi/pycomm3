DEMO_PLC_INFO = {'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type': 'Programmable Logic Controller',
                 'product_code': 89, 'serial': 'c00fa09b',
                 'product_name': '1769-L23E-QBFC1 LOGIX5323E-QBFC1', 'revision': {'major': 20, 'minor': 19},
                 'keyswitch': 'REMOTE RUN', 'name': 'pycomm3_demo',
                 'tasks': {'MAIN': {'instance_id': 16174}},
                 'modules': {'Local': {
                     'slots': {4: {'types': ['C']}, 3: {'types': ['O']}, 2: {'types': ['O']}, 1: {'types': ['I']}}}}}


def test_demo_plc(plc):
    assert 'status' in plc.info
    del plc.info['status']

    assert 'pycomm3' in plc.info['programs']
    del plc.info['programs']

    assert plc.info == DEMO_PLC_INFO


def test_get_time(plc):
    time = plc.get_plc_time()
    assert time
    assert time.value['string'] == time.value['datetime'].strftime('%A, %B %d, %Y %I:%M:%S%p')


def test_set_time(plc):
    assert plc.set_plc_time()


def test_discover():
    from pycomm3 import CIPDriver
    devices = CIPDriver.discover()

    expected = [
        {'encap_protocol_version': 1, 'ip_address': '192.168.1.237',
        'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type': 'Communications Adapter',
        'product_code': 185, 'revision': {'major': 2, 'minor': 7},

        'serial': '73015738', 'product_name': '1763-L16BWA B/7.00', 'state': 0},
       {'encap_protocol_version': 1, 'ip_address': '192.168.1.236',
        'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type':
        'Communications Adapter', 'product_code': 191, 'revision': {'major': 20, 'minor': 19},
        'serial': 'c01ebe90', 'product_name': '1769-L23E-QBFC1 Ethernet Port', 'state': 3},

       # {'encap_protocol_version': 1, 'ip_address': '192.168.1.125', 'vendor': 'Rockwell Software, Inc.',
       #  'product_type': 'Communications Adapter', 'product_code': 115, 'revision': {'major': 12, 'minor': 1},
       #   'serial': '21ac1903', 'product_name': 'DESKTOP-907P98D', 'state': 255}
    ]

    # status can change based on number of connections or other reasons
    # just check to make sure it has a value then remove it from the
    # rest of the device info
    # for device in devices:
    #     assert 'status' in device
    #     del device['status']
    #     assert device in expected
    for device in devices:
        assert 'ip_address' in device
        assert 'vendor' in device
        assert 'product_type' in device
        assert 'product_code' in device
        assert 'revision' in device


def test_tags_json_serialization(plc):
    import json
    assert isinstance(json.dumps(plc.tags_json), str)

