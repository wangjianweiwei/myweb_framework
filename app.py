import json
import logging
from collections import defaultdict

"""
web应用矿建
"""


class Route:
    def __init__(self):
        self.routes = defaultdict(dict)

    def match(self, url, method):
        methods = self.routes.get(url)
        if not methods:
            raise HttpError(status_code=404, reason="Not found")
        endpoint = methods.get(method)
        if not endpoint:
            raise HttpError(status_code=405, reason="Not allowed")

        return endpoint

    def add_route(self, path, method):
        def wrapper(endpoint):
            self.routes[path][method] = endpoint

            return endpoint

        return wrapper


class Request:
    def __init__(self, data):
        self._data = data

    @property
    def method(self):
        return self._data['method']

    @property
    def url(self):
        return self._data['path']

    @property
    def headers(self):
        return self._data['headers']

    @property
    def query_params(self):
        return self._data['query_params']

    @property
    def body(self):
        return self._data['body']

    @property
    def version(self):
        return self._data['version']

    @property
    def addr(self):
        return self._data['client']


class Response:
    default_content_type = 'text/plain'

    types_map = {
        'css': 'text/css',
        'gif': 'image/gif',
        'html': 'text/html',
        'jpg': 'image/jpeg',
        'js': 'application/javascript',
        'json': 'application/json',
        'png': 'image/png',
        'txt': 'text/plain',
        'svg': 'image/svg+xml',
    }

    def __init__(self, body, headers=None, status_code=200, reason=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.reason = reason
        if isinstance(body, (list, dict)):
            self.body = json.dumps(body).encode()
            self.headers['Content-Type'] = 'application/json'
        elif isinstance(body, str):
            self.body = body.encode()
            self.headers['Content-Type'] = 'text/plain'
        else:
            self.body = body

    def start(self):
        if isinstance(self.body, bytes):
            self.headers['Content-Length'] = str(len(self.body))

        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = self.default_content_type
            if "charset=" not in self.headers["Content-Type"]:
                self.headers['Content-Type'] += '; charset=utf-8'

        if self.reason:
            reason = self.reason
        else:
            if self.status_code == 200:
                reason = "OK"
            else:
                reason = "N/A"

        b = f'HTTP/1.0 {self.status_code} {reason}\r\n'.encode()

        for k, v in self.headers.items():
            b += f"{k}: {v}\r\n".encode()

        b += b'\r\n'

        b += self.body

        return b


class HttpError(Response, Exception):

    def __init__(self, status_code, reason):
        self.status_code = status_code
        self.reason = reason
        Response.__init__(self, reason, status_code=status_code, reason=reason)


class App:

    def __init__(self, route=Route):
        self.router = route()
        self.logger = logging.getLogger("myweb.access")
        logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(levelname)s %(message)s")

    def __call__(self, scope, send):
        request = Request(scope)
        self.dispatch(request, send)

    def get(self, path):
        return self.router.add_route(path, "GET")

    def post(self, path):
        return self.router.add_route(path, "POST")

    def route(self, path, method):
        return self.router.add_route(path, method)

    def dispatch(self, request: Request, send):
        try:
            endpoint = self.router.match(request.url, request.method)
            response = endpoint(request)
        except HttpError as e:
            response = e
        self.logger.info('%s - "%s %s %s" %d',
                         request.addr,
                         request.method,
                         request.url,
                         request.version,
                         response.status_code
                         )
        send(response.start())
