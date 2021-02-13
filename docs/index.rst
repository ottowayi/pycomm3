:mod:`pycomm3` - A Python Ethernet/IP library for communicating with Allen-Bradley PLCs.
========================================================================================

.. module:: pycomm3

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
seeks to continue and expand upon the great work done by the original ``pycomm`` developers.
`pylogix`_ is another library with similar features (including Python 2 support) for ControlLogix and CompactLogix PLCs.
Referencing ``pylogix`` code was a big help in implementing some features missing from ``pycomm``.  This library is
supported on Python 3.6.1 and newer.

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
----------

PLCs can be used to control heavy or dangerous equipment, this library is provided 'As Is' and makes no guarantees on
it's reliability in a production environment.  This library makes no promises in the completeness or correctness of the
protocol implementations and should not be solely relied upon for critical systems.  The development for this library
is aimed at providing quick and convenient access for reading/writing data inside Allen-Bradley PLCs.


Installation
------------

This library is distributed on `PyPI`_ and can be installed from ``pip``:

::

   pip install pycomm3

.. _PyPI: https://pypi.org/project/pycomm3/


Setup
-----
The package can be installed from `PyPI`_ using ``pip``: ``pip install pycomm3`` or ``python -m pip install pycomm3``.

.. _PyPI: https://pypi.org/project/pycomm3/

Optionally, you may configure logging using the Python standard `logging`_ library.

.. _logging: https://docs.python.org/3/library/logging.html


Implementation
--------------

The Logix5000 Controller Data Access Manual, available from the `Rockwell Developer How-to Guides`_, was used to implement
the Ethernet/IP features in this library.  Features like reading tags/arrays, writing tags/arrays, getting the tag list are
all implemented based on the Data Access Manual.  The Rockwell KB Article *CIP Messages References* `748424`_ lists many useful KB Articles
for using the MSG instruction to perform various Ethernet/IP services. The Rockwell Knowledge Base Article `23341`_ was used to implement feature
for getting the program name of the controller.  Article `28917`_ was used for collecting other controller information.

.. _Rockwell Developer How-to Guides: https://www.rockwellautomation.com/en-us/company/news/articles/technology-licensing-developer-how-to-guides.html

.. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

.. _748424: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/748424

.. _28917: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/28917



Contents
--------

.. toctree::
   :maxdepth: 3

   usage
   logixdriver
   slcdriver
   cipdriver
   examples
   cip_constants
