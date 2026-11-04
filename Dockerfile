# syntax=docker/dockerfile:1

# build: on the build platform, checks that the generated code matches the
# .proto files and runs the smoke test against a started server.
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
RUN cd src && (PORT=50099 python app.py & echo $! > /tmp/server.pid) \
 && python smoke_test.py localhost:50099; status=$?; kill "$(cat /tmp/server.pid)"; exit $status
RUN mkdir /out && cp requirements.txt /out/ && cp src/*.py src/*.proto /out/

# artifact: the release artifact, exported by scripts/release.sh artifact.
FROM scratch AS artifact
COPY --from=build /out /

FROM python:3.15-slim

LABEL org.opencontainers.image.title="sample-grpc" \
      org.opencontainers.image.description="A sample gRPC server in Python" \
      org.opencontainers.image.source="https://github.com/nalbam/sample-grpc"

# grpc_health_probe for Kubernetes probes, for the target architecture.
ARG TARGETARCH
ARG GRPC_HEALTH_PROBE_VERSION=v0.4.61
ADD --chmod=755 https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-${TARGETARCH} /bin/grpc_health_probe

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
