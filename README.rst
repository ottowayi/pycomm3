=======
pycomm3
=======

.. image:: https://img.shields.io/pypi/v/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/l/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: License

.. image:: https://img.shields.io/pypi/pyversions/pycomm3.svg?style=for-the-badge
   :target: https://pypi.python.org/pypi/pycomm3
   :alt: Python Versions

.. image:: https://readthedocs.org/projects/pycomm3/badge/?version=latest&style=for-the-badge
   :target: https://pycomm3.readthedocs.io/en/latest/
   :alt: Read the Docs


``pycomm3`` is a Python 3 fork of `pycomm`_, which is a native python library for communicating
with PLCs using Ethernet/IP.  The initial Python 3 translation was done in this fork_, this library
seeks to continue and expand upon the great work done by the original ``pycomm`` developers.
`pylogix`_ is another library with similar features (including Python 2 support) for ControlLogix and CompactLogix PLCs.
Referencing ``pylogix`` code was a big help in implementing some features missing from ``pycomm``.

This library contains 3 drivers:

LogixDriver
    This is the main driver for this library, it supports ControlLogix, CompactLogix, and Micro800 PLCs.

SLCDriver
    **New in version 0.10.0**

    This driver can be used for reading/writing data files in SLC 500 or MicroLogix PLCs.  This driver is an update to the
    original pycomm SLC driver with some minor changes to make it similar to the LogixDriver. Some of the more advanced
    or automatic features are not supported.  Even though this driver was newly added, it's considered legacy and it's development
    will be on a limited basis.

CIPDriver
    This is the base class for the other two drivers, it handles some common shared services.  It can also be used for
    generic CIP messaging to other non-PLC devices.


.. _pycomm: https://github.com/ruscito/pycomm

.. _fork: https://github.com/bpaterni/pycomm/tree/pycomm3

.. _pylogix: https://github.com/dmroeder/pylogix


Disclaimer
==========

PLCs can be used to control heavy or dangerous equipment, this library is provided 'As Is' and makes no guarantees on
it's reliability in a production environment.  This library makes no promises in the completeness or correctness of the
protocol implementations and should not be solely relied upon for critical systems.  The development for this library
is aimed at providing quick and convenient access for reading/writing data inside Allen-Bradley PLCs.

Python and OS Support
=====================

`pycomm3` is a Python 3 only library.  The minimum supported version of Python is 3.6.1 and has been tested up to 3.9.
There should be no OS specific requirements and should be able to run on any OS that Python is supported on.
Development and testing is done primarily on Windows 10.  If you encounter an OS-related problem, please open an issue
in this repository and it will be investigated.

Setup
=====

The package can be installed from `PyPI`_ using ``pip``: ``pip install pycomm3`` or ``python -m pip install pycomm3``.

.. _PyPI: https://pypi.org/project/pycomm3/

Optionally, you may configure logging using the Python standard `logging`_ library.

.. _logging: https://docs.python.org/3/library/logging.html

Documentation
=============

This README covers a basic overview of the library, full documentation can be found on
`Read the Docs`_.

.. _Read the Docs: https://pycomm3.readthedocs.io/en/latest/

Contributions
=============

If you'd like to contribute or are having an issue, please read the `Contributing`_ guidelines.

.. _Contributing: CONTRIBUTING.md



LogixDriver
===========

Highlighted Features
--------------------

- simple API, only 1 ``read`` method and 1 ``write`` method for tags.

    - does not require using different methods for different data types
    - requires the tag name only, no other information required from the user
    - automatically manages request/response size to pack as many requests into a single packet
    - automatically handles fragmented requests for large tags that can't fit in a single packet
    - both support full structure reading/writing (UDTs, AOIs, etc)

        - for ``read`` the ``Tag.value`` will be a ``dict`` of ``{attribute: value}``
        - for ``write`` the value should be a sequence of values or dict of {attribute: value} , nesting as needed

            - does not do partial writes, the value must match the complete structure
            - not recommended for builtin type (TIMER, CONTROL, COUNTER, etc)

        - both require no attributes to have an External Access of None

- ``generic_message`` for extra functionality not directly implemented
  
    - working similar to the MSG instruction in Logix, arguments similar to the MESSAGE properties
    - tested getting/setting drive parameters (see under examples in docs)
    - used internally to implement some of the other methods (get/set_plc_time, forward open/close, etc)
    
- simplified data types

    - strings use normal Python ``str`` objects, does not require reading/writing of the ``LEN`` and ``DATA`` attributes
    - BOOL arrays use normal Python ``bool`` objects, does not require complicated bit shifting of the DWORD value

- uploads the tag list and data type definitions from the PLC

    - no requirement for user to determine tags available (like from an L5X export)
    - controller-scoped tags by default, program-scoped tags are optional
    - definitions are required for ``read``/``write`` methods

- automatically enables/disables different features based on the target PLC

    - Extended Forward Open (EN2T or newer and v20+)
    - Symbol Instance Addressing (Logix v21+)
    - detection of Micro800 and disables unsupported features (CIP Path, Ex. Forward Open, Instance Addressing, etc)

Basic Usage
-----------

