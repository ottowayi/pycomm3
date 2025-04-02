from ..cip_object import CIPObject, CIPAttribute
from ..common_services import GetAttributesAllService
from pycomm3.data_types import UINT, WORD, UDINT, SHORT_STRING, USINT, Revision, StructType
from enum import IntEnum


class IdentityGetAttrsAllInstance(StructType):
    vendor_id: UINT
    device_type: UINT
    product_code: UINT
    revision: Revision
    status: WORD
    serial_number: UDINT
    product_name: SHORT_STRING


class Identity(CIPObject):
    """
    This object provides general identity and status information about a device.
    It is required by all CIP objects and if a device contains multiple discrete
    components, multiple instances of this object may be created.
    """

    class_code = 0x01

    # --- Required attributes ---
    #: Identification code assigned to the vendor
    vendor_id = CIPAttribute(id=1, data_type=UINT)
    #: Indication of general type of product
    device_type = CIPAttribute(id=2, data_type=UINT)
    #: Identification code of a particular product for an individual vendor
    product_code = CIPAttribute(id=3, data_type=UINT)
    #: Revision of the item the Identity Object represents
    revision = CIPAttribute(id=4, data_type=Revision)
    #: Summary status of the device
    status = CIPAttribute(id=5, data_type=WORD)
    #: Serial number of the device
    serial_number = CIPAttribute(id=6, data_type=UDINT)
    #: Human readable identification of the device
    product_name = CIPAttribute(id=7, data_type=SHORT_STRING)

    # TODO: add custom type for status that shows what the bits mean

    # --- Optional attributes ---
    #: Present state of the device, see :class:`~IdentityObject.States`
    state = CIPAttribute(id=8, data_type=USINT)

    class States(IntEnum):
        """
        Enum of the possible state attribute values,
        any not listed are 'reserved'
        """

        #: The device is powered off
        Nonexistent = 0
        #: The device is currently running self tests
        DeviceSelfTesting = 1
        #: The device requires commissioning, configuration is invalid or incomplete
        Standby = 2
        #: The device is functioning normally
        Operational = 3
        #: The device experienced a fault that it can recover from
        MajorRecoverableFault = 4
        #: The device experienced a fault that it cannot recover from
        MajorUnrecoverableFault = 5
        #: Default value for a ``get_attributes_all`` service response if attribute is not supported
        DefaultGetAttributesAll = 255

    get_attributes_all = GetAttributesAllService(IdentityGetAttrsAllInstance)
