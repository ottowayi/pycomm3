# -*- coding: utf-8 -*-
#
# cip_const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
#
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

ELEMENT_ID = {
    "8-bit": '\x28',
    "16-bit": '\x29',
    "32-bit": '\x2a'
}

CLASS_ID = {
    "8-bit": '\x20',
    "16-bit": '\x21',
}

INSTANCE_ID = {
    "8-bit": '\x24',
    "16-bit": '\x25'
}

ATTRIBUTE_ID = {
    "8-bit": '\x30',
    "16-bit": '\x31'
}

# Path are combined as:
# CLASS_ID + PATHS
# For example PCCC path is CLASS_ID["8-bit"]+PATH["PCCC"] -> 0x20, 0x67, 0x24, 0x01.
PATH = {
    'Connection Manager': '\x06\x24\x01',
    'Router': '\x02\x24\x01',
    'Backplane Data Type': '\x66\x24\x01',
    'PCCC': '\x67\x24\x01',
    'DHCP Channel A': '\xa6\x24\x01\x01\x2c\x01',
    'DHCP Channel B': '\xa6\x24\x01\x02\x2c\x01'
}

ENCAPSULATION_COMMAND = {  # Volume 2: 2-3.2 Command Field UINT 2 byte
    "nop": '\x00\x00',
    "list_targets": '\x01\x00',
    "list_services": '\x04\x00',
    "list_identity": '\x63\x00',
    "list_interfaces": '\x64\x00',
    "register_session": '\x65\x00',
    "unregister_session": '\x66\x00',
    "send_rr_data": '\x6F\x00',
    "send_unit_data": '\x70\x00'
}

"""
When a tag is created, an instance of the Symbol Object (Class ID 0x6B) is created
inside the controller.

When a UDT is created, an instance of the Template object (Class ID 0x6C) is
created to hold information about the structure makeup.
"""
CLASS_CODE = {
    "Message Router": '\x02',  # Volume 1: 5-1
    "Symbol Object": '\x6b',
    "Template Object": '\x6c',
    "Connection Manager": '\x06'  # Volume 1: 3-5
}

CONNECTION_MANAGER_INSTANCE = {
    'Open Request': '\x01',
    'Open Format Rejected': '\x02',
    'Open Resource  Rejected': '\x03',
    'Open Other Rejected': '\x04',
    'Close Request': '\x05',
    'Close Format Request': '\x06',
    'Close Other Request': '\x07',
    'Connection Timeout': '\x08'
}

TAG_SERVICES_REQUEST = {
    "Read Tag": 0x4c,
    "Read Tag Fragmented": 0x52,
    "Write Tag": 0x4d,
    "Write Tag Fragmented": 0x53,
    "Read Modify Write Tag": 0x4e,
    "Multiple Service Packet": 0x0a,
    "Get Instance Attributes List": 0x55,
    "Get Attributes": 0x03,
    "Read Template": 0x4c,
}

TAG_SERVICES_REPLY = {
    0xcc: "Read Tag",
    0xd2: "Read Tag Fragmented",
    0xcd: "Write Tag",
    0xd3: "Write Tag Fragmented",
    0xce: "Read Modify Write Tag",
    0x8a: "Multiple Service Packet",
    0xd5: "Get Instance Attributes List",
    0x83: "Get Attributes",
    0xcc: "Read Template"
}


I_TAG_SERVICES_REPLY = {
    "Read Tag": 0xcc,
    "Read Tag Fragmented": 0xd2,
    "Write Tag": 0xcd,
    "Write Tag Fragmented": 0xd3,
    "Read Modify Write Tag": 0xce,
    "Multiple Service Packet": 0x8a,
    "Get Instance Attributes List": 0xd5,
    "Get Attributes": 0x83,
    "Read Template": 0xcc
}


"""
EtherNet/IP Encapsulation Error Codes

Standard CIP Encapsulation Error returned in the cip message header
"""
STATUS = {
    0x0000: "Success",
    0x0001: "The sender issued an invalid or unsupported encapsulation command",
    0x0002: "Insufficient memory",
    0x0003: "Poorly formed or incorrect data in the data portion",
    0x0064: "An originator used an invalid session handle when sending an encapsulation message to the target",
    0x0065: "The target received a message of invalid length",
    0x0069: "Unsupported Protocol Version"
}

