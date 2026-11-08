import logging
import os
import signal
import threading
import time
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

import helloworld_pb2
import helloworld_pb2_grpc

GREETER_SERVICE = helloworld_pb2.DESCRIPTOR.services_by_name['Greeter'].full_name
# Shutdown: health turns NOT_SERVING, the server keeps accepting requests for
# DRAIN_SECONDS so that clients and load balancers see it, then stops and gives
# in-flight requests GRACE_SECONDS to finish. DRAIN_SECONDS + GRACE_SECONDS must
# stay below the stop timeout of the runtime (Docker 10s, Kubernetes
# terminationGracePeriodSeconds 30s by default).
DRAIN_SECONDS = 2
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
    """Returns (server, health_servicer, bound_port). Port 0 binds a free port."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    for name in ('', GREETER_SERVICE):
        health_servicer.set(name, health_pb2.HealthCheckResponse.SERVING)

    reflection.enable_server_reflection(
        (GREETER_SERVICE, health.SERVICE_NAME, reflection.SERVICE_NAME), server)

    bound_port = server.add_insecure_port(f'[::]:{port}')
    return server, health_servicer, bound_port


def shutdown(server, health_servicer, drain=DRAIN_SECONDS, grace=GRACE_SECONDS):
    """Stops the server gracefully and returns the event that server.stop() returns.

    1. Every service ("" and helloworld.Greeter) turns NOT_SERVING.
    2. For `drain` seconds the server still accepts new requests, so health
       checks see NOT_SERVING instead of UNAVAILABLE.
    3. server.stop(grace) rejects new requests and lets in-flight requests
       finish for up to `grace` seconds.
    """
    logging.info(f"Shutting down: health NOT_SERVING, draining for {drain}s")
    health_servicer.enter_graceful_shutdown()
    time.sleep(drain)
    logging.info(f"Stopping: waiting up to {grace}s for in-flight requests")
    return server.stop(grace)


def serve():
    logging.basicConfig(level=logging.INFO)
    port = os.environ.get('PORT', '50051')
    version = os.environ.get('VERSION', 'v0.0.0')
    server, health_servicer, _ = create_server(port)
    server.start()
    logging.info(f"gRPC server {version} started on port {port}")

    # The handler only sets the event, so a second SIGTERM does nothing more.
    # The main thread runs the shutdown.
    terminating = threading.Event()

    def on_sigterm(signum, frame):
        logging.info("SIGTERM received")
        terminating.set()

    signal.signal(signal.SIGTERM, on_sigterm)
    while not terminating.wait(1):
        pass
    shutdown(server, health_servicer)
    server.wait_for_termination()
    logging.info("gRPC server stopped")


if __name__ == '__main__':
    serve()
