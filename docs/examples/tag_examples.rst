=====================================
Examples of Working with the Tag List
=====================================

Data Types
----------

For UDT/AOI or built-in structure data-types, information and definitions are stored in the ``data_types`` property.
This property allow you to query the PLC to determine what types of tags it may contain.  For details on the contents of
a data type definition view :ref:`usage/logixdriver:Structure Definitions`.

Print out the public attributes for all structure types in the PLC:

    .. literalinclude:: ../../examples/tags.py
        :pyobject: find_attributes

    >>> find_attributes()
    STRING attributes:  ['LEN', 'DATA']
    TIMER attributes:  ['CTL', 'PRE', 'ACC', 'EN', 'TT', 'DN']
    CONTROL attributes:  ['CTL', 'LEN', 'POS', 'EN', 'EU', 'DN', 'EM', 'ER', 'UL', 'IN', 'FD']
    DateTime attributes:  ['Yr', 'Mo', 'Da', 'Hr', 'Min', 'Sec', 'uSec']
    ...


Tag List
--------

Part of the requirement for reading/writing tags is knowing the tag definitions stored in the PLC so that user does not
need to provide any information about the tag besides it's name.  By default, the tag list is uploaded on creation of the
LogixDriver, for details reference the :ref:`api_reference/logix_driver:LogixDriver API`.

Example showing how the tag list is stored:

    .. literalinclude:: ../../examples/tags.py
        :pyobject: tag_list_equal

    >>> tag_list_equal()
    They are the same!
    Calling get_tag_list() does the same thing.

Filtering
^^^^^^^^^

There are multiple properties of tags that can be used to locate and filter down the tag list.  For available properties,
reference :ref:`usage/logixdriver:Tag Structure`. Examples below show some methods for filtering the tag list.

Finding all PID tags:

    .. literalinclude:: ../../examples/tags.py
        :pyobject: find_pids

    >>> find_pids()
    ['FIC100_PID', 'TIC100_PID']