FROM python:3.10-slim-bookworm AS base

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]

FROM python:3.10-bookworm AS production-builder

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir nuitka ordered-set zstandard patchelf

COPY . .
RUN python -m nuitka \
    --mode=standalone \
    --assume-yes-for-downloads \
    --include-package=app \
    --include-package=sqlalchemy.dialects \
    --output-dir=/build \
    nuitka_entrypoint.py

FROM python:3.10-slim-bookworm AS production

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY --from=production-builder /build/nuitka_entrypoint.dist/ /app/

EXPOSE 80

CMD ["/app/nuitka_entrypoint.bin"]
