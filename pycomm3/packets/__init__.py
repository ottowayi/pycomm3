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


from .base import RequestPacket, ResponsePacket
from .ethernetip import (SendUnitDataRequestPacket, SendUnitDataResponsePacket,
                         SendRRDataRequestPacket, SendRRDataResponsePacket,
                         RegisterSessionRequestPacket, RegisterSessionResponsePacket,
                         UnRegisterSessionRequestPacket, UnRegisterSessionResponsePacket,
                         ListIdentityRequestPacket, ListIdentityResponsePacket)
from .cip import (GenericConnectedRequestPacket, GenericConnectedResponsePacket,
                  GenericUnconnectedRequestPacket, GenericUnconnectedResponsePacket)
from .logix import (ReadTagRequestPacket, ReadTagResponsePacket,
                    ReadTagFragmentedRequestPacket, ReadTagFragmentedResponsePacket,
                    WriteTagRequestPacket, WriteTagResponsePacket,
                    WriteTagFragmentedRequestPacket, WriteTagFragmentedResponsePacket,
                    ReadModifyWriteRequestPacket, ReadModifyWriteResponsePacket,
                    MultiServiceRequestPacket, MultiServiceResponsePacket)
from .util import *


class RequestTypes(EnumMap):
    send_unit_data = SendUnitDataRequestPacket
    send_rr_data = SendRRDataRequestPacket
    register_session = RegisterSessionRequestPacket
    unregister_session = UnRegisterSessionRequestPacket
    list_identity = ListIdentityRequestPacket
    read_tag = ReadTagRequestPacket
    multi_request = MultiServiceRequestPacket
    read_tag_fragmented = ReadTagFragmentedRequestPacket
    write_tag = WriteTagRequestPacket
    write_tag_fragmented = WriteTagFragmentedRequestPacket
    generic_connected = GenericConnectedRequestPacket
    generic_unconnected = GenericUnconnectedRequestPacket
    read_modify_write = ReadModifyWriteRequestPacket
