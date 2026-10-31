FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements /app/backend/requirements
RUN pip install --no-cache-dir -r /app/backend/requirements/prod.txt

COPY backend /app/backend
COPY data_pipelines /app/data_pipelines
COPY ml /app/ml

WORKDIR /app/backend

RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput \
    && useradd --system --uid 1000 --create-home app \
    && mkdir -p media \
    && chown -R app:app media

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
