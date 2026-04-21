FROM python:3.14

ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/backend/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

COPY ./packages /app/packages

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/app/backend:/app

COPY ./backend/scripts /app/backend/scripts

COPY ./backend/pyproject.toml ./backend/uv.lock ./backend/alembic.ini /app/backend/

COPY ./backend/app /app/backend/app
COPY ./backend/tests /app/backend/tests

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Install Chromium binaries required by legacy Playwright scraping/login flows.
RUN .venv/bin/python -m playwright install --with-deps chromium

# Keep the default container command aligned with Fly's 2-worker process.
CMD ["fastapi", "run", "--workers", "2", "app/main.py"]
