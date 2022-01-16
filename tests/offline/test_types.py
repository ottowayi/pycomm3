from pycomm3 import n_bytes, BYTES, UINT, USINT, Struct
from pycomm3.custom_types import ModuleIdentityObject
from io import BytesIO


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


def test_n_bytes():
    assert n_bytes(10).encode(b'1234567890') == b'1234567890'
    assert n_bytes(10).decode(b'1234567890') == b'1234567890'
    assert n_bytes(1).encode(b'1234567890') == b'1'
    assert n_bytes(1).decode(b'1234567890') == b'1'

    stream = BytesIO(b'1234567890')
    assert n_bytes(4).decode(stream) == b'1234'
    assert stream.read() == b'567890'

    stream.seek(0)
    assert n_bytes(-1).decode(stream) == b'1234567890'
    assert not stream.read()


# TODO: a whole lot of tests

def test_byte_arrays():
    assert BYTES[...].encode(b'12345') == b'12345'
    assert BYTES[...].decode(b'12345') == b'12345'
    assert BYTES[3].encode(b'12345') == b'123'
    assert BYTES[3].decode(b'12345') == b'123'
    assert USINT[UINT].decode(b'\x02\x00\x01\x03') == [1, 3]
    assert BYTES[UINT].encode(b'12345') == b'12345'
    assert BYTES[UINT].decode(b'\x05\x0012345') == b'12345'
    # assert Struct(UINT('x'), BYTES[USINT]('data')).encode({'x': 0, 'data':''})