"""
MSG Error Codes:

The following error codes have been taken from:

Rockwell Automation Publication
1756-RM003P-EN-P - December 2014
"""
SERVICE_STATUS = {
    0x01: "Connection failure (see extended status)",
    0x02: "Insufficient resource",
    0x03: "Invalid value",
    0x04: "IOI syntax error. A syntax error was detected decoding the Request Path (see extended status)",
    0x05: "Destination unknown, class unsupported, instance \nundefined or structure element undefined (see extended status)",
    0x06: "Insufficient Packet Space",
    0x07: "Connection lost",
    0x08: "Service not supported",
    0x09: "Error in data segment or invalid attribute value",
    0x0A: "Attribute list error",
    0x0B: "State already exist",
    0x0C: "Object state conflict",
    0x0D: "Object already exist",
    0x0E: "Attribute not settable",
    0x0F: "Permission denied",
    0x10: "Device state conflict",
    0x11: "Reply data too large",
    0x12: "Fragmentation of a primitive value",
    0x13: "Insufficient command data",
    0x14: "Attribute not supported",
    0x15: "Too much data",
    0x1A: "Bridge request too large",
    0x1B: "Bridge response too large",
    0x1C: "Attribute list shortage",
    0x1D: "Invalid attribute list",
    0x1E: "Request service error",
    0x1F: "Connection related failure (see extended status)",
    0x22: "Invalid reply received",
    0x25: "Key segment error",
    0x26: "Invalid IOI error",
    0x27: "Unexpected attribute in list",
    0x28: "DeviceNet error - invalid member ID",
    0x29: "DeviceNet error - member not settable",
    0xD1: "Module not in run state",
    0xFB: "Message port not supported",
    0xFC: "Message unsupported data type",
    0xFD: "Message uninitialized",
    0xFE: "Message timeout",
    0xff: "General Error (see extended status)"
}

EXTEND_CODES = {
    0x01: {
        0x0100: "Connection in use",
        0x0103: "Transport not supported",
        0x0106: "Ownership conflict",
        0x0107: "Connection not found",
        0x0108: "Invalid connection type",
        0x0109: "Invalid connection size",
        0x0110: "Module not configured",
        0x0111: "EPR not supported",
        0x0114: "Wrong module",
        0x0115: "Wrong device type",
        0x0116: "Wrong revision",
        0x0118: "Invalid configuration format",
        0x011A: "Application out of connections",
        0x0203: "Connection timeout",
        0x0204: "Unconnected message timeout",
        0x0205: "Unconnected send parameter error",
        0x0206: "Message too large",
        0x0301: "No buffer memory",
        0x0302: "Bandwidth not available",
        0x0303: "No screeners available",
        0x0305: "Signature match",
        0x0311: "Port not available",
        0x0312: "Link address not available",
        0x0315: "Invalid segment type",
        0x0317: "Connection not scheduled"
    },
    0x04: {
        0x0000: "Extended status out of memory",
        0x0001: "Extended status out of instances"
    },
    0x05: {
        0x0000: "Extended status out of memory",
        0x0001: "Extended status out of instances"
    },
    0x1F: {
        0x0203: "Connection timeout"
    },
    0xff: {
        0x7: "Wrong data type",
        0x2001: "Excessive IOI",
        0x2002: "Bad parameter value",
        0x2018: "Semaphore reject",
        0x201B: "Size too small",
        0x201C: "Invalid size",
        0x2100: "Privilege failure",
        0x2101: "Invalid keyswitch position",
        0x2102: "Password invalid",
        0x2103: "No password issued",
        0x2104: "Address out of range",
        0x2105: "Address and how many out of range",
        0x2106: "Data in use",
        0x2107: "Type is invalid or not supported",
        0x2108: "Controller in upload or download mode",
        0x2109: "Attempt to change number of array dimensions",
        0x210A: "Invalid symbol name",
        0x210B: "Symbol does not exist",
        0x210E: "Search failed",
        0x210F: "Task cannot start",
        0x2110: "Unable to write",
        0x2111: "Unable to read",
        0x2112: "Shared routine not editable",
        0x2113: "Controller in faulted mode",
        0x2114: "Run mode inhibited"

    }
}
DATA_ITEM = {
    'Connected': '\xb1\x00',
    'Unconnected': '\xb2\x00'
}

