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

.. image:: https://img.shields.io/pypi/dm/pycomm3?style=for-the-badge
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

``pycomm3`` is a Python 3 fork of `pycomm`_, which is a native python library for communicating
with PLCs using Ethernet/IP.  The initial Python 3 translation was done in this fork_, this library
seeks to continue and expand upon the great work done by the original ``pycomm`` developers.  This library supports
Ethernet/IP communications with Allen-Bradley Control/Compact Logix and Micro800 PLCs. `pycomm`_ has support for SLC and MicroLogix
PLCs, but they have not been ported yet.  The module still exists in the package, but is broken and will raise a NotImplementedError
on import.  `pylogix`_ is another library with similar features (including Python 2 support), thank you to them for their hard
work as well.  Referencing `pylogix`_ code was a big help in implementing some features missing from `pycomm`_.
This library is only supported on Python 3.6 and up.

.. _pycomm: https://github.com/ruscito/pycomm

.. _fork: https://github.com/bpaterni/pycomm/tree/pycomm3

.. _pylogix: https://github.com/dmroeder/pylogix


Disclaimer
----------
PLCs can be used to control heavy or dangerous equipment, this library is provided 'As Is' and makes no guarantees on
it's reliability in a production environment.  This library makes no promises in the completeness or correctness of the
protocol implementations and should not be solely relied upon for critical systems.  The development for this library
is aimed at providing quick and convenient access for reading/writing data inside Allen-Bradley Control/Compact Logix PLCs.


Implementation
--------------
The Logix5000 Controller Data Access Manual, available from the `Rockwell Developer How-to Guides`_, was used to implement
the Ethernet/IP features in this library.  Features like reading tags/arrays, writing tags/arrays, getting the tag list are
all implemented based on the Data Access Manual.  The Rockwell KB Article *CIP Messages References* `748424`_ lists many useful KB Articles
for using the MSG instruction to perform various Ethernet/IP services. The Rockwell KB Article `23341`_ was used to implement feature
for getting the program name of the controller.  Article `28917`_ was used for collecting other controller information.

.. _Rockwell Developer How-to Guides: https://www.rockwellautomation.com/global/detail.page?pagetitle=Technology-Licensing-Developer-How-To-Guides&content_type=article&docid=f997dd3546ab8a53b86390649d17b89b#gate-44235fb6-1c27-499f-950b-e36e93af98de

.. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

.. _748424: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/748424

.. _28917: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/28917



Setup
-----
The package can be installed from

PIP:
::

    pip install pycomm3


Documentation
-------------

This README covers a basic overview of the library, full documentation can be found on
`Read the Docs <https://pycomm3.readthedocs.io/en/latest/>`_


Basic Usage
-----------

Connect to a PLC and get some basic information about it.  The ``path`` argument is the only one required, and it
has 3 forms:

  - IP Address Only (``10.20.30.100``) - Use if PLC is in slot 0 or if connecting to CompactLogix
  - IP Address/Slot (``10.20.30.100/1``) - Use if PLC is not in slot 0
  - CIP Routing Path (``10.20.30.100/backplane/3/enet/10.20.40.100/backplane/0``) - Use if needing to route thru a backplane
     - first 2 examples will be replaced with the full path automatically, they're there for convenience.
     - ``enet``/``backplane`` (or ``bp``) are for port selection, standard CIP routing but without having to remember
       which port is what value.

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
controller info, and get all the controller scoped tags.  Using the ``init_tags`` kwarg will enable/disable automatically
getting the controller tag list, and ``init_info`` will enable/disable program name and controller info loading.
By reading the tag list first, this allows us to cache all the tag type/structure information, including the instance ids
for all the tags.  This information allows the ``read``/``write`` methods to require only the tag name. If your project
will require program-scoped tags, be sure to set the ``init_program_tags`` kwarg.  By default, only the controller-scoped
tags will be read and cached.  Calling ``plc.get_tag_list(program='*')`` will also have the same effect.

Symbol Instance Addressing is only available on v21+, if the PLC is on a firmware lower than that,
getting the controller info will automatically disable that feature.  If you disable ``init_info`` and are using a controller
on a version lower than 21, set the ``plc.use_instance_ids`` attribute to false or your reads/writes will fail.

Default behavior is to use the Extended Forward Open service when opening a connection.  This allows the use of ~4KB of data for
each request, standard is only 500B.  Although this requires the communications module to be an EN2T or newer and the PLC
firmware to be version 20 or newer.  To use standard the Forward Open service set the ``large_packets`` kwarg to False.

