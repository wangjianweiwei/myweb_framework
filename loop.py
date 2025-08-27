import selectors
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
        self._callback(*self._args)


class Loop:

    def __init__(self, selector=None):
        if selector is None:
            selector = selectors.DefaultSelector()
        self._selector = selector
        self._stop = False
        self._pool = ThreadPoolExecutor(max_workers=10)

    def start_serving(self, sock, backlog, protocol_cls):
        self.add_reader(sock, self.accept_connections, sock, backlog, protocol_cls)

    def accept_connections(self, sock, backlog: int, protocol_cls):
        for i in range(backlog):
            try:
                conn, addr = sock.accept()
            except (BlockingIOError, InterruptedError):
                return
            conn.setblocking(False)
            self.make_transport(conn, addr, protocol_cls)

    def make_transport(self, conn, addr, protocol_cls):
        return SocketTransport(conn, self, addr, protocol_cls)

    def add_reader(self, sock, callback, *args):
        handle = Handle(callback, args)
        self._selector.register(sock, selectors.EVENT_READ, handle)

    def remove_reader(self, sock):
        self._selector.unregister(sock)

    def add_writer(self, sock, callback, *args):
        handle = Handle(callback, args)
        self._selector.register(sock, selectors.EVENT_WRITE, handle)

    def remove_writer(self, sock):
        self._selector.unregister(sock)

    def run_once(self):
        events = self._selector.select(1.0)
        for key, mask in events:
            sock, handle = key.fileobj, key.data
            self._pool.submit(handle.run)

    def stop(self):
        self._stop = True

    def run_forever(self):
        while not self._stop:
            self.run_once()
