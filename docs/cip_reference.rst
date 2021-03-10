=============
CIP Reference
=============

Documented CIP service and class codes are available in enum-like classes that can be imported for use, mostly useful for
generic messaging.  The following classes may be imported directly from the ``pycomm3`` package.

Ethernet/IP Encapsulation Commands
==================================

.. literalinclude:: ../pycomm3/cip/services.py
    :pyobject: EncapsulationCommands


CIP Services and Class Codes
=============================

.. literalinclude:: ../pycomm3/cip/services.py
    :pyobject: Services

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: ClassCode

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: CommonClassAttributes


Identity Object
===============

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: IdentityObjectInstanceAttributes


Connection Manager Object
=========================

.. literalinclude:: ../pycomm3/cip/services.py
    :pyobject: ConnectionManagerServices

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: ConnectionManagerInstances


File Object
===========

.. literalinclude:: ../pycomm3/cip/services.py
    :pyobject: FileObjectServices

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: FileObjectClassAttributes

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: FileObjectInstanceAttributes

.. literalinclude:: ../pycomm3/cip/object_library.py
    :pyobject: FileObjectInstances