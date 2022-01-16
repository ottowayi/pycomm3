from abc import ABC, abstractmethod
from enum import IntEnum
from dataclasses import dataclass, replace
from typing import Union, Type, NamedTuple, Dict, Optional, Set, Any

from ....data_types import DataType, Struct, UINT, BYTES, USINT
from ....map import EnumMap
from ..cip import CIPRequest, CIPResponse


@dataclass
class CIPAttribute:
    #: Attribute ID number
    id: Union[bytes, int]
    #: Data type of the attribute
    type: Union[DataType, Type[DataType]]
    #: Flag indicating if the attribute is included in the ``get_attributes_all`` response
    all: bool = True
    #: Flag to indicate the attribute is a class attribute if True, False if it is an instance attribute
    class_attr: bool = False

    # set by metaclass
    object: Type['CIPObject'] = None  # object containing the attribute
    name: str = None  # attribute name (variable name of CIPObject class var)

    def __str__(self):
        return f'{self.object.__name__}.{self.name}'


@dataclass(frozen=True)
class CIPService(ABC):
    #: Service code
    id: int
    #: Request data format type, used for encoding the service request, ``None`` if no request data is required
    request_type: Union[None, DataType, Type[DataType]] = BYTES[...]
    #: Type of request to create for this service
    request_class: Type[CIPRequest] = CIPRequest
    #: Response data format type, used for decoding the service response, ``None`` if no response expected
    response_type: Union[None, DataType, Type[DataType]] = BYTES[...]
    #: Response data format type for failed requests, ``None`` to use ``response_type``
    failed_response_type: Union[None, DataType, Type[DataType]] = None

    # set by metaclass
    object: Type['CIPObject'] = None  # object containing the service attribute
    name: str = None  # attribute name (variable name of CIPObject class var)

    @abstractmethod
    def __call__(self, *args, **kwargs) -> CIPRequest:
        ...


@dataclass(frozen=True)
class SimpleCIPService(CIPService):
    def __call__(
        self,
        instance: Optional[int] = None,
        attribute: Optional[Union[CIPAttribute, int]] = None,
        request_data: Optional[dict[str, Any]] = None,
    ) -> CIPRequest:
        if isinstance(attribute, CIPAttribute):
            attr = attribute.id
        else:
            attr = attribute

        return self.request_class(
            class_code=self.object.class_code,
            service=USINT.encode(self.id),
            instance=instance or CIPObject.Instance.DEFAULT,
            attribute=attr,
            request_data=self.request_type.encode(request_data),
            response_type=self.response_type,
        )


@dataclass(frozen=True)
class GetAttributesAllService(CIPService):
    id: int = 0x01

    def __call__(self, instance: Optional[int] = None, *args, **kwargs) -> CIPRequest:
        if instance == CIPObject.Instance.CLASS:
            response_type = self.object._class_all_type
        else:
            response_type = self.object._instance_all_type

        return CIPRequest(
            class_code=self.object.class_code,
            service=self.id,
            instance=instance or CIPObject.Instance.DEFAULT,
            response_type=response_type,
        )


class _MetaCIPObject(type):
    def __new__(cls, name, bases, classdict):
        klass = super().__new__(cls, name, bases, classdict)
        cip_attrs: Dict[str, CIPAttribute] = {
            attr_name: attr
            for _class in (*bases, klass)  # include common attributes from base class plus new ones in klass
            for attr_name, attr in vars(_class).items()
            if isinstance(attr, CIPAttribute)
        }

        instance_all = [attr.type(name) for name, attr in cip_attrs.items() if attr.all and not attr.class_attr]
        if instance_all:
            klass._instance_all_type = Struct(*instance_all)

        class_all = [
            attr.type(name)
            for name, attr in cip_attrs.items()
            if attr.all and attr.class_attr and attr.name not in klass._class_all_exclude
        ]
        if class_all:
            klass._class_all_type = Struct(*class_all)

        # point each attr back to the class, so that just the attr can be passed to methods
        # and not also need to include the class, also set the name to the variable name
        # since we included the base class in the gathering the attributes, klass will have copies of all
        # the common cip attributes as class variables that point to klass instead of the base class
        for attr_name, attr in cip_attrs.items():
            setattr(klass, attr_name, replace(attr, object=klass, name=attr_name))

        services: Dict[str, CIPService] = {
            svc_name: service
            for _class in (*bases, klass)
            for svc_name, service in vars(_class).items()
            if isinstance(service, CIPService)
        }

        for svc_name, service in services.items():
            setattr(klass, svc_name, replace(service, object=klass, name=svc_name))

        return klass

    def __repr__(cls):
        return cls.__name__


class CIPObject(metaclass=_MetaCIPObject):
    """
    Base class for all CIP objects.  Defines services, attributes, and other properties common to all CIP objects.
    """
    class_code: int = 0
    _instance_all_type: Optional[DataType] = None
    _class_all_type: Optional[DataType] = None
    _class_all_exclude: Set[str] = {}  # to exclude some inherited class attrs from all response
                                       # without needing to redefine all the attrs

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
    object_revision = CIPAttribute(id=1, type=UINT, class_attr=True)
    #: Maximum instance id for instances of the object
    max_instance = CIPAttribute(id=2, type=UINT, class_attr=True)
    #: Number of instances of the object
    num_instances = CIPAttribute(id=3, type=UINT, class_attr=True)
    #: List of attribute ids for optional attributes supported by device
    optional_attrs_list = CIPAttribute(id=4, type=UINT[UINT], class_attr=True)
    #: List of service codes for optional services supported by device
    optional_service_list = CIPAttribute(id=5, type=UINT[UINT], class_attr=True)
    #: The attribute id of the last (max) attribute supported by device
    max_class_attr = CIPAttribute(id=6, type=UINT, class_attr=True)
    #: The instance id of the last (max) instance of the object in the device
    max_instance_attr = CIPAttribute(id=7, type=UINT, class_attr=True)

    # --- Common services (not all supported by all classes) ---
    #: Returns all instance/class attributes defined for the object
    get_attributes_all = GetAttributesAllService()

