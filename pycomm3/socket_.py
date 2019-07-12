import socket
from autologging import logged
from . import CommError, const
import struct


@logged
class Socket:

    def __init__(self, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def connect(self, host, port):
        try:
            self.sock.connect((host, port))
        except socket.timeout:
            raise CommError("Socket timeout during connection.")

    def send(self, msg, timeout=0):
        if timeout != 0:
            self.sock.settimeout(timeout)
        total_sent = 0
        while total_sent < len(msg):
            try:
                sent = self.sock.send(msg[total_sent:])
                if sent == 0:
                    raise CommError("socket connection broken.")
                total_sent += sent
            except socket.error:
                raise CommError("socket connection broken.")
        return total_sent

    def receive(self, timeout=0):
        try:
            if timeout != 0:
                self.sock.settimeout(timeout)
            data = self.sock.recv(4096)
            data_len = struct.unpack_from('<H', data, 2)[0]
            while len(data) - const.HEADER_SIZE < data_len:
                data += self.sock.recv(4096)

            return data
        except socket.error as err:
            raise CommError(err)

    def close(self):
        self.sock.close()
