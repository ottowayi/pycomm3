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

__all__ = [
    "SLCDriver",
]

import logging
import re
from typing import List, Tuple, Optional, Union

from .cip_driver import CIPDriver, with_forward_open
from .cip import (
    PCCC_CT,
    PCCC_DATA_TYPE,
    PCCC_DATA_SIZE,
    PCCC_ERROR_CODE,
    USINT,
    UINT,
    PCCCDataTypes,
)
from .const import (
    SUCCESS,
    SLC_CMD_CODE,
    SLC_FNC_READ,
    SLC_FNC_WRITE,
    SLC_REPLY_START,
    PCCC_PATH,
)
from .exceptions import ResponseError, RequestError
from .tag import Tag
from .packets import SendUnitDataRequestPacket

AtomicValueType = Union[int, float, bool]
TagValueType = Union[AtomicValueType, List[Union[AtomicValueType, str]]]
ReadWriteReturnType = Union[Tag, List[Tag]]

IO_RE = re.compile(
    r"(?P<file_type>[IO])(?P<file_number>\d{1,3})?"
    r"(:)(?P<element_number>\d{1,3})"
    r"((\.)(?P<position_number>\d{1,3}))?"
    r"(/(?P<sub_element>\d{1,2}))?"
    r"(?P<_elem_cnt_token>{(?P<element_count>\d+)})?",
    flags=re.IGNORECASE,
)

CT_RE = re.compile(
    r"(?P<file_type>[CT])(?P<file_number>\d{1,3})"
    r"(:)(?P<element_number>\d{1,3})"
    r"(.)(?P<sub_element>ACC|PRE|EN|DN|TT|CU|CD|DN|OV|UN|UA)",
    flags=re.IGNORECASE,
)

LFBN_RE = re.compile(
    r"(?P<file_type>[LFBN])(?P<file_number>\d{1,3})"
    r"(:)(?P<element_number>\d{1,3})"
    r"(/(?P<sub_element>\d{1,2}))?"
    r"(?P<_elem_cnt_token>{(?P<element_count>\d+)})?",
    flags=re.IGNORECASE,
)

S_RE = re.compile(
    r"(?P<file_type>S)"
    r"(:)(?P<element_number>\d{1,3})"
    r"(/(?P<sub_element>\d{1,2}))?"
    r"(?P<_elem_cnt_token>{(?P<element_count>\d+)})?",
    flags=re.IGNORECASE,
)

A_RE = re.compile(
    r"(?P<file_type>A)(?P<file_number>\d{1,3})"
    r"(:)(?P<element_number>\d{1,4})"
    r"(?P<_elem_cnt_token>{(?P<element_count>\d+)})?",
    flags=re.IGNORECASE,
)

B_RE = re.compile(
    r"(?P<file_type>B)(?P<file_number>\d{1,3})"
    r"(/)(?P<element_number>\d{1,4})"
    r"(?P<_elem_cnt_token>{(?P<element_count>\d+)})?",
    flags=re.IGNORECASE,
)

ST_RE = re.compile(
    r"(?P<file_type>ST)(?P<file_number>\d{1,3})"
    r"(:)(?P<element_number>\d{1,4})"
    r"(?P<_elem_cnt_token>{(?P<element_count>[12])})?",
    flags=re.IGNORECASE,
)


