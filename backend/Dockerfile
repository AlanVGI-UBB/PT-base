# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m spacy download es_core_news_md

COPY app/ ./app/
COPY data/schema.sql ./data/
COPY scripts/ ./scripts/
COPY data/videos_senas/ ./data/videos_senas/

EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed_glosario.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]