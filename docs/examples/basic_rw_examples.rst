======================================
Basic Reading and Writing Tag Examples
======================================

Basic Reading
-------------

Reading a single tag returns a Tag object.

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_single

    >>> read_single()
    Tag(tag='DINT1', value=20, type='DINT', error=None)

Reading multiple tags returns a list of Tag objects.

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_multiple

    >>> read_multiple()
    [Tag(tag='DINT1', value=20, type='DINT', error=None), Tag(tag='SINT1', value=5, type='SINT', error=None), Tag(tag='REAL1', value=100.0009994506836, type='REAL', error=None)]

An array is represented in a single Tag object, but the ``value`` attribute is a list.

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_array

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_array_slice

    >>> read_array()
    Tag(tag='DINT_ARY1', value=[0, 1000, 2000, 3000, 4000], type='DINT[5]', error=None)
    >>> read_array_slice()
    Tag(tag='DINT_ARY1[50]', value=[50000, 51000, 52000, 53000, 54000], type='DINT[5]', error=None)

You can read strings just like a normal value, no need to handle the ``LEN`` and ``DATA`` attributes individually.

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_strings

    >>> read_strings()
    [Tag(tag='STRING1', value='A Test String', type='STRING', error=None), Tag(tag='STRING_ARY1[2]', value=['THIRD', 'FoUrTh'], type='STRING[2]', error=None)]

Structures can be read as a whole, assuming that no attributes have External Access set to None. Structure tags will be
a single Tag object, but the ``value`` attribute will be a ``dict`` of ``{attribute: value}``.

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_udt

    .. literalinclude:: ../../examples/basic_reads.py
        :pyobject: read_timer

    >>> read_udt()
    Tag(tag='SimpleUDT1_1', value={'bool': True, 'sint': 100, 'int': -32768, 'dint': -1, 'real': 0.0}, type='SimpleUDT1', error=None)
    >>> read_timer()
    Tag(tag='TIMER1', value={'CTL': [False, False, False, False, False, False, False, False, False, False, False,
                                     False, False, False, False, False, False, False, False, False, False, False,
                                     False, False, False, False, False, False, False, True, True, False],
                              'PRE': 30000, 'ACC': 30200, 'EN': False, 'TT': True, 'DN': True}, type='TIMER', error=None)

    .. note:: Most builtin data types appear to have a BOOL array (or DWORD) attribute called ``CTL`` that is not shown
              in the Logix tag browser.

Basic Writing
-------------

Writing a single tag returns a single Tag object response.

    .. literalinclude:: ../../examples/basic_writes.py
        :pyobject: write_single

    >>> write_single()
    Tag(tag='DINT2', value=100000000, type='DINT', error=None)

Writing multiple tags will return a list of Tag objects.

    .. literalinclude:: ../../examples/basic_writes.py
        :pyobject: write_multiple

    >>> write_multiple()
    [Tag(tag='REAL2', value=25.2, type='REAL', error=None), Tag(tag='STRING3', value='A test for writing to a string.', type='STRING', error=None)]

Writing a whole structure is possible too.  As with reading, all attributes are required to NOT have an External Access of None.
Also, when writing a structure your value must match the structure exactly and provide data for all attributes. The value
should be a list of values or a dict of attribute name and value, nesting as needed for arrays or other structures with the target.
This example shows a simple recipe UDT:

+-------------------+---------------+
| Attribute         |  Data Type    |
+===================+===============+
| Enabled           |  BOOL         |
+-------------------+---------------+
| OpCodes           |  DINT[10]     |
+-------------------+---------------+
| Targets           |  REAL[10]     |
+-------------------+---------------+
| StepDescriptions  |  STRING[10]   |
+-------------------+---------------+
| TargetUnits       |  STRING8[10]  |
+-------------------+---------------+
| Name              |  STRING       |
+-------------------+---------------+

    .. literalinclude:: ../../examples/basic_writes.py
        :pyobject: write_structure