class SLCDriver(CIPDriver):
    """
    An Ethernet/IP Client driver for reading and writing of data files in SLC or MicroLogix PLCs.
    """

    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    _auto_slot_cip_path = True

    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, large_packets=False, **kwargs)

    def _msg_start(self):
        """
        No idea what this part is, but it starts all messages
        """
        return b"".join(
            (
                b"\x4b",
                b"\x02",
                b"\x20",  # 8-bit class
                PCCC_PATH,  # b"\x67\x24\x01"
                b"\x07",
                self._cfg["vid"], #"vid": b"\x09\x10",
                self._cfg["vsn"], #"vsn": b"\x09\x10\x19\x71",
            )
        )


    @with_forward_open
    def read(self, *addresses: str) -> ReadWriteReturnType:
        """
        Reads data file addresses. To read multiple words add the word count to the address using curly braces,
        e.g. ``N120:10{10}``.

        Does not track request/response size like the CLXDriver.

        :param addresses: one or many data file addresses to read
        :return: a single or list of ``Tag`` objects
        """
        results = [self._read_tag(tag) for tag in addresses]

        if len(results) == 1:
            return results[0]

        return results

    def _read_tag(self, tag) -> Tag:
        _tag = parse_tag(tag)
        if _tag is None:
            raise RequestError(f"Error parsing the tag passed to read() - {tag}")

        message_request = [
            self._msg_start(),
            # page 83 of eip manual
            SLC_CMD_CODE,  # request command code
            b"\x00",  # status code
            UINT.encode(next(self._sequence)),  # transaction identifier
            SLC_FNC_READ,  # function code
            USINT.encode(PCCC_DATA_SIZE[_tag["file_type"]] * _tag["element_count"]),  # byte size
            USINT.encode(int(_tag["file_number"])),
            PCCC_DATA_TYPE[_tag["file_type"]],
            USINT.encode(int(_tag["element_number"])),
            USINT.encode(int(_tag.get("pos_number", 0))),  # sub-element number
        ]

        request = SendUnitDataRequestPacket(self._sequence)
        request.add(b"".join(message_request))
        response = self.send(request)
        self.__log.debug(f"SLC read_tag({tag})")
        

        status = request_status(response.raw)

        if status is not None:
            return Tag(_tag["tag"], None, _tag["file_type"], status)

        try:
            return _parse_read_reply(_tag, response.raw[SLC_REPLY_START:])
        except ResponseError as err:
            self.__log.exception(f'Failed to parse read reply for {_tag["tag"]}')
            return Tag(_tag["tag"], None, _tag["file_type"], str(err))

    @with_forward_open
    def write(self, *address_values: Tuple[str, TagValueType]) -> ReadWriteReturnType:
        """
        Write values to data file addresses.  To write to multiple words in a file use curly braces in the address
        to indicate the number of words, then set the value to a list of values to write e.g. ``('N120:10{10}', [1, 2, ...])``.

        Does not track request/response size like the CLXDriver.


        :param address_values: one or many 2-element tuples of (address, value)
        :return: a single or list of ``Tag`` objects
        """
        results = [self._write_tag(tag, value) for tag, value in address_values]

        if len(results) == 1:
            return results[0]

        return results

    def _write_tag(self, tag: str, value: TagValueType) -> Tag:
        """write tag from a connected plc
        Possible combination can be passed to this method:
            c.write_tag('N7:0', [-30, 32767, -32767])
            c.write_tag('N7:0', 21)
            c.read_tag('N7:0', 10)
        It is not possible to write status bit
        :return: None is returned in case of error
        """
        _tag = parse_tag(tag)
        if _tag is None:
            raise RequestError(f"Error parsing the tag passed to write() - {tag}")

        _tag["data_size"] = PCCC_DATA_SIZE[_tag["file_type"]]

        message_request = [
            self._msg_start(),
            SLC_CMD_CODE,
            b"\x00",
            UINT.encode(next(self._sequence)),
            SLC_FNC_WRITE,
            USINT.encode(_tag["data_size"] * _tag["element_count"]),
            USINT.encode(int(_tag["file_number"])),
            PCCC_DATA_TYPE[_tag["file_type"]],
            USINT.encode(int(_tag["element_number"])),
            USINT.encode(int(_tag.get("pos_number", 0))),
            writeable_value(_tag, value),
        ]
        request = SendUnitDataRequestPacket(self._sequence)
        request.add(b"".join(message_request))
        response = self.send(request)

        status = request_status(response.raw)
        if status is not None:
            return Tag(_tag["tag"], None, _tag["file_type"], status)

        return Tag(_tag["tag"], value, _tag["file_type"], None)

    @with_forward_open
    def get_processor_type(self):

        msg_request = (
            self._msg_start(),
            # diagnostic status - CMD 06, FNC 03 - pg93 DF1 manual (1770-rm516)
            b"\x06",  # CMD
            b"\x00",  # status code
            UINT.encode(next(self._sequence)),  # transaction identifier
            b"\x03",  # FNC
        )

        request = SendUnitDataRequestPacket(self._sequence)
        request.add(b"".join(msg_request))
        response = self.send(request)
        if response:
            try:
                typ = response.raw[SLC_REPLY_START:][5:16].decode("utf-8").strip()
            except Exception as err:
                self.__log.exception(f"failed getting processor type: {err}")
                typ = None
            finally:
                return typ
        else:
            self.__log.error(
                f"failed to get processor type: {request_status(response.raw)}",
            )
            return None
        
    @with_forward_open
    def get_datalog_queue(self, num_data_logs, queue_num):
        data = []
        
        for i in range(num_data_logs):        
            data.append(self._get_datalog(queue_num))
        
        #extra read to clear the queue
        #will thow error in _get_datalog due to Status == None
        trash = self._get_datalog(queue_num)
        
        if data is not None:
            return data
        else:
            raise ResponseError("No Data in Queue")
        raise ResponseError("Failed to read processor type")
        
    def _get_datalog(self, queue_num):
        msg_request = [
            b"\x4b",            # Ethernet/IP Service Code
            b"\x02",            # Request Path Size, 2 words
            b"\x20",            # Request Path, Path Segment (8-bit Class)
            b"\x67",            # Request Path, Path Segment, Class (PCCC Class)
            b"\x24",            # Request Path, Path Segment (8 Bit Instance)
            b"\x01",            # Request Path, Path Segment, Instance 
            b"\x07",            # Requestor ID, Length
            b"\x4d\x00",        # Requestor ID, CIP Vendor ID
            b"\xa1\x4e\xc3\x30",# Requestor ID, CIP Serial Number
            b"\x0f",            # PCCC Command Data, CMD code
            b"\x00",            # PCCC Command Data, Status Code
            b"\x30\x00",         # PCCC Command Data, Transaction Code
            b"\xa2",            # PCCC Command Data, Function Code
            b"\x6d",            # Function Specific Data, Byte Size
            b"\x00",            # Function Specific Data, File Number
            b"\xa5",            # Function Specific Data, File Type
            USINT.encode(queue_num), # Function Specific Data, Element Number (queue to be read)
            b"\x00",            # Function Specific Data, Sub-Element Number
        ]
        
        request = SendUnitDataRequestPacket(self._sequence)
        request.add(b"".join(msg_request))
        response = self.send(request)

        status = request_status(response.raw)
        
        if status is None:
            try:
                datalog_entry = response.raw[SLC_REPLY_START:]
                datalog_entry = datalog_entry.decode("UTF-8")
            except Exception as err:
                self.__log.exception("Failed to retreive data log")
            finally:
                return datalog_entry
        else:
            self.__log.error(
                f"Failed to retreive data log",
            )
            return None
        
    
    @with_forward_open
    def get_file_directory(self):
        plc_type = self.get_processor_type()

        if plc_type is not None:
            sys0_info = _get_sys0_info(plc_type)
            # file_type, element = _get_file_and_element_for_plc_type(plc_type)
            sys0_info["size"] = self._get_file_directory_size(sys0_info)
            
            if sys0_info["size"] is not None:
                data = self._read_whole_file_directory(sys0_info)
                return _parse_file0(sys0_info, data)
            else:
                raise ResponseError("Failed to read file directory size")
        else:
            raise ResponseError("Failed to read processor type")

    def _get_file_directory_size(self, sys0_info):
        msg_request = [
            self._msg_start(),
            SLC_CMD_CODE,  # request command code
            b"\x00",  # status code
            UINT.encode(next(self._sequence)),  # transaction identifier
            b"\xa1",  # function code, from RSLinx capture
            sys0_info["size_len"],  # size
            b"\x00",  # file number
            sys0_info["file_type"],
            sys0_info["size_element"],
        ]

        request = SendUnitDataRequestPacket(self._sequence)
        request.add(b"".join(msg_request))
        response = self.send(request)
        status = request_status(response.raw)
        if status is None:
            try:
                size = UINT.decode(response.raw[SLC_REPLY_START:]) - sys0_info.get("size_const", 0)
                self.__log.debug(f"SYS 0 file size: {size}")
            except Exception as err:
                self.__log.exception("failed to parse size of File 0")
                size = None
            finally:
                return size
        else:
            self.__log.error(
                f"failed to read size of File 0: {status}",
            )
            return None

    def _read_whole_file_directory(self, sys0_info):
        file0_data = b""
        offset = 0
        file0_size = sys0_info["size"]
        file_type = sys0_info["file_type"]

        while len(file0_data) < file0_size:
            bytes_remaining = file0_size - len(file0_data)
            size = 0x50 if bytes_remaining > 0x50 else bytes_remaining

            msg_request = [
                self._msg_start(),
                # page 83 of eip manual
                SLC_CMD_CODE,  # request command code
                b"\x00",  # status code
                UINT.encode(next(self._sequence)),  # transaction identifier
                b"\xa1",
                # SLC_FNC_READ,  # function code
                USINT.encode(size),  # size
                b"\x00",  # file number
                file_type,
            ]

            msg_request += (
                [USINT.encode(offset)] if offset < 256 else [b"\xFF", UINT.encode(offset)]
            )

            request = SendUnitDataRequestPacket(self._sequence)
            request.add(b"".join(msg_request))
            response = self.send(request)
            status = request_status(response.raw)
            if status is None:
                data = response.raw[SLC_REPLY_START:]
                offset += len(data) // 2
                file0_data += data
            else:
                msg = f"Error reading File 0 contents: {status}"
                self.__log.error(msg)
                raise ResponseError(msg)

        return file0_data


