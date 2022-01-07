# Dockerfile

FROM python:3.9-slim-bullseye

RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean

ENV PYTHONUNBUFFERED 1
ENV PKG_DIR /tmp/pkg
ENV SRC_DIR /opt
ENV PORT 50051

COPY requirements.txt ${PKG_DIR}/requirements.txt

RUN pip install --upgrade pip && \
    pip install --upgrade -r ${PKG_DIR}/requirements.txt

RUN rm -rf /tmp/*
ARG CACHEBUST=1
COPY src ${SRC_DIR}
WORKDIR ${SRC_DIR}

ENV PYTHONPATH "${PYTONPATH}:${SRC_DIR}"

# For gRPC health check on k8s
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.6 && \
    curl -fsSL -o /bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

CMD ["sh", "-c", "homi run app.py -w 100 -p $PORT"]
