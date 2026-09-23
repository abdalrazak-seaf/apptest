# Used for both the API and the worker (same Python workspace).
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
RUN mkdir -p apps/api/src/api apps/worker/src/worker \
 && touch apps/api/src/api/__init__.py apps/worker/src/worker/__init__.py \
 && uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY apps/api apps/api
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --all-packages

RUN useradd --create-home app
USER app
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
