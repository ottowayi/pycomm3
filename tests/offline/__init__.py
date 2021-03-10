class Mocket:
    """
    A mocked socket
    """
    def __init__(self, *responses: bytes):
        self._responses = iter(responses)

    def receive(self) -> bytes:
        try:
            return next(self._responses)
        except StopIteration:
            return b''

    def send(self, *args, **kwargs):
        ...

    def close(self, *args, **kwargs):
        ...

    def connect(self, *args, **kwargs):
        ...
