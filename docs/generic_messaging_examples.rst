=================
Generic Messaging
=================

.. py:currentmodule:: pycomm3

The :meth:`LogixDriver.generic_message` works in a similar way to the MSG instruction in Logix.  It allows the user
to perform messaging services not directly implemented in the library. It is also used internally to implement some of the
CIP services used by the library (Forward Open, get/set PLC time, etc).


Accessing Drive Parameters
==========================

While a drive may not be a PLC, we can use generic messaging to read parameters from it.  In order to do so we need to
disable some of the PLC-only options in the LogixDriver.  The target drive is a PowerFlex 525 and using this
`Rockwell KB Article`_ we can get the appropriate parameters to read/write parameters from the drive.


    .. literalinclude:: ../examples/generic_messaging.py
        :pyobject: read_pf525_parameter

    >>> read_pf525_parameter()
    pf525_param, {'AccelTime': 500}, None, None

    .. literalinclude:: ../examples/generic_messaging.py
        :pyobject: write_pf525_parameter

.. _Rockwell KB Article: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/566003/loc/en_US#__highlight