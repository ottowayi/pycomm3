import pytest

from pycomm3 import PADDED_EPATH_LEN, LogicalSegment, LogicalSegmentType
from pycomm3.protocols.cip.protocol_base import CIPRequest
from pycomm3.protocols.cip.object_library import Identity, Port

get_attr_single_tests = [
    (Identity.serial_number, 1, "0E 03 20 01 24 01 30 06"),
    (Port.port_name, 2, "0E 03 20 F4 24 02 30 04"),
]


@pytest.mark.parametrize("attribute, instance, encoded", get_attr_single_tests)
def test_get_attr_single_requests(attribute, instance, encoded):
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
