from .base import Response, Request
from typing import Protocol
from functools import wraps
from pycomm3.exceptions import ConnectionError


class Connection[ReqT: Request, RespT: Response](Protocol):
    def send(self, request: ReqT) -> RespT | None: ...

    @property
    def connected(self) -> bool: ...


def is_connected(func):
    @wraps(func)
    def wrapped(self: Connection, *args, **kwargs):
        if not self.connected:
            raise ConnectionError("not connected")
        return func(self, *args, **kwargs)

    return wrapped
