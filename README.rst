pycomm3
=======
``pycomm3`` is a Python 3 fork of `pycomm`_, which is a native python library for communicating
with PLCs using Ethernet/IP.  The initial Python 3 translation was done in this fork_, this library
seeks to continue and expand upon the great work done by the original ``pycomm`` developers.  This library supports
Ethernet/IP communications with Allen-Bradley Control & Compact Logix PLCs. ``pycomm`` has support for SLC and MicroLogix
PLCs, but they have not been ported yet.  The module still exists in the package, but is broken and will raise a NotImplementedError
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


Implementation
--------------
The Logix5000 Controller Data Access Manual, available here `Rockwell Developer How-to Guides`_, was used to implement
the Ethernet/IP features in this library.  Features like reading tags/arrays, writing tags/arrays, getting the tag list are
all implemented based on the Data Access Manual.  The Rockwell KB Article *CIP Messages References* `748424`_ lists many useful KB Articles
for using the MSG instruction to perform various Ethernet/IP services. The Rockwell Knowledge Base Article `23341`_ was used to implement feature
for getting the program name of the controller.  Article `28917`_ was used for collecting other controller information.

.. _Rockwell Developer How-to Guides: https://www.rockwellautomation.com/global/detail.page?pagetitle=Technology-Licensing-Developer-How-To-Guides&content_type=article&docid=f997dd3546ab8a53b86390649d17b89b#gate-44235fb6-1c27-499f-950b-e36e93af98de

.. _23341: https://rockwellautomation.custhelp.com/app/answers/detail/a_id/23341

.. _748424: https://rockwellautomation.custhelp.com/app/answers/detail/a_id/748424/page/1

.. _28917: https://rockwellautomation.custhelp.com/app/answers/detail/a_id/28917



Setup
-----
The package can be installed from

PIP:
::

    pip install git+https://github.com/ottowayi/pycomm3.git


Basic Usage
-----------

Connect to a PLC and get some basic information,
use the ``slot`` kwarg if the PLC is not in slot 0.  CompactLogix leave ``slot=0``.

::

    from pycomm3 import LogixDriver

    with LogixDriver('10.20.30.100', slot=1) as plc:
        print(plc)
        # OUTPUT:
        # Program Name: PLCA, Device: 1756-L74/A LOGIX5574, Revision: 31.11

        print(plc.info)
        # OUTPUT:
        # {'vendor': 'Rockwell Automation/Allen-Bradley', 'product_type': 'Programmable Logic Controller',
        # 'product_code': 55, 'version_major': 20, 'version_minor': 12, 'revision': '20.12', 'serial': '004b8fe0',
        # 'device_type': '1756-L62/B LOGIX5562', 'keyswitch': 'REMOTE RUN', 'name': 'PLCA'}



By default, when creating the LogixDriver object, it will open a connection to the plc, read the program name, get the
controller info, and get all the controller scoped tags.  Using the ``init_tags`` kwarg will enable/disable automatically
getting the controller tag list, and ``init_info`` will enable/disable program name and controller info loading.
By reading the tag list first, this allows us to cache all the tag type/structure information, including the instance ids
for all the tags.  This information allows the ``read``/``write`` methods to require only the tag name. If your project
will require program-scoped tags, be sure to set the ``init_program_tags`` kwarg.  By default, only the controller-scoped
tag will be read and cached.  Calling ``plc.get_tag_list(program='*')`` will also have the same effect.

Symbol Instance Addressing is only available on v21+, if the PLC is on a firmware lower than that,
getting the controller info will automatically disable that feature.  If you disable ``init_info`` and are using a controller
on a version lower than 21, set the ``use_instance_ids`` attribute to false or your reads/writes will fail.

Reading Tags
------------

TODO: add examples

Writing Tags
------------

TODO: add examples


COM Usage
---------

For Windows clients, a COM server is also available.  This way ``pycomm3`` can be used from VBA in Excel like RSLinx.

To register, run the following command: ``python -m pycomm3 --register``

VBA Example:
::

    Sub Test()

        Dim plc As Object: Set plc = CreateObject("Pycomm3.COMServer")

        plc.ip_address = "10.20.30.100"
        plc.slot = 1

        plc.Open
        Debug.Print plc.read_tag("Tag1")
        Debug.Print plc.get_plc_name  # also stores the name in plc.name
        Debug.Print plc.name
        plc.Close

    End Sub


License
~~~~~~~
``pycomm3`` is distributed under the MIT License
