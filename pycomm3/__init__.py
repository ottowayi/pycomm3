__version_info__ = (1, 0, 0)
__version__ = '.'.join(f'{x}' for x in __version_info__)


# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())


class PycommError(Exception):
    ...
