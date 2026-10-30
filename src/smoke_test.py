"""Smoke test: call the Greeter and the health service of a running server.

Usage: python smoke_test.py [host:port]   (default: $TARGET or localhost:50051)
"""

import os
import sys

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

import helloworld_pb2
import helloworld_pb2_grpc


def main(target):
    with grpc.insecure_channel(target) as channel:
        grpc.channel_ready_future(channel).result(timeout=30)

        health = health_pb2_grpc.HealthStub(channel).Check(health_pb2.HealthCheckRequest())
        assert health.status == health_pb2.HealthCheckResponse.SERVING, health

        stub = helloworld_pb2_grpc.GreeterStub(channel)
        for method, expected in ((stub.SayHello, 'Hello smoke!'), (stub.SayHelloAgain, 'Hello Again smoke!')):
            message = method(helloworld_pb2.HelloRequest(name='smoke')).message
            assert message == expected, message
    print('smoke test passed')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TARGET', 'localhost:50051'))
