===========
Basic Usage
===========

.. py:currentmodule:: pycomm3


Creating the Driver
-------------------

The :class:`pycomm3.LogixDriver` class implements a single Ethernet/IP client connection to a PLC.  The only required
argument when creating a driver is the CIP path to target PLC.  The ``path`` argument is formatted to appear similar
to how it would in RSLogix / Logix Designer.  For details on the different options, refer to :meth:`~LogixDriver.__init__`.

>>> from pycomm3 import LogixDriver
>>> with LogixDriver('10.20.30.100') as plc:
>>>     print(plc)
Program Name: PLCA, Device: 1756-L73/B LOGIX5573, Revision: 24.12

Using the driver in a context manager automatically handles opening and closing of the connection to the PLC.  It is not
required be used with one though.  Simply calling :meth:`~LogixDriver.open` and :meth:`~LogixDriver.close` will work as well.
This works well when placing the driver in a background thread or making a long-lived connection, since it will keep the
same connection open and will not require re-uploading all of the tag definitions.

.. code-block:: Python

    class EIPThread(Thread)
        def __init__(*args, **kwargs)
            ...
            self.plc = LogixDriver(*args, **kwargs)
            self.plc.open()
            self._running = True
            self.start()

        def run():
            while self._running:
                ... # do reading and stuff

        def shutdown():
            self._running = False
            self.plc.close()


Get Basic Information About the PLC
-----------------------------------

There is some data that is collected about the target controller when a connection is first established.  Assuming the
``init_info`` kwarg is set to True (default) when creating the LogixDriver, it will call both the :meth:`~LogixDriver.get_plc_info`
and :meth:`~LogixDriver.get_plc_name` methods.  These methods provide some simple information about the target controller.
:meth:`~LogixDriver.get_plc_info` returns a dict of the info collected and stores that information, making it accessible
from the :attr:`~LogixDriver.info` property. See :attr:`~LogixDriver.info` for details on the specific fields.
