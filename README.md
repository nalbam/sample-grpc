# sample-grpc

[![build](https://img.shields.io/github/actions/workflow/status/nalbam/sample-grpc/push.yml?branch=main&style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/actions/workflows/push.yml)
[![release](https://img.shields.io/github/v/release/nalbam/sample-grpc?style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/releases)

<!-- [![CircleCI](https://circleci.com/gh/nalbam/sample-grpc.svg?style=svg)](https://circleci.com/gh/nalbam/sample-grpc) -->

[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/nalbam/sample-grpc?label=Docker%20Hub&style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)
[![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/nalbam/sample-grpc?style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)
[![Docker Pulls](https://img.shields.io/docker/pulls/nalbam/sample-grpc?style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)

<!-- [![DockerHub Badge](http://dockeri.co/image/nalbam/sample-grpc)](https://hub.docker.com/r/nalbam/sample-grpc/) -->

## Docker

```bash
docker pull nalbam/sample-grpc

docker run --rm -p 50051:50051 nalbam/sample-grpc
```

Build the image locally (`TARGETARCH` is set by BuildKit for the build platform):

```bash
docker build -t sample-grpc .
```

## pip install

```bash
pip3 install --upgrade -r requirements.txt

cd src
PORT=50051 python3 app.py
```

`app.py` is a plain grpcio server. It serves `helloworld.Greeter`, the gRPC health service and server reflection on `[::]:$PORT` (default `50051`) and stops gracefully on `SIGTERM`.

## Test

Start the server, then run the greeter client and the smoke test from another shell:

```bash
cd src
python3 greeter_client.py localhost:50051
python3 smoke_test.py localhost:50051
```

`smoke_test.py` calls the Greeter, the health service (service name `""`) and reflection (`helloworld.Greeter` must be listed). `greeter_server.py` starts the same server as `app.py`.

## Regenerate protobuf code

```bash
pip3 install -r requirements-dev.txt

cd src
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto health.proto
```

The generated `*_pb2.py` header shows the `protoc` version bundled with `grpcio-tools`, which can be older than the installed `protobuf` runtime.

CI (`.github/workflows/push.yml`) builds the image on pull requests and on `main`, starts the container and runs the smoke test. Only pushes to `main` release and push the image.
