from distutils.core import setup
from pycomm import common
import os


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()

setup(
    name="pycomm",
    author="Agostino Ruscito",
    author_email="uscito@gmail.com",
    version=common.__version__,
    description="A PLC communication library for Python",
    long_description=read('README.rst'),
    license="MIT",
    url="https://github.com/ruscito/pycomm",
    packages=[
        "pycomm",
        "pycomm.ab_comm",
        "pycomm.cip"
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)