from setuptools import setup
from pycomm3 import __version__
import os


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name="pycomm3",
    version=__version__,
    author='Ian Ottoway',
    author_email="ian@ottoway.dev",
    url="https://github.com/ottowayi/pycomm3",
    download_url="",
    description="A PLC communication library for Python",
    long_description=read('README.rst'),
    license="MIT",
    packages=["pycomm3"],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces',
    ],
    include_package_data=True
)