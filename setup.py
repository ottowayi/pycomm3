
from pycomm import common
from distutils.core import setup

with open('README.md') as f:
    description = f.read()

setup(
    name="pycomm",
    author="Agostino Ruscito",
    author_email="uscito@gmail.com",
    version=common.__version__,
    description="A PLC communication library for Python",
    long_description=description,
    license="MIT",
    url="https://github.com/ruscito/pycomm",
    packages=["pycomm", "pycomm.ab_comm", "pycomm.cip"],
    platforms="any",
)