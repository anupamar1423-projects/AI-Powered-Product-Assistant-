FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    DEBUG=False \
    DB_ENGINE=sqlite \
    SQLITE_PATH=/data/db.sqlite3 \
    MEDIA_ROOT=/data/media \
    ALLOWED_HOSTS=localhost,127.0.0.1,.hf.space \
    AI_PROVIDER=huggingface \
    DJANGO_BASE_URL=http://127.0.0.1:8000 \
    DEPLOY_ADMIN_USERNAME=storeadmin \
    STREAMLIT_API_USER=storeadmin \
    GUNICORN_WORKERS=2

RUN apt-get update && apt-get install -y --no-install-recommends nginx curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /data/media /var/log/nginx /var/lib/nginx /app/staticfiles \
    && chmod +x /app/deploy/start.sh /app/build.sh

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7860/ >/dev/null || exit 1

CMD ["bash", "/app/deploy/start.sh"]
