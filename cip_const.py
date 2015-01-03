COMMAND = {
    "nop": 0x00,
    "list_targets": 0x01,
    "list_services": 0x04,
    "list_identity": 0x63,
    "list_interfaces": 0x64,
    "register_session": 0x65,
    "unregister_session": 0x66,
    "send_rr_data": 0x6F,
    "send_unit_data": 0x70

}

STATUS = {
    0x0000: "Success",
    0x0001: "The sender issued an invalid or unsupported encapsulation command",
    0x0002: "Insufficient memory",
    0x0003: "Poorly formed or incorrect data in the data portion",
    0x0064: "An originator used an invalid session handle when sending an encapsulation message to the target",
    0x0065: "The target received a message of invalid length",
    0x0069: "Unsupported Protocol Version"
}

SERVICES = {
    "Read Tag": 0x45,
    "Read Tag Fragmented": 0x52,
    "Write Tag": 0x4d,
    "Write Tag Fragmented": 0x53,
    "Read Modify Write Tag": 0x4c,
    "Multiple Service Packet": 0x0a
}

SERVICE_STATUS = {
    0x04: "A syntax error was detected decoding the Request Path.",
    0x05: "Request Path destination unknown: Probably instance number is not present.",
    0x06: "Insufficient Packet Space: Not enough room in the response buffer for all the data.",
    0x10: "Device state conflict: See extended status",
    0x13: "Insufficient Request Data: Data too short for expected parameters.",
    0x26: "The Request Path Size received was shorter or longer than expected.",
    0xff: "General Error: See extended status."
}

SERVICE_EXTEND_STATUS = {
    0x45: {
        0x2105: "Access beyond end of the object."
    },
    0x52: {
        0x2105: "Number of Elements or Byte Offset is beyond the end of the requested tag."
    },
    0x4d: {
        0x2101: "Keyswitch Position: The requester is attempting to change force information in HARD RUN mode.",
        0x2105: "Number of Elements extends beyond the end of the requested tag.",
        0x2107: "Tag type used in the request does not match the target's tag data type.",
        0x2802: "Safety Status: The controller is in a state in which Safety Memory cannot be modified."
    },
    0x53: {
        0x2101: "Keyswitch Position: The requester is attempting to change force information in HARD RUN mode.",
        0x2104: "Offset is beyond end of the requested tag.",
        0x2105: "Offset plus Number of Elements extends beyond the end of the requested tag.",
        0x2107: "Data type used in the request does not match the target's tag data type.",
        0x2802: "Safety Status: The controller is in a state in which Safety Memory cannot be modified."
    },
    0x4c: {
        0x2101: "Keyswitch Position: The requester is attempting to change force information in HARD RUN mode.",
        0x2802: "Safety Status: The controller is in a state in which Safety Memory cannot be modified."
    }
}


HEADER_SIZE = 24