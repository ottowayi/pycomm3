from pycomm3._logging import get_logger

from pycomm3.protocols.cip import CIPRoute, CIPConnection, CIPConfig
from pycomm3.protocols.cip.object_library.identity import Identity, IdentityInstanceAttrs
from pycomm3.protocols.ethernetip import EIPConnection, EIPConfig, ETHERNETIP_PORT
from typing import Self, cast, reveal_type


class CIPDriver:
    __log = get_logger(__qualname__)

    def __init__(self, path: str | None = None, connection: CIPConnection | None = None) -> None:
        match path, connection:
            case None, None:
                raise ValueError("must supply `path` or `connection`")
            case None, CIPConnection():
                self._connection = connection
            case str(), None:
                host, port, route = parse_connection_path(path)
                self._connection = CIPConnection(
                    config=CIPConfig(route), transport=EIPConnection(EIPConfig(host=host, port=port))
                )
            case _:
                raise ValueError("cannot supply both `path` and `connection`")

        self._identity: IdentityInstanceAttrs | None = None

    @property
    def connection(self) -> CIPConnection:
        return self._connection

    def open(self, cip_connected: bool = False) -> Self:
        if not self._connection.connected:
            self._connection.connect()
        if cip_connected and not self._connection.cip_connected:
            try:
                self._connection.forward_open()
            except Exception:
                raise ConnectionError("failed to create cip connection")
        return self

    def close(self) -> None:
        if self._connection.cip_connected:
            try:
                self._connection.forward_close()
            except Exception:
                self.__log.exception("failed to close cip connection")
        if self._connection.connected:
            self._connection.disconnect()

    def __enter__(self):
        if not self.connection.connected:
            self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except ConnectionError:
            self.__log.exception("error closing connection")
            return False
        else:
            if not exc_type:
                return True
            self.__log.exception("unhandled client error", exc_info=(exc_type, exc_val, exc_tb))
            return False

    @property
    def identity(self) -> IdentityInstanceAttrs | None:
        if self._identity is None:
            resp = self._connection.get_attributes_all(Identity)
            if resp:
                self._identity = cast(IdentityInstanceAttrs, resp.data)

        return self._identity


def parse_connection_path(path: str) -> tuple[str, int, CIPRoute]:
    try:
        _path = path.replace(",", "/").replace("\\", "/").split("/", maxsplit=1)
        _host, _route = (_path[0], _path[1]) if len(_path) == 2 else (_path[0], None)
        _host = _host.split(":", maxsplit=1)
        if len(_host) == 2:
            host, port = _host[0], int(_host[1])
        else:
            host, port = _host[0], ETHERNETIP_PORT

        return host, port, CIPRoute(_route)

    except Exception as err:
        raise ValueError("invalid connection path") from err