ADDRESS_ITEM = {
    'Connection Based': '\xa1\x00',
    'Null': '\x00\x00',
    'UCMM': '\x00\x00'
}

UCMM = {
    'Interface Handle': 0,
    'Item Count': 2,
    'Address Type ID': 0,
    'Address Length': 0,
    'Data Type ID': 0x00b2
}

CONNECTION_SIZE = {
    'Backplane': '\x03',     # CLX
    'Direct Network': '\x02'
}

HEADER_SIZE = 24
EXTENDED_SYMBOL = '\x91'
BOOL_ONE = 0xff
REQUEST_SERVICE = 0
REQUEST_PATH_SIZE = 1
REQUEST_PATH = 2
SUCCESS = 0
INSUFFICIENT_PACKETS = 6
OFFSET_MESSAGE_REQUEST = 40


FORWARD_CLOSE = '\x4e'
UNCONNECTED_SEND = '\x52'
FORWARD_OPEN = '\x54'
LARGE_FORWARD_OPEN = '\x5b'
GET_CONNECTION_DATA = '\x56'
SEARCH_CONNECTION_DATA = '\x57'
GET_CONNECTION_OWNER = '\x5a'
MR_SERVICE_SIZE = 2

PADDING_BYTE = '\x00'
PRIORITY = '\x0a'
TIMEOUT_TICKS = '\x05'
TIMEOUT_MULTIPLIER = '\x01'
TRANSPORT_CLASS = '\xa3'

CONNECTION_PARAMETER = {
    'PLC5': 0x4302,
    'SLC500': 0x4302,
    'CNET': 0x4320,
    'DHP': 0x4302,
    'Default': 0x43f8,
}

"""
Atomic Data Type:

          Bit = Bool
     Bit array = DWORD (32-bit boolean aray)
 8-bit integer = SINT
16-bit integer = UINT
32-bit integer = DINT
  32-bit float = REAL
64-bit integer = LINT

From Rockwell Automation Publication 1756-PM020C-EN-P November 2012:
When reading a BOOL tag, the values returned for 0 and 1 are 0 and 0xff, respectively.
"""

S_DATA_TYPE = {
    'BOOL': 0xc1,
    'SINT': 0xc2,    # Signed 8-bit integer
    'INT': 0xc3,     # Signed 16-bit integer
    'DINT': 0xc4,    # Signed 32-bit integer
    'LINT': 0xc5,    # Signed 64-bit integer
    'USINT': 0xc6,   # Unsigned 8-bit integer
    'UINT': 0xc7,    # Unsigned 16-bit integer
    'UDINT': 0xc8,   # Unsigned 32-bit integer
    'ULINT': 0xc9,   # Unsigned 64-bit integer
    'REAL': 0xca,    # 32-bit floating point
    'LREAL': 0xcb,   # 64-bit floating point
    'STIME': 0xcc,   # Synchronous time
    'DATE': 0xcd,
    'TIME_OF_DAY': 0xce,
    'DATE_AND_TIME': 0xcf,
    'STRING': 0xd0,   # character string (1 byte per character)
    'BYTE': 0xd1,     # byte string 8-bits
    'WORD': 0xd2,     # byte string 16-bits
    'DWORD': 0xd3,    # byte string 32-bits
    'LWORD': 0xd4,    # byte string 64-bits
    'STRING2': 0xd5,  # character string (2 byte per character)
    'FTIME': 0xd6,    # Duration high resolution
    'LTIME': 0xd7,    # Duration long
    'ITIME': 0xd8,    # Duration short
    'STRINGN': 0xd9,  # character string (n byte per character)
    'SHORT_STRING': 0xda,  # character string (1 byte per character, 1 byte length indicator)
    'TIME': 0xdb,     # Duration in milliseconds
    'EPATH': 0xdc,    # CIP Path segment
    'ENGUNIT': 0xdd,  # Engineering Units
    'STRINGI': 0xde   # International character string
}

