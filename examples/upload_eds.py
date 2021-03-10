from pycomm3 import (CIPDriver, Services, ClassCode,  FileObjectServices, FileObjectInstances,
                     FileObjectInstanceAttributes, Struct, UDINT, USINT, n_bytes)
import itertools
import gzip
from pathlib import Path

SAVE_PATH = Path.home()


def upload_eds():
    """
    Uploads the EDS and ICO files from the device and saves the files.
    """
    with CIPDriver('192.168.1.236') as driver:
        if initiate_transfer(driver):
            file_data = upload_file(driver)
            encoding = get_file_encoding(driver)

            if encoding == 'zlib':
                # in this case the file has both the eds and ico files in it
                files = decompress_eds(file_data)

                for filename, file_data in files.items():
                    file_path = SAVE_PATH / filename
                    file_path.write_bytes(file_data)

            elif encoding == 'binary':
                file_name = get_file_name(driver)
                file_path = SAVE_PATH / file_name
                file_path.write_bytes(file_data)
            else:
                print('Unsupported Encoding')
        else:
            print('Failed to initiate transfer')


def initiate_transfer(driver):
    """
    Initiates the transfer with the device
    """
    resp = driver.generic_message(
        service=FileObjectServices.initiate_upload,
        class_code=ClassCode.file_object,
        instance=FileObjectInstances.eds_file_and_icon,
        route_path=True,
        unconnected_send=True,
        connected=False,
        request_data=b'\xFF',  # max transfer size
        data_type=Struct(UDINT('FileSize'), USINT('TransferSize'))
    )
    return resp


def upload_file(driver):
    contents = b''

    for i in itertools.cycle(range(256)):
        resp = driver.generic_message(
            service=FileObjectServices.upload_transfer,
            class_code=ClassCode.file_object,
            instance=FileObjectInstances.eds_file_and_icon,
            route_path=True,
            unconnected_send=True,
            connected=False,
            request_data=USINT.encode(i),
            data_type=Struct(USINT('TransferNumber'), USINT('PacketType'), n_bytes(-1, 'FileData'))

        )

        if resp:
            packet_type = resp.value['PacketType']
            data = resp.value['FileData']

            contents += data

            # CIP Vol 1 Section 5-42.4.5
            # 0 - first packet
            # 1 - middle packet
            # 2 - last packet
            # 3 - Abort transfer
            # 4 - first & last packet
            # 5-255 - Reserved
            if packet_type not in (0, 1):
                break
        else:
            print(f'failed response {resp}')
            break

    contents = contents[:-2]  # strip off checksum
    return contents


def get_file_encoding(driver):
    """
    get the encoding format for the eds file object
    """
    attr = FileObjectInstanceAttributes.file_encoding_format

    resp = driver.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=attr.attr_id,
        instance=FileObjectInstances.eds_file_and_icon,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_type=attr.data_type,
    )
    _enc_code = resp.value if resp else None
    EDS_ENCODINGS = {
        0: 'binary',
        1: 'zlib'
    }
    file_encoding = EDS_ENCODINGS.get(_enc_code, 'UNSUPPORTED ENCODING')
    return file_encoding


def decompress_eds(contents):
    """
    extract the eds and ico files from the uploaded file

    returns a dict of {file name: file contents}
    """
    GZ_MAGIC_BYTES = b'\x1f\x8b'

    # there is actually 2 files, the eds file and the icon
    # we need to split the file contents since gzip
    # only supports single files

    end_file1 = contents.find(GZ_MAGIC_BYTES, 2)
    file1, file2 = contents[:end_file1], contents[end_file1:]
    eds = gzip.decompress(file1)
    ico = gzip.decompress(file2)
    eds_name = file1[10:file1.find(b'\x00', 10)].decode()
    ico_name = file2[10:file2.find(b'\x00', 10)].decode()

    return {eds_name: eds, ico_name: ico}


def get_file_name(driver):
    """
    Get the filename of the eds file object
    """
    attr = FileObjectInstanceAttributes.file_name
    resp = driver.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.file_object,
        attribute=attr.attr_id,
        instance=FileObjectInstances.eds_file_and_icon,
        route_path=True,
        unconnected_send=True,
        connected=False,
        data_type=attr.data_type
    )

    file_name = resp.value['FileName'][0] if resp else None
    return file_name


if __name__ == '__main__':
    upload_eds()
