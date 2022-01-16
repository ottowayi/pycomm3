from abc import abstractmethod, ABC
from io import BytesIO
from typing import Union, Optional
from ..exceptions import RequestError, ResponseError


class Request(ABC):
    def __init__(self):
        self._message: bytes = b''

        try:
            self._message = self._build_message()
        except RequestError:
            raise
        except Exception as err:
            raise RequestError('Error building request') from err

    @abstractmethod
    def _build_message(self) -> bytes:
        """
        Encodes the request into bytes message
        """

    @property
    def message(self) -> bytes:
        return self._message


class Response:

    def __init__(self, data: bytes, request: Request):
        self._raw_data = data
        self._data = BytesIO(data)
        self._request = request

        try:
            self._parse_reply()
        except ResponseError:
            raise
        except Exception as err:
            raise ResponseError('Error parsing response') from err

    @abstractmethod
    def _parse_reply(self):
        """
        Parses the response data.  Response data is a BytesIO stream, so the entire contents of
        a response should be consumed by
        """

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Returns the status of the response, True for no errors else False
        """

    @property
    @abstractmethod
    def error(self) -> Optional[str]:
        ...

    def __bool__(self):
        return self.is_valid()