Reading/Writing Tags
--------------------

Reading or writing tags is as simple as calling the ``read`` and ``write`` methods. Both methods accept any number of tags,
and will automatically pack multiple tags into a *Multiple Service Packet Service (0x0A)* while making sure to stay below the connection size.
If there is a tag value that cannot fit within the request/reply packet, it will automatically handle that tag independently
using the *Read Tag Fragmented (0x52)* or *Write Tag Fragmented (0x53)* requests.
Other similar libraries do not do this automatically, this library attempts to be as seamless as possible.

Both methods will return ``Tag`` objects to reflect the success or failure of the operation.

::

    class Tag(NamedTuple):
        tag: str
        value: Any
        type: Optional[str] = None
        error: Optional[str] = None

``Tag`` objects are considered successful if the value is not None and the error is None.  Otherwise, the error will
indicate either the CIP error or exception that was thrown.  ``Tag.__bool__()`` has been implemented in this way.
``type`` will indicate the data type of the tag and include ``[<length>]`` if multiple array elements are requested.
``value`` will contain the value of the tag either read or written, structures (read only) will be in the form of a
``{ attribute: value, ... }``.  Even though strings are technically structures, both reading and writing support
automatically converting them to/from normal string objects.  Any structures that have only the attributes ``LEN`` (DINT)
and ``DATA`` (array of SINT) will automatically be treated as strings. Reading of structures as a whole is supported
as long as no attributes have External Access set to None (CIP limitation).  Writing structures as a whole is not
supported (for the time being) except for string objects.


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

Tag Definitions
---------------

Tag definitions are uploaded from the controller automatically when connecting.  This allows the ``read``/``writing`` methods
to work.  These definitions contain information like instance ids and structure size and composition.  This information
allows for many optimizations and features that other similar libraries do not offer. The old ``pycomm`` API does not
depend on these, but the new ``read``/``write`` methods do. The tag definitions are accessible from the ``tags`` attribute.
The ``tags`` property is a dict of ``{tag name: definition}``.

Tag Information Collected::

    {
        'tag1': {
            'tag_name': 'tag1',  # same as key
            'dim': 0,  # number of dimensions of array (0-3)
            'instance_id':  # used for reads/writes on v21+ controllers
            'alias': True/False,  # if the tag is an alias to another (this is not documented, but an educated guess found thru trial and error
            'external_access': 'Read/Write',  # string value of external access setting
            'dimensions': [0, 0, 0]  # array dimensions
            'tag_type': 'atomic',
            'data_type' : 'DINT'  # string value of an atomic type
       }
       'tag2' : {
            ...
            'tag_type': 'struct',
            'data_type': {
                'name': 'TYPE', # name of structure, udt, or aoi
                'internal_tags': {
                    'attribute': {  # is an atomic type
                        'offset': 0 # byte offset for members within the struct, used mostly for reading an entire structure
                        'tag_type': 'atomic',
                        'data_type:  'Type', # name of data type
                        'bit': 0   # optional, exists if element is mapped to a bit of a dint or element of a bool array
                        'array': 0,  # optional, length of error if the attribute is an array
                        }
                    'attribute2': {  # is a struct
                        ...,
                        'tag_type': 'struct',
                        'data_type': {
                            'name': 'TYPE',  # name of data type,
                            'internal_tags' : {  # definition of all tags internal/hidden and public attributes
                                ... # offset/array/bit/tag_type/data_type
                            },
                            'attributes' : [...], # list of public attributes (shown in Logix)
                            'template' : {...}, # used internally
                        }

                    }
                ...
                }
            }
       }


        ...
    }



.. Note::
    If running multiple clients, you can initialize all the tag definitions in one client and pass them to other clients
    by turning off the init_* args and setting ``plc2._tags = plc1.tags``.


Unit Testing
------------

``pytest`` is used for unit testing. The ``tests`` directory contains an L5X export of the ``Pycomm3_Testing`` program
that contains all tags necessary for testing.  The only requirement for testing (besides a running PLC with the testing
program) is the environment variable ``PLCPATH`` for the PLC defined.

.. Note::
    Test coverage is not complete, pull requests are very much welcome to cover all combinations for reading and writing tags.


License
~~~~~~~
``pycomm3`` is distributed under the MIT License