def _parse_file0(sys0_info, data):
    num_data_files = data[52]
    num_lad_files = data[46]
    print(f"data files: {num_data_files}, logic files: {num_lad_files}")

    file_pos = sys0_info["file_position"]
    row_size = sys0_info["row_size"]

    data_files = {}
    file_num = 0
    while file_pos < len(data):
        file_code = data[file_pos : file_pos + 1]
        file_type = PCCC_DATA_TYPE.get(file_code, None)

        if file_type:
            file_name = f"{file_type}{file_num}"

            element_size = PCCC_DATA_SIZE.get(file_type, 2)
            file_size = UINT.decode(data[file_pos + 1 :])
            data_files[file_name] = {
                "elements": file_size // element_size,
                "length": file_size,
            }

        if file_type or file_code == b"\x81":  # 0x81 reserved type, for skipped file numbers?
            file_num += 1

        file_pos += row_size

    return data_files


def _get_sys0_info(plc_type):
    prefix = plc_type[:4]

    if prefix in {
        "1761",
    }:  # MLX1000, SLC 5/02
        # FIXME: Not sure if these are correct, never tested
        return {
            "file_position": 93,
            "row_size": 8,
            "file_type": b"\x00",
            "size_element": b"\x23",
            "size_len": b"\x04",
        }
    elif prefix in {"1763", "1762", "1764"}:  # MLX 1100, 1200, 1500
        # FIXME: values from 1100 and 1400, not tested on 1200/1500
        return {
            "file_position": 233,
            "row_size": 10,
            "file_type": b"\x02",
            "size_element": b"\x28",
            "size_len": b"\x08",
            "size_const": 19968,  # no idea why, but this seems like a const added to the size? wtf?
        }
    elif prefix in {
        "1766",
    }:  # MLX 1400
        return {
            "file_position": 233,
            "row_size": 10,
            "file_type": b"\x03",
            "size_element": b"\x2b",
            "size_len": b"\x08",
            "size_const": 19968,  # no idea why, but this seems like a const added to the size? wtf?
            "file_type_queue": b"\xA5",
        }
    else:  # SLC 5/05
        return {
            "file_position": 79,
            "row_size": 10,
            "file_type": b"\x01",
            "size_element": b"\x23",
            "size_len": b"\x04",
        }


