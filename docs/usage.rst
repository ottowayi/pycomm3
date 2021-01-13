====================
LogixDriver Overview
====================

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

There is some data that is collected about the target controller when a connection is first established.  Assuming the
``init_info`` kwarg is set to ``True`` (default) when creating the LogixDriver, it will call both the :meth:`~LogixDriver.get_plc_info`
and :meth:`~LogixDriver.get_plc_name` methods. :meth:`~LogixDriver.get_plc_info` returns a dict of the info collected
and stores that information, making it accessible from the :attr:`~LogixDriver.info` property. :meth:`~LogixDriver.get_plc_name`
will return the name of the program running in the PLC and store it in :attr:`~LogixDriver.info['name']`.
See :attr:`~LogixDriver.info` for details on the specific fields.

Symbol Instance Addressing is a feature that allows more requests to be sent in a single packet by using a short identifier
for a tag instead of needing to encode the full tag name in the request.  These instance ids are uploaded with the tag definitions.
But, this feature is only available on v21+ firmwares. If the PLC is on a firmware lower than that, getting the controller info
will automatically disable that feature. If you disable ``init_info`` and are using a controller on a version lower than 21,
set the ``plc.use_instance_ids`` attribute to false or your reads/writes will fail.

Default behavior is to use the *Extended Forward Open* service when opening a connection.  This allows the use of ~4KB of data for
each request, standard is only 500B.  Although this requires the communications module to be an EN2T or newer and the PLC
firmware to be version 20 or newer.  Upon opening a connection, the ``LogixDriver`` will attempt an *Extended Forward Open*,
if that fails it will then try using the standard *Forward Open*. To use standard the Forward Open service directly,
set the ``large_packets`` kwarg to False.


Tags and Data Types
-------------------

When creating the driver it will automatically upload all of the controller scope tag and their data type definitions.
These definitions are required for the :meth:`~LogixDriver.read` and :meth:`~LogixDriver.write` methods to function.
Those methods abstract away a lot of the details required for actually implementing the Ethernet/IP protocol. Uploading
the tags typically takes a few seconds depending on the size of program and the network.  It was decided this small
upfront overhead provided a greater benefit to the user since they would not have to worry about specific implementation
details for different types of tags.  The ``init_tags`` kwarg is ``True`` by default, meaning that all of the controller
scoped tags will be uploaded. ``init_program_tags`` will upload the program-scoped tags for all programs, this is ``False``
by default, it should be set if you will be using any program-scoped tags.

Below shows how the init tag options are equivalent to calling the :meth:`~LogixDriver.get_tag_list` method.

>>> plc1 = LogixDriver('10.20.30.100')
>>> plc2 = LogixDriver('10.20.30.100', init_tags=False)
>>> plc2.get_tag_list()
>>> plc1.tags == plc2.tags
True
>>> plc3 = LogixDriver('10.20.30.100', init_program_tags=True)
>>> plc4 = LogixDriver('10.20.30.100')
>>> plc4.get_tag_list(program='*')
>>> plc3.tags == plc4.tags
True

.. _tag-def:

Tag Structure
^^^^^^^^^^^^^

Each tag definition is a dict containing all the details retrieved from the PLC.  :meth:`~LogixDriver.get_tag_list`
returns a list of dicts for the tag list while the :attr:`LogixDriver.tags` property stores them as a dict of ``{tag name: definition}``.

**Tag Definition Properties:**

tag_name
    Symbolic name of the tag

instance_id
    Internal PLC identifier for the tag.  Used for reads/writes on v21+ controllers. Saves space in packet by not requiring
    the full tag name to be encoded into the request.

tag_type
    - ``'atomic'`` base data types like BOOL, DINT, REAL, etc.
    - ``'struct'`` complex data types like STRING, TIMER, PID, etc as well as UDTs and AOIs.

.. _data_type:

data_type
    - ``'DINT'``/``'REAL'``/etc name of data type for atomic types
    - ``{data type definition}`` for structures, detailed in `Structure Definitions`_

data_type_name
    - the string name of the data type: ``'DINT'``/``'REAL'``/``'TIMER'``/``'MyCoolUDT'``

string
    **Optional** string size if the tag is a STRING type (or custom string)

external_access
    ``'Read/Write'``/``'Read Only'``/``'None'`` matches the External Access tag property in the PLC

dim
    number dimensions defined for the tag
    - ``0`` - not an array
    - ``1-3`` - a 1 to 3 dimension array tag

dimensions
    length of each dimension defined, ``0`` if dimension does not exist.  ``[dim0, dim1, dim2]``

alias
    ``True``/``False`` if the tag is an alias to another.

    .. note:: This is not documented, but an educated guess found through trial and error.


.. _struct-def:

Structure Definitions
^^^^^^^^^^^^^^^^^^^^^

