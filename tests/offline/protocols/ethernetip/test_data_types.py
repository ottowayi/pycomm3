from dataclasses import asdict
import pytest
from pycomm3.data_types import UINT
from pycomm3.protocols.ethernetip.data_types import (
    EtherNetIPHeader,
    CPFItem,
    ConnectedAddress,
    NullAddress,
    UnconnectedData,
    Sockaddr,
    CommonPacketFormat,
)


EIP_HEADER_TESTS = [
    (
        {
            "command": 1,
            "length": 2,
            "session": 3,
            "status": 4,
            "context": b"\x05" * 8,
            "options": 6,
        },
        b"\x01\x00\x02\x00\x03\x00\x00\x00\x04\x00\x00\x00\x05\x05\x05\x05\x05\x05\x05\x05\x06\x00\x00\x00",
    ),
]


@pytest.mark.parametrize("decoded, encoded", EIP_HEADER_TESTS)
def test_eip_header(decoded, encoded):
    assert bytes(EtherNetIPHeader(**decoded)) == encoded
    assert EtherNetIPHeader.decode(encoded) == EtherNetIPHeader(**decoded)
    assert asdict(EtherNetIPHeader(**decoded)) == decoded


def test_cpf_item():
    cpf = CPFItem(1, 0)
    a = ConnectedAddress(100)
    assert bytes(a) == b"\xa1\x00\x04\x00d\x00\x00\x00"

    uc = UnconnectedData(b"123456")
    assert bytes(uc) == b"\xb2\x00\x06\x00123456"
    assert Sockaddr.size == 16
    c = CommonPacketFormat(a, uc)
    assert bytes(c) == b"\x02\x00\xa1\x00\x04\x00d\x00\x00\x00\xb2\x00\x06\x00123456"
    assert CommonPacketFormat.decode(b"\x02\x00\xa1\x00\x04\x00d\x00\x00\x00\xb2\x00\x06\x00123456") == c


# COMMON_PACKET_ITEM_TESTS = [
#     (
#         NullAddressItem,
#         b"\x00\x00" b"\x00\x00" b"",
#         None,
#     ),
#     (ConnectedAddressItem, b"\xa1\x00" b"\x04\x00" b"\x01\x00\x00\x00", {"connection_id": 1}),
#     (
#         SequencedAddressItem,
#         b"\x02\x80" b"\x08\x00" b"\x01\x00\x00\x00\x02\x00\x00\x00",
#         {"connection_id": 1, "sequence_number": 2},
#     ),
# ]
#
#
# @pytest.mark.parametrize("item_type, encoded, data", COMMON_PACKET_ITEM_TESTS)
# def test_common_packet_items(item_type, encoded, data):
#     assert item_type.decode(encoded) == {"type_id": item_type.type_id, "data_len": len(encoded) - 4, "data": data}
#     assert item_type.encode(data) == encoded
