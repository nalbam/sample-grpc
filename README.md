# sample-grpc

[![ci](https://img.shields.io/github/actions/workflow/status/nalbam/sample-grpc/ci.yml?branch=main&label=ci&style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/nalbam/sample-grpc?style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/releases)

A gRPC server in Python. It serves `helloworld.Greeter`, the gRPC health service and server reflection.

## Docker

```bash
docker run -d --name sample-grpc -p 50051:50051 ghcr.io/nalbam/sample-grpc
docker exec sample-grpc grpc_health_probe -addr=localhost:50051
docker rm -f sample-grpc
```

The image uses `python:3.15-slim`, runs as the non-root uid `10001`, and contains
`grpc_health_probe` v0.4.61 for Kubernetes probes.

| Environment variable | Default | Description |
| --- | --- | --- |
| `PORT` | `50051` | Listen port. |
| `VERSION` | image tag | Version that the start log line reports (`gRPC server <VERSION> started on port <PORT>`). |

To build the image, test it in its build stage, and smoke-test it (needs Docker with Buildx and `jq`):

```bash
docker buildx build --load -t sample-grpc:dev .
scripts/smoke.sh sample-grpc:dev
```

The build stage checks that `src/*_pb2*.py` match the `.proto` files for the pinned
`grpcio-tools`, then runs `src/smoke_test.py` against a started server.
`scripts/smoke.sh` runs `grpc_health_probe` and `smoke_test.py` in the container, and
checks the version log line, the non-root user, a clean `docker stop` and a custom `PORT`.

## pip install

Use Python 3.15 (the image version). The dependency versions also support Python 3.10 or later.

```bash
python3.15 -m venv .venv
. .venv/bin/activate
pip install --upgrade -r requirements.txt
pip check

cd src
PORT=50051 python app.py
```

`app.py` is a plain grpcio server. It serves `helloworld.Greeter`, the gRPC health service and server reflection on `[::]:$PORT` (default `50051`) and stops gracefully on `SIGTERM`.

## Test

Start the server, then run the greeter client and the smoke test from another shell.
A new shell does not keep the virtual environment active, so activate it again from
the repository root:

```bash
. .venv/bin/activate
cd src
python greeter_client.py localhost:50051
python smoke_test.py localhost:50051
```

`smoke_test.py` checks that:

- `SayHello` returns `Hello smoke!` and `SayHelloAgain` returns `Hello Again smoke!`.
- The health service returns `SERVING` for the service names `""` and `helloworld.Greeter`.
- Reflection lists `helloworld.Greeter`.

It exits with a non-zero status when a check fails. Without an argument it uses `$TARGET`,
else `localhost:$PORT`, else `localhost:50051`. For a custom port, start the server with
`PORT=50052 python app.py` and run `PORT=50052 python smoke_test.py`.
`greeter_server.py` starts the same server as `app.py`.

## Regenerate protobuf code

```bash
pip install --upgrade -r requirements-dev.txt
pip check

cd src
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto health.proto
git diff --exit-code -- '*_pb2*.py'
```

The command writes all four files: `helloworld_pb2.py`, `helloworld_pb2_grpc.py`,
`health_pb2.py` and `health_pb2_grpc.py`. `git diff` shows no change because `requirements-dev.txt` pins the
`grpcio-tools` version that generated the committed files (1.85.1). The Docker build fails when they differ.

The generated code sets the minimum runtime versions:

- `*_pb2.py` shows the `protoc` version bundled with `grpcio-tools` (7.35.1 for 1.85.1).
  It runs on any `protobuf` 7.x runtime at that version or later. The runtime does not
  need to equal the header version.
- `*_pb2_grpc.py` sets `GRPC_GENERATED_VERSION` and fails on import with an older `grpcio`.

To update `grpcio-tools`, change its pin, regenerate, and raise the `grpcio` minimum in
`requirements.txt` to that version, and the `protobuf` minimum if the header version is higher.

## CI/CD

Pull requests and pushes to `main` run CI. A `v*` tag releases the image `ghcr.io/nalbam/sample-grpc:<tag>`
and a GitHub Release with the source archive. Jenkins can run the same pipeline with Nexus and Harbor or ECR.
See [docs/pipeline.md](docs/pipeline.md).
