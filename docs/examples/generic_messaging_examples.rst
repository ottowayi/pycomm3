=================
Generic Messaging
=================

.. py:currentmodule:: pycomm3

The :meth:`LogixDriver.generic_message` works in a similar way to the MSG instruction in Logix.  It allows the user
to perform messaging services not directly implemented in the library. It is also used internally to implement some of the
CIP services used by the library (Forward Open, get/set PLC time, etc).


Accessing Drive Parameters
==========================

While a drive may not be a PLC, we can use generic messaging to read parameters from it.  The target drive is a PowerFlex 525 and using this
`Rockwell KB Article`_ we can get the appropriate parameters to read/write parameters from the drive.


    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: read_pf525_parameter

    >>> read_pf525_parameter()
    pf525_param, 500, None, None

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: write_pf525_parameter

.. _Rockwell KB Article: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/566003/loc/en_US#__highlight


Reading Device Statuses
=======================

ENBT/EN2T OK LED Status
-----------------------

This message will get the current status of the OK LED from and ENBT or EN2T module.

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: enbt_ok_led_status

Link Status
-----------

This message will read the current link status for any ethernet module.

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: link_status


Stratix Switch Power Status
---------------------------

This message will read the current power status for both power inputs on a Stratix switch.

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: stratix_power_status


IP Configuration
================

Static/DHCP/BOOTP Status
------------------------

This message will read the IP setting configuration type from an ethernet module.

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: ip_config

Communication Module MAC Address
--------------------------------

This message will read the MAC address of ethernet module where the current connection is opened.

    .. literalinclude:: ../../examples/generic_messaging.py
        :pyobject: get_mac_address


Upload EDS File
===============

This example shows how to use generic messaging to upload and save an EDS file from a device.

    .. literalinclude:: ../../examples/upload_eds.py