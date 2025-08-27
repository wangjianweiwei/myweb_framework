import os
import signal
import socket
import logging
from contextlib import contextmanager

"""
web服务器层
"""


class Server:
    HANDLED_SIGNALS = [
        signal.SIGINT,
        signal.SIGTERM,
    ]

    def __init__(self, app, protocol, loop, host="127.0.0.1", port=8989, backlog=100):
        self._app = app
        self._host = host
        self._port = port
        self._backlog = backlog
        self._loop = loop
        self._protocol = protocol
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._server.setblocking(False)
        self._server.bind((self._host, self._port))
        self._server.listen(self._backlog)

    @contextmanager
    def capture_signals(self):
        for s in self.HANDLED_SIGNALS:
            signal.signal(s, self.stop)

        yield

    def stop(self, signum, frame):
        self._loop.stop()

    def run(self):
        pid = os.getpid()
        logging.info("Starting server process [%d]", pid)
        logging.info("Waiting for application startup.")

        def create_protocol():
            return self._protocol(app=self._app)

        with self.capture_signals():
            self._loop.start_serving(self._server, self._backlog, create_protocol)
            logging.info("Application startup complete")
            logging.info(f"MyServer running on http://{self._host}:{self._port} (Press CTRL+C to quit)")

            self._loop.run_forever()
