from app import App, Response
from server import Server
from protocol import Protocol
from loop import Loop

app = App()


@app.route('/get', method="GET")
def index(request):
    return Response("Hello, /get")


@app.get('/get2')
def foo(request):
    return Response(body=request.__dict__)


if __name__ == '__main__':
    server = Server(app, Protocol, loop=Loop(), host="0.0.0.0")
    server.run()
