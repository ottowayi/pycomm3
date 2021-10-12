=======
pycomm3
=======

.. <<start>>

.. image:: https://img.shields.io/pypi/v/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/l/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: License

.. image:: https://img.shields.io/pypi/pyversions/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: Python Versions

|

.. image:: https://img.shields.io/pypi/dm/pycomm3?style=social
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: Downloads

.. image:: https://img.shields.io/github/watchers/ottowayi/pycomm3?style=social
    :target: https://github.com/ottowayi/pycomm3
    :alt: Watchers

.. image:: https://img.shields.io/github/stars/ottowayi/pycomm3?style=social
    :target: https://github.com/ottowayi/pycomm3
    :alt: Stars

.. image:: https://img.shields.io/github/forks/ottowayi/pycomm3?style=social
    :target: https://github.com/ottowayi/pycomm3
    :alt: Forks

|

.. image:: https://readthedocs.org/projects/pycomm3/badge/?version=latest&style=for-the-badge
   :target: https://pycomm3.readthedocs.io/en/latest/
   :alt: Read the Docs

.. image:: https://img.shields.io/badge/gitmoji-%20%F0%9F%98%9C%20%F0%9F%98%8D-FFDD67.svg?style=for-the-badge
    :target: https://gitmoji.dev
    :alt: Gitmoji


Introduction
============

``pycomm3`` started as a Python 3 fork of `pycomm`_, which is a Python 2 library for
communicating with Allen-Bradley PLCs using Ethernet/IP.  The initial Python 3 port was done
in this `fork`_ and was used as the base for ``pycomm3``.  Since then, the library has been
almost entirely rewritten and the API is no longer compatible with ``pycomm``.  Without the
hard work done by the original ``pycomm`` developers, ``pycomm3`` would not exist.  This
library seeks to expand upon their great work.


.. _pycomm: https://github.com/ruscito/pycomm

.. _fork: https://github.com/bpaterni/pycomm/tree/pycomm3


Drivers
=======

``pycomm3`` includes 3 drivers:

- `CIPDriver`_
    This driver is the base driver for the library, it handles common CIP services used
    by the other drivers.  Things like opening/closing a connection, register/unregister sessions,
    forward open/close services, device discovery, and generic messaging.  It can be used to connect to
    any Ethernet/IP device, like: drives, switches, meters, and other non-PLC devices.

- `LogixDriver`_
    This driver supports services specific to ControlLogix, CompactLogix, and Micro800 PLCs.
    Services like reading/writing tags, uploading the tag list, and getting/setting the PLC time.

- `SLCDriver`_
    This driver supports basic reading/writing data files in a SLC500 or MicroLogix PLCs.  It is
    a port of the ``SlcDriver`` from ``pycomm`` with minimal changes to make the API similar to the
    other drivers. Currently this driver is considered legacy and it's development will be on
    a limited basis.

.. _CIPDriver: https://docs.pycomm3.dev/en/latest/usage/cipdriver.html

.. _LogixDriver: https://docs.pycomm3.dev/en/latest/usage/logixdriver.html

.. _SLCDriver: https://docs.pycomm3.dev/en/latest/usage/slcdriver.html

Disclaimer
==========

PLCs can be used to control heavy or dangerous equipment, this library is provided "as is" and makes no guarantees on
its reliability in a production environment.  This library makes no promises in the completeness or correctness of the
protocol implementations and should not be solely relied upon for critical systems.  The development for this library
is aimed at providing quick and convenient access for reading/writing data inside Allen-Bradley PLCs.


Setup
=====

The package can be installed from `PyPI`_ using ``pip``: ``pip install pycomm3`` or ``python -m pip install pycomm3``.

.. _PyPI: https://pypi.org/project/pycomm3/

Optionally, you may configure logging using the Python standard `logging`_ library.  A convenience method is provided
to help configure basic logging, see the `Logging Section`_ in the docs for more information.

.. _logging: https://docs.python.org/3/library/logging.html

.. _Logging Section: https://docs.pycomm3.dev/en/latest/getting_started.html#logging


Python and OS Support
=====================

``pycomm3`` is a Python 3-only library and is supported on Python versions from 3.6.1 up to 3.10.
There should be no OS-specific requirements and should be able to run on any OS that Python is supported on.
Development and testing is done primarily on Windows 10.  If you encounter an OS-related problem, please open an issue
in the `GitHub repository`_ and it will be investigated.

.. attention::

    Python 3.6.0 is not supported due to ``NamedTuple`` not supporting
    `default values and methods <https://docs.python.org/3/library/typing.html#typing.NamedTuple>`_ until 3.6.1

.. _GitHub repository:  https://github.com/ottowayi/pycomm3

.. <<end>>

Documentation
=============

This README covers a basic overview of the library, full documentation can be found on
`Read the Docs`_ or by visiting `https://pycomm3.dev <https://pycomm3.dev>`_.

.. _Read the Docs: https://pycomm3.readthedocs.io/en/latest/

Contributions
=============

If you'd like to contribute or are having an issue, please read the `Contributing`_ guidelines.

.. _Contributing: CONTRIBUTING.md


Highlighted Features
====================

- ``generic_message`` for extra functionality not directly implemented
    - working similar to the MSG instruction in Logix, arguments similar to the MESSAGE properties
    - See the examples section for things like getting/setting drive parameters, IP configuration, or uploading an EDS file
    - used internally to implement some of the other methods (get/set_plc_time, forward open/close, etc)
- simplified data types
    - allows use of standard Python types by abstracting CIP implementation details away from the user
    - strings use normal Python ``str`` objects, does not require handling of the ``LEN`` and ``DATA`` attributes separately
    - custom string types are also identified automatically and not limited to just the builtin one
    - BOOL arrays use normal Python ``bool`` objects, does not require complicated bit shifting of the DWORD value
    - powerful type system to allow types to represent any CIP object and handle encoding/decoding the object

