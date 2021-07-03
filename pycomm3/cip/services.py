# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
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

from ..map import EnumMap
from .data_types import USINT

__all__ = [
    "EncapsulationCommands",
    "ConnectionManagerServices",
    "Services",
    "MULTI_PACKET_SERVICES",
    "FileObjectServices",
]


class EncapsulationCommands(EnumMap):
    nop = b"\x00\x00"
    list_targets = b"\x01\x00"
    list_services = b"\x04\x00"
    list_identity = b"\x63\x00"
    list_interfaces = b"\x64\x00"
    register_session = b"\x65\x00"
    unregister_session = b"\x66\x00"
    send_rr_data = b"\x6F\x00"
    send_unit_data = b"\x70\x00"


class ConnectionManagerServices(EnumMap):
    forward_close = b"\x4E"
    unconnected_send = b"\x52"
    forward_open = b"\x54"
    get_connection_data = b"\x56"
    search_connection_data = b"\x57"
    get_connection_owner = b"\x5A"
    large_forward_open = b"\x5B"


class Services(EnumMap):

    # Common CIP Services
    get_attributes_all = b"\x01"
    set_attributes_all = b"\x02"
    get_attribute_list = b"\x03"
    set_attribute_list = b"\x04"
    reset = b"\x05"
    start = b"\x06"
    stop = b"\x07"
    create = b"\x08"
    delete = b"\x09"
    multiple_service_request = b"\x0A"
    apply_attributes = b"\x0D"
    get_attribute_single = b"\x0E"
    set_attribute_single = b"\x10"
    find_next_object_instance = b"\x11"
    error_response = b"\x14"
    restore = b"\x15"
    save = b"\x16"
    nop = b"\x17"
    get_member = b"\x18"
    set_member = b"\x19"
    insert_member = b"\x1A"
    remove_member = b"\x1B"
    group_sync = b"\x1C"

    # Rockwell Custom Services
    read_tag = b"\x4C"
    read_tag_fragmented = b"\x52"
    write_tag = b"\x4D"
    write_tag_fragmented = b"\x53"
    read_modify_write = b"\x4E"
    get_instance_attribute_list = b"\x55"

    @classmethod
    def from_reply(cls, reply_service):
        """
        Get service from reply service code
        """
        val = cls.get(USINT.encode(USINT.decode(reply_service) - 128))
        return val


MULTI_PACKET_SERVICES = {
    Services.read_tag_fragmented,
    Services.write_tag_fragmented,
    Services.get_instance_attribute_list,
    Services.multiple_service_request,
    Services.get_attribute_list,
}


class FileObjectServices(EnumMap):
    initiate_upload = b"\x4B"
    initiate_download = b"\x4C"
    initiate_partial_read = b"\x4D"
    initiate_partial_write = b"\x4E"
    upload_transfer = b"\x4F"
    download_transfer = b"\x50"
    clear_file = b"\x51"
