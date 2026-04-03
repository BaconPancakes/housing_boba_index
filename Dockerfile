FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY *.py ./
COPY api_clients/ ./api_clients/
COPY templates/ ./templates/
COPY static/ ./static/
COPY shops.db prices.db ./

ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