LogixDriver
-----------

- simple API, only 1 ``read`` method and 1 ``write`` method for tags.
    - does not require using different methods for different data types
    - requires the tag name only, no other information required from the user
    - automatically manages request/response size to pack as many requests into a single packet
    - automatically handles fragmented requests for large tags that can't fit in a single packet
    - both support full structure reading/writing (UDTs, AOIs, etc)
        - for ``read`` the ``Tag.value`` will be a ``dict`` of ``{attribute: value}``
        - for ``write`` the value should be a dict of ``{attribute: value}`` , nesting as needed
            - does not do partial writes, the value must match the complete structure
            - not recommended for builtin type (TIMER, CONTROL, COUNTER, etc)
        - both require no attributes to have an External Access of None
- uploads the tag list and data type definitions from the PLC
    - no requirement for user to determine tags available (like from an L5X export)
    - definitions are required for ``read``/``write`` methods
- automatically enables/disables different features based on the target PLC
    - Extended Forward Open (EN2T or newer and v20+)
    - Symbol Instance Addressing (Logix v21+)
    - detection of Micro800 and disables unsupported features (CIP Path, Ex. Forward Open, Instance Addressing, etc)

LogixDriver Overview
====================

Creating a driver is simple, only a ``path`` argument is required.  The ``path`` can be the IP address, IP and slot,
or a full CIP route, refer to the documentation for more details.  The example below shows how to create a simple
driver and print some of the information collected about the device.

::

    from pycomm3 import LogixDriver

    with LogixDriver('10.20.30.100/1') as plc:
        print(plc)
        # OUTPUT:
        # Program Name: PLCA, Device: 1756-L83E/B, Revision: 28.13

        print(plc.info)
        # OUTPUT:
        # {'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type': 'Programmable Logic Controller',
        #  'product_code': 166, 'version_major': 28, 'version_minor': 13, 'revision': '28.13', 'serial': 'FFFFFFFF',
        #  'device_type': '1756-L83E/B', 'keyswitch': 'REMOTE RUN', 'name': 'PLCA'}


Reading/Writing Tags
--------------------

Reading or writing tags is as simple as calling the ``read`` and ``write`` methods. Both methods accept any number of tags,
and will automatically pack multiple tags into a *Multiple Service Packet Service (0x0A)* while making sure to stay below the connection size.
If there is a tag value that cannot fit within the request/reply packet, it will automatically handle that tag independently
using the *Read Tag Fragmented (0x52)* or *Write Tag Fragmented (0x53)* requests.

Both methods will return ``Tag`` objects to reflect the success or failure of the operation.

::

    class Tag(NamedTuple):
        tag: str  # the name of the tag, does not include ``{<# elements>}`` from request
        value: Any  # value read or written, may be ``None`` if an error occurred
        type: Optional[str] = None  # data type of tag, including ``[<# elements>]`` from request
        error: Optional[str] = None  # ``None`` if successful, else the CIP error or exception thrown

``Tag`` objects are considered successful (truthy) if the ``value`` is not ``None`` and the ``error`` is ``None``.


Examples::

    with LogixDriver('10.20.30.100') as plc:
        plc.read('tag1', 'tag2', 'tag3')  # read multiple tags
        plc.read('array{10}') # read 10 elements starting at 0 from an array
        plc.read('array[5]{20}) # read 20 elements starting at elements 5 from an array
        plc.read('string_tag')  # read a string tag and get a string
        plc.read('a_udt_tag') # the response .value will be a dict like: {'attr1`: 1, 'attr2': 'a string', ...}

        # writes require a sequence of tuples of [(tag name, value), ... ]
        plc.write('tag1', 0)  # single writes do not need to be passed as a tuple
        plc.write(('tag1', 0), ('tag2', 1), ('tag3', 2))  # write multiple tags
        plc.write(('array{5}', [1, 2, 3, 4, 5]))  # write 5 elements to an array starting at the 0 element
        plc.write('array[10]{5}', [1, 2, 3, 4, 5])  # write 5 elements to an array starting at element 10
        plc.write('string_tag', 'Hello World!')  # write to a string tag with a string
        plc.write('string_array[2]{5}', 'Write an array of strings'.split())  # write an array of 5 strings starting at element 2
        plc.write('a_udt_tag', {'attr1': 1, 'attr2': 'a string', ...})  # can also use a dict to write a struct

        # Check the results
        results = plc.read('tag1', 'tag2', 'tag3')
        if all(results):
            print('They all worked!')
        else:
            for result in results:
                if not result:
                    print(f'Reading tag {result.tag} failed with error: {result.error}')

.. Note::

    Tag names for both ``read`` and ``write`` are case-sensitive and are required to be the same as they are named in
    the controller.  This may change in the future.


Unit Testing
============

``pytest`` is used for unit testing. The ``tests`` directory contains an L5X export of the testing program
that contains all tags necessary for testing.  The only requirement for testing (besides a running PLC with the testing
program) is the environment variable ``PLCPATH`` for the PLC defined.

User Tests
----------

These tests are for users to run.  There are a few tests that are specific to a demo
plc, those are excluded. To run them you have the following options:

with `tox`:

    - modify the ``PLCPATH`` variable in ``tox.ini``
    - then run this command: ``tox -e user``

or with ``pytest``:

.. code-block::

    set PLCPATH=192.168.1.100
    pytest --ignore tests/online/test_demo_plc.py

*(or the equivalent in your shell)*


.. Note::
    Test coverage is not complete, pull requests are welcome to help improve coverage.


License
=======
``pycomm3`` is distributed under the MIT License
