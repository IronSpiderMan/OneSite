FROM python:3.10-slim-bookworm AS base

WORKDIR /app

ENV PYTHONPATH=/app \
    PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    PIP_DEFAULT_TIMEOUT=180

{% if kafka %}
# python-snappy needs the Snappy headers during installation.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*
{% endif %}

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --retries 10 --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir --retries 20 -r requirements.txt

FROM base AS development

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

FROM python:3.10-bookworm AS production-builder

WORKDIR /app

ENV PYTHONPATH=/app \
    PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    PIP_DEFAULT_TIMEOUT=180

{% if kafka %}
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*
{% endif %}

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --retries 10 --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir --retries 20 -r requirements.txt
RUN python -m pip install --no-cache-dir --retries 20 nuitka ordered-set zstandard patchelf

COPY . .
RUN python -m nuitka \
    --mode=standalone \
    --assume-yes-for-downloads \
    --include-package=app \
    --include-package=onesite_runtime \
    --include-package=sqlalchemy.dialects \
    --include-package=passlib.handlers \
    --include-package=bcrypt \
    --output-dir=/build \
    nuitka_entrypoint.py

FROM debian:bookworm-slim AS production

WORKDIR /app
{% if kafka %}
# The compiled python-snappy extension requires the Snappy shared library at runtime.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libsnappy1v5 \
    && rm -rf /var/lib/apt/lists/*
{% endif %}

RUN mkdir -p /app/data /app/uploads

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY --from=production-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=production-builder /build/nuitka_entrypoint.dist/ /app/

EXPOSE 80

CMD ["/app/nuitka_entrypoint.bin"]
