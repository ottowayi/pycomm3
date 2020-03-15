.. pycomm3 documentation master file, created by
   sphinx-quickstart on Fri Mar 13 09:59:18 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


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
   :alt: License


``pycomm3`` is a Python 3 fork of `pycomm`_, which is a native python library for communicating
with PLCs using Ethernet/IP.  The initial Python 3 translation was done in this fork_, this library
seeks to continue and expand upon the great work done by the original ``pycomm`` developers.  This library supports
Ethernet/IP communications with Allen-Bradley Control & Compact Logix PLCs. ``pycomm`` has support for SLC and MicroLogix
PLCs, but they have not been ported yet.  The module still exists in the package, but is broken and will raise a ``NotImplementedError``
on import.  `pylogix`_ is another library with similar features (including Python 2 support), thank you to them for their hard
work as well.  Referencing ``pylogix`` code was a big help in implementing some features missing from ``pycomm``.
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


Installation
------------

This library is distributed on `PyPI`_ and can be installed from ``pip``:

::

   pip install pycomm3

.. _PyPI: https://pypi.org/project/pycomm3/



Implementation
--------------

The Logix5000 Controller Data Access Manual, available from the `Rockwell Developer How-to Guides`_, was used to implement
the Ethernet/IP features in this library.  Features like reading tags/arrays, writing tags/arrays, getting the tag list are
all implemented based on the Data Access Manual.  The Rockwell KB Article *CIP Messages References* `748424`_ lists many useful KB Articles
for using the MSG instruction to perform various Ethernet/IP services. The Rockwell Knowledge Base Article `23341`_ was used to implement feature
for getting the program name of the controller.  Article `28917`_ was used for collecting other controller information.

.. _Rockwell Developer How-to Guides: https://www.rockwellautomation.com/global/detail.page?pagetitle=Technology-Licensing-Developer-How-To-Guides&content_type=article&docid=f997dd3546ab8a53b86390649d17b89b#gate-44235fb6-1c27-499f-950b-e36e93af98de

.. _23341: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/23341

.. _748424: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/748424

.. _28917: https://rockwellautomation.custhelp.com/app/answers/answer_view/a_id/28917



Contents
--------

.. toctree::
   :maxdepth: 2

   usage
   logixdriver
