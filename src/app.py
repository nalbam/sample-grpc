import logging

from homi import App, Server
from homi.extend.service import reflection_service, health_service

try:
    from .helloworld_pb2 import _GREETER
except Exception:
    from helloworld_pb2 import _GREETER


app = App(
    services=[
        _GREETER,
        reflection_service,
        health_service,
    ]
)
service_name = 'helloworld.Greeter'


# unary-unary method
@app.method(service_name)
def SayHello(name, **kwargs):
    logging.info(f"{name} is request SayHello")
    return {"message": f"Hello {name}!"}


# unary-stream method
@app.method(service_name)
def SayHelloAgain(name, **kwargs):
    logging.info(f"{name} is request SayHelloAgain")
    return {"message": f"Hello Again {name}!"}


if __name__ == '__main__':
    server = Server(app)
    server.run()
