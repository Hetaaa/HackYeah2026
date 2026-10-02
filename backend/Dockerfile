FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so this layer is cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000

# Shell form on purpose: ${PORT} is expanded at runtime (Render/Railway set it).
# exec hands PID 1 to uvicorn so it receives SIGTERM directly.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
