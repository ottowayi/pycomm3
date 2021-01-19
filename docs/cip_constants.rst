=============
CIP Constants
=============

Documented CIP service and class codes are available in enum-like classes that can be imported for use, mostly useful for
generic messaging.  The following classes may be imported directly from the ``pycomm3`` package.

Ethernet/IP Encapsulation Commands
==================================

.. literalinclude:: ../pycomm3/const/services.py
    :pyobject: EncapsulationCommands


CIP Services and Class Codes
=============================

.. literalinclude:: ../pycomm3/const/services.py
    :pyobject: Services

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: ClassCode

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: CommonClassAttributes

CIP Data Types
==============

.. literalinclude:: ../pycomm3/const/datatypes.py
    :pyobject: DataType

Converting from Python to CIP data types can be done using the ``Pack`` class and from CIP to
Python types using the ``Unpack`` class.

.. literalinclude:: ../pycomm3/bytes_.py
    :pyobject: Pack

.. literalinclude:: ../pycomm3/bytes_.py
    :pyobject: Unpack

Identity Object
===============

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: IdentityObjectInstanceAttributes


Connection Manager Object
=========================

.. literalinclude:: ../pycomm3/const/services.py
    :pyobject: ConnectionManagerServices

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: ConnectionManagerInstances


File Object
===========

.. literalinclude:: ../pycomm3/const/services.py
    :pyobject: FileObjectServices

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: FileObjectClassAttributes

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: FileObjectInstanceAttributes

.. literalinclude:: ../pycomm3/const/object_library.py
    :pyobject: FileObjectInstances