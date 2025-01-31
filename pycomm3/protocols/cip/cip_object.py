from enum import IntEnum
from dataclasses import dataclass, field
from typing import Self

from pycomm3.data_types import DataType, StructType, UINT, BYTES, USINT, attr
from ._base import CIPRequest, CIPResponse, CIPService


@dataclass
class CIPAttribute:
    #: Attribute ID number
    id: bytes | int
    #: Data type of the attribute
    data_type: "type[DataType]"
    #: Flag to indicate the attribute is a class attribute if True, False if it is an instance attribute
    class_attr: bool = False
    # set by metaclass
    object: type["CIPObject"] = field(init=False)  # object containing the attribute
    name: str = field(init=False)  # attribute name (variable name of CIPObject class var)

    def __str__(self):
        return f"{self.object.__name__}.{self.name}"


class _MetaCIPObject(type):
    def __new__(cls, name, bases, classdict):
        klass = super().__new__(cls, name, bases, classdict)
        cip_attrs: dict[str, CIPAttribute] = {
            attr_name: attr
            for _class in (
                *bases,
                klass,
            )  # include common attributes from base class plus new ones in klass
            for attr_name, attr in vars(_class).items()
            if isinstance(attr, CIPAttribute)
        }

        # instance_all = [(_name, attr.data_type) for _name, attr in cip_attrs.items() if attr.all and not attr.class_attr]
        # if instance_all:
        #     klass._instance_all_type = StructType.create(f"{klass.__name__}InstanceAllType", instance_all)
        #
        # class_all = [
        #     (_name, attr.type)
        #     for _name, attr in cip_attrs.items()
        #     if attr.all and attr.class_attr and attr.name not in klass._class_all_exclude
        # ]
        # if class_all:
        #     klass._class_all_type = StructType.create(f"{klass.__name__}ClassAllType", class_all)

        # point each attr back to the class, so that just the attr can be passed to methods
        # and not also need to include the class, also set the name to the variable name
        # since we included the base class in the gathering the attributes, klass will have copies of all
        # the common cip attributes as class variables that point to klass instead of the base class
        for attr_name, attr in cip_attrs.items():
            attr.name = attr_name
            attr.object = klass  # type: ignore

        services: dict[str, CIPService] = {
            svc_name: service
            for _class in (*bases, klass)
            for svc_name, service in vars(_class).items()
            if isinstance(service, CIPService)
        }

        for svc_name, service in services.items():
            service.name = svc_name
            service.object = klass  # type: ignore

        return klass

    def __repr__(cls):
        return cls.__name__


class GetAttributesAllService(CIPService):
    id: USINT = attr(init=False, default=USINT(1))
    data_type: InitVar[DataType]


class ClassAllAttrsCIPObject:
    object_revision: UINT
    max_instance: UINT
    num_instances: UINT
    optional_attrs_list: UINT[UINT]
    optional_service_list: UINT[UINT]
    max_class_attr: UINT
    max_instance_attr: UINT


class CIPObject(metaclass=_MetaCIPObject):
    """
    Base class for all CIP objects.  Defines services, attributes, and other properties common to all CIP objects.
    """

    class_code: int = 0

    class Instance(IntEnum):
        CLASS = 0  #: The class itself and not an instance
        DEFAULT = 1  #: The first instance of a class, used as the default if not specified

    STATUS_CODES = {}
    # TODO: add functionality to lookup status codes by class, service, etc
    #       if each object subclasses CIPObject we can reverse MRO for looking up the status messages
    #
    # Map of object-specific service codes to status and extended status codes and error messages
    # ::
    #     {
    #         <service>: {
    #             <status>: {
    #                 <extended_status>: <message>
    #             }
    #         }
    #     }
    #

    # --- Reserved class attributes, common to all object classes ---

    #: CIP object specification revision
    object_revision = CIPAttribute(id=1, data_type=UINT, class_attr=True)
    #: Maximum instance id for instances of the object
    max_instance = CIPAttribute(id=2, data_type=UINT, class_attr=True)
    #: Number of instances of the object
    num_instances = CIPAttribute(id=3, data_type=UINT, class_attr=True)
    #: List of attribute ids for optional attributes supported by device
    optional_attrs_list = CIPAttribute(id=4, data_type=UINT[UINT], class_attr=True)
    #: List of service codes for optional services supported by device
    optional_service_list = CIPAttribute(id=5, data_type=UINT[UINT], class_attr=True)
    #: The attribute id of the last (max) attribute supported by device
    max_class_attr = CIPAttribute(id=6, data_type=UINT, class_attr=True)
    #: The instance id of the last (max) instance of the object in the device
    max_instance_attr = CIPAttribute(id=7, data_type=UINT, class_attr=True)

    # --- Common services (not all supported by all classes) ---
    #: Returns all instance/class attributes defined for the object
    get_attributes_all = GetAttributesAllService()
