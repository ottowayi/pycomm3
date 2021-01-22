DEMO_PLC_INFO = {'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type': 'Programmable Logic Controller',
                 'product_code': 89, 'version_major': 20, 'version_minor': 19, 'serial': 'c00fa09b',
                 'device_type': '1769-L23E-QBFC1 LOGIX5323E-QBFC1', 'revision': '20.19', 'keyswitch': 'REMOTE RUN',
                 'name': 'pycomm3_demo',
                 'programs': {'MainProgram': {'instance_id': 26297, 'routines': ['MainRoutine']},
                              'pycomm3': {'instance_id': 56519,
                                          'routines': ['global_reads', 'program_writes', 'global_writes', 'MAIN',
                                                       'program_reads']}}, 'tasks': {'MAIN': {'instance_id': 16174}},
                 'modules': {'Local': {
                     'slots': {4: {'types': ['C']}, 3: {'types': ['O']}, 2: {'types': ['O']}, 1: {'types': ['I']}}}}}


def test_demo_plc(plc):
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

    # status can change based on number of connections or other reasons
    # just check to make sure it has a value then remove it from the
    # rest of the device info
    assert devices[0]['status']
    del devices[0]['status']

    assert devices == [{'item_type_code': 12, 'item_length': 63, 'encap_protocol_version': 1,
                        'ip_address': '192.168.1.236', 'vendor_id': 1, 'device_type': 12, 'product_code': 191,
                        'revision_major': 20, 'revision_minor': 19, 'serial_number': 3223240336,
                        'product_name': '1769-L23E-QBFC1 Ethernet Port', 'state': 3}]
