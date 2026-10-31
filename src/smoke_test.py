"""Smoke test: call the Greeter, the health and the reflection service of a running server.

Usage: python smoke_test.py [host:port]   (default: $TARGET, else localhost:$PORT, else localhost:50051)
"""

import os
import sys

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

import helloworld_pb2
import helloworld_pb2_grpc


def main(target):
    with grpc.insecure_channel(target) as channel:
        grpc.channel_ready_future(channel).result(timeout=30)

        health = health_pb2_grpc.HealthStub(channel)
        for service in ('', 'helloworld.Greeter'):
            status = health.Check(health_pb2.HealthCheckRequest(service=service)).status
            assert status == health_pb2.HealthCheckResponse.SERVING, (service, status)

        reflection = reflection_pb2_grpc.ServerReflectionStub(channel)
        responses = reflection.ServerReflectionInfo(iter([reflection_pb2.ServerReflectionRequest(list_services='')]))
        services = [s.name for r in responses for s in r.list_services_response.service]
        assert 'helloworld.Greeter' in services, services

        stub = helloworld_pb2_grpc.GreeterStub(channel)
        for method, expected in ((stub.SayHello, 'Hello smoke!'), (stub.SayHelloAgain, 'Hello Again smoke!')):
            message = method(helloworld_pb2.HelloRequest(name='smoke')).message
            assert message == expected, message
    print(f'smoke test passed on {target}')


if __name__ == '__main__':
    default_target = os.environ.get('TARGET') or f"localhost:{os.environ.get('PORT', '50051')}"
    main(sys.argv[1] if len(sys.argv) > 1 else default_target)
