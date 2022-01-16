from .base import *
from .cip_common import *
from .conn_mgr import ConnectionManagerObject


class ClassCode(EnumMap):
    identity_object = b"\x01"
    message_router = b"\x02"
    device_net = b"\x03"
    assembly = b"\x04"
    connection = b"\x05"
    connection_manager = b"\x06"
    register = b"\x07"
    discrete_input = b"\x08"
    discrete_output = b"\x09"
    analog_input = b"\x0A"
    analog_output = b"\x0B"
    presence_sensing = b"\x0E"
    parameter = b"\x0F"

    parameter_group = b"\x10"
    group = b"\x12"
    discrete_input_group = b"\x1D"
    discrete_output_group = b"\x1E"
    discrete_group = b"\x1F"

    analog_input_group = b"\x20"
    analog_output_group = b"\x21"
    analog_group = b"\x22"
    position_sensor = b"\x23"
    position_controller_supervisor = b"\x24"
    position_controller = b"\x25"
    block_sequencer = b"\x26"
    command_block = b"\x27"
    motor_data = b"\x28"
    control_supervisor = b"\x29"
    ac_dc_drive = b"\x2A"
    acknowledge_handler = b"\x2B"
    overload = b"\x2C"
    softstart = b"\x2D"
    selection = b"\x2E"

    s_device_supervisor = b"\x30"
    s_analog_sensor = b"\x31"
    s_analog_actuator = b"\x32"
    s_single_stage_controller = b"\x33"
    s_gas_calibration = b"\x34"
    trip_point = b"\x35"
    file_object = b"\x37"
    s_partial_pressure = b"\x38"
    safety_supervisor = b"\x39"
    safety_validator = b"\x3A"
    safety_discrete_output_point = b"\x3B"
    safety_discrete_output_group = b"\x3C"
    safety_discrete_input_point = b"\x3D"
    safety_discrete_input_group = b"\x3E"
    safety_dual_channel_output = b"\x3F"

    s_sensor_calibration = b"\x40"
    event_log = b"\x41"
    motion_axis = b"\x42"
    time_sync = b"\x43"
    modbus = b"\x44"
    modbus_serial_link = b"\x46"

    symbol_object = b"\x6b"
    template_object = b"\x6c"
    program_name = b"\x64"  # Rockwell KB# 23341

    wall_clock_time = b"\x8b"  # Micro800 CIP client messaging quick start

    controlnet = b"\xF0"
    controlnet_keeper = b"\xF1"
    controlnet_scheduling = b"\xF2"
    connection_configuration = b"\xF3"
    port = b"\xF4"
    tcp_ip_interface = b"\xF5"
    ethernet_link = b"\xF6"
    componet_link = b"\xF7"
    componet_repeater = b"\xF8"


class ConnectionManagerInstances(EnumMap):
    open_request = b"\x01"
    open_format_rejected = b"\x02"
    open_resource_rejected = b"\x03"
    open_other_rejected = b"\x04"
    close_request = b"\x05"
    close_format_request = b"\x06"
    close_other_request = b"\x07"
    connection_timeout = b"\x08"

