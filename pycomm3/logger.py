

import logging
import sys

LOG_VERBOSE = 5

_root = logging.getLogger()
_root.addHandler(logging.NullHandler())

logger = logging.getLogger('pycomm3')


def _verbose(self: logging.Logger, msg, *args, **kwargs):
    if self.isEnabledFor(LOG_VERBOSE):
        self._log(LOG_VERBOSE, msg, *args, **kwargs)


logging.addLevelName(LOG_VERBOSE, 'VERBOSE')
logging.verbose = _verbose
logging.Logger.verbose = _verbose


def configure_default_logger(level: int = logging.INFO):
    logger.setLevel(level)
    formatter = logging.Formatter(fmt='{asctime} [{levelname}] {name}.{funcName}(): {message}', style='{')
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
