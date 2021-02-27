===============
Getting Started
===============

.. py:currentmodule:: pycomm3


Creating a Driver
-----------------

Drivers are simple to create and use, the quickest way is to use them within on context manager (``with`` statement).  Most of the
examples in the documentation will shown them used in that way. But, if you are using them as part of a larger program
or creating long-lived connections, you may not want to use the context manager in this case.  When used outside a context
manager, you will need to call the :meth:`~CIPDriver.open` method first and the :meth:`~CIPDriver.close` method on
shutdown.  Failing to close the connection could cause issues communicating with the device.  Each driver opens a
single connection to the device, you may use multiple instances to create multiple connections.  It is also the user's
responsibility to maintain the connection, the drivers do not implement any periodic handshaking.  The default timeout
is fairly long, but a long lived connection will need to issue a request usually at least once a minute or the PLC
may close the connection.

Each driver requires a ``path`` argument, this is a CIP path to the destination device. The paths used in ``pycomm3`` are
similar to how they appear in Logix.

There are three possible forms:

    IP Address Only (``10.20.30.100``)
        Use for devices without a backplane (drives, switches, Micro800 PLCs, etc) or for PLCs in slot 0 of a backplane.

    IP Address/Slot (``10.20.30.100/1``)
        Use for PLCs in a backplane that are not in slot 0.

    CIP Routing Path (``1.2.3.4/backplane/2/enet/6.7.8.9/backplane/0``)
        This is a full CIP route to a device, it should appear similar to how paths are shown in Logix.  For port selection,
        use ``backplane`` or ``bp`` for the backplane and ``enet`` for the ethernet port.  Both slash (``/``) and backslash (``\``)
        are supported.

    .. note::

        Both the IP Address and IP Address/Slot options are shortcuts, they will be replaced with the
        CIP path automatically.

>>> from pycomm3 import CIPDriver
>>> with CIPDriver('10.20.30.100') as drive:
>>>     print(drive)
Device: AC Drive, Revision: 1.2

Default behavior is to use the *Extended Forward Open* service when opening a connection.  This allows the use of ~4KB of
data for each request, standard is only 500B.  Although this requires the communications module to be an EN2T or newer
and the PLC firmware to be version 20 or newer.  Upon opening a connection, the ``CIPDriver`` will attempt an
*Extended Forward Open*, if that fails it will then try using the standard *Forward Open*.

Creating a LogixDriver
^^^^^^^^^^^^^^^^^^^^^^

The :class:`LogixDriver` has two additional arguments:

    ``init_tags`` (default ``True``)
        When true, the driver will upload all tags in the PLC and the definitions for any UDTs and AOIs.
        These definitions are required for the :meth:`~LogixDriver.read` and :meth:`~LogixDriver.write` methods
        to work.

    ``init_program_tags`` (default ``True``)
        When uploading the tag list, if ``True`` all program scoped tags are uploaded.
        Set ``False`` to upload controller-scoped tags only.  This arg is only checked if ``init_tags`` is ``True``.


There is some data that is collected about the target controller when a connection is first established.  It will
call both the :meth:`~LogixDriver.get_plc_info` and :meth:`~LogixDriver.get_plc_name` methods.
:meth:`~LogixDriver.get_plc_info` returns a dict of the info collected and stores that information,
making it accessible from the :attr:`~LogixDriver.info` property. :meth:`~LogixDriver.get_plc_name` will return the name
of the program running in the PLC and store it in :attr:`~LogixDriver.info['name']`.
See :attr:`~LogixDriver.info` for details on the specific fields.

Symbol Instance Addressing is a feature that allows more requests to be sent in a single packet by using a short identifier
for a tag instead of needing to encode the full tag name in the request.  These instance ids are uploaded with the tag definitions.
But, this feature is only available on v21+ firmwares. If the PLC is on a firmware lower than that, getting the controller info
will automatically disable that feature.

After the controller info has been retrieved, the driver will begin uploading the tag list. (Assuming the ``init_tags``
option has not been set ``False``).  Depending on the number of tags, the PLC model, and other factors, this upload
could take some time to upload.  A very large tag list on an old processor with high CPU utilization could take 10-15 seconds,
while a small tag list or a new processor might take <1 second.  If you are setting up multiple drivers to the same PLC,
it can save startup time by uploading the tag list is in the first driver and disabling it in the others.  Then pass the
tag list to the other drivers from the first one.

::

    from pycomm3 import LogixDriver
    first_plc = LogixDriver('10.20.30.100')
    first_plc.open()  # uploads the tag list
    second_plc = LogixDriver('10.20.30.100', init_tags=False)
    second_plc._tags = first_plc.tags
    second_plc.open()  # doesn't upload any tags


Creating a SLCDriver
^^^^^^^^^^^^^^^^^^^^

Currently, there is no additional configuration for a ``SLCDriver`` over a ``CIPDriver``.


Response Tag Object
-------------------

Many methods return a :class:`Tag` object, like :meth:`~CIPDriver.generic_message` or the ``read`` and ``write`` methods
of the :class:`LogixDriver` or :class:`SLCDriver`.  The truthiness of a ``Tag`` object represents the status of a request.
A successful request will have a ``value`` that is not ``None`` and the ``error`` attribute is ``None``.  Anything otherwise
will be a failed request.  The ``error`` attribute will contain either the CIP error message or exception raised during
the request.

