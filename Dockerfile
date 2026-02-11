# Production image for HRS Data Pipeline API + static UI
FROM python:3.12-slim

WORKDIR /app

# Copy full package so pip can build (no editable install = no metadata-for-build-editable)
COPY pyproject.toml ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

ENV PORT=8000
EXPOSE 8000

CMD uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}
