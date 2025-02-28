from pycomm3.protocols.cip.cip_object import CIPObject, GeneralStatusCodes
from pycomm3.protocols.cip.object_library.connection_manager import ConnectionManager, ConnMgrExtStatusCodesConnFailure
from pycomm3.data_types import BYTES, UINT
import pytest
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class StatusMsgTest:
    cip_object: type[CIPObject] = CIPObject
    service: int = 0x00
    status: int = 0x00
    ext_status: Sequence[int] = field(default_factory=lambda: [0x00])
    extra_data: BYTES = BYTES(b"")


status_msg_tests = [
    # any object, any service, success
    (StatusMsgTest(), (GeneralStatusCodes.success.description, None)),
    # specific object, any service, success
    (StatusMsgTest(ConnectionManager), (GeneralStatusCodes.success.description, None)),
    (  # specific object, any service, known ext, no extras
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[ConnMgrExtStatusCodesConnFailure.connection_missing],
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            ConnMgrExtStatusCodesConnFailure.connection_missing.description,
        ),
    ),
    (  # specific object, any service, known ext, unused extras
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[ConnMgrExtStatusCodesConnFailure.connection_missing, UINT(69)],
            extra_data=BYTES(b"nice."),
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            "Target connection not found: Addl status words=[UINT(69)], Extra data=BYTES[...](b'nice.')",
        ),
    ),
]


@pytest.mark.parametrize("inputs, expected", status_msg_tests)
def test_get_status_messages(inputs, expected):
    msgs = inputs.cip_object.get_status_messages(inputs.service, inputs.status, inputs.ext_status, inputs.extra_data)
    assert msgs == expected
