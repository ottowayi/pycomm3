from distutils.core import setup
from pycomm import common
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
    name="pycomm",
    author="Agostino Ruscito",
    author_email="uscito@gmail.com",
    version=common.__version__,
    description="A PLC communication library for Python",
    long_description=long_description,
    license="MIT",
    url="https://github.com/ruscito/pycomm",
    packages=[
        "pycomm",
        "pycomm.ab_comm",
        "pycomm.cip"
    ],
    package_data = {
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'hello': ['*.msg'],
    }
)