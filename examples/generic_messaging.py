from pycomm3 import CIPDriver, Services, ClassCode, INT, Array, USINT


# Read PF525 Parameter
def read_pf525_parameter():
    drive_path = '10.10.10.100/bp/1/enet/192.168.1.55'

    with CIPDriver(drive_path) as drive:
        param = drive.generic_message(
            service=Services.get_attribute_single,
            class_code=b'\x93',
            instance=41,  # Parameter 41 = Accel Time
            attribute=b'\x09',
            data_type=INT,
            connected=False,
            unconnected_send=True,
            route_path=True,
            name='pf525_param'
        )
        print(param)


# Write PF525 Parameter
def write_pf525_parameter():
    drive_path = '10.10.10.100/bp/1/enet/192.168.1.55'

    with CIPDriver(drive_path) as drive:
        drive.generic_message(
            service=Services.set_attribute_single,
            class_code=b'\x93',
            instance=41,  # Parameter 41 = Accel Time
            attribute=b'\x09',
            request_data=INT.encode(500),  # = 5 seconds * 100
            connected=False,
            unconnected_send=True,
            route_path=True,
            name='pf525_param'
        )


# Read OK LED Status From ENBT/EN2T
def enbt_ok_led_status():
    message_path = '10.10.10.100/bp/2'

    with CIPDriver(message_path) as device:
        data = device.generic_message(
            service=Services.get_attribute_single,
            class_code=b'\x01',  # Values from RA Knowledgebase
            instance=1,  # Values from RA Knowledgebase
            attribute=5,  # Values from RA Knowledgebase
            data_type=INT,
            connected=False,
            unconnected_send=True,
            route_path=True,
            name='OK LED Status'
        )
        # The LED Status is returned as a binary representation on bits 4, 5, 6, and 7. The decimal equivalents are:
        # 0 = Solid Red, 64 = Flashing Red, and 96 = Solid Green. The ENBT/EN2T do not display link lost through the OK LED.
        statuses = {
            0: 'solid red',
            64: 'flashing red',
            96: 'solid green'
        }
        print(statuses.get(data.value), 'unknown')


# Read Link Status of any Logix Ethernet Module
def link_status():
    message_path = '10.10.10.100/bp/2'

    with CIPDriver(message_path) as device:
        data = device.generic_message(
            service=Services.get_attribute_single,
            class_code=b'\xf6',  # Values from RA Knowledgebase
            instance=1,  # For multiport devices, change to "2" for second port, "3" for third port.
                         # For CompactLogix, front port is "1" and back port is "2".
            attribute=2,  # Values from RA Knowledgebase
            data_type=INT,
            connected=False,
            unconnected_send=True,
            route_path=True,
            name='LinkStatus'
        )
        # Prints the binary representation of the link status. The definition of the bits are:
        #   Bit 0 - Link Status - 0 means inactive link (Link Lost), 1 means active link.
        #   Bit 1 - Half/Full Duplex - 0 means half duplex, 1 means full duplex
        #   Bit 2 to 4 - Binary representation of auto-negotiation and speed detection status:
        #       0 = Auto-negotiation in progress
        #       1 = Auto-negotiation and speed detection failed 
        #       2 = Auto-negotiation failed, speed detected
        #       3 = Auto-negotiation successful and speed detected
        #       4 = Manually forced speed and duplex
        #   Bit 5 - Setting Requires Reset - if 1, a manual setting requires resetting of the module
        #   Bit 6 - Local Hardware Fault - 0 indicates no hardware faults, 1 indicates a fault detected. 
        print(bin(data.value))


# Get the status of both power inputs from a Stratix switch.
def stratix_power_status():
    message_path = '10.10.10.100/bp/2/enet/192.168.1.1'

    with CIPDriver(message_path) as device:
        data = device.generic_message(
            service=b'\x0e',
            class_code=863,  # use decimal representation of hex class code
            instance=1,
            attribute=8,
            connected=False,
            unconnected_send=True,
            route_path=True,
            data_type=INT,
            name='Power Status'
        )
        # Returns a binary representation of the power status. Bit 0 is PWR A, Bit 1 is PWR B. If 1, power is applied. If 0, power is off.
        pwr_a = 'on' if data.value & 0b_1 else 'off'
        pwr_b = 'on' if data.value & 0b_10 else 'off'
        print(f'PWR A: {pwr_a}, PWR B: {pwr_b}')


# Get the IP Configuration from an Ethernet Module
def ip_config():
    message_path = '10.10.10.100/bp/2'

    with CIPDriver(message_path) as plc:  # L85
        data = plc.generic_message(
            service=b'\x0e',
            class_code=b'\xf5',
            instance=1,
            attribute=3,
            connected=False,
            unconnected_send=True,
            route_path=True,
            data_type=INT,
            name='IP_config'
        )

        statuses = {
            0b_0000: 'static',
            0b_0001: 'BOOTP',
            0b_0010: 'DHCP'
        }

        ip_status = data.value & 0b_1111  # only need the first 4 bits
        print(statuses.get(ip_status, 'unknown'))


# Get MAC address of
def get_mac_address():
    with CIPDriver('10.10.10.100') as plc:
        response = plc.generic_message(
            service=Services.get_attribute_single,
            class_code=ClassCode.ethernet_link,
            instance=1,
            attribute=3,
            data_type=USINT[6],
            connected=False
        )

        if response:
            return ':'.join(f'{x:0>2x}' for x in response.value)
        else:
            print(f'error getting MAC address - {response.error}')
