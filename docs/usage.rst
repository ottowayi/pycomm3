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

external_access
    ``'Read/Write'``/``'Read Only'``/``'None'`` matches the External Access tag property in the PLC

dim
    dimensions defined for the tag
    - ``0`` - not an array
    - ``1-3`` - a 1 to 3 dimension array tag

dimensions
    length of each dimension defined, ``0`` if dimension is does not exist.  ``[dim0, dim1, dim2]``

alias
    ``True``/``False`` if tag is an alias to another.

    .. note:: This is not documented, but an educated guess found through trial and error.



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

    offset
        Position of this tag in the response data this tag.

    bit
        **Optional** BOOL tags are aliased to internal hidden integer tags, this indicates which bit it is aliased to.

    array
        **Optional** Length of the array if this tag is an array, ``0`` if not an array,


Reading/Writing Tags
--------------------

All reading and writing is handled by the :meth:`~LogixDriver.read` and :meth:`~LogixDriver.write` methods.  The original
pycomm and other similar libraries will have different methods for handling different types like strings and arrays.