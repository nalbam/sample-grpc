import logging
import os
import signal
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

import helloworld_pb2
import helloworld_pb2_grpc

GREETER_SERVICE = helloworld_pb2.DESCRIPTOR.services_by_name['Greeter'].full_name
GRACE_SECONDS = 5


class Greeter(helloworld_pb2_grpc.GreeterServicer):

    # unary-unary method
    def SayHello(self, request, context):
        logging.info(f"{request.name} is request SayHello")
        return helloworld_pb2.HelloReply(message=f"Hello {request.name}!")

    # unary-unary method
    def SayHelloAgain(self, request, context):
        logging.info(f"{request.name} is request SayHelloAgain")
        return helloworld_pb2.HelloReply(message=f"Hello Again {request.name}!")


def create_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    for name in ('', GREETER_SERVICE):
        health_servicer.set(name, health_pb2.HealthCheckResponse.SERVING)

    reflection.enable_server_reflection(
        (GREETER_SERVICE, health.SERVICE_NAME, reflection.SERVICE_NAME), server)

    server.add_insecure_port(f'[::]:{port}')
    return server


def serve():
    logging.basicConfig(level=logging.INFO)
    port = os.environ.get('PORT', '50051')
    server = create_server(port)
    server.start()
    logging.info(f"gRPC server started on port {port}")

    def stop(signum, frame):
        logging.info("SIGTERM received, stopping")
        server.stop(GRACE_SECONDS)

    signal.signal(signal.SIGTERM, stop)
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
