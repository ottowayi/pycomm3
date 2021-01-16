from pycomm3 import CIPDriver, Services, ClassCode, Pack, Unpack
import itertools
import gzip
from pathlib import Path


EDS_INSTANCE = 0xc8
EDS_ATTR_FILE_NAME = 0x04
EDS_ATTR_FILE_ENCODING = 0x0B
EDS_ATTR_FILE_SIZE = 0x06
EDS_ATTR_FILE_REV = 0x05

EDS_SERVICE_INIT_UPLOAD = 0x4B
EDS_SERVICE_UPLOAD_TRANSFER = 0x4F

EDS_ENCODINGS = {
    0: 'binary',
    1: 'zlib'
}

with CIPDriver('192.168.1.236') as plc:

    file_name_resp = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=EDS_ATTR_FILE_NAME,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_format=[('FileName', 'STRINGI')]
    )

    file_name = file_name_resp.value['FileName'][0] if file_name_resp else None

    file_encoding_resp = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=EDS_ATTR_FILE_NAME,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_format=[('FileEncoding', 'USINT')]
    )
    _enc_code = file_encoding_resp.value['FileEncoding'] if file_encoding_resp else None
    file_encoding = EDS_ENCODINGS.get(_enc_code, 'UNSUPPORTED ENCODING')

    file_encoding_resp = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=EDS_ATTR_FILE_NAME,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_format=[('FileEncoding', 'USINT')]
    )
    _enc_code = file_encoding_resp.value['FileEncoding'] if file_encoding_resp else None

    file_size_resp = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=EDS_ATTR_FILE_SIZE,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_format=[('FileSize', 'UDINT')]
    )
    file_size = file_size_resp.value['FileSize'] if file_size_resp else None

    file_rev_resp = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=EDS_ATTR_FILE_REV,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_format=[('FileRevMajor', 'USINT'), ('FileRevMinor', 'USINT')]
    )
    if file_rev_resp:
        file_rev = f'{file_rev_resp.value["FileRevMajor"]}.{file_rev_resp.value["FileRevMinor"]:03}'
    else:
        file_rev = None
    print(f'file name: {file_name!r}, encoding: {file_encoding}, size: {file_size} bytes, rev: {file_rev}')

    init_resp = plc.generic_message(
        service=EDS_SERVICE_INIT_UPLOAD,
        class_code=ClassCode.file_object,
        instance=0xc8,
        route_path=True,
        unconnected_send=True,
        connected=False,
        request_data=b'\xFF',  # max transfer size
        data_format=[
            ('FileSize', 'UDINT'),
            ('TransferSize', 'USINT')
        ],
    )

    if init_resp:
        contents = b''

        for i in itertools.cycle(range(256)):
            resp = plc.generic_message(
                service=EDS_SERVICE_UPLOAD_TRANSFER,
                class_code=ClassCode.file_object,
                instance=0xc8,
                route_path=True,
                unconnected_send=True,
                connected=False,
                request_data=Pack.usint(i),
                data_format=[
                    ('TransferNumber', 'USINT'),
                    ('PacketType', 'USINT'),
                    ('FileData', '*')
                ],
            )

            if resp:
                print(resp.value)
                packet_type = resp.value['PacketType']
                transfer_num = resp.value['TransferNumber']
                data = resp.value['FileData']

                contents += data
                if packet_type in (2, 3, 4, 5):
                    print(f'final packet type: {packet_type}')
                    break
            else:
                print(f'failed response {resp}')
                break

        contents = contents[:-2]  # strip off checksum
        print(f'bytes received {len(contents)}')

        GZ_MAGIC_BYTES = b'\x1f\x8b'
        if file_encoding == 'zlib':
            end_file1 = contents.find(GZ_MAGIC_BYTES, 2)
            file1, file2 = contents[:end_file1], contents[end_file1:]
            eds = gzip.decompress(file1)
            ico = gzip.decompress(file2)
            eds_name = file1[10:file1.find(b'\x00', 10)].decode()
            ico_name = file2[10:file2.find(b'\x00', 10)].decode()

            save_path = Path.home()
            eds_path = save_path / eds_name
            ico_path = save_path / ico_name

            eds_path.write_bytes(eds)
            ico_path.write_bytes(ico)