def _parse_read_reply(tag, data) -> Tag:
    try:
        bit_read = tag.get("address_field", 0) == 3
        bit_position = int(tag.get("sub_element") or 0)
        data_size = PCCC_DATA_SIZE[tag["file_type"]]
        unpack_func = PCCCDataTypes[tag["file_type"]].decode
        if bit_read:
            new_value = 0
            if tag["file_type"] in {"T", "C"}:
                if bit_position == PCCC_CT["PRE"]:
                    return Tag(
                        tag["tag"],
                        unpack_func(data[new_value + 2 : new_value + 2 + data_size]),
                        tag["file_type"],
                        None,
                    )

                elif bit_position == PCCC_CT["ACC"]:
                    return Tag(
                        tag["tag"],
                        unpack_func(data[new_value + 4 : new_value + 4 + data_size]),
                        tag["file_type"],
                        None,
                    )

            tag_value = unpack_func(data[new_value : new_value + data_size])
            return Tag(tag["tag"], get_bit(tag_value, bit_position), tag["file_type"], None)

        else:
            values_list = [
                unpack_func(data[i : i + data_size]) for i in range(0, len(data), data_size)
            ]
            if len(values_list) > 1:
                return Tag(tag["tag"], values_list, tag["file_type"], None)
            else:
                return Tag(tag["tag"], values_list[0], tag["file_type"], None)
    except Exception as err:
        raise ResponseError("Failed parsing tag read reply") from err


