# Production image for HRS Data Pipeline API + static UI
FROM python:3.12-slim

WORKDIR /app

# Copy package manifest and source so pip can build (hatchling needs src/ for metadata)
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir .

# Render/Fly.io set PORT
ENV PORT=8000
EXPOSE 8000

CMD uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}
