# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Ian Ottoway <ian@ottoway.dev>
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

from typing import NamedTuple, Sequence, Union, Tuple
from ..map import EnumMap


__all__ = ['DataFormat', 'Attribute', 'ConnectionManagerInstances', 'ClassCode',
           'CommonClassAttributes', 'IdentityObjectInstanceAttributes',
           'FileObjectClassAttributes', 'FileObjectInstanceAttributes', 'FileObjectInstances']


DataFormat = Tuple[str, Union[str, 'DataFormat']]


class Attribute(NamedTuple):
    attr_id: Union[bytes, int]
    data_format: Sequence[DataFormat]


class ConnectionManagerInstances(EnumMap):
    open_request = b'\x01'
    open_format_rejected = b'\x02'
    open_resource_rejected = b'\x03'
    open_other_rejected = b'\x04'
    close_request = b'\x05'
    close_format_request = b'\x06'
    close_other_request = b'\x07'
    connection_timeout = b'\x08'


class ClassCode(EnumMap):
    identity_object = b'\x01'
    message_router = b'\x02'
    device_net = b'\x03'
    assembly = b'\x04'
    connection = b'\x05'
    connection_manager = b'\x06'
    register = b'\x07'
    discrete_input = b'\x08'
    discrete_output = b'\x09'
    analog_input = b'\x0A'
    analog_output = b'\x0B'
    presence_sensing = b'\x0E'
    parameter = b'\x0F'

    parameter_group = b'\x10'
    group = b'\x12'
    discrete_input_group = b'\x1D'
    discrete_output_group = b'\x1E'
    discrete_group = b'\x1F'

    analog_input_group = b'\x20'
    analog_output_group = b'\x21'
    analog_group = b'\x22'
    position_sensor = b'\x23'
    position_controller_supervisor = b'\x24'
    position_controller = b'\x25'
    block_sequencer = b'\x26'
    command_block = b'\x27'
    motor_data = b'\x28'
    control_supervisor = b'\x29'
    ac_dc_drive = b'\x2A'
    acknowledge_handler = b'\x2B'
    overload = b'\x2C'
    softstart = b'\x2D'
    selection = b'\x2E'

    s_device_supervisor = b'\x30'
    s_analog_sensor = b'\x31'
    s_analog_actuator = b'\x32'
    s_single_stage_controller = b'\x33'
    s_gas_calibration = b'\x34'
    trip_point = b'\x35'
    file_object = b'\x37'
    s_partial_pressure = b'\x38'
    safety_supervisor = b'\x39'
    safety_validator = b'\x3A'
    safety_discrete_output_point = b'\x3B'
    safety_discrete_output_group = b'\x3C'
    safety_discrete_input_point = b'\x3D'
    safety_discrete_input_group = b'\x3E'
    safety_dual_channel_output = b'\x3F'

    s_sensor_calibration = b'\x40'
    event_log = b'\x41'
    motion_axis = b'\x42'
    time_sync = b'\x43'
    modbus = b'\x44'
    modbus_serial_link = b'\x46'

    symbol_object = b'\x6b'
    template_object = b'\x6c'
    program_name = b'\x64'  # Rockwell KB# 23341

    wall_clock_time = b'\x8b'  # Micro800 CIP client messaging quick start

    controlnet = b'\xF0'
    controlnet_keeper = b'\xF1'
    controlnet_scheduling = b'\xF2'
    connection_configuration = b'\xF3'
    port = b'\xF4'
    tcp_ip_interface = b'\xF5'
    ethernet_link = b'\xF6'
    componet_link = b'\xF7'
    componet_repeater = b'\xF8'


class CommonClassAttributes(EnumMap):
    revision = Attribute(1, (('revision', 'UINT'), ))
    max_instance = Attribute(2, (('max_instance', 'UINT'), ))
    number_of_instances = Attribute(3, (('number_of_instances','UINT'), ))
    optional_attribute_list = Attribute(4, (('count', 'UINT', ),
                                            ('attributes', 'UINT[]'),))
    optional_service_list = Attribute(5, (('count', 'UINT'),
                                          ('services','UINT[]'), ))
    max_id_number_class_attributes = Attribute(6, 'UINT')
    max_id_number_instance_attributes = Attribute(7, 'UINT')


class IdentityObjectInstanceAttributes(EnumMap):
    vendor_id = Attribute(1, (('vendor_id', 'UINT'),))
    device_type = Attribute(2, (('device_type', 'UINT'),))
    product_code = Attribute(3, (('product_code', 'UINT'),))
    revision = Attribute(4, (('major', 'USINT'), ('minor', 'USINT'), ))
    status = Attribute(5, (('status', 'WORD'), ))
    serial_number = Attribute(6, (('serial_number', 'UDINT'), ))
    product_name = Attribute(7, (('product_name', 'SHORT_STRING'), ))


class FileObjectClassAttributes(EnumMap):
    directory = Attribute(32, (('instance_number', 'UINT'),
                               ('instance_name', 'STRINGI'),
                               ('file_name', 'STRINGI'), ))  # array of struct, len in attr 3


class FileObjectInstanceAttributes(EnumMap):
    state = Attribute(1, (('state', 'USINT'), ))
    instance_name = Attribute(2, (('instance_name', 'STRINGI'), ))
    instance_format_version = Attribute(3, (('instance_format_version', 'UINT'), ))
    file_name = Attribute(4, (('file_name', 'STRINGI'), ))
    file_revision = Attribute(5, (('major', 'USINT'), ('minor', 'USINT'), ))
    file_size = Attribute(6, (('file_size', 'UDINT'), ))
    file_checksum = Attribute(7, (('file_checksum', 'INT'), ))
    invocation_method = Attribute(8, (('invocation_metho', 'USINT'), ))
    file_save_params = Attribute(9, (('file_save_params', 'BYTE'), ))
    file_type = Attribute(10, (('file_type', 'USINT'), ))
    file_encoding_format = Attribute(11, (('file_encoding_format', 'USINT'), ))


class FileObjectInstances(EnumMap):
    eds_file_and_icon = 0xC8
    related_eds_files_and_icons = 0xC9
