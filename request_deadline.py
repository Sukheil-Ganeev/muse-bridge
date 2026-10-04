"""Bound HTTP header reads by one absolute deadline, even for slow drips."""

import socket
import time


class HeaderDeadlineReader:
    def __init__(self, reader, connection, timeout):
        self.reader = reader
        self.connection = connection
        self.deadline = time.monotonic() + timeout

    def readline(self, size=-1):
        if size == 0:
            return b""
        line = bytearray()
        while size < 0 or len(line) < size:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("request headers read timed out")
            if self.connection is not None:
                self.connection.settimeout(remaining)
            char = self.reader.read(1)
            if not char:
                break
            line.extend(char)
            if char == b"\n":
                break
        return bytes(line)

    def read(self, size=-1):
        return self.reader.read(size)

    def read1(self, size=-1):
        read1 = getattr(self.reader, "read1", self.reader.read)
        return read1(size)