While uploading the tag list, any tags with complex data types will have the full definition of structure uploaded as well.
Inside a tag definition, the `data_type`_ attribute will be a dict containing the structure definition.  The :attr:`LogixDriver.data_types`
property also provides access to these definitions as a dict of ``{data type name: definition}``.

**Data Type Properties:**

name
    Name of the data type, UDT, AOI, or builtin structure data types

attributes
    List of names for each attribute in the structure. Does not include internal tags not shown in Logix, like the host
    DINT tag that BOOL attributes are mapped to.

template
    Dict with template definition. Used internally within LogixDriver, allows reading of full structs and allows the read/write
    methods to monitor the request/response size.

internal_tags
    A dict with each attribute (including internal, not shown in Logix attributes) of the structure containing the
    definition for the attribute, ``{attribute: {definition}}``.

    **Definition:**

    tag_type
        Same as `Tag Structure`_

    data_type
        Same as `Tag Structure`_

    data_type_name
        Same as `Tag Structure`_

    string
        Same as `Tag Structure`_

    offset
        Location/Byte offset of this tag's data in the response data.

    bit
        **Optional** BOOL tags are aliased to internal hidden integer tags, this indicates which bit it is aliased to.

    array
        **Optional** Length of the array if this tag is an array, ``0`` if not an array,

.. note:: ``attributes`` and ``internal_tags`` do **NOT** include InOut parameters.


Reading/Writing Tags
--------------------

All reading and writing is handled by the :meth:`~LogixDriver.read` and :meth:`~LogixDriver.write` methods.  The original
pycomm and other similar libraries will have different methods for handling different types like strings and arrays.
Both methods accept any number of tags, they will automatically use the *Multiple Service Packet (0x0A)* service and track
the request/return data size making sure to stay below the connection size.  If there is a tag value that cannot fit
within the request/reply packet, it will automatically handle that tag independently using the *Read Tag Fragmented (0x52)*
or *Write Tag Fragmented (0x53)* requests.


Response Tag
^^^^^^^^^^^^

Both read/write methods return ``Tag`` objects with the results of the operation.

.. code-block:: python

    class Tag(NamedTuple):
        tag: str
        value: Any
        type: Optional[str] = None
        error: Optional[str] = None


**Attributes:**

    tag
        tag name

    value
        will contain the value of tag read, or the value written.  May be ``None`` on error.

    type
        data type of tag, will include ``[<len>]`` when multiple array elements are requested

    error
        ``None`` if successful, else the CIP error or exception thrown


Reading Tags
^^^^^^^^^^^^

