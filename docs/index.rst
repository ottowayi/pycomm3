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


Introduction
------------

`pycomm3` started as a Python 3 fork of `pycomm`_, which is a Python 2 library for
communicating with Allen-Bradley PLCs using Ethernet/IP.  The initial Python 3 port was done
in this `fork`_ and was used as the base for `pycomm3`.  Since then, the library has been
almost entirely rewritten and the API is no longer compatible with `pycomm`.  Without the
hard work done by the original `pycomm` developers, `pycomm3` would not exist.  This
library seeks to expand upon their great work.


.. _pycomm: https://github.com/ruscito/pycomm

.. _fork: https://github.com/bpaterni/pycomm/tree/pycomm3


Drivers
-------

`pycomm3` includes 3 drivers: :class:`CIPDriver`, :class:`LogixDriver`, :class:`SLCDriver`.

- :class:`CIPDriver`
    This driver is the base driver for the library, it handles common CIP services used
    by the other drivers.  Things like opening/closing a connection, register/unregister sessions,
    forward open/close services, device discovery, and generic messaging.

- :class:`LogixDriver`
    This driver supports services specific to ControlLogix, CompactLogix, and Micro800 PLCs.
    Services like reading/writing tags, uploading the tag list, and getting/setting the PLC time.

- :class:`SLCDriver`
    This driver supports basic reading/writing data files in a SLC500 or MicroLogix PLCs.  It is
    a port of the `SlcDriver` from `pycomm` with minimal changes to make the API similar to the
    other drivers. Currently this driver is considered legacy and it's development will be on
    a limited basis.


Disclaimer
----------

PLCs can be used to control heavy or dangerous equipment, this library is provided 'As Is' and makes no guarantees on
its reliability in a production environment.  This library makes no promises in the completeness or correctness of the
protocol implementations and should not be solely relied upon for critical systems.  The development for this library
is aimed at providing quick and convenient access for reading/writing data inside Allen-Bradley PLCs.


Setup
-----
The package can be installed from `PyPI`_ using ``pip``: ``pip install pycomm3`` or ``python -m pip install pycomm3``.

.. _PyPI: https://pypi.org/project/pycomm3/

Optionally, you may configure logging using the Python standard `logging`_ library.  A convenience method is provided
to help configure basic logging, see the :ref:`getting_started:Logging` section.

.. _logging: https://docs.python.org/3/library/logging.html



Contents
--------

.. toctree::
    :maxdepth: 3

    getting_started
    usage/index
    examples/index
    api_reference/index
