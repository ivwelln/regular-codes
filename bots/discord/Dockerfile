# ------------ BASE ------------
FROM python:3.12-slim AS base

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# -------- DEPENDENCIES --------
FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./

RUN --mount-type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# -------------- DEV -----------
FROM builder AS dev

RUN --mount-type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

COPY --chown=app:app . .

USER app
CMD ["python", "-m", "bot"]

# ------------- PROD --------------
FROM base as prod

COPY --from=builder /app/.venv /app/.venv

COPY bot ./bot

USER app
CMD ["python", "-m", "bot"]