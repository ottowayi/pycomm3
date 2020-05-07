import datetime


def test_get_time(plc):
    time = plc.get_plc_time()
    assert time
    assert time.value['string'] == time.value['datetime'].strftime('%A, %B %d, %Y %I:%M:%S%p')


def test_set_time(plc):
    assert plc.set_plc_time()


