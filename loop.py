import selectors
import traceback
from concurrent.futures import ThreadPoolExecutor
from transport import SocketTransport

"""
基于事件IO的loop
"""


class Handle:

    def __init__(self, callback, args):
        self._callback = callback
        self._args = args

    def run(self):
        try:
            self._callback(*self._args)
        except Exception as e:
            traceback.print_exc()


class Loop:

    def __init__(self, selector=None):
        if selector is None:
            selector = selectors.DefaultSelector()
        self._selector = selector
        self._stop = False
        self._pool = ThreadPoolExecutor(max_workers=20)

    def start_serving(self, sock, backlog, protocol_cls):
        self.add_reader(sock, self.accept_connections, sock, backlog, protocol_cls)

    def accept_connections(self, sock, backlog: int, protocol_cls):
        for i in range(backlog):
            try:
                conn, addr = sock.accept()
            except (BlockingIOError, InterruptedError):
                return
            else:
                conn.setblocking(False)
                self.make_transport(conn, addr, protocol_cls)

    def make_transport(self, conn, addr, protocol_cls):
        return SocketTransport(conn, self, addr, protocol_cls)

    def add_reader(self, sock, callback, *args):
        handle = Handle(callback, args)
        try:
            key = self._selector.get_key(sock)
        except KeyError:
            self._selector.register(sock, selectors.EVENT_READ, (handle, None))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(sock, mask | selectors.EVENT_READ, (handle, writer))

    def remove_reader(self, sock):
        try:
            key = self._selector.get_key(sock)
        except KeyError:
            return
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~selectors.EVENT_READ
            if not mask:
                self._selector.unregister(sock)
            else:
                self._selector.modify(sock, mask, (None, writer))

    def add_writer(self, sock, callback, *args):
        handle = Handle(callback, args)
        try:
            key = self._selector.get_key(sock)
        except KeyError:
            self._selector.register(sock, selectors.EVENT_WRITE, (None, handle))
        else:
            mask, (reader, writer) = key.events, key.data
            self._selector.modify(sock, mask | selectors.EVENT_WRITE, (reader, handle))

    def remove_writer(self, sock):
        try:
            key = self._selector.get_key(sock)
        except KeyError:
            return
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~selectors.EVENT_WRITE
            if not mask:
                self._selector.unregister(sock)
            else:
                self._selector.modify(sock, mask, (reader, None))

    def run_once(self):
        events = self._selector.select(0.5)
        for key, mask in events:
            sock, (reader, writer) = key.fileobj, key.data
            if mask & selectors.EVENT_READ and reader is not None:
                self._pool.submit(reader.run)
                # reader.run()
            if mask & selectors.EVENT_WRITE and writer is not None:
                self._pool.submit(writer.run)
                # writer.run()

    def stop(self):
        self._stop = True

    def run_forever(self):
        while not self._stop:
            self.run_once()
