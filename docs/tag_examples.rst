=====================================
Examples of Working with the Tag List
=====================================

Data Type Structures
--------------------

For UDT/AOI or built-in structure data-types, information and definitions are stored in the ``data_types`` property.
This property allow you to query the PLC to determine what types of tags it may contain.

Print out the public attributes for all structure types in the PLC:

    .. literalinclude:: ../examples/tags.py
        :pyobject: find_attributes

    >>> find_attributes()
    STRING attributes:  ['LEN', 'DATA']
    TIMER attributes:  ['CTL', 'PRE', 'ACC', 'EN', 'TT', 'DN']
    CONTROL attributes:  ['CTL', 'LEN', 'POS', 'EN', 'EU', 'DN', 'EM', 'ER', 'UL', 'IN', 'FD']
    DateTime attributes:  ['Yr', 'Mo', 'Da', 'Hr', 'Min', 'Sec', 'uSec']
    ...