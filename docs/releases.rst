===============
Release History
===============

1.1.1
=====

LogixDriver
-----------

- |:bug:| fixed read/write errors by preventing program-scoped tags from using instance ids in the request


1.1.0
=====

LogixDriver
-----------

- |:bug:| fixed bugs in handling of built-in types (TIMER, CONTROL, etc)
- |:bug:| fixed bugs in structure tag handling when padding exists between attributes
- |:sparkles:| changed the meaning of the element count for BOOL arrays
    - Previously, the ``{#}`` referred to the underlying ``DWORD`` elements of the ``BOOL`` array.
      A ``BOOL[64]`` array is actually a `DWORD[2]` array, so ``array{1}`` translated to BOOL elements
      0-31 or the first ``DWORD`` element. Now, the ``{#}`` refers to the number of ``BOOL`` elements.  So
      ``array{1}`` is only a single ``BOOL`` element and ``array{32}`` would be the 0-31 ``BOOL`` elements.
    - Refer to the documentation_ for limitations on writing.

.. _documentation: https://docs.pycomm3.dev/en/latest/usage/logixdriver.html#bool-arrays

1.0.1
=====

- |:bug:| Fixed incorrect/no error in response Tag for some failed requests in a multi-request
- |:recycle:| Minor refactor to status and extended status parsing



1.0.0
=====

- |:sparkles:| New type system to replace the ``Pack`` and ``Unpack`` helper classes
    - New types represent any CIP type or object and allow encoding and decoding of values
    - Allows users to create their own custom types
    - |:boom:| **[Breaking]** ``generic_message`` replaced the ``data_format`` argument with ``data_type``, see documentation for details.
- |:sparkles:| Added a new ``discover()`` method for finding Ethernet/IP devices on the local network
- |:sparkles:| Added a ``configure_default_logger`` method for simple logging setup
    - Packet contents are now logged using a custom ``VERBOSE`` level
- |:art:| Internal package structure changed.
- |:recycle:| Lots of refactoring, decoupling, etc
- |:white_check_mark:| Increased test coverage
- |:memo:| New and improved documentation
    - |:construction:| Still a work-in-progress


Logix Driver
^^^^^^^^^^^^

- |:triangular_flag_on_post:| Upload of program-scoped tags is now enabled by default
    - Use ``init_program_tags=False`` in initializer for to upload controller-scoped only tags
- |:boom:| Removed the ``init_info`` and ``micro800`` init args and the ``use_instance_ids`` property
    - These have all been automatic for awhile now, but were left for backwards compatibility
    - If you need to customize this behavior, override the ``_initialize_driver`` method
