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
    "Read Tag fragmented": 0x52,
    "Write Tag": 0x4d,
    "Write Data Fragmented": 0x53,
    "Read Modify Write Tag": 0x4c
}

MR_GENERAL_STATUS = {
    0x0000: "Success",
    0x0001: "Ext error code",
    0x0002: "Resource unavailable",
    0x0003: "Invalid parameters value",
    0x0004: "Path segment error",
    0x0005: "Path destination unknow",
    0x0006: "Partial transferred",
    0x0007: "Connection lost",
    0x0008: "Service not supported",
    0x0009: "Invalid attribute value",
    0x000A: "Attribute list error",
    0x000B: "Already in requested mode/state",
    0x000C: "Object state conflict",
    0x000D: "Object already exist",
    0x000E: "Attribute not settable",
    0x000F: "Privilege violation",
    0x0010: "Device state conflict",
    0x0011: "Reply data too large",
    0x0012: "Fragmentation of a primitive value",
    0x0013: "Not enough data",
    0x0014: "Attribute not supported",
    0x0015: "Too much data",
    0x0016: "Object does not exist",
    0x0017: "Service fragmentation sequence not in progress",
    0x0018: "No stored attribute data",
    0x0019: "Store operation failure",
    0x001A: "Routing failure,request packet too large",
    0x001B: "Routing failure,response packet too large",
    0x001C: "Missing attribute list entry data",
    0x001D: "Invalid attribute value list",
    0x001E: "Embedded service error",
    0x001F: "Vendor specific",
    0x0020: "Invalid parameter",
    0x0021: "Write once value or medium already written",
    0x0022: "Invalid reply received",
    0x0025: "Key failure in path",
    0x0026: "Path size invalid",
    0x0027: "Unexpected attribute in list",
    0x0028: "Invalid member ID",
    0x0029: "Member not settable",
    0x002A: "Group 2 only server general failure"
}

MR_EXTEND_STATUS = {
    0x0100: "Connection in use or Duplicate Forward Open",
    0x0103: "Transport Class and Trigger combination not supported",
    0x0106: "Ownership conflict",
    0x0107: "Connection not found at target application",
    0x0108: "Invalid session type",
    0x0109: "Invalid session size",
    0x0110: "Device not configured",
    0x0111: "RPI not supported",
    0x0113: "Connection manager cannot support any more connections",
    0x0114: "Vendor Id or product code in the key segment did not match the device",
    0x0115: "Product type in the key segment did not match the device",
    0x0116: "Major or minor revision information in the key segment did not match the device",
    0x0117: "Invalid session point",
    0x0118: "Invalid configuration format",
    0x0119: "Connection request fails since there is no controlling session currently open"
}


HEADER_SIZE = 24