def parse_tag(tag: str) -> Optional[dict]:
    t = CT_RE.search(tag)
    if (
        t
        and (1 <= int(t.group("file_number")) <= 255)
        and (0 <= int(t.group("element_number")) <= 255)
    ):
        return {
            "file_type": t.group("file_type").upper(),
            "file_number": t.group("file_number"),
            "element_number": t.group("element_number"),
            "sub_element": PCCC_CT[t.group("sub_element").upper()],
            "address_field": 3,
            "element_count": 1,
            "tag": t.group(0),
        }

    t = LFBN_RE.search(tag)
    if t:
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)

        if t.group("sub_element") is not None:
            if (
                (1 <= int(t.group("file_number")) <= 255)
                and (0 <= int(t.group("element_number")) <= 255)
                and (0 <= int(t.group("sub_element")) <= 15)
            ):
                element_count = t.group("element_count")
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": t.group("file_number"),
                    "element_number": t.group("element_number"),
                    "sub_element": t.group("sub_element"),
                    "address_field": 3,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": tag_name,
                }
        else:
            if (1 <= int(t.group("file_number")) <= 255) and (
                0 <= int(t.group("element_number")) <= 255
            ):
                element_count = t.group("element_count")
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": t.group("file_number"),
                    "element_number": t.group("element_number"),
                    "sub_element": t.group("sub_element"),
                    "address_field": 2,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": tag_name,
                }

    t = IO_RE.search(tag)
    if t:
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)
        file_number = "0" if t.group("file_type").upper() == "O" else "1"
        position_number = "0" if t.group("position_number") == None else t.group("position_number")
        if t.group("sub_element") is not None:
            if (
                (0 <= int(file_number) <= 255)
                and (0 <= int(t.group("element_number")) <= 255)
                and (0 <= int(t.group("sub_element")) <= 15)
            ):
                element_count = t.group("element_count")
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": file_number,
                    "element_number": t.group("element_number"),
                    "pos_number": position_number,
                    "sub_element": t.group("sub_element"),
                    "address_field": 3,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": tag_name,
                }
        else:
            if 0 <= int(t.group("element_number")) <= 255:
                element_count = t.group("element_count")
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": file_number,
                    "element_number": t.group("element_number"),
                    "pos_number": position_number,
                    "sub_element": 0,
                    "address_field": 2,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": tag_name,
                }

    t = ST_RE.search(tag)
    if (
        t
        and (1 <= int(t.group("file_number")) <= 255)
        and (0 <= int(t.group("element_number")) <= 255)
    ):
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)
        element_number = int(t.group("element_number"))
        element_count = t.group("element_count")
        return {
            "file_type": t.group("file_type").upper(),
            "file_number": t.group("file_number"),
            "element_number": element_number,
            "address_field": 2,
            "element_count": int(element_count) if element_count is not None else 1,
            "tag": tag_name,
        }

    t = A_RE.search(tag)
    if (
        t
        and (1 <= int(t.group("file_number")) <= 255)
        and (0 <= int(t.group("element_number")) <= 255)
    ):
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)
        element_number = int(t.group("element_number"))
        element_count = t.group("element_count")
        return {
            "file_type": t.group("file_type").upper(),
            "file_number": t.group("file_number"),
            "element_number": element_number,
            "address_field": 2,
            "element_count": int(element_count) if element_count is not None else 1,
            "tag": tag_name,
        }

    t = S_RE.search(tag)
    if t:
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)
        element_count = t.group("element_count")
        if t.group("sub_element") is not None:
            if (0 <= int(t.group("element_number")) <= 255) and (
                0 <= int(t.group("sub_element")) <= 15
            ):
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": "2",
                    "element_number": t.group("element_number"),
                    "sub_element": t.group("sub_element"),
                    "address_field": 3,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": t.group(0),
                }
        else:
            if 0 <= int(t.group("element_number")) <= 255:
                return {
                    "file_type": t.group("file_type").upper(),
                    "file_number": "2",
                    "element_number": t.group("element_number"),
                    "address_field": 2,
                    "element_count": int(element_count) if element_count is not None else 1,
                    "tag": tag_name,
                }

    t = B_RE.search(tag)
    if (
        t
        and (1 <= int(t.group("file_number")) <= 255)
        and (0 <= int(t.group("element_number")) <= 4095)
    ):
        _cnt = t.group("_elem_cnt_token")
        tag_name = t.group(0).replace(_cnt, "") if _cnt else t.group(0)
        bit_position = int(t.group("element_number"))
        element_number = bit_position / 16
        sub_element = bit_position - (element_number * 16)
        element_count = t.group("element_count")
        return {
            "file_type": t.group("file_type").upper(),
            "file_number": t.group("file_number"),
            "element_number": element_number,
            "sub_element": sub_element,
            "address_field": 3,
            "element_count": int(element_count) if element_count is not None else 1,
            "tag": tag_name,
        }

    return None


