=============
CIP Constants
=============

Documented CIP service and class codes are available in enum-like classes that can be imported for use, mostly useful for
generic messaging.  The following classes may be imported directly from the ``pycomm3`` package.


CIP Services and Class Codes
===================================

.. literalinclude:: ../pycomm3/const.py
    :pyobject: Services

.. literalinclude:: ../pycomm3/const.py
    :pyobject: ClassCode


CIP Data Types
==============

.. literalinclude:: ../pycomm3/const.py
    :pyobject: DataType

Converting from Python to CIP data types can be done using the ``Pack`` class and from CIP to
Python types using the ``Unpack`` class.

.. literalinclude:: ../pycomm3/bytes_.py
    :pyobject: Pack

.. literalinclude:: ../pycomm3/bytes_.py
    :pyobject: Unpack


Connection Manager Object
=========================

.. literalinclude:: ../pycomm3/const.py
    :pyobject: ConnectionManagerService

.. literalinclude:: ../pycomm3/const.py
    :pyobject: ConnectionManagerInstance
