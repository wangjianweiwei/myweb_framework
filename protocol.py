from urllib.parse import urlparse

"""
协议层
"""


class Protocol:

    def __init__(self, app=None):
        self.app = app
        self.transport = None

    def parse_data(self, data: str):
        lines = data.split("\n")
        method = None
        path = None
        query_params = None
        version = None
        headers = {}
        body = ""

        body_start = False
        for i, line in enumerate(lines):
            if i == 0:
                method, path_and_query, version = line.split()
                url = urlparse(path_and_query)
                path = url.path
                query_params = url.query
            else:
                if line == "\r":
                    body_start = True
                if body_start:
                    body += line
                else:
                    k, v = line.split(":", 1)
                    headers[k.strip()] = v.strip()
        return {
            "method": method,
            "path": path,
            "query_params": query_params,
            "version": version,
            "headers": headers,
            "body": body,
            "client": self.transport.addr,
        }

    def data_received(self, data):
        data = self.parse_data(data.decode())
        self.app(data, self.send)

    def send(self, data):
        self.transport.write(data)

    def set_transport(self, transport):
        self.transport = transport
