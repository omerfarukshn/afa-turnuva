FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Pillow için sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fly.io persistent volume: /data
RUN mkdir -p /data/uploads
ENV DATABASE_PATH=/data/database.db
ENV UPLOADS_DIR=/data/uploads

EXPOSE 8080

CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 app:app
