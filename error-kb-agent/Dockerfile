FROM python:3.14-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY error_kb_agent/ error_kb_agent/

ENV PORT=8080

CMD ["uv", "run", "uvicorn", "error_kb_agent.agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
