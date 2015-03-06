from distutils.core import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="pycomm",
    author="Agostino Ruscito",
    author_email="uscito@gmail.com",
    version='0.0.2',
    description="A PLC communication library for Python",
    long_description=long_description,
    license="MIT",
    url="https://github.com/ruscito/pycomm",
    packages=[
        "pycomm",
        "pycomm.ab_comm",
        "pycomm.cip"
    ]
)