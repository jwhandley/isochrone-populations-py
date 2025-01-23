FROM python:3.13 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Install libexpat1 to get libexpat.so
RUN apt-get update && apt-get install -y \
    libexpat1 \
    libexpat1-dev && \
    rm -rf /var/lib/apt/lists/*



RUN python -m venv .venv
COPY pyproject.toml ./
RUN .venv/bin/pip install .
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .
CMD ["/app/.venv/bin/fastapi", "run"]