def get_bit(value: int, idx: int) -> bool:
    """:returns value of bit at position idx"""
    return (value & (1 << idx)) != 0


def writeable_value(tag: dict, value: Union[bytes, TagValueType]) -> bytes:
    if isinstance(value, bytes):
        return value
    bit_field = tag.get("address_field", 0) == 3
    bit_position = int(tag.get("sub_element") or 0) if bit_field else 0
    bit_mask = UINT.encode(2 ** bit_position) if bit_field else b"\xFF\xFF"

    element_count = tag.get("element_count") or 1
    if element_count > 1:
        if len(value) < element_count:
            raise RequestError(
                f"Insufficient data for requested elements, expected {element_count} and got {len(value)}"
            )
        if len(value) > element_count:
            value = value[:element_count]

    try:
        pack_func = PCCCDataTypes[tag["file_type"]].encode

        if element_count > 1:
            _value = b"".join(pack_func(val) for val in value)
        else:
            if bit_field:
                tag["data_size"] = 2

                if tag["file_type"] in ["T", "C"] and bit_position in {
                    PCCC_CT["PRE"],
                    PCCC_CT["ACC"],
                }:
                    bit_mask = b"\xff\xff"
                    _value = pack_func(value)
                else:
                    _value = bit_mask if value else b"\x00\x00"
            else:
                _value = pack_func(value)

    except Exception as err:
        raise RequestError(
            f'Failed to create a writeable value for {tag["tag"]} from {value}'
        ) from err

    else:
        return bit_mask + _value


def request_status(data) -> Optional[str]:
    try:
        _status_code = int(data[58])
        if _status_code == SUCCESS:
            return None
        return PCCC_ERROR_CODE.get(_status_code, "Unknown Status")
    except Exception:
        return "Unknown Status"
