from pycomm3.protocols.cip.cip_object import CIPObject, GeneralStatusCodes
from pycomm3.protocols.cip.object_library.connection_manager import ConnectionManager, ConnMgrExtStatusCodesConnFailure
from pycomm3.data_types import BYTES, UINT, UDINT
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
    (StatusMsgTest(), (GeneralStatusCodes.success.description, "(0x0000)")),
    # specific object, any service, success
    (StatusMsgTest(ConnectionManager), (GeneralStatusCodes.success.description, "(0x0000)")),
    (  # specific object, any service, ext msg, no extras
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[ConnMgrExtStatusCodesConnFailure.connection_missing],
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            "Target connection not found (0x0107)",
        ),
    ),
    (  # specific object, any service, ext msg, unused extras
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[ConnMgrExtStatusCodesConnFailure.connection_missing, UINT(69)],
            extra_data=BYTES(b"nice."),
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            "Target connection not found (0x0107): ext_status_words=[UINT(69)], extra_data=BYTES[...](b'nice.')",
        ),
    ),
    (  # specific object, any service, no ext msg, with extras
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[UINT(69), UINT(69)],
            extra_data=BYTES(b"nice."),
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            "(0x0045): ext_status_words=[UINT(69)], extra_data=BYTES[...](b'nice.')",
        ),
    ),
    (  # specific object, any service, known ext, with ext addl
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[ConnMgrExtStatusCodesConnFailure.invalid_connection_size, UINT(500)],
        ),
        (
            GeneralStatusCodes.connection_failure.description,
            "Requested connection size not supported by target/router (0x0109): max_supported_size=500",
        ),
    ),
    (  # specific object, any service, no ext, with ext addl
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.connection_failure,
            ext_status=[],
            extra_data=BYTES(b"blah blah blah blahhhhhhhhhhhhh"),
        ),
        (GeneralStatusCodes.connection_failure.description, None),
    ),
    # a few custom message handlers
    (
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.object_state_conflict,
            ext_status=[1],
        ),
        (
            GeneralStatusCodes.object_state_conflict.description,
            "(0x0001): state=0x0001",
        ),
    ),
    (
        StatusMsgTest(
            cip_object=ConnectionManager,
            status=GeneralStatusCodes.object_state_conflict,
            ext_status=[UDINT(0x42069)],  # udint not in spec, but testing formatting of it
        ),
        (
            GeneralStatusCodes.object_state_conflict.description,
            "(0x42069): state=0x42069",
        ),
    ),
]


@pytest.mark.parametrize("inputs, expected", status_msg_tests)
def test_get_status_messages(inputs, expected):
    msgs = inputs.cip_object.get_status_messages(inputs.service, inputs.status, inputs.ext_status, inputs.extra_data)
    assert msgs == expected
