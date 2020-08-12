import datetime


def test_get_time(plc):
    time = plc.get_plc_time()
    assert time
    assert time.value['string'] == time.value['datetime'].strftime('%A, %B %d, %Y %I:%M:%S%p')


def test_set_time(plc):
    assert plc.set_plc_time()


def test_get_module_info(plc):
    info = plc.get_module_info(0)
    assert info
    assert info['vendor']
    assert info['product_code']
    assert f"{info['version_major']}.{info['version_minor']}" == info['revision']
    assert info['serial']

