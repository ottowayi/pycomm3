import pytest

from pycomm3 import PADDED_EPATH_LEN, LogicalSegment, LogicalSegmentType, BYTES
from pycomm3.protocols.cip.protocol_base import CIPRequest
from pycomm3.protocols.cip.object_library import Identity, Port, ConnectionManager
from tests.offline.protocols.cip.test_cip_object import status_msg_tests

get_attr_single_tests = [
    (Identity.serial_number, 1, "0E 03 20 01 24 01 30 06", 0xDEADBEEF, "8E 00 00 00 EF BE AD DE"),
    (Port.port_name, 2, "0E 03 20 F4 24 02 30 04", "A", "8E 00 00 00 01 41"),
]


@pytest.mark.parametrize("attribute, instance, encoded, response, encoded_response", get_attr_single_tests)
def test_get_attr_single_requests(attribute, instance, encoded, response, encoded_response):
    request: CIPRequest = attribute.object.get_attribute_single(attribute=attribute, instance=instance)  # type: ignore
    assert bytes(request.message) == bytes.fromhex(encoded)
    assert request.message.service == attribute.object.get_attribute_single.__cip_service_id__
    assert not request.message.data
    assert request.message.path == PADDED_EPATH_LEN(
        [
            LogicalSegment(LogicalSegmentType.type_class_id, attribute.object.class_code),
            LogicalSegment(LogicalSegmentType.type_instance_id, instance),
            LogicalSegment(LogicalSegmentType.type_attribute_id, attribute.id),
        ]
    )
    assert request.response_parser.response_type is attribute.data_type

    _enc_resp = BYTES(bytes.fromhex(encoded_response))
    resp = request.response_parser.parse(_enc_resp, request)
    assert resp.data == response
    assert (
        resp.message.request_service
        == request.message.service
        == attribute.object.get_attribute_single.__cip_service_id__
    )


status_msg_tests = [
    (Port.get_attributes_all(), "81 00 08 00", "Service not supported"),
    (
        ConnectionManager.forward_open(BYTES(b"")),
        "D4 00 01 02 09 01 4F 01 00 00 09 00 04 20 00 69 FF 00",
        "Connection failure(0x01): (0x0109): ext_status_words=[UINT(335)], extra_data=ForwardOpenFailedResponse(connection_serial=UINT(0), originator_vendor_id=UINT(9), originator_serial=UDINT(1761615876), remaining_path_size=USINT(255), _reserved=USINT(0))",
    ),
]


@pytest.mark.parametrize("_request, encoded, status_message", status_msg_tests)
def test_response_messages(_request, encoded, status_message):
    resp = _request.response_parser.parse(bytes.fromhex(encoded), _request)
    assert resp.status_message == status_message
