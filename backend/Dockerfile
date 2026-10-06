# syntax=docker/dockerfile:1.7
# Imagen del backend de Saber Uli (T008). Contexto de construcción: raíz del repositorio.
#
# Una sola imagen para los servicios api, worker, beat y migrate; el servicio elige con su
# `command` (ver infra/docker/backend-entrypoint.sh). Corre sin root (UID 10001) y sin
# herramientas de compilación (constitución X, research R-32).

ARG PYTHON_IMAGE=python:3.13-slim

FROM ghcr.io/astral-sh/uv:0.11 AS uv

# ---------------------------------------------------------------------------------------------
# builder: resuelve dependencias con uv.lock y construye el entorno virtual.
# ---------------------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src

# Primero solo las dependencias, para aprovechar la caché de capas.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---------------------------------------------------------------------------------------------
# runtime: solo el entorno virtual, las migraciones y el punto de entrada.
# ---------------------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

RUN groupadd --system --gid 10001 saber \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --no-create-home \
       --shell /usr/sbin/nologin saber

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SABER_MIGRATIONS_DIR=/app/migrations

WORKDIR /app
# Archivos de solo lectura para el usuario de ejecución (propiedad de root).
COPY --from=builder /app/.venv /app/.venv
COPY backend/migrations /app/migrations
COPY --chmod=0755 infra/docker/backend-entrypoint.sh /usr/local/bin/saber-entrypoint

USER 10001:10001
EXPOSE 8000

ENTRYPOINT ["saber-entrypoint"]
CMD ["api"]
