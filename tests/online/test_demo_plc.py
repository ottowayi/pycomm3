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
