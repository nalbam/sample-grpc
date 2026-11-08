# syntax=docker/dockerfile:1

# build: on the build platform, checks that the generated code matches the
# .proto files, runs the unit tests in tests/ and runs the smoke test against a
# started server. The tests stay in this stage; /out holds only src/*.py and *.proto.
FROM --platform=$BUILDPLATFORM python:3.15-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && pip check
COPY src src
RUN mkdir /tmp/gen \
 && python -m grpc_tools.protoc -I src --python_out=/tmp/gen --grpc_python_out=/tmp/gen \
      src/helloworld.proto src/health.proto \
 && for f in /tmp/gen/*.py; do diff -u "src/${f##*/}" "$f" || exit 1; done
COPY tests tests
RUN python -m unittest discover -s tests -v
RUN cd src && (PORT=50099 python app.py & echo $! > /tmp/server.pid) \
 && python smoke_test.py localhost:50099; status=$?; kill "$(cat /tmp/server.pid)"; exit $status
RUN mkdir /out && cp requirements.txt /out/ && cp src/*.py src/*.proto /out/

# artifact: the release artifact, exported by scripts/release.sh artifact.
FROM scratch AS artifact
COPY --from=build /out /

# grpc_health_probe v0.4.61 for Kubernetes probes. The checksums are from the
# release checksums.txt; the build fails when a download does not match.
FROM scratch AS probe-amd64
ADD --chmod=755 --checksum=sha256:3746f63e89561616ce69eafdc9b46f8b23b47db3a564f6f2e8c31359a60e2f38 \
    https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.61/grpc_health_probe-linux-amd64 /grpc_health_probe
FROM scratch AS probe-arm64
ADD --chmod=755 --checksum=sha256:c6ede27c8da07748f188930dfffba089e058cf711e26604591a152ff225d3a99 \
    https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.61/grpc_health_probe-linux-arm64 /grpc_health_probe
FROM probe-${TARGETARCH} AS probe

FROM python:3.15-slim

LABEL org.opencontainers.image.title="sample-grpc" \
      org.opencontainers.image.description="A sample gRPC server in Python" \
      org.opencontainers.image.source="https://github.com/nalbam/sample-grpc"

COPY --from=probe /grpc_health_probe /bin/grpc_health_probe

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/app

# grpcio has native code, so the dependencies install for the target platform.
COPY --from=artifact /requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip check

COPY --from=artifact / ./

RUN useradd --system --uid 10001 --no-create-home app
USER 10001

ARG VERSION=v0.0.0-dev
ENV PORT=50051 \
    VERSION=${VERSION}

EXPOSE 50051

CMD ["python", "app.py"]
