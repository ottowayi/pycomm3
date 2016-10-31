from distutils.core import setup
from pycomm import common
import os


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()

setup(
    name="pycomm",
    version=common.__version__,
    author="Agostino Ruscito",
    author_email="ruscito@gmail.com",
    url="https://github.com/ruscito/pycomm",
    download_url="",
    description="A PLC communication library for Python",
    long_description=read('README.rst'),
    license="MIT",
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
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)