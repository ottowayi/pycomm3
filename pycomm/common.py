__author__ = 'Agostino Ruscito'
__version__ = "1.0.7"
__date__ = "08 03 2015"
import logging


logging.basicConfig(
    filename="pycomm.log",
    filemode='w',
    level=logging.INFO,
    format="%(name)-13s %(levelname)-10s %(asctime)s %(message)s",
    # propagate=0,
)

LOGGER = logging.getLogger('pycomm')


class PycommError(Exception):
    pass


def setup_logger(name, level, filename=None):
    log = logging.getLogger('pycomm.'+name)
    log.setLevel(level)
    if filename:
        fh = logging.FileHandler(filename, mode='w')
        fh.setFormatter(logging.Formatter("%(levelname)-10s %(asctime)s %(message)s"))
        log.addHandler(fh)
        log.propagate = False

    return log

