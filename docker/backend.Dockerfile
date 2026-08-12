# =====================================================================
# ANNEX backend image — used by both the API and the Celery worker
# (same runtime, different command; Phase 7 dev stack). Production
# hardening (multi-stage, image scanning, pinned digests) lands with the
# release pipeline in Phase 11.
#
# Build context: repository root (docker compose sets it automatically).
# =====================================================================
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Install the backend package (deps + app) from the repository context.
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

# Non-root runtime user (useradd is present in slim images).
RUN useradd --create-home --uid 10001 annex
USER annex

EXPOSE 8000

# Healthcheck relies on the unversioned liveness probe.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["annex-api"]
