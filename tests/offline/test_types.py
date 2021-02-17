from pycomm3.custom_types import ModuleIdentityObject


PLC_INFOS = [
    {'vendor': 'Honeywell Inc.',
     'product_type': 'Limit Switch',
     'product_code': 0x03,
     'revision': {'major': 12, 'minor': 34},
     'status': b'\x01\x02',
     'serial': 'c00fa09b',
     'product_name': 'Test-Product-1'},


]


def test_info_encode_decode():
    encoded = ModuleIdentityObject.encode(PLC_INFOS[0])
    assert encoded
    decoded = ModuleIdentityObject.decode(encoded)
    assert decoded == PLC_INFOS[0]


# TODO: a whole lot of tests
