# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
from typing import List, Iterator

import pycomm3
import re

# -- Project information -----------------------------------------------------

project = 'pycomm3'
copyright = '2021, Ian Ottoway'
author = 'Ian Ottoway'


# The full version, including alpha/beta/rc tags
release = pycomm3.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.todo',
    'sphinxemoji.sphinxemoji',
    'm2r2',
    'sphinx_copybutton',
]

autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

master_doc = 'index'

autodoc_member_order = 'bysource'

source_suffix = ['.rst', '.md']


# ------- Customizations -------------------------------------------------------------------------------
# customize how autodoc documents some objects, this is mostly for the CIP object library documentation
# so that the docs can just use the automodule directive instead of having to list out each
# object and attribute to get nicer formatting that strictly api-docs

from pycomm3 import CIPAttribute, CIPObject
import sphinx

logger = sphinx.util.logging.getLogger('sphinx.ext.autodoc')


def cip_object_status_codes_table(obj):
    if not hasattr(obj, 'STATUS_CODES') or not obj.STATUS_CODES:
        return []

    pad = ' ' * 2
    lines = [
        '.. list-table:: Service Status Codes',
        f'{pad}:header-rows: 1',
        f'{pad}:widths: 30 15 15 40',
        '',
        f'{pad}* - Service',
        f'{pad * 2}- Status',
        f'{pad * 2}- Ex. Status',
        f'{pad * 2}- Description',
    ]

    for service, statuses in obj.STATUS_CODES.items():
        first_service = True
        if service != 'Any':
            service = obj.Services[service]
        for status, ex_statuses in statuses.items():
            first_status = True
            for ex_status, message in ex_statuses.items():
                service_line = service if first_service else ''
                status_line = f'{status:#04x}' if first_status else ''
                if ex_status is not None:
                    ex_fmt = '#06x' if ex_status > 0xff else '#04x'
                    ex_line = f'{ex_status:{ex_fmt}}'
                else:
                    ex_line = 'N/A'

                lines += [
                    f"{pad}* - {service_line}",
                    f"{pad * 2}- {status_line}",
                    f"{pad * 2}- {ex_line}",
                    f"{pad * 2}- {message}",
                ]
                first_service, first_status = False, False

    lines.append('\n')
    return lines


def process_docstring_cip_object(app, what, name, obj, options, lines):
    if what != 'CIPObject' or not issubclass(obj, CIPObject) or obj == CIPObject:
        return

    lines.insert(0, f'Class Code: ``{obj.class_code:#04x}``')
    lines.insert(1, '')

    lines += cip_object_status_codes_table(obj)


def process_docstring_cip_attr(app, what, name, obj, options, lines):
    if what != 'attribute' or not isinstance(obj, CIPAttribute):
        return

    if obj.all:
        lines.append('This attribute is included in the ``get_attributes_all`` response.')


original_object_description = sphinx.util.inspect.object_description


def patched_object_description(obj):
    """
    Monkeypatch the object_description method that is used to display the value/repr
    of the object.  For most objects we could just monkeypatch the __repr__ method instead,
    but bytes.__repr__ is read only so need to do it here and might as well do them all here instead
    of making multiple patches.

    bytes: as escaped hex values instead of ascii.
    CIPAttribute: non-repr description for attribute


    """
    typ = type(obj)
    if typ == bytes:
        sig = ''.join(r'\x' + hex(bite)[2:] for bite in obj)
        return f"b'{sig}'"

    if typ == CIPAttribute:
        return f'{"Class" if obj.class_attr else "Instance"} Attribute {obj.id:#04x} ({obj.type!r})'

    return original_object_description(obj)


sphinx.util.inspect.object_description = patched_object_description

# only import after we've patched the object_description function
from sphinx.ext.autodoc import ClassDocumenter  # noqa


class CIPObjectDocumenter(ClassDocumenter):
    objtype = 'CIPObject'
    directivetype = 'class'

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        try:
            return issubclass(member, CIPObject) and member != CIPObject
        except Exception:
            return False

    def add_directive_header(self, sig: str) -> None:
        name = ' '.join(re.findall('[A-Z][^A-Z]*', self.format_name().split('.')[-1]))
        src_name = self.get_sourcename()
        self.add_line(name, src_name)
        self.add_line('-' * len(name), src_name)
        self.add_line('', src_name)

        super().add_directive_header(sig)


def setup(app):
    app.connect('autodoc-process-docstring', process_docstring_cip_object)
    app.connect('autodoc-process-docstring', process_docstring_cip_attr)
    app.add_autodocumenter(CIPObjectDocumenter)
