"""Tests for socket_.py.

This wrapper around Python sockets is in the critical path of all
functionality of this library. As such great care should be taken to
understand and test it.

The Socket class as it currently stands has no dependency injection
capabilities, and as such the tests will need to make use of mocking in
order to support the Python socket underneath.

These tests currently bind the code fairly tightly to Python's socket
object, but in this instance I think that's okay as I don't forsee this
changing any time soon, and if it did I would rather that be obvious by
breaking these tests.

The only remaining untested code in Socket is the while loop in receive
"""
import socket
from unittest import mock
import struct

import pycomm3
import pytest
from pycomm3.exceptions import CommError, PycommError
from pycomm3.socket_ import Socket


def test_socket_init_creates_socket():
    with mock.patch('socket.socket') as mock_socket:
        my_sock = Socket()
        assert my_sock
        mock_socket.assert_called_once()

def test_socket_connect_raises_commerror_on_timeout():
    """Test the Socket.connect method.

    This test covers both the calling of Python socket's connect and
    the pycomm exception being raised.
    """
    with mock.patch.object(socket.socket, 'connect') as mock_socket_connect:
        mock_socket_connect.side_effect = socket.timeout
        my_sock = Socket()
        with pytest.raises(CommError):
            my_sock.connect('123.456.789.101', 12345)

        mock_socket_connect.assert_called_once()

def test_socket_send_raises_commerror_on_no_bytes_sent():
    TEST_MSG = b"Meaningless Data"

    with mock.patch.object(socket.socket, 'send') as mock_socket_send:
        mock_socket_send.return_value = 0    
        my_sock = Socket()
        with pytest.raises(CommError):
            my_sock.send(msg=TEST_MSG)

def test_socket_send_returns_length_of_bytes_sent():
    BYTES_TO_SEND = b"Baah baah black sheep"

    with mock.patch.object(socket.socket, 'send') as mock_socket_send:
        mock_socket_send.return_value = len(BYTES_TO_SEND)

        my_sock = Socket()
        sent_bytes = my_sock.send(BYTES_TO_SEND)

        mock_socket_send.assert_called_once_with(BYTES_TO_SEND)
        assert sent_bytes == len(BYTES_TO_SEND)

def test_socket_send_sets_timeout():
    """Pass along our timeout arg to our socket."""
    TIMEOUT_VALUE = 1
    SOCKET_SEND_RESPONSE = 20  # A nonzero number will prevent an exception.
    with mock.patch.object(socket.socket, 'settimeout') as mock_socket_settimeout, \
         mock.patch.object(socket.socket, 'send') as mock_socket_send:
        mock_socket_send.return_value = SOCKET_SEND_RESPONSE

        my_sock = Socket()
        my_sock.send(b"Some Message", timeout=TIMEOUT_VALUE)

        mock_socket_settimeout.assert_called_with(TIMEOUT_VALUE)

def test_socket_send_raises_commerror_on_socketerror():
    TEST_MESSAGE = b"Useless Bytes"
    with mock.patch.object(socket.socket, 'send') as mock_socket_send:
        mock_socket_send.side_effect = socket.error

        my_sock = Socket()
        with pytest.raises(CommError):
            my_sock.send(TEST_MESSAGE)


# Prefixing with the data_len value expected in a message. This
# seems like an implementation detail that should live in cip_base
# rather than directly in the Socket wrapper.
DATA_LEN = 256
DATA_LEN_BYTES = struct.pack('<HH', 0, DATA_LEN)
NULL_HEADER_W_DATA_LEN = DATA_LEN_BYTES.ljust(pycomm3.const.HEADER_SIZE, b'\x00') # len 256
RECVD_BYTES = b"These are the bytes we will recv"
FULL_RECV_MSG = (NULL_HEADER_W_DATA_LEN + RECVD_BYTES).ljust(DATA_LEN+pycomm3.const.HEADER_SIZE, b'\x00')
def test_socket_receive_calls_recv_once_when_data_ge_data_len():
    with mock.patch.object(socket.socket, 'recv') as mock_socket_recv:
        mock_socket_recv.return_value = FULL_RECV_MSG

        my_sock = Socket()
        response = my_sock.receive()

        mock_socket_recv.assert_called_once()
        assert RECVD_BYTES in response

def test_socket_receive_sets_timeout():
    TIMEOUT_VALUE = 1
    with mock.patch.object(socket.socket, 'settimeout') as mock_socket_settimeout, \
         mock.patch.object(socket.socket, 'recv') as mock_socket_recv:
        mock_socket_recv.return_value = FULL_RECV_MSG

        my_sock = Socket()
        my_sock.receive(timeout=TIMEOUT_VALUE)

        mock_socket_settimeout.assert_called_with(TIMEOUT_VALUE)

def test_socket_receive_returns_correct_amount_received_bytes():
    DATA_LEN = 4352
    DATA_LEN_BYTES = struct.pack('<HH', 0, DATA_LEN)
    NULL_HEADER_W_DATA_LEN = DATA_LEN_BYTES.ljust(pycomm3.const.HEADER_SIZE, b'\x00') # len 4352
    RECVD_BYTES = b"These are the bytes we will recv"
    FULL_RECV_MSG = (NULL_HEADER_W_DATA_LEN + RECVD_BYTES).ljust(DATA_LEN+pycomm3.const.HEADER_SIZE, b'\x00')
    with mock.patch.object(socket.socket, 'recv') as mock_socket_recv:
        mock_socket_recv.return_value = FULL_RECV_MSG

        my_sock = Socket()
        response = my_sock.receive()

        assert RECVD_BYTES in response
        assert len(response) - pycomm3.const.HEADER_SIZE == DATA_LEN

def test_socket_receive_raises_commerror_opn_socketerror():
    with mock.patch.object(socket.socket, 'recv') as mock_socket_recv:
        mock_socket_recv.side_effect = socket.error

        my_sock = Socket()
        with pytest.raises(CommError):
            my_sock.receive()

def test_socket_close_closes_socket():
    with mock.patch.object(socket.socket, 'close') as mock_socket_close:
        my_sock = Socket()
        my_sock.close()
        mock_socket_close.assert_called_once()
