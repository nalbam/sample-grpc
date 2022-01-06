# Dockerfile

FROM python:3.8

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

CMD ["sh", "-c","homi run app.py -w 100 -p $PORT"]
