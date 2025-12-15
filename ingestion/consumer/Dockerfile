FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY src/ src/
COPY main.py .

ENV MODE=full

CMD ["sh", "-c", "uv run python main.py $MODE"]
