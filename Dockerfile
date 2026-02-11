# Production image for HRS Data Pipeline API + static UI
FROM python:3.12-slim

WORKDIR /app

# Install from pyproject.toml (no dev deps)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Application code
COPY src ./src
COPY config ./config

# Render/Fly.io set PORT
ENV PORT=8000
EXPOSE 8000

CMD uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}
