from setuptools import setup
import os

__version__ = "0.0.0"
with open("pycomm3/_version.py") as f:
    exec(f.read())


def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()


setup(
    name="pycomm3",
    version=__version__,
    author="Ian Ottoway",
    author_email="ian@ottoway.dev",
    url="https://github.com/ottowayi/pycomm3",
    description="A Python Ethernet/IP library for communicating with Allen-Bradley PLCs.",
    long_description=read("README.rst"),
    license="MIT",
    packages=["pycomm3", "pycomm3.packets", "pycomm3.cip"],
    package_data={"pycomm3": ["py.typed"]},
    python_requires=">=3.6.1",
    include_package_data=True,
    extras_require={
        'tests': ['pytest']
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Manufacturing",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
    ],
)

# Build and Publish Commands:
#
# python -m build
# twine upload --skip-existing dist/*