.. autoclass:: pycomm3.Tag
    :members:

    .. automethod:: __bool__


Data Types
----------

Data types are a major component of ``pycomm3``, they are classes used to represent any tag or CIP object. They are able to
encode and decode to and from Python values and bytes. Atomic and structure values along with array of either are supported.



Logging
-------

This library uses the standard Python `logging`_ module.  You may configure the logging module as needed.  The ``DEBUG``
level will log every sent/received packed and other diagnostic data.  Set the level to higher than ``DEBUG`` if you only
wish to see errors, exceptions, etc.  A helper method called ``configure_default_logger`` is provided to setup basic
logging.  There are two optional parameters, ``level`` and ``filename``.  ``level`` (default ``logging.INFO``) is the
logging level.  ``filename`` (default ``None``) if set, will also log to the specified file.

.. code-block::

    from pycomm3.logger import configure_default_logger

    configure_default_logger(filename='c:/tmp/pycomm3.log')



Produces output similar to::

    2021-02-26 14:37:41,389 [DEBUG] pycomm3.cip_driver.CIPDriver.open(): Opening connection to 192.168.1.236
    2021-02-26 14:37:41,393 [DEBUG] pycomm3.cip_driver.CIPDriver.send(): Sent: RegisterSessionRequestPacket(message=[b'\x01\x00', b'\x00\x00'])
    2021-02-26 14:37:41,397 [DEBUG] pycomm3.cip_driver.CIPDriver.send(): Received: RegisterSessionResponsePacket(session=184719106, error=None)
    2021-02-26 14:37:41,398 [INFO] pycomm3.cip_driver.CIPDriver._register_session(): Session=184719106 has been registered.
    2021-02-26 14:37:41,398 [INFO] pycomm3.logix_driver.LogixDriver._initialize_driver(): Initializing driver...



``pycomm3`` also uses a custom logging level for verbose logging, this level prints also prints the contents of each
packet send and received.  If submitting a bug report, this level of logging is the most helpful.

.. code-block::

    from pycomm3.logger import configure_default_logger, LOG_VERBOSE
    configure_default_logger(level=LOG_VERBOSE, filename='c:/tmp/pycomm3.log')

Verbose output::

    2021-02-26 14:42:36,752 [DEBUG] pycomm3.cip_driver.CIPDriver.open(): Opening connection to 192.168.1.236
    2021-02-26 14:42:36,765 [VERBOSE] pycomm3.cip_driver.CIPDriver._send(): >>> SEND >>>
    (0000) 65 00 04 00 00 00 00 00 00 00 00 00 5f 70 79 63     e•••••••••••_pyc
    (0010) 6f 6d 6d 5f 00 00 00 00 01 00 00 00                 omm_••••••••
    2021-02-26 14:42:36,766 [DEBUG] pycomm3.cip_driver.CIPDriver.send(): Sent: RegisterSessionRequestPacket(message=[b'\x01\x00', b'\x00\x00'])
    2021-02-26 14:42:36,768 [VERBOSE] pycomm3.cip_driver.CIPDriver._receive(): <<< RECEIVE <<<
    (0000) 65 00 04 00 02 98 02 0b 00 00 00 00 5f 70 79 63     e•••••••••••_pyc
    (0010) 6f 6d 6d 5f 00 00 00 00 01 00 00 00                 omm_••••••••
    2021-02-26 14:42:36,768 [DEBUG] pycomm3.cip_driver.CIPDriver.send(): Received: RegisterSessionResponsePacket(session=184719362, error=None)
    2021-02-26 14:42:36,769 [INFO] pycomm3.cip_driver.CIPDriver._register_session(): Session=184719362 has been registered.
    2021-02-26 14:42:36,769 [INFO] pycomm3.logix_driver.LogixDriver._initialize_driver(): Initializing driver...
    2021-02-26 14:42:36,769 [VERBOSE] pycomm3.cip_driver.CIPDriver._send(): >>> SEND >>>
    (0000) 63 00 00 00 02 98 02 0b 00 00 00 00 5f 70 79 63     c•••••••••••_pyc
    (0010) 6f 6d 6d 5f 00 00 00 00                             omm_••••
    2021-02-26 14:42:36,769 [DEBUG] pycomm3.cip_driver.CIPDriver.send(): Sent: ListIdentityRequestPacket(message=[])
    2021-02-26 14:42:36,771 [VERBOSE] pycomm3.cip_driver.CIPDriver._receive(): <<< RECEIVE <<<
    (0000) 63 00 45 00 02 98 02 0b 00 00 00 00 5f 70 79 63     c•E•••••••••_pyc
    (0010) 6f 6d 6d 5f 00 00 00 00 01 00 0c 00 3f 00 01 00     omm_••••••••?•••
    (0020) 00 02 af 12 c0 a8 01 ec 00 00 00 00 00 00 00 00     ••••••••••••••••
    (0030) 01 00 0c 00 bf 00 14 13 30 00 90 be 1e c0 1d 31     ••••••••0••••••1
    (0040) 37 36 39 2d 4c 32 33 45 2d 51 42 46 43 31 20 45     769-L23E-QBFC1 E
    (0050) 74 68 65 72 6e 65 74 20 50 6f 72 74 03              thernet Port•

.. _logging: https://docs.python.org/3/library/logging.html