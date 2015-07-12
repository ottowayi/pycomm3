from distutils.core import setup
from pycomm import common


def read(_paths):
    """Build a file path from *paths* and return the contents."""
    with open(_paths, 'r') as f:
        return f.read()

setup(
    name="pycomm",
    author="Agostino Ruscito",
    author_email="uscito@gmail.com",
    version=common.__version__,
    description="A PLC communication library for Python",
    long_description=(read('README.rst')),
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
    package_data = {
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'hello': ['*.msg'],
    }
)