from pycomm3 import CIPDriver, CommonService, Pack


def read_pf525_parameter():
    drive_path = '10.10.10.100/bp/1/enet/192.168.1.55'

    with CIPDriver(drive_path) as drive:
        param = drive.generic_message(
            service=CommonService.get_attribute_single,
            class_code=b'\x93',
            instance=b'\x29',  # (hex) Parameter 41 = Accel Time
            attribute=b'\x09',
            connected=False,
            unconnected_send=True,
            route_path=True,
            data_format=[('AccelTime', 'INT'), ],
            name='pf525_param'
        )
        print(param)


def write_pf525_parameter():
    drive_path = '10.10.10.100/bp/1/enet/192.168.1.55'

    with CIPDriver(drive_path) as drive:
        drive.generic_message(
            service=CommonService.set_attribute_single,
            class_code=b'\x93',
            instance=b'\x29',  # (hex) Parameter 41 = Accel Time
            attribute=b'\x09',
            request_data=Pack.int(500),  # = 5 seconds * 100
            connected=False,
            unconnected_send=True,
            route_path=True,
            name='pf525_param'
        )
