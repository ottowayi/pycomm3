import contextlib
import logging
import sys
from typing import Final, cast, ContextManager, Generator, Literal
import string
import contextlib

__all__ = ("Pycomm3Logger", "get_logger", "configure_logging", "VERBOSE_LEVEL")
VERBOSE_LEVEL: Final[int] = logging.DEBUG - 5
VERBOSE_NAME: Final[str] = "VERBOSE"

logging.VERBOSE = VERBOSE_LEVEL  # type: ignore
logging.addLevelName(VERBOSE_LEVEL, VERBOSE_NAME)


class Pycomm3Logger(logging.getLoggerClass()):
    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(VERBOSE_LEVEL):
            self.log(VERBOSE_LEVEL, msg, *args, stacklevel=kwargs.pop("stacklevel", 2), **kwargs)

    def log_bytes(self, title: str, data: bytes) -> None:
        self.verbose("%s\n    %r\n%s", title, data, LazyHexDump(data), stacklevel=3)


class Pycomm3Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == VERBOSE_LEVEL:
            with self.temp_log_format("{msg}"):
                msg = super().format(record)
        else:
            msg = super().format(record)

        return msg.replace(record.name, record.name.replace("pycomm3.", ""))

    @contextlib.contextmanager
    def temp_log_format(self, fmt: str) -> Generator[None, None, None]:
        try:
            orig_fmt: str | None = self._fmt
            self._fmt = fmt
            yield
        finally:
            self._fmt = orig_fmt  # type: ignore


logging.setLoggerClass(Pycomm3Logger)


def get_logger(name: str) -> Pycomm3Logger:
    if not name.startswith("pycomm3"):
        name = f"pycomm3.{name}"
    return cast(Pycomm3Logger, logging.getLogger(name))


DEFAULT_FORMAT: Final[str] = "{asctime} [{levelname}] {name}.{funcName}:{lineno}:: {message}"


def configure_logging(
    level: int | str = logging.DEBUG,
    fmt: str = DEFAULT_FORMAT,
    fmt_style: Literal["{", "%"] = "{",
    handler: logging.Handler | None = None,
) -> None:
    if handler is None:
        handler = logging.StreamHandler()
    handler.setFormatter(Pycomm3Formatter(fmt=fmt, style=fmt_style))
    logger = logging.getLogger("pycomm3")
    logger.addHandler(handler)
    logger.setLevel(level)


PRINTABLE: set[int] = set(
    b"".join(bytes(x, "ascii") for x in (string.ascii_letters, string.digits, string.punctuation, " "))
)


def _to_ascii(bites):
    return "".join(f"{chr(b)}" if b in PRINTABLE else "•" for b in bites)


def hex_dump(msg: bytes) -> str:
    line_len = 16
    lines = (msg[i : i + line_len] for i in range(0, len(msg), line_len))

    formatted_lines = (
        f"    ({i * line_len:0>4x}) {line.hex(' '): <48}    {_to_ascii(line)}" for i, line in enumerate(lines)
    )

    return "\n".join(formatted_lines)


class LazyHexDump:
    def __init__(self, data):
        self._data = data

    def __str__(self):
        return hex_dump(self._data)

    def __len__(self):
        return len(self._data)
