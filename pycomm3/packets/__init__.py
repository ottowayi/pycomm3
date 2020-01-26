# -*- coding: utf-8 -*-
#
# const.py - A set of structures and constants used to implement the Ethernet/IP protocol
#
# Copyright (c) 2019 Ian Ottoway <ian@ottoway.dev>
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

from autologging import logged


@logged
class Packet:
    ...


from .responses import (ResponsePacket, SendUnitDataResponsePacket, SendRRDataResponsePacket, ListIdentityResponsePacket,
                        RegisterSessionResponsePacket, UnRegisterSessionResponsePacket, ReadTagServiceResponsePacket,
                        MultiServiceResponsePacket, ReadTagFragmentedServiceResponsePacket,
                        WriteTagServiceResponsePacket, WriteTagFragmentedServiceResponsePacket)

from .requests import (RequestPacket, SendUnitDataRequestPacket, SendRRDataRequestPacket, ListIdentityRequestPacket,
                       RegisterSessionRequestPacket, UnRegisterSessionRequestPacket, ReadTagServiceRequestPacket,
                       MultiServiceRequestPacket, ReadTagFragmentedServiceRequestPacket, WriteTagServiceRequestPacket,
                       WriteTagFragmentedServiceRequestPacket)

from collections import defaultdict


REQUEST_MAP = defaultdict(RequestPacket,
{
    'send_unit_data': SendUnitDataRequestPacket,
    'send_rr_data': SendRRDataRequestPacket,
    'register_session': RegisterSessionRequestPacket,
    'unregister_session': UnRegisterSessionRequestPacket,
    'list_identity': ListIdentityRequestPacket,
    'read_tag': ReadTagServiceRequestPacket,
    'multi_request': MultiServiceRequestPacket,
    'read_tag_fragmented': ReadTagFragmentedServiceRequestPacket,
    'write_tag': WriteTagServiceRequestPacket,
    'write_tag_fragmented': WriteTagFragmentedServiceRequestPacket,
})