I_DATA_TYPE = {
    0xc1: 'BOOL',
    0xc2: 'SINT',    # Signed 8-bit integer
    0xc3: 'INT',     # Signed 16-bit integer
    0xc4: 'DINT',    # Signed 32-bit integer
    0xc5: 'LINT',    # Signed 64-bit integer
    0xc6: 'USINT',   # Unsigned 8-bit integer
    0xc7: 'UINT',    # Unsigned 16-bit integer
    0xc8: 'UDINT',   # Unsigned 32-bit integer
    0xc9: 'ULINT',   # Unsigned 64-bit integer
    0xca: 'REAL',    # 32-bit floating point
    0xcb: 'LREAL',   # 64-bit floating point
    0xcc: 'STIME',   # Synchronous time
    0xcd: 'DATE',
    0xce: 'TIME_OF_DAY',
    0xcf: 'DATE_AND_TIME',
    0xd0: 'STRING',   # character string (1 byte per character)
    0xd1: 'BYTE',     # byte string 8-bits
    0xd2: 'WORD',     # byte string 16-bits
    0xd3: 'DWORD',    # byte string 32-bits
    0xd4: 'LWORD',    # byte string 64-bits
    0xd5: 'STRING2',  # character string (2 byte per character)
    0xd6: 'FTIME',    # Duration high resolution
    0xd7: 'LTIME',    # Duration long
    0xd8: 'ITIME',    # Duration short
    0xd9: 'STRINGN',  # character string (n byte per character)
    0xda: 'SHORT_STRING',  # character string (1 byte per character, 1 byte length indicator)
    0xdb: 'TIME',     # Duration in milliseconds
    0xdc: 'EPATH',    # CIP Path segment
    0xdd: 'ENGUNIT',  # Engineering Units
    0xde: 'STRINGI'    # International character string
}

REPLAY_INFO = {
    0x4e: 'FORWARD_CLOSE (4E,00)',
    0x52: 'UNCONNECTED_SEND (52,00)',
    0x54: 'FORWARD_OPEN (54,00)',
    0x6f: 'send_rr_data (6F,00)',
    0x70: 'send_unit_data (70,00)',
    0x00: 'nop',
    0x01: 'list_targets',
    0x04: 'list_services',
    0x63: 'list_identity',
    0x64: 'list_interfaces',
    0x65: 'register_session',
    0x66: 'unregister_session',
}

PCCC_DATA_TYPE = {
    'N': '\x89',
    'B': '\x85',
    'T': '\x86',
    'C': '\x87',
    'S': '\x84',
    'F': '\x8a',
    'ST': '\x8d',
    'A': '\x8e',
    'R': '\x88',
    'O': '\x8b',
    'I': '\x8c'
}

PCCC_DATA_SIZE = {
    'N': 2,
    'B': 2,
    'T': 6,
    'C': 6,
    'S': 2,
    'F': 4,
    'ST': 84,
    'A': 2,
    'R': 6,
    'O': 2,
    'I': 2
}

PCCC_CT = {
    'PRE': 1,
    'ACC': 2,
    'EN': 15,
    'TT': 14,
    'DN': 13,
    'CU': 15,
    'CD': 14,
    'OV': 12,
    'UN': 11,
    'UA': 10
}

PCCC_ERROR_CODE = {
    -2: "Not Acknowledged (NAK)",
    -3: "No Reponse, Check COM Settings",
    -4: "Unknown Message from DataLink Layer",
    -5: "Invalid Address",
    -6: "Could Not Open Com Port",
    -7: "No data specified to data link layer",
    -8: "No data returned from PLC",
    -20: "No Data Returned",
    16: "Illegal Command or Format, Address may not exist or not enough elements in data file",
    32: "PLC Has a Problem and Will Not Communicate",
    48: "Remote Node Host is Missing, Disconnected, or Shut Down",
    64: "Host Could Not Complete Function Due To Hardware Fault",
    80: "Addressing problem or Memory Protect Rungs",
    96: "Function not allows due to command protection selection",
    112: "Processor is in Program mode",
    128: "Compatibility mode file missing or communication zone problem",
    144: "Remote node cannot buffer command",
    240: "Error code in EXT STS Byte"
}