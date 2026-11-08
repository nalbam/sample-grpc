"""Tests the shutdown contract of src/app.py.

On shutdown the health service returns NOT_SERVING for "" and helloworld.Greeter
while the server drains, in-flight Greeter requests still get their reply, and
the server stops within DRAIN_SECONDS + GRACE_SECONDS.

Run from the repository root: python -m unittest discover -s tests -v
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'src')
sys.path.insert(0, SRC)

import app  # noqa: E402
import helloworld_pb2  # noqa: E402
import helloworld_pb2_grpc  # noqa: E402

SERVICES = ('', app.GREETER_SERVICE)
NOT_SERVING = health_pb2.HealthCheckResponse.NOT_SERVING
SERVING = health_pb2.HealthCheckResponse.SERVING


def check_status(channel, service):
    """Returns the health status, or the gRPC status code when the RPC fails."""
    try:
        return health_pb2_grpc.HealthStub(channel).Check(
            health_pb2.HealthCheckRequest(service=service), timeout=1).status
    except grpc.RpcError as error:
        return error.code()


def wait_for(predicate, timeout, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class InProcessShutdownTest(unittest.TestCase):

    DRAIN = 0.5
    GRACE = 5

    def test_not_serving_then_in_flight_request_finishes(self):
        entered = threading.Event()
        release = threading.Event()
        say_hello = app.Greeter.SayHello

        def slow_say_hello(servicer, request, context):
            if request.name == 'slow':
                entered.set()
                release.wait(10)
            return say_hello(servicer, request, context)

        with mock.patch.object(app.Greeter, 'SayHello', slow_say_hello):
            server, health_servicer, port = app.create_server(0)
        server.start()
        self.addCleanup(server.stop, None)
        channel = grpc.insecure_channel(f'localhost:{port}')
        self.addCleanup(channel.close)
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = helloworld_pb2_grpc.GreeterStub(channel)

        for service in SERVICES:
            self.assertEqual(check_status(channel, service), SERVING, service)

        in_flight = stub.SayHello.future(helloworld_pb2.HelloRequest(name='slow'), timeout=20)
        self.assertTrue(entered.wait(5), 'the slow request did not start')

        stopped = []
        started = time.monotonic()
        shutter = threading.Thread(
            target=lambda: stopped.append(app.shutdown(server, health_servicer, self.DRAIN, self.GRACE)))
        shutter.start()
        self.addCleanup(shutter.join, 10)

        # (a) During the drain, Check returns NOT_SERVING for every service,
        # and new Greeter requests still get a reply.
        self.assertTrue(wait_for(lambda: check_status(channel, '') == NOT_SERVING, self.DRAIN))
        for service in SERVICES:
            self.assertEqual(check_status(channel, service), NOT_SERVING, service)
        self.assertEqual(stub.SayHello(helloworld_pb2.HelloRequest(name='drain'), timeout=1).message,
                         'Hello drain!')

        # After the drain, server.stop() rejects new RPCs while the slow one is in flight.
        self.assertTrue(wait_for(
            lambda: check_status(channel, '') == grpc.StatusCode.UNAVAILABLE, self.DRAIN + 2),
            'server.stop() was not called after the drain')
        self.assertFalse(in_flight.done())

        # (b) The in-flight request finishes with its normal reply.
        release.set()
        self.assertEqual(in_flight.result(timeout=self.GRACE).message, 'Hello slow!')

        # (c) The server stops within drain + grace.
        shutter.join(self.DRAIN + self.GRACE)
        self.assertEqual(len(stopped), 1)
        self.assertTrue(stopped[0].wait(max(0.0, started + self.DRAIN + self.GRACE - time.monotonic())),
                        'the server did not stop within drain + grace')


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


class SigtermTest(unittest.TestCase):

    def test_sigterm_turns_not_serving_and_exits_zero(self):
        port = free_port()
        env = dict(os.environ, PORT=str(port), VERSION='v0.0.0-test', PYTHONUNBUFFERED='1')
        proc = subprocess.Popen([sys.executable, 'app.py'], cwd=SRC, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        channel = grpc.insecure_channel(f'localhost:{port}')
        self.addCleanup(channel.close)

        self.assertTrue(wait_for(lambda: check_status(channel, '') == SERVING, 20, interval=0.2),
                        'the server did not become SERVING')

        proc.send_signal(signal.SIGTERM)
        sent = time.monotonic()
        # A second SIGTERM must not cause an error or a second stop.
        proc.send_signal(signal.SIGTERM)

        self.assertTrue(wait_for(lambda: check_status(channel, '') == NOT_SERVING, app.DRAIN_SECONDS),
                        'health did not turn NOT_SERVING after SIGTERM')
        for service in SERVICES:
            self.assertEqual(check_status(channel, service), NOT_SERVING, service)

        code = proc.wait(timeout=app.DRAIN_SECONDS + app.GRACE_SECONDS)
        elapsed = time.monotonic() - sent
        log = proc.stderr.read()
        proc.stderr.close()
        self.assertEqual(code, 0, log)
        self.assertLess(elapsed, app.DRAIN_SECONDS + app.GRACE_SECONDS, log)
        self.assertIn(f'gRPC server v0.0.0-test started on port {port}', log)
        self.assertNotIn('Traceback', log)


if __name__ == '__main__':
    unittest.main()
