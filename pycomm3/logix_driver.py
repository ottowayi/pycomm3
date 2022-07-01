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
    "LogixDriver",
]

import datetime
import logging
import operator
import time
from functools import reduce
from io import BytesIO
from typing import List, Tuple, Optional, Union, Dict, Type, Sequence

from . import util
from .cip import (
    ClassCode,
    Services,
    KEYSWITCH,
    EXTERNAL_ACCESS,
    DataTypes,
    Struct,
    STRING,
    n_bytes,
    ULINT,
    DataSegment,
    USINT,
    UINT,
    LogicalSegment,
    PADDED_EPATH,
    UDINT,
    DINT,
    Array,
    DataType,
    ArrayType,
    PortSegment,
)
from .cip_driver import CIPDriver, with_forward_open, parse_connection_path
from .const import (
    EXTENDED_SYMBOL,
    MICRO800_PREFIX,
    MULTISERVICE_READ_OVERHEAD,
    SUCCESS,
    INSUFFICIENT_PACKETS,
    BASE_TAG_BIT,
    MIN_VER_INSTANCE_IDS,
    SEC_TO_US,
    TEMPLATE_MEMBER_INFO_LEN,
    MIN_VER_EXTERNAL_ACCESS,
)
from .custom_types import (
    StructTemplateAttributes,
    StructTag,
    FixedSizeString,
    ModuleIdentityObject,
)
from .exceptions import ResponseError, RequestError
from .packets import (
    RequestPacket,
    ReadTagFragmentedRequestPacket,
    WriteTagFragmentedRequestPacket,
    ReadTagFragmentedResponsePacket,
    WriteTagFragmentedResponsePacket,
    SendUnitDataRequestPacket,
    ReadTagRequestPacket,
    WriteTagRequestPacket,
    MultiServiceRequestPacket,
    ReadModifyWriteRequestPacket,
)
from .tag import Tag

AtomicValueType = Union[int, float, bool, str]
TagValueType = Union[AtomicValueType, List[AtomicValueType], Dict[str, "TagValueType"]]
ReadWriteReturnType = Union[Tag, List[Tag]]


