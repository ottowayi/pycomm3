# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Ian Ottoway <ian@ottoway.dev>
# Copyright (c) 2014 Agostino Ruscito <ruscito@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import logging
import sys

__all__ = ["configure_default_logger", "LOG_VERBOSE"]

LOG_VERBOSE = 5


_logger = logging.getLogger("pycomm3")
_logger.addHandler(logging.NullHandler())


def _verbose(self: logging.Logger, msg, *args, **kwargs):
    if self.isEnabledFor(LOG_VERBOSE):
        self._log(LOG_VERBOSE, msg, *args, **kwargs)


logging.addLevelName(LOG_VERBOSE, "VERBOSE")
logging.verbose = _verbose
logging.Logger.verbose = _verbose


def configure_default_logger(level: int = logging.INFO, filename: str = None, logger: str = None):
    """
    Helper method to configure basic logging.  `level` will set the logging level.
    To enable the verbose logging (where the contents of every packet sent/received is logged)
    import the `LOG_VERBOSE` level from the `pycomm3.logger` module. The default level is `logging.INFO`.

    To log to a file in addition to the terminal, set `filename` to the desired log file.

    By default this method only configures the 'pycomm3' logger, to also configure your own logger,
    set the `logger` argument to the name of the logger you wish to also configure.  For the root logger
    use an empty string (``''``).
    """
    loggers = [logging.getLogger('pycomm3'), ]
    if logger == '':
        loggers.append(logging.getLogger())
    elif logger:
        loggers.append(logging.getLogger(logger))

    formatter = logging.Formatter(
        fmt="{asctime} [{levelname}] {name}.{funcName}(): {message}", style="{"
    )
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    if filename:
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(formatter)

    for _log in loggers:
        _log.setLevel(level)
        _log.addHandler(handler)

        if filename:
            _log.addHandler(file_handler)