Connect to a PLC and get some basic information about it.  The ``path`` argument is the only one required, and it
has 3 forms:

  - IP Address Only (``10.20.30.100``) - Use if PLC is in slot 0 or if connecting to CompactLogix
  - IP Address/Slot (``10.20.30.100/1``) - Use if PLC is not in slot 0
  - CIP Routing Path (``10.20.30.100/backplane/3/enet/10.20.40.100/backplane/0``) - Use for more complex routing

     - first 2 examples will be replaced with the full path automatically, they're there for convenience.
     - ``enet``/``backplane`` (or ``bp``) are for port selection, easy to remember symbols for standard CIP routing pairs

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


By default, when creating the LogixDriver object, it will open a connection to the plc, read the program name, get the
controller info, and get all the controller scoped tags.  By reading the tag list first, this allows us to cache all the
tag type/structure information, including the instance ids for all the tags.  This information allows the ``read``/``write``
methods to require only the tag name. If your project will require program-scoped tags, be sure to set the ``init_program_tags`` kwarg.
By default, only the controller-scoped tags will be retrieved and cached.

Reading/Writing Tags
--------------------

Reading or writing tags is as simple as calling the ``read`` and ``write`` methods. Both methods accept any number of tags,
and will automatically pack multiple tags into a *Multiple Service Packet Service (0x0A)* while making sure to stay below the connection size.
If there is a tag value that cannot fit within the request/reply packet, it will automatically handle that tag independently
using the *Read Tag Fragmented (0x52)* or *Write Tag Fragmented (0x53)* requests.

Both methods will return ``Tag`` objects to reflect the success or failure of the operation.

::

    class Tag(NamedTuple):
        tag: str
        value: Any
        type: Optional[str] = None
        error: Optional[str] = None

``Tag`` objects are considered successful if the ``value`` is not ``None`` and the ``error`` is ``None``.
Otherwise, the ``error`` will indicate either the CIP error or exception that was thrown.  ``Tag.__bool__()`` has been implemented in this way.
``type`` will indicate the data type of the tag and include ``[<length>]`` if multiple array elements are requested.
``value`` will contain the value of the tag either read or written, structures (read only) will be in the form of a
``{ attribute: value, ... }`` dict.  Even though strings are technically structures, both reading and writing support
automatically converting them to/from normal string objects.  Any structures that have only the attributes ``LEN`` (DINT)
and ``DATA`` (array of SINT) will automatically be treated as strings.


Examples::

    with LogixDriver('10.20.30.100') as plc:
        plc.read('tag1', 'tag2', 'tag3')  # read multiple tags
        plc.read('array{10}') # read 10 elements starting at 0 from an array
        plc.read('array[5]{20}) # read 20 elements starting at elements 5 from an array
        plc.read('string_tag')  # read a string tag and get a string

        # writes require a sequence of tuples of [(tag name, value), ... ]
        plc.write(('tag1', 0), ('tag2', 1), ('tag3', 2))  # write multiple tags
        plc.write(('array{5}', [1, 2, 3, 4, 5]))  # write 5 elements to an array starting at the 0 element
        plc.write(('array[10]{5}', [1, 2, 3, 4, 5]))  # write 5 elements to an array starting at element 10
        plc.write(('string_tag', 'Hello World!'))  # write to a string tag with a string
        plc.write(('string_array[2]{5}', 'Write an array of strings'.split()))  # write an array of 5 strings starting at element 2

.. Note::

    Tag names for both ``read`` and ``write`` are case-sensitive and are required to be the same as they are named in
    the controller.  This may change in the future. (pull requests welcome)

Tag Definitions and Data Types
------------------------------

Tag definitions are uploaded from the controller automatically when connecting.  This allows the ``read``/``writing`` methods
to work.  These definitions contain information like instance ids and structure size and composition.  This information
allows for many optimizations and features that other similar libraries do not offer. The old ``pycomm`` API does not
depend on these, but the new ``read``/``write`` methods do. The tag definitions are accessible from the ``tags`` attribute.
The ``tags`` property is a dict of ``{tag name: definition}``.

Definitions for structures are accessible from the ``data_types`` attribute.  These include things like User-Defined Data Types (UDT),
Add-On Instructions (AOI), strings, and pre-defined types (TIMER, COUNTER, etc).  For structure tags (``tag['tag_type'] == 'struct'``),
the data type definition will be stored in the ``data_type`` attribute. (``'atomic'`` tags will only have a
string with their data type name: ``'DINT', 'REAL', ...``).

For details on the information contained and the structure of the definitions, refer the to the `Documentation`_.


Unit Testing
============

``pytest`` is used for unit testing. The ``tests`` directory contains an L5X export of the testing program
that contains all tags necessary for testing.  The only requirement for testing (besides a running PLC with the testing
program) is the environment variable ``PLCPATH`` for the PLC defined.

User Tests
----------

These tests are for users to run.  There are a few tests that are specific to a demo
plc, those are excluded. To run them you have the following options:

.. code-block::

    set PLCPATH=192.168.1.100
    pytest --ignore tests/online/test_demo_plc.py

*(or the equivalent in your shell)*

or using `tox`:

    - modify the ``PLCPATH`` variable in ``tox.ini``
    - then run this command: ``tox -e user``


.. Note::
    Test coverage is not complete, pull requests are welcome to help improve coverage.


License
=======
``pycomm3`` is distributed under the MIT License