:meth:`LogixDriver.read` accepts any number of tags, all that is required is the tag names. To read an array,
add ``{<# elements>}`` suffix to the tag name.  Reading of entire structures is support as long as none of the
attributes have an external access of None. To read a structure, just request the base name.  The ``value`` for
the ``Tag`` object will a a dict of ``{attribute: value}``

Read an atomic tag

>>> plc.read('dint_tag')
Tag(tag='dint_tag', value=0, type='DINT', error=None)

Read multiple tags

>>> plc.read('tag_1', 'tag_2', 'tag_3')
[Tag(tag='tag_1', value=100, type='INT', error=None), Tag(tag='tag_2', value=True, type='BOOL', error=None), ...]

Read a structure

>>> plc.read('simple_udt')
Tag(tag='simple_udt', value={'attr1': 0, 'attr2': False, 'attr3': 1.234}, type='SimpleUDT', error=None)

Read arrays

>>> plc.read('dint_array{5}')  # starts at index 0
Tag(tag='dint_array', value=[1, 2, 3, 4, 5], type='DINT[5]', error=None)
>>> plc.read('dint_array[20]{3}') # read 3 elements starting at index 20
Tag(tag='dint_array[20]', value=[20, 21, 22], type='DINT[3]', error=None)

Verify all reads were successful

>>> tag_list = ['tag1', 'tag2', ...]
>>> results = plc.read(*tag_list)
>>> if all(results):
...     print('All tags read successfully')
All tags read successfully


Writing Tags
^^^^^^^^^^^^

:meth:`LogixDriver.write` method accepts any number of tag-value pairs of the tag name and value to be written.
To write arrays, include ``{<# elements>}`` suffix to the tag name and the value should be a list of the values to write.
A ``RequestError`` will be raised if the value list is too short, else it will be truncated if too long.

Write a tag

>>> plc.write(('dint_tag', 100))
Tag(tag='dint_tag', value=100, type='DINT', error=None)

Write many tags

>>> plc.write(('tag_1', 1), ('tag_2', True), ('tag_3', 1.234))
[Tag(tag='tag_1', value=1, type='INT', error=None), Tag(tag='tag_2', value=True, type='BOOL', error=None), ...]

Write arrays

>>> plc.write(('dint_array{10}', list(range(10))))  # starts at index 0
Tag(tag='dint_array', value=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], type='DINT[10]', error=None)
>>> plc.write(('dint_array[10]{3}', [10, 11, 12]))  # write 3 elements starting at index 10
Tag(tag='dint_array[10]', value=[10, 11, 12], type='DINT[3]', error=None)

Check if all writes were successful

>>> tag_values = [('tag1', 10), ('tag2', True), ('tag3', 12.34)]
>>> results = plc.write(*tag_values)
>>> if all(results):
...     print('All tags written successfully')
All tags written successfully


String Tags
^^^^^^^^^^^

Strings are technically structures within the PLC, but are treated as atomic types in this library.  There is no need
to handle the ``LEN`` and ``DATA`` attributes, the structure is converted to/from Python ``str`` objects transparently.
Any structures that contain only a DINT-``LEN`` and a SINT[]-``DATA`` attributes will be automatically treated as string tags.
This allows the builtin STRING types plus custom strings to be handled automatically.  Strings that are longer than the
plc tag will be truncated when writing.

>>> plc.read('string_tag')
Tag(tag='string_tag', value='Hello World!', type='STRING', error=None)
>>> plc.write(('short_string_tag', 'Test Write'))
Tag(tag='short_string_tag', value='Test Write', type='STRING20', error=None)


Logging
-------

This library uses the standard Python `logging`_ module.  You may configure the logging module as needed.  The ``DEBUG``
level will log every sent/received packed and other diagnostic data.  Set the level to higher than ``DEBUG`` if you only
wish to see errors, exceptions, etc.

.. code-block::

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

Produces output similar to::

    DEBUG:pycomm3.packets.requests.RequestPacket:Sent: RegisterSessionRequestPacket()
    DEBUG:pycomm3.packets.requests.RequestPacket:Received: RegisterSessionResponsePacket(session=659398, error=None)
    DEBUG:pycomm3.clx.LogixDriver:Session = 659398 has been registered.
    DEBUG:pycomm3.packets.requests.RequestPacket:Sent: SendRRDataRequestPacket()
    DEBUG:pycomm3.packets.requests.RequestPacket:Received: SendRRDataResponsePacket(service=b'\xdb', command=b'o\x00', error=None)
    DEBUG:pycomm3.packets.requests.GenericReadRequestPacket:Sent: GenericReadRequestPacket(service=b'\x01', class_code=b'\x01', instance=b'\x01\x00', request_data=None)
    DEBUG:pycomm3.packets.requests.GenericReadRequestPacket:Received: GenericReadResponsePacket(value={'_keyswitch': b'`1', 'device_type': '1756-L73/A LOGIX5573', 'product_code': 94, 'product_type': 14, ...}, error=None)


A separate ``VERBOSE_DEBUG`` option is available to print out the raw bytes contents of the sent/received packets to aid
in development and debugging.

.. code-block::

    from pycomm3.packets.requests import RequestPacket
    RequestPacket.VERBOSE_DEBUG = True

Verbose output::

    DEBUG:pycomm3.packets.requests.RequestPacket:>>> SEND >>>
    (0000) 65 00 04 00 00 00 00 00 00 00
    (0010) 00 00 5f 70 79 63 6f 6d 6d 5f
    (0020) 00 00 00 00 01 00 00 00
    DEBUG:pycomm3.packets.requests.RequestPacket:Sent: RegisterSessionRequestPacket()
    DEBUG:pycomm3.packets.requests.RequestPacket:<<< RECEIVE <<<
    (0000) 65 00 04 00 de 0f 6f 00 00 00
    (0010) 00 00 5f 70 79 63 6f 6d 6d 5f
    (0020) 00 00 00 00 01 00 00 00
    DEBUG:pycomm3.packets.requests.RequestPacket:Received: RegisterSessionResponsePacket(session=7278558, error=None)
    DEBUG:pycomm3.clx.LogixDriver:Session = 7278558 has been registered.
    DEBUG:pycomm3.packets.requests.RequestPacket:>>> SEND >>>
    (0000) 6f 00 44 00 de 0f 6f 00 00 00
    (0010) 00 00 5f 70 79 63 6f 6d 6d 5f
    (0020) 00 00 00 00 00 00 00 00 0a 00
    (0030) 02 00 00 00 00 00 b2 00 34 00
    (0040) 5b 02 20 06 24 01 0a 05 00 00
    (0050) 00 00 45 d7 99 a1 27 04 09 10
    (0060) 56 45 45 60 07 00 00 00 01 40
    (0070) 20 00 a0 0f 00 42 01 40 20 00
    (0080) a0 0f 00 42 a3 03 01 0a 20 02
    (0090) 24 01
    DEBUG:pycomm3.packets.requests.RequestPacket:Sent: SendRRDataRequestPacket()

.. _logging: https://docs.python.org/3/library/logging.html