class LogixDriver(CIPDriver):
    """
    An Ethernet/IP Client driver for reading and writing tags in ControlLogix and CompactLogix PLCs.
    """

    __log = logging.getLogger(f"{__module__}.{__qualname__}")
    _auto_slot_cip_path = True

    def __init__(
        self,
        path: str,
        *args,
        init_tags: bool = True,
        init_program_tags: bool = True,
        **kwargs,
    ):
        """
        :param path: CIP path to intended target

            The path may contain 3 forms:

            - IP Address Only (``10.20.30.100``) - Use for a ControlLogix PLC is in slot 0 or if connecting to a CompactLogix or Micro800 PLC.
            - IP Address/Slot (``10.20.30.100/1``) - (ControlLogix) if PLC is not in slot 0
            - CIP Routing Path (``1.2.3.4/backplane/2/enet/6.7.8.9/backplane/0``) - Use for more complex routing.

            .. note::

                Both the IP Address and IP Address/Slot options are shortcuts, they will be replaced with the
                CIP path automatically.  The ``enet`` / ``backplane`` (or ``bp``) segments are symbols for the CIP routing
                port numbers and will be replaced with the correct value.

        :param init_tags: if True (default), uploads all controller-scoped tag definitions on connect
        :param init_program_tags: if False, bypasses uploading program-scoped tags. set to False if there are a lot of program tags and you aren't
                using any of them to decrease tag upload times.

        .. tip::

            Initialization of tags is required for the :meth:`.read` and :meth:`.write` to work.  This is because
            they require information about the data type and structure of the tags inside the controller.  If opening
            multiple connections to the same controller, you may disable tag initialization in all but the first connection
            and set ``plc2._tags = plc1.tags`` to prevent needing to upload the tag definitions multiple times.

        """

        super().__init__(path, *args, **kwargs)
        self._cache = None
        self._data_types = {}
        self._tags = {}
        self._micro800 = False
        self._cfg["use_instance_ids"] = True
        self._init_args = {
            "init_tags": init_tags,
            "init_program_tags": init_program_tags,
        }

    def __str__(self):
        _rev = self._info.get("revision", {"major": -1, "minor": -1})
        return f'Program Name: {self._info.get("name")}, Revision: {_rev}'

    def __repr__(self):
        init_args = ", ".join(f"{k}={v}" for k, v in self._init_args.items())
        return f"{self.__class__.__name__}(path={self._cip_path}, {init_args})"

    def open(self):
        ret = super().open()
        if ret:
            self._initialize_driver(**self._init_args)
        return ret

    def _initialize_driver(self, init_tags, init_program_tags):
        self.__log.info("Initializing driver...")

        target_identity = self._list_identity()
        self.__log.debug("Identified target: %r", target_identity)
        self._micro800 = target_identity.get("product_name", "").startswith(MICRO800_PREFIX)
        self._info = self.get_plc_info()

        self._cfg["use_instance_ids"] = (
            self.revision_major >= MIN_VER_INSTANCE_IDS
        ) and not self._micro800
        if not self._micro800:
            self.get_plc_name()

        if (
            self._micro800
            and self._cfg["cip_path"]
            and isinstance(self._cfg["cip_path"][-1], PortSegment)
        ):
            self._cfg["cip_path"].pop(
                -1
            )  # strip off backplane/0 segment, not used for these processors

        if init_tags:
            self.get_tag_list(program="*" if init_program_tags else None)

        self.__log.info("Initialization complete.")

    @property
    def revision_major(self) -> int:
        """
        Returns the major revision for the PLC or 0 if not available
        """
        return self.info.get("revision", {}).get("major", 0)

    @property
    def tags(self) -> dict:
        """
        Read-only property to access all the tag definitions uploaded from the controller.
        """
        return self._tags

    @property
    def tags_json(self):
        """
        Read-only property to access all the tag definitions uploaded from the controller.
        Filters out any non-JSON serializable objects.
        """

        def _copy_datatype(src: dict):
            # copy the entire tag/data type skipping keys that have type classes in the value
            new = {k: v for k, v in src.items() if k not in {"type_class", "_struct_members"}}

            # tags or a data type internal tag need to filter the data_type too
            if isinstance(src.get("data_type"), dict):
                new["data_type"] = _copy_datatype(src["data_type"])

            # if src is from 'data_type', do each internal tag as well
            if "internal_tags" in src:
                new["internal_tags"] = {
                    k: _copy_datatype(v) for k, v in src["internal_tags"].items()
                }

            return new

        json_tags = {tag: _copy_datatype(data) for tag, data in self._tags.items()}

        return json_tags

    @property
    def data_types(self) -> dict:
        """
        Read-only property for access to all data type definitions uploaded from the controller.
        """
        return self._data_types

    @property
    def connected(self) -> bool:
        """
        Read-Only Property to check whether or not a connection is open.

        :return: True if a connection is open, False otherwise
        """
        return self._connection_opened

    @property
    def info(self) -> dict:
        """
        Property containing a dict of all the information collected about the connected PLC.

        **Fields**:

        - *vendor* - name of hardware vendor, e.g. ``'Rockwell Automation/Allen-Bradley'``
        - *product_type* - typically ``'Programmable Logic Controller'``
        - *product_code* - code identifying the product type
        - *revision* - dict of {'major': <major rev (int)>, 'minor': <minor rev (int)>}
        - *serial* - hex string of PLC serial number, e.g. ``'FFFFFFFF'``
        - *product_name* - string value for PLC device type, e.g. ``'1756-L83E/B'``
        - *keyswitch* - string value representing the current keyswitch position, e.g. ``'REMOTE RUN'``
        - *name* - string value of the current PLC program name, e.g. ``'PLCA'``

        **The following fields are added from calling** :meth:`.get_tag_list`

        - *programs* - dict of all Programs in the PLC and their routines, ``{program: {'routines': [routine, ...}...}``
        - *tasks* - dict of all Tasks in the PLC, ``{task: {'instance_id': ...}...}``
        - *modules* - dict of I/O modules in the PLC, ``{module: {'slots': {1: {'types': ['O,' 'I', 'C']}, ...}, 'types':[...]}...}``

        """
        return self._info

    @property
    def name(self) -> Optional[str]:
        """
        :return: name of PLC program
        """
        return self._info.get("name")

    @with_forward_open
    def get_plc_name(self) -> str:
        """
        Requests the name of the program running in the PLC. Uses KB `23341`_ for implementation.

        .. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

        :return:  the controller program name
        """

        try:
            response = self.generic_message(
                service=Services.get_attributes_all,
                class_code=ClassCode.program_name,
                instance=1,
                data_type=STRING,
                name="get_plc_name",
            )
            if not response:
                raise ResponseError(f"response did not return valid data - {response.error}")

            self._info["name"] = response.value
            return self._info["name"]
        except Exception as err:
            raise ResponseError("failed to get the plc name") from err

    def get_plc_info(self) -> dict:
        """
        Reads basic information from the controller, returns it and stores it in the ``info`` property.
        """

        try:
            response = self.generic_message(
                class_code=ClassCode.identity_object,
                instance=b"\x01",
                service=Services.get_attributes_all,
                data_type=ModuleIdentityObject,
                connected=False,
                unconnected_send=not self._micro800,
                name="get_plc_info",
            )

            if not response:
                raise ResponseError(f"get_plc_info did not return valid data - {response.error}")

            info = response.value
            info["keyswitch"] = KEYSWITCH.get(info["status"][0], {}).get(
                info["status"][1], "UNKNOWN"
            )
            return info
        except Exception as err:
            raise ResponseError("Failed to get PLC info") from err

    def get_plc_time(self, fmt: str = "%A, %B %d, %Y %I:%M:%S%p") -> Tag:
        """
        Gets the current time of the PLC system clock. The ``value`` attribute will be a dict containing the time in
        3 different forms, *datetime* is a Python datetime.datetime object, *microseconds* is the integer value epoch time,
        and *string* is the *datetime* formatted using ``strftime`` and the ``fmt`` parameter.

        :param fmt: format string for converting the time to a string
        :return: a Tag object with the current time
        """
        tag = self.generic_message(
            service=Services.get_attribute_list,
            class_code=ClassCode.wall_clock_time,
            instance=b"\x01",
            request_data=b"\x01\x00\x0B\x00",
            data_type=Struct(n_bytes(6), ULINT("µs")),
        )
        if tag:
            _time = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=tag.value["µs"])
            value = {
                "datetime": _time,
                "microseconds": tag.value["µs"],
                "string": _time.strftime(fmt),
            }
        else:
            value = None
        return Tag("get_plc_time", value, None, error=tag.error)

    def set_plc_time(self, microseconds: Optional[int] = None) -> Tag:
        """
        Set the time of the PLC system clock.

        :param microseconds: None to use client PC clock, else timestamp in microseconds to set the PLC clock to
        :return: Tag with status of request
        """
        if microseconds is None:
            microseconds = int(time.time() * SEC_TO_US)

        _struct = Struct(UINT, UINT, ULINT)

        return self.generic_message(
            service=Services.set_attribute_list,
            class_code=ClassCode.wall_clock_time,
            instance=b"\x01",
            request_data=_struct.encode(
                [1, 6, microseconds]
            ),  # attribute count 1, attribute #6, time
            name="set_plc_time",
        )

    @with_forward_open
    def get_tag_list(self, program: str = None, cache: bool = True) -> List[dict]:
        """
        Reads the tag list from the controller and the definition for each tag.  Definitions include tag name, tag type
        (atomic vs struct), data type (including nested definitions for structs), external access, dimensions defined (0-3)
        for arrays and their length, etc.

        .. note::

            For program scoped tags the tag['tag_name'] will be ``'Program:{program}.{tag_name}'``. This is so the tag
            list can be fed directly into the read function.


        :param program: scope to retrieve tag list, None for controller-only tags, ``'*'`` for all tags, else name of program
        :param cache: store the retrieved list in the :attr:`.tags` property.  Disable if you wish to get tags retrieved
                      to not overwrite the currently cached definition. For instance if you're checking tags in a single
                      program but currently reading controller-scoped tags.

        :return: a list containing dicts for each tag definition collected
        """

        self._cache = {
            "tag_name:id": {},
            "id:struct": {},
            "handle:id": {},
            "id:udt": {},
        }

        if program in {"*", None}:
            self._info["programs"] = {}
            self._info["tasks"] = {}
            self._info["modules"] = {}

        self.__log.info("Starting tag list upload...")
        if program == "*":
            tags = self._get_tag_list()
            for prog in self._info["programs"]:
                tags += self._get_tag_list(prog)
        else:
            tags = self._get_tag_list(program)

        if cache:
            self._tags = {tag["tag_name"]: tag for tag in tags}

        self._cache = None

        self.__log.info(f"Completed tag list upload. Uploaded {len(self._tags)} tags.")
        return tags

    def _get_tag_list(self, program=None):
        self.__log.info(f'Beginning upload of {program or "controller"} tags...')
        all_tags = self._get_instance_attribute_list_service(program)
        self.__log.info(f'Completed upload of {program or "controller"} tags')
        return self._isolate_user_tags(all_tags, program)

    def _get_instance_attribute_list_service(self, program=None):
        """Step 1: Finding user-created controller scope tags in a Logix5000 controller

        This service returns instance IDs for each created instance of the symbol class, along with a list
        of the attribute data associated with the requested attribute
        """
        try:
            last_instance = 0
            tag_list = []
            while last_instance != -1:
                # Creating the Message Request Packet
                self.__log.debug(f"Getting tags starting with instance {last_instance}")
                _start_instance = last_instance
                _num_tags_start = len(tag_list)
                segments = []
                if program:
                    if not program.startswith("Program:"):
                        program = f"Program:{program}"
                    path = [
                        EXTENDED_SYMBOL,
                        USINT.encode(len(program)),
                        program.encode("utf-8"),
                    ]
                    segments = [
                        DataSegment(program),
                    ]
                    if len(program) % 2:
                        path.append(b"\x00")

                segments += [
                    LogicalSegment(ClassCode.symbol_object, "class_id"),
                    LogicalSegment(last_instance, "instance_id"),
                ]

                new_path = PADDED_EPATH.encode(segments, length=True)
                request = SendUnitDataRequestPacket(self._sequence)

                attributes = [
                    b"\x01\x00",  # Attr. 1: Symbol name
                    b"\x02\x00",  # Attr. 2 : Symbol Type
                    b"\x03\x00",  # Attr. 3 : Symbol Address
                    b"\x05\x00",  # Attr. 5 : Symbol Object Address
                    b"\x06\x00",  # Attr. 6 : ? - Not documented (Software Control?)
                    b"\x08\x00",  # Attr. 8 : array dimensions [1,2,3]
                ]

                if self.revision_major >= MIN_VER_EXTERNAL_ACCESS:
                    attributes.append(b"\x0a\x00")  # Attr. 10 : external access

                request.add(
                    Services.get_instance_attribute_list,
                    new_path,
                    UINT.encode(len(attributes)),
                    *attributes,
                )
                response = self.send(request)
                if not response:
                    raise ResponseError(
                        f"send_unit_data returned not valid data - {response.error}"
                    )

                last_instance = self._parse_instance_attribute_list(response, tag_list)
                self.__log.debug(
                    f"Uploaded {len(tag_list) - _num_tags_start} tags, last instance: {last_instance}"
                )

            return tag_list

        except Exception as err:
            raise ResponseError("failed to get attribute list") from err

    def _parse_instance_attribute_list(self, response, tag_list):
        """extract the tags list from the message received"""

        stream = BytesIO(response.data)
        tags_returned_length = stream.getbuffer().nbytes
        count = instance = 0
        # TODO: turn this into an array of struct with new types
        try:
            while stream.tell() < tags_returned_length:
                instance = UDINT.decode(stream)
                tag_name = STRING.decode(stream)
                symbol_type = UINT.decode(stream)
                count += 1
                symbol_address = UDINT.decode(stream)
                symbol_object_address = UDINT.decode(stream)
                software_control = UDINT.decode(stream)
                dim1 = UDINT.decode(stream)
                dim2 = UDINT.decode(stream)
                dim3 = UDINT.decode(stream)

                if self.revision_major >= MIN_VER_EXTERNAL_ACCESS:
                    access = USINT.decode(stream)
                else:
                    access = None

                tag_list.append(
                    {
                        "instance_id": instance,
                        "tag_name": tag_name,
                        "symbol_type": symbol_type,
                        "symbol_address": symbol_address,
                        "symbol_object_address": symbol_object_address,
                        "software_control": software_control,
                        "external_access": EXTERNAL_ACCESS.get(access, "Unknown"),
                        "dimensions": [dim1, dim2, dim3],
                    }
                )

        except Exception as err:
            raise ResponseError("failed to parse instance attribute list") from err

        if response.service_status == SUCCESS:
            return -1
        elif response.service_status == INSUFFICIENT_PACKETS:
            return instance + 1
        else:
            self.__log.warning("unknown status during _parse_instance_attribute_list")
            return -1

    def _isolate_user_tags(self, all_tags, program=None):
        try:
            user_tags = []
            self.__log.debug(f'Isolating user tags for {program or "controller"} ...')
            for tag in all_tags:
                io_tag = False
                name = tag["tag_name"]

                if name.startswith("Program:"):
                    prog_name = name.replace("Program:", "")
                    self._info["programs"][prog_name] = {
                        "instance_id": tag["instance_id"],
                        "routines": [],
                    }
                    continue

                if name.startswith("Routine:"):
                    rtn_name = name.replace("Routine:", "")
                    _program = self._info["programs"].get(program)
                    if _program is None:
                        self.__log.error(f"Program {program} not defined in tag list")
                    else:
                        _program["routines"].append(rtn_name)
                    continue

                if name.startswith("Task:"):
                    self._info["tasks"][name.replace("Task:", "")] = {
                        "instance_id": tag["instance_id"]
                    }
                    continue

                # system tags that may interfere w/ finding I/O modules
                if "Map:" in name or "Cxn:" in name:
                    continue

                # I/O module tags
                # Logix 5000 Controllers I/O and Tag Data, page 17  (1756-pm004_-en-p.pdf)
                if any(x in name for x in (":I", ":O", ":C", ":S")):
                    io_tag = True
                    mod = name.split(":")
                    mod_name = mod[0]
                    if mod_name not in self._info["modules"]:
                        self._info["modules"][mod_name] = {"slots": {}}
                    if len(mod) == 3 and mod[1].isdigit():
                        mod_slot = int(mod[1])
                        if mod_slot not in self._info["modules"][mod_name]:
                            self._info["modules"][mod_name]["slots"][mod_slot] = {"types": []}
                        self._info["modules"][mod_name]["slots"][mod_slot]["types"].append(mod[2])
                    elif len(mod) == 2:
                        if "types" not in self._info["modules"][mod_name]:
                            self._info["modules"][mod_name]["types"] = []
                        self._info["modules"][mod_name]["types"].append(mod[1])
                    # Not sure if this branch will ever be hit, but added to see if above branches may need additional work
                    else:
                        if "__UNKNOWN__" not in self._info["modules"][mod_name]:
                            self._info["modules"][mod_name]["__UNKNOWN__"] = []
                        self._info["modules"][mod_name]["__UNKNOWN__"].append(":".join(mod[1:]))

                # other system or junk tags
                if (not io_tag and ":" in name) or name.startswith("__"):
                    continue
                if tag["symbol_type"] & 0b0001_0000_0000_0000:
                    continue

                if program is not None:
                    name = f"Program:{program}.{name}"

                self._cache["tag_name:id"][name] = tag["instance_id"]

                user_tags.append(self._create_tag(name, tag))

            self.__log.debug(f'Finished isolating tags for {program or "controller"}')
            return user_tags
        except Exception as err:
            raise ResponseError("failed isolating user tags") from err

    def _create_tag(self, name, raw_tag):
        copy_keys = [
            "instance_id",
            "symbol_address",
            "symbol_object_address",
            "software_control",
            "external_access",
            "dimensions",
        ]
        new_tag = {
            "tag_name": name,
            "dim": (raw_tag["symbol_type"] & 0b0110000000000000)
            >> 13,  # bit 13 & 14, number of array dims
            "alias": False if raw_tag["software_control"] & BASE_TAG_BIT else True,
            **{k: raw_tag[k] for k in copy_keys},
        }

        if raw_tag["symbol_type"] & 0b_1000_0000_0000_0000:  # bit 15, 1 = struct, 0 = atomic
            template_instance_id = raw_tag["symbol_type"] & 0b_0000_1111_1111_1111
            tag_type = "struct"
            new_tag["template_instance_id"] = template_instance_id
            new_tag["data_type"] = self._get_data_type(template_instance_id, raw_tag["symbol_type"])
            new_tag["data_type_name"] = new_tag["data_type"]["name"]
        else:
            tag_type = "atomic"
            datatype = raw_tag["symbol_type"] & 0b_0000_0000_1111_1111
            new_tag["data_type"] = DataTypes.get(datatype)
            new_tag["data_type_name"] = new_tag["data_type"]
            new_tag["type_class"] = DataTypes.get(new_tag["data_type"])
            if datatype == DataTypes.bool.code:  # TODO: make sure this is right
                new_tag["bit_position"] = (raw_tag["symbol_type"] & 0b_0000_0111_0000_0000) >> 8

        _type_class = (
            new_tag["data_type"]["type_class"]
            if tag_type == "struct"
            else DataTypes.get(new_tag["data_type"])
        )

        if new_tag["dim"]:
            total_elements = reduce(operator.mul, new_tag["dimensions"][: new_tag["dim"]], 1)
            type_class = Array(length_=total_elements, element_type_=_type_class)
        else:
            type_class = _type_class

        new_tag["tag_type"] = tag_type
        new_tag["type_class"] = type_class

        return new_tag

    def _get_structure_makeup(self, instance_id):
        """
        get the structure makeup for a specific structure
        """
        if instance_id not in self._cache["id:struct"]:
            attrs = (
                b"\x04\x00",  # Number of attributes
                b"\x04\x00",  # Template Object Definition Size UDINT
                b"\x05\x00",  # Template Structure Size UDINT
                b"\x02\x00",  # Template Member Count UINT
                b"\x01\x00",  # Structure Handle We can use this to read and write UINT
            )

            response = self.generic_message(
                service=Services.get_attribute_list,
                class_code=ClassCode.template_object,
                instance=instance_id,
                connected=True,
                request_data=b"".join(attrs),
                data_type=StructTemplateAttributes,
                name=f"_get_structure_makeup(instance_id={instance_id!r})",
            )
            if not response:
                raise ResponseError("send_unit_data returned not valid data", response.error)
            _struct = _parse_structure_makeup_attributes(response)
            self._cache["id:struct"][instance_id] = _struct
            self._cache["handle:id"][_struct["structure_handle"]] = instance_id

        return self._cache["id:struct"][instance_id]

    def _read_template(self, instance_id, object_definition_size):
        """get a list of the tags in the plc"""

        offset = 0
        template_raw = b""
        try:
            while True:
                response = self.generic_message(
                    service=Services.read_tag,
                    class_code=ClassCode.template_object,
                    instance=instance_id,
                    request_data=b"".join(
                        (
                            DINT.encode(offset),
                            UINT.encode(((object_definition_size * 4) - 21) - offset),
                        )
                    ),
                    name=f"_read_template(instance_id={instance_id}, object_definition_size={object_definition_size})",
                    return_response_packet=True,
                )
                response_pkt = response.value
                if response_pkt.service_status not in (SUCCESS, INSUFFICIENT_PACKETS):
                    raise ResponseError("Error reading template", response)

                template_raw += response_pkt.data

                if response_pkt.service_status == SUCCESS:
                    break

                offset += len(response_pkt.data)

        except Exception as err:
            raise ResponseError("Failed to read template") from err
        else:
            return template_raw

    def _parse_template_data(self, data, template, symbol_type):
        info_len = template["member_count"] * TEMPLATE_MEMBER_INFO_LEN
        info_data = data[:info_len]
        self.__log.debug(f"Parsing template {template!r} from {data!r}")

        chunks = (
            info_data[i : i + TEMPLATE_MEMBER_INFO_LEN]
            for i in range(0, info_len, TEMPLATE_MEMBER_INFO_LEN)
        )

        member_data = [self._parse_template_data_member_info(chunk) for chunk in chunks]

        member_names = []
        template_name = None
        try:
            for name in (
                x.decode(errors="replace") for x in data[info_len:].split(b"\x00")
            ):
                if template_name is None and ";" in name:
                    template_name, _ = name.split(";", maxsplit=1)
                else:
                    member_names.append(name)
        except ValueError as err:
            raise ResponseError("Unable to decode template or member names") from err

        _type = symbol_type & 0b_0000_1111_1111_1111

        # range of non-predefined structs is 0x100 - 0xEFF according to spec
        # so if outside that range assume it is a predefined type
        predefine = _type < 0x100 or _type > 0xEFF
        if predefine and template_name is None:  # predefined types put name as first member (DWORD)
            template_name = member_names.pop(0)

        if template_name == "ASCIISTRING82":  # internal name for STRING builtin type
            template_name = "STRING"

        data_type = {
            "name": template_name,
            "internal_tags": {},
            "attributes": [],
            "template": template,
        }

        _struct_members = []
        _bit_members = {}
        _private_members = set()
        _unk_member_count = 0
        for member, info in zip(member_names, member_data):
            if not member:  # handle unnamed private members
                member = f'__unknown{_unk_member_count}'  # double-underscore makes it 'private'
                _unk_member_count += 1
            if (
                member.startswith("ZZZZZZZZZZ") or
                member.startswith("__") or
                (predefine and member in {"CTL", "Control"})
            ):
                _private_members.add(member)
            else:
                data_type["attributes"].append(member)

            data_type["internal_tags"][member] = info

            if info["data_type_name"] == "BOOL" and 'bit' in info:
                # bit members aren't really 'struct' members since they are aliased to bits of other members
                _bit_members[member] = (info['offset'], info['bit'])
            else:
                _struct_members.append((info["type_class"](member), info["offset"]))

        if (  # determine if struct is a string or not
            data_type["attributes"] == ["LEN", "DATA"]
            and data_type["internal_tags"]["DATA"]["data_type_name"] == "SINT"
            and data_type["internal_tags"]["DATA"].get("array")
        ):
            data_type["string"] = data_type["internal_tags"]["DATA"]["array"]

            data_type["type_class"] = FixedSizeString(template["structure_size"] - 4)
        else:
            data_type["_struct_members"] = (_struct_members, _bit_members)
            data_type["type_class"] = StructTag(
                *_struct_members,
                bit_members=_bit_members,
                struct_size=template["structure_size"],
                private_members=_private_members,
            )

        self.__log.debug(f"Completed parsing template as data type {data_type!r}")

        return data_type

    def _parse_template_data_member_info(self, info):
        stream = BytesIO(info)
        type_info = UINT.decode(stream)
        typ = UINT.decode(stream)
        member = {"offset": UDINT.decode(stream)}
        tag_type = "atomic"

        data_type = DataTypes.get(typ)
        if data_type:
            type_class = DataTypes.get_type(typ)
        if data_type is None:
            instance_id = typ & 0b0000_1111_1111_1111
            type_class = DataTypes.get_type(instance_id)
            if type_class:
                data_type = str(type_class)
        if data_type is None:
            tag_type = "struct"
            data_type = self._get_data_type(instance_id, typ)
            type_class = data_type["type_class"]

        member["tag_type"] = tag_type
        member["data_type"] = data_type
        member["data_type_name"] = data_type["name"] if tag_type == "struct" else data_type

        if data_type == "BOOL":
            member["bit"] = type_info
        elif data_type is not None:
            member["array"] = type_info
            if type_info:
                type_class = Array(length_=type_info, element_type_=type_class)

        member["type_class"] = type_class

        return member

    def _get_data_type(self, instance_id, symbol_type):
        if instance_id not in self._cache["id:udt"]:
            try:
                self.__log.debug(f"Getting data type for id {instance_id}")
                template = self._get_structure_makeup(instance_id)  # instance id from type
                if not template.get("error"):
                    _data = self._read_template(instance_id, template["object_definition_size"])
                    data_type = self._parse_template_data(_data, template, symbol_type)
                    self._cache["id:udt"][instance_id] = data_type
                    self._data_types[data_type["name"]] = data_type
                    self.__log.debug(f'Got data type {data_type["name"]} for id {instance_id}')
            except Exception as err:
                raise ResponseError(
                    f"Failed to get data type information for {instance_id}"
                ) from err

        return self._cache["id:udt"][instance_id]

    @with_forward_open
    def read(self, *tags: str) -> ReadWriteReturnType:
        """
        Read the value of tag(s).  Automatically will split tags into multiple requests by tracking the request and
        response size.  Will use the multi-service request to group many tags into a single packet and also will automatically
        use fragmented read requests if the response size will not fit in a single packet.  Supports arrays (specify element
        count in using curly braces (array{10}).  Also supports full structure reading (when possible), return value
        will be a dict of {attribute name: value}.

        :param tags: one or many tags to read
        :return: a single or list of ``Tag`` objects
        """

        parsed_requests = self._parse_requested_tags(tags, "r")
        requests = self._read_build_requests(parsed_requests)
        read_results = self._send_requests(requests)

        results = []

        for i, tag in enumerate(tags):
            try:
                request_data = parsed_requests[i]
                if request_data.get("error"):
                    results.append(Tag(tag, None, None, request_data["error"]))
                    continue

                result = read_results[i]
                bool_elements = request_data["bool_elements"]
                if result:
                    bit = request_data.get("bit")

                    if request_data["tag_info"]["data_type_name"] != "DWORD":
                        if bit is not None:
                            result = Tag(
                                request_data["user_tag"],
                                bool(result.value & 1 << bit),
                                "BOOL",
                                result.error,
                            )
                    else:
                        bit = bit or 0
                        if bool_elements is not None:
                            bools = result.value[bit : bit + bool_elements]
                            data_type = f"BOOL[{bool_elements}]"
                            result = Tag(request_data["user_tag"], bools, data_type, result.error)
                        else:
                            val = result.value[bit]
                            result = Tag(request_data["user_tag"], val, "BOOL", result.error)
                else:
                    result = Tag(request_data["user_tag"], None, None, result.error)

                results.append(result)

            except Exception as err:
                self.__log.exception("Invalid tag request")
                results.append(Tag(tag, None, None, f"Invalid tag request - {err!r}"))

        if len(tags) > 1:
            return results
        else:
            return results[0]

    def _read_build_requests(self, parsed_tags):
        if len(parsed_tags) != 1 and not self._micro800:
            return self._read_build_multi_requests(parsed_tags)
        requests = (
            self._read_build_single_request(parsed_tags[request_id]) for request_id in parsed_tags
        )
        return [r for r in requests if r is not None]

    def _read_build_multi_requests(self, parsed_tags):
        """
        creates a list of multi-request packets
        """
        multi_requests = []
        fragmented_requests = []
        read_requests = []  # [ (request, response_size), ...]
        for request_id, tag_data in parsed_tags.items():
            if tag_data.get("error"):
                self.__log.error(
                    f'Skipping making request for {tag_data["request_tag"]}, error: {tag_data.get("error")}'
                )
                continue

            request = ReadTagRequestPacket(
                self._sequence,
                tag_data["plc_tag"],
                tag_data["elements"],
                tag_data["tag_info"],
                request_id,
                self._cfg["use_instance_ids"],
            )
            request.build_message()
            # TODO: this isn't very accurate right now, the message len is not part of the response
            # so we may be fragmenting more than needed
            return_size = (
                _tag_return_size(tag_data) + len(request.message) + 2
            )  # response overhead  # TODO make const
            if return_size > self.connection_size:
                request = ReadTagFragmentedRequestPacket.from_request(self._sequence, request)
                fragmented_requests.append(request)
            else:
                read_requests.append((request, return_size))

        # TODO: this should try and combine these into the fewest packets
        grouped_requests = [[]]
        current_group = grouped_requests[0]
        current_response_size = MULTISERVICE_READ_OVERHEAD
        for req, resp_size in read_requests:
            if current_response_size + resp_size > self.connection_size:
                current_group = []
                grouped_requests.append(current_group)
                current_response_size = MULTISERVICE_READ_OVERHEAD

            current_group.append(req)
            current_response_size += resp_size

        # test if the first list is empty
        if grouped_requests[0]:
            multi_requests = [
                MultiServiceRequestPacket(self._sequence, group) for group in grouped_requests
            ]

        return multi_requests + fragmented_requests

    def _read_build_single_request(self, parsed_tag):
        """
        creates a single read_tag request packet
        """

        if parsed_tag.get("error") is None:
            request = ReadTagRequestPacket(
                self._sequence,
                parsed_tag["plc_tag"],
                parsed_tag["elements"],
                parsed_tag["tag_info"],
                parsed_tag["request_id"],
                self._cfg["use_instance_ids"],
            )

            return_size = _tag_return_size(parsed_tag) + len(request.message)
            if return_size > self.connection_size:
                request = ReadTagFragmentedRequestPacket.from_request(self._sequence, request)

            return request

        self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
        return None

    @with_forward_open
    def write(
        self, *tags_values: Union[str, TagValueType, Tuple[str, TagValueType]]
    ) -> ReadWriteReturnType:
        """
        Write to tag(s). Automatically will split tags into multiple requests by tracking the request and
        response size.  Will use the multi-service request to group many tags into a single packet and also will automatically
        use fragmented read requests if the response size will not fit in a single packet.  Supports arrays (specify element
        count in using curly braces (array{10}).  Also supports full structure writing (when possible), value must be a
        sequence of values or a dict of {attribute: value} matching the exact structure of the destination tag.

        :param tags_values: (tag, value) tuple or sequence of tag and value tuples [(tag, value), ...]
        :return: a single or list of ``Tag`` objects.
        """

        if len(tags_values) == 2 and isinstance(tags_values[0], str):
            tags_values = ((*tags_values,),)

        tags = (tag for (tag, value) in tags_values)
        parsed_requests = self._parse_requested_tags(tags, "w")

        for i, (tag, value) in enumerate(tags_values):
            parsed_requests[i]["value"] = value

        requests = self._write_build_requests(parsed_requests)
        write_results = self._send_requests(requests)

        for r in requests:
            if isinstance(r, ReadModifyWriteRequestPacket):
                result = write_results.pop(r.request_id)
                for req_id in r._request_ids:
                    write_results[req_id] = result

        results = []
        for i, (tag, value) in enumerate(tags_values):
            try:
                request_data = parsed_requests[i]
                if request_data.get("error"):
                    results.append(Tag(tag, None, None, request_data["error"]))
                    continue

                bit = parsed_requests[i].get("bit")
                result = write_results[i]
                data_type = request_data["tag_info"]["data_type_name"]
                bool_elements = request_data["bool_elements"]

                if bit is not None and bool_elements is None:
                    data_type = "BOOL"
                elif bool_elements:
                    data_type = f"BOOL[{bool_elements}]"
                elif request_data["elements"] > 1:
                    data_type = f'{data_type}[{request_data["elements"]}]'

                user_result = Tag(request_data["user_tag"], value, data_type, result.error)

                results.append(user_result)
            except Exception as err:
                self.__log.exception("Invalid tag request")
                results.append(Tag(tag, None, None, f"Invalid tag request - {err!r}"))

        if len(tags_values) > 1:
            return results
        else:
            return results[0]

    def _write_build_requests(self, parsed_tags):
        if len(parsed_tags) != 1 and not self._micro800:
            return self._write_build_multi_requests(parsed_tags)

        # micro800 don't support multi-request packets
        requests = (self._write_build_single_request(parsed_tags[tag]) for tag in parsed_tags)
        return [r for r in requests if r is not None]

    def _write_build_multi_requests(self, parsed_tags):
        fragmented_requests = []
        write_requests = []
        bit_writes = {}

        for request_id, tag_data in parsed_tags.items():
            if tag_data.get("error") is None:

                bit = tag_data.get("bit")
                data_type = tag_data["tag_info"]["data_type_name"]
                if bit is not None and tag_data["bool_elements"] is None:
                    if tag_data["plc_tag"] not in bit_writes:

                        request = ReadModifyWriteRequestPacket(
                            self._sequence,
                            tag_data["plc_tag"],
                            tag_data["tag_info"],
                            -1 * (1 + len(bit_writes)),
                            self._cfg["use_instance_ids"],
                        )
                        bit_writes[tag_data["plc_tag"]] = request
                    else:
                        request = bit_writes[tag_data["plc_tag"]]

                    request.set_bit(bit, tag_data["value"], tag_data["request_id"])
                    continue

                try:
                    tag_data["write_value"] = encode_value(tag_data)
                except Exception as err:
                    tag_data["error"] = f"Error encoding value - {err!r}"
                    continue

                request = WriteTagRequestPacket(
                    self._sequence,
                    tag_data["plc_tag"],
                    tag_data["elements"],
                    tag_data["tag_info"],
                    request_id,
                    self._cfg["use_instance_ids"],
                    tag_data["write_value"],
                )
                request.build_message()
                request._msg_setup = False

                req_size = len(request.message)
                if req_size > self.connection_size:
                    request = WriteTagFragmentedRequestPacket.from_request(self._sequence, request)
                    fragmented_requests.append(request)
                else:
                    write_requests.append(request)

        grouped_requests = [
            [],
        ]
        current_group = grouped_requests[0]
        current_response_size = MULTISERVICE_READ_OVERHEAD
        for req in write_requests:
            if current_response_size + len(req.message) > self.connection_size:
                current_group = []
                grouped_requests.append(current_group)
                current_response_size = MULTISERVICE_READ_OVERHEAD

            current_group.append(req)
            current_response_size += len(req.message)

        multi_requests = [
            MultiServiceRequestPacket(
                self._sequence,
                group,
            )
            for group in grouped_requests
            if group
        ]

        return multi_requests + fragmented_requests + [request for request in bit_writes.values()]

    def _write_build_single_request(self, parsed_tag):
        if parsed_tag.get("error"):
            self.__log.error(f'Skipping making request, error: {parsed_tag["error"]}')
            return None

        try:
            bit = parsed_tag.get("bit")
            data_type = parsed_tag["tag_info"]["data_type_name"]
            if bit is not None and parsed_tag["bool_elements"] is None:
                request = ReadModifyWriteRequestPacket(
                    self._sequence,
                    parsed_tag["plc_tag"],
                    parsed_tag["tag_info"],
                    -1,
                    self._cfg["use_instance_ids"],
                )

                request.set_bit(bit, parsed_tag["value"], parsed_tag["request_id"])
            else:
                parsed_tag["write_value"] = encode_value(parsed_tag)

                request = WriteTagRequestPacket(
                    self._sequence,
                    parsed_tag["plc_tag"],
                    parsed_tag["elements"],
                    parsed_tag["tag_info"],
                    parsed_tag["request_id"],
                    self._cfg["use_instance_ids"],
                    parsed_tag["write_value"],
                )
                request.build_message()
                request._msg_setup = False

                req_size = len(parsed_tag["write_value"]) + len(request.message)
                if req_size > self.connection_size:
                    request = WriteTagFragmentedRequestPacket.from_request(self._sequence, request)

            return request
        except RequestError as err:
            parsed_tag["error"] = f"Invalid Tag Request - {err!r}"
            self.__log.exception(f'Failed to build request for {parsed_tag["plc_tag"]} - skipping')
            return None

    def get_tag_info(self, tag_name: str) -> Optional[dict]:
        """
        Returns the tag information for a tag collected during the tag list upload.  Can be a base tag or an attribute.

        :param tag_name: name of tag to get info for
        :return: a dict of the tag's definition

        """
        base, *attrs = tag_name.split(".")
        if base.startswith("Program:"):
            base = f"{base}.{attrs.pop(0)}"
        return self._get_tag_info(base, attrs)

    def _get_tag_info(self, base, attrs) -> Optional[dict]:
        def _recurse_attrs(attrs, data):
            cur, *remain = attrs
            curr_tag = util.strip_array(cur)
            if not len(remain):
                return data[curr_tag]
            else:
                if curr_tag in data:
                    return _recurse_attrs(remain, data[curr_tag]["data_type"]["internal_tags"])
                else:
                    return None

        try:
            data = self._tags[util.strip_array(base)]
            if not len(attrs):
                return data
            else:
                return _recurse_attrs(attrs, data["data_type"]["internal_tags"])

        except KeyError as err:
            raise RequestError(f"Tag doesn't exist - {err.args[0]}")

        except Exception as err:
            _msg = f"failed to get tag data for: {base}, {attrs}"
            self.__log.exception(_msg)
            raise RequestError(_msg) from err

    def _parse_requested_tags(self, tags, rw="r"):

        requests = {}
        for i, tag in enumerate(tags):
            parsed = {"request_id": i, "request_tag": tag}
            try:
                parsed_request = self._parse_tag_request(tag, rw)
                if parsed_request is not None:
                    parsed.update(parsed_request)

            except RequestError as err:
                self.__log.exception(f"Failed to parse tag request: {tag}")
                parsed["error"] = str(err)

            finally:
                requests[i] = parsed
        return requests

    def _parse_tag_request(self, tag: str, rw="r") -> dict:
        """
        rw: read/write - because of how bool arrays always read from 0, but writing doesn't
        """
        try:
            if tag.endswith("}") and "{" in tag:
                tag, _tmp = tag.split("{")
                elements = int(_tmp[:-1])
                implicit_element = False
            else:
                elements = 1
                implicit_element = True

            request_tag = tag
            bit = None
            bool_elements = None

            base, *attrs = tag.split(".")
            if base.startswith("Program:"):
                base = f"{base}.{attrs.pop(0)}"

            if len(attrs) and attrs[-1].isdigit():
                bit = int(attrs.pop(-1))
                tag = base if not len(attrs) else f"{base}.{'.'.join(attrs)}"

            tag_info = self._get_tag_info(base, attrs)

            if tag_info["data_type"] == "DWORD":
                _tag, idx = util.get_array_index(tag)
                if idx is not None:
                    tag = f"{_tag}[0]" if rw == "r" else f"{_tag}[{idx // 32}]"
                bit = idx
                bool_elements = None if implicit_element or elements == 1 else elements
                total_size = (bit or 0) + elements
                elements = (total_size // 32) + (1 if total_size % 32 else 0)

            return {
                "user_tag": request_tag,  # tag name from user, without element request
                "plc_tag": tag,  # parsed tag name, the name of the tag in the plc the request will be using
                "bit": bit,
                "elements": elements,
                "tag_info": tag_info,
                "bool_elements": bool_elements,
            }
        except RequestError:
            raise
        except Exception as err:
            raise RequestError("Failed to parse tag request", tag) from err

    def _send_requests(self, requests):
        results = {}

        for request in requests:
            try:
                response = self.send(request)
            except (RequestError, ResponseError) as err:
                self.__log.exception("Error sending request")
                if request.type_ != "multi":
                    results[request.request_id] = Tag(request.tag, None, None, str(err))
                else:
                    for tag in request.tags:
                        results[tag["request_id"]] = Tag(tag["tag"], None, None, str(err))
            else:
                if request.type_ != "multi":
                    if response:
                        results[request.request_id] = Tag(
                            request.tag,
                            response.value if request.type_ == "read" else request.value,
                            response.data_type if request.type_ == "read" else request.data_type,
                            response.error,
                        )
                    else:
                        results[request.request_id] = Tag(request.tag, None, None, response.error)
                else:
                    for resp in response.responses:
                        req = resp.request
                        if resp:
                            results[req.request_id] = Tag(
                                resp.tag, resp.value, resp.data_type, None
                            )
                        else:
                            results[req.request_id] = Tag(
                                req.tag, None, None, req.error or resp.error
                            )
        return results

    def send(self, request: RequestPacket):
        if isinstance(request, ReadTagFragmentedRequestPacket):
            return self._send_read_fragmented(request)
        elif isinstance(request, WriteTagFragmentedRequestPacket):
            return self._send_write_fragmented(request)
        else:
            return super().send(request)

    def _send_read_fragmented(
        self, request: ReadTagFragmentedRequestPacket
    ) -> ReadTagFragmentedResponsePacket:
        if not request.error:
            offset = 0
            responses = []
            while offset is not None:
                response: ReadTagFragmentedResponsePacket = super().send(request)
                responses.append(response)
                if response.service_status == INSUFFICIENT_PACKETS:
                    offset += len(response.value_bytes)
                    request = ReadTagFragmentedRequestPacket.from_request(
                        self._sequence, request, offset
                    )
                else:
                    if response.error:
                        self.__log.error(f"Fragment failed with error: {response.error}")

                    offset = None

            if all(responses):
                final_response = responses[-1]
                final_response.value_bytes = b"".join(resp.value_bytes for resp in responses)
                final_response.parse_value()

                self.__log.debug(f"Reassembled Response: {final_response!r}")
                return final_response

        failed_response = ReadTagFragmentedResponsePacket(request, None)
        failed_response._error = request.error or "One or more fragment responses failed"
        self.__log.debug(f"Reassembled Response: {failed_response!r}")
        return failed_response

    def _send_write_fragmented(
        self, request: WriteTagFragmentedRequestPacket
    ) -> WriteTagFragmentedResponsePacket:
        if not request.error:
            responses = []
            request.build_message()
            segment_size = self.connection_size - (len(request.message) - len(request.value))
            segments = (
                request.value[i : i + segment_size]
                for i in range(0, len(request.value), segment_size)
            )

            offset = 0
            for segment in segments:
                _request = WriteTagFragmentedRequestPacket.from_request(
                    self._sequence, request, offset, segment
                )
                _response = super().send(_request)
                offset += len(segment)
                responses.append(_response)

            if all(responses):
                final_response = responses[-1]
                self.__log.debug(f"Final Response: {final_response!r}")
                return final_response

        failed_response = WriteTagFragmentedResponsePacket(request, None)
        failed_response._error = request.error or "One or more fragment responses failed"
        self.__log.debug(f"Reassembled Response: {failed_response!r}")
        return failed_response


def _parse_structure_makeup_attributes(response):
    """
    extract the tags list from the message received
    """
    structure = {}

    if not response:
        structure["error"] = response.error
        return

    try:
        _struct = response.value
        structure["object_definition_size"] = _struct["object_definition_size"]["size"]
        structure["structure_size"] = _struct["structure_size"]["size"]
        structure["member_count"] = _struct["member_count"]["count"]
        structure["structure_handle"] = _struct["structure_handle"]["handle"]

        return structure

    except Exception as err:
        raise ResponseError("failed to parse structure attributes") from err


def encode_value(parsed_tag: dict) -> bytes:
    if isinstance(parsed_tag["value"], bytes):
        return parsed_tag["value"]

    try:
        value = parsed_tag["value"]
        elements = parsed_tag["elements"]
        data_type = parsed_tag["tag_info"]["data_type_name"]
        _type: Type[DataType] = parsed_tag["tag_info"]["type_class"]

        value_elements = parsed_tag["bool_elements"] or elements
        if data_type == "DWORD":
            if (parsed_tag.get("bit") or 0) % 32:
                raise RequestError(
                    "BOOL arrays only support writing full DWORDs, indexes must be multiples of 32"
                )
            parsed_tag["elements"] = elements = elements - (parsed_tag["bit"] or 0) // 32

        if issubclass(_type, ArrayType):

            if value_elements > 1:
                if len(value) < value_elements:
                    raise RequestError(
                        f"Insufficient data for requested elements, expected {value_elements} and got {len(value)}"
                    )
                if len(value) > value_elements:
                    value = value[:value_elements]
            elif not isinstance(value, Sequence) or isinstance(value, str):
                value = [
                    value,
                ]

            return _type.encode(value, value_elements)

        return _type.encode(value)

    except Exception as err:
        raise RequestError("Unable to create a writable value") from err


def _tag_return_size(tag_data):
    tag_info = tag_data["tag_info"]
    if tag_info["tag_type"] == "atomic":
        size = DataTypes[tag_info["data_type"]].size
    else:
        size = tag_info["data_type"]["template"]["structure_size"]

    size = size * tag_data["elements"]

    return size
