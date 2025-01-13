from .base import Response, Request


class Connection[ReqT: Request, RespT: Response]:
    def send(self, request: ReqT) -> RespT | None: ...
