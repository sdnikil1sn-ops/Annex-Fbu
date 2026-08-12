# syntax=docker/dockerfile:1

# =====================================================================
# ANNEX backend image — multi-stage build (Phase 11).
#
# Stage 1 (builder) installs the package and its pinned dependencies
# into an isolated prefix; stage 2 (runtime) copies only those runtime
# artifacts into a slim, non-root image. Build tooling and intermediate
# layers never ship. Both the API service and the Celery worker run
# from this image — same runtime, different command (ADR-0008).
#
# Build context: repository root (docker compose sets it automatically).
#
# Optional build arg:
#   APP_VERSION=<release tag>   stamped into the OCI labels by the
#                               release pipeline (.github/workflows/release.yml)
# =====================================================================

FROM python:3.14-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install the backend package (deps + app) into a clean prefix. The
# runtime stage copies /install, so nothing but runtime artifacts ships.
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir --prefix=/install --no-compile .

FROM python:3.14-slim AS runtime

ARG APP_VERSION=dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Runtime artifacts only: pinned dependencies + the app package + the
# `annex-api` console script (installed under /usr/local/bin).
COPY --from=builder /install /usr/local

LABEL org.opencontainers.image.title="ANNEX backend" \
      org.opencontainers.image.description="ANNEX API & workers — AI-powered Media & Information Literacy platform" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0"

# Non-root runtime user (useradd is present in slim images).
RUN useradd --create-home --uid 10001 annex
USER annex

EXPOSE 8000

# Healthcheck relies on the unversioned liveness probe.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["annex-api"]
