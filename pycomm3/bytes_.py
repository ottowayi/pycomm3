import struct


def pack_sint(n):
    return struct.pack('b', n)


def pack_usint(n):
    return struct.pack('B', n)


def pack_int(n):
    """pack 16 bit into 2 bytes little endian"""
    return struct.pack('<h', n)


def pack_uint(n):
    """pack 16 bit into 2 bytes little endian"""
    return struct.pack('<H', n)


def pack_dint(n):
    """pack 32 bit into 4 bytes little endian"""
    return struct.pack('<i', n)


def pack_udint(n):
    """pack 32 bit into 4 bytes little endian"""
    return struct.pack('<I', n)


def pack_real(r):
    """unpack 4 bytes little endian to int"""
    return struct.pack('<f', r)


def pack_lint(l):
    """unpack 4 bytes little endian to int"""
    return struct.pack('<q', l)


def unpack_bool(st):
    return 1 if not st[0] == 0 else 0


def unpack_sint(st):
    return int(struct.unpack('b', bytes([st[0]]))[0])


def unpack_usint(st):
    return int(struct.unpack('B', bytes([st[0]]))[0])


def unpack_int(st):
    """unpack 2 bytes little endian to int"""
    return int(struct.unpack('<h', st[0:2])[0])


def unpack_uint(st):
    """unpack 2 bytes little endian to int"""
    return int(struct.unpack('<H', st[0:2])[0])


def unpack_dint(st):
    """unpack 4 bytes little endian to int"""
    return int(struct.unpack('<i', st[0:4])[0])


def unpack_real(st):
    """unpack 4 bytes little endian to int"""
    return float(struct.unpack('<f', st[0:4])[0])


def unpack_lint(st):
    """unpack 4 bytes little endian to int"""
    return int(struct.unpack('<q', st[0:8])[0])


def print_bytes_line(msg):
    out = ''
    for ch in msg:
        out += "{:0>2x}".format(ch)
    return out


def print_bytes_msg(msg, info=''):
    out = info
    new_line = True
    line = 0
    column = 0
    for idx, ch in enumerate(msg):
        if new_line:
            out += "\n({:0>4d}) ".format(line * 10)
            new_line = False
        out += "{:0>2x} ".format(ch)
        if column == 9:
            new_line = True
            column = 0
            line += 1
        else:
            column += 1
    return out


PACK_DATA_FUNCTION = {
    'BOOL': pack_sint,
    'SINT': pack_sint,    # Signed 8-bit integer
    'INT': pack_int,     # Signed 16-bit integer
    'UINT': pack_uint,    # Unsigned 16-bit integer
    'USINT': pack_usint,  # Unsigned Byte Integer
    'DINT': pack_dint,    # Signed 32-bit integer
    'REAL': pack_real,    # 32-bit floating point
    'LINT': pack_lint,
    'BYTE': pack_sint,     # byte string 8-bits
    'WORD': pack_uint,     # byte string 16-bits
    'DWORD': pack_dint,    # byte string 32-bits
    'LWORD': pack_lint    # byte string 64-bits
}


UNPACK_DATA_FUNCTION = {
    'BOOL': unpack_bool,
    'SINT': unpack_sint,    # Signed 8-bit integer
    'INT': unpack_int,     # Signed 16-bit integer
    'UINT': unpack_uint,    # Unsigned 16-bit integer
    'USINT': unpack_usint,  # Unsigned Byte Integer
    'DINT': unpack_dint,    # Signed 32-bit integer
    'REAL': unpack_real,    # 32-bit floating point,
    'LINT': unpack_lint,
    'BYTE': unpack_sint,     # byte string 8-bits
    'WORD': unpack_uint,     # byte string 16-bits
    'DWORD': unpack_dint,    # byte string 32-bits
    'LWORD': unpack_lint    # byte string 64-bits
}


DATA_FUNCTION_SIZE = {
    'BOOL': 1,
    'SINT': 1,    # Signed 8-bit integer
    'USINT': 1,  # Unisgned 8-bit integer
    'INT': 2,     # Signed 16-bit integer
    'UINT': 2,    # Unsigned 16-bit integer
    'DINT': 4,    # Signed 32-bit integer
    'REAL': 4,    # 32-bit floating point
    'LINT': 8,
    'BYTE': 1,     # byte string 8-bits
    'WORD': 2,     # byte string 16-bits
    'DWORD': 4,    # byte string 32-bits
    'LWORD': 8    # byte string 64-bits
}


UNPACK_PCCC_DATA_FUNCTION = {
    'N': unpack_int,
    'B': unpack_int,
    'T': unpack_int,
    'C': unpack_int,
    'S': unpack_int,
    'F': unpack_real,
    'A': unpack_sint,
    'R': unpack_dint,
    'O': unpack_int,
    'I': unpack_int
}


PACK_PCCC_DATA_FUNCTION = {
    'N': pack_int,
    'B': pack_int,
    'T': pack_int,
    'C': pack_int,
    'S': pack_int,
    'F': pack_real,
    'A': pack_sint,
    'R': pack_dint,
    'O': pack_int,
    'I': pack_int
}