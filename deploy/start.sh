#!/usr/bin/env bash
set -euo pipefail

cd /app
export DJANGO_BASE_URL="${DJANGO_BASE_URL:-http://127.0.0.1:8000}"
export SQLITE_PATH="${SQLITE_PATH:-/data/db.sqlite3}"
export MEDIA_ROOT="${MEDIA_ROOT:-/data/media}"
mkdir -p "$(dirname "$SQLITE_PATH")" "$MEDIA_ROOT"

# A Space should provide SECRET_KEY and STREAMLIT_API_TOKEN as Secrets. These
# ephemeral fallbacks keep the demo bootable but reset sessions/tokens on restart.
if [ -z "${SECRET_KEY:-}" ]; then
    export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
    echo "WARNING: SECRET_KEY is not configured. Generated an ephemeral key; add a Space Secret for stable sessions." >&2
fi
if [ -z "${STREAMLIT_API_TOKEN:-}" ]; then
    export STREAMLIT_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    echo "WARNING: STREAMLIT_API_TOKEN is not configured. Generated an ephemeral token; add a Space Secret." >&2
fi
if [ -z "${STREAMLIT_CREATOR_PASSWORD:-}" ]; then
    echo "WARNING: STREAMLIT_CREATOR_PASSWORD is not configured; the Streamlit product creator stays locked." >&2
fi
if [ -z "${DEPLOY_ADMIN_PASSWORD:-}" ]; then
    echo "WARNING: DEPLOY_ADMIN_PASSWORD is not configured; /admin/ has no password login." >&2
fi

echo "Applying migrations and preparing the demo catalog..."
python manage.py migrate --noinput
python manage.py seed_data
python manage.py bootstrap_deploy_admin
python manage.py collectstatic --noinput

DJANGO_PID=""
STREAMLIT_PID=""
NGINX_PID=""
cleanup() {
    local pid
    for pid in "$DJANGO_PID" "$STREAMLIT_PID" "$NGINX_PID"; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT INT TERM

echo "Starting Gunicorn on 127.0.0.1:8000..."
gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --chdir /app \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - &
DJANGO_PID=$!

echo "Starting Streamlit on 127.0.0.1:8501/studio/..."
streamlit run streamlit_app/app.py \
    --server.address=127.0.0.1 \
    --server.port=8501 \
    --server.baseUrlPath=studio \
    --server.headless=true \
    --server.fileWatcherType=none \
    --browser.gatherUsageStats=false &
STREAMLIT_PID=$!

wait_for_url() {
    local url="$1" label="$2" pid="$3"
    local attempt
    for attempt in $(seq 1 60); do
        if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
            echo "$label is ready."
            return 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "ERROR: $label exited during startup." >&2
            return 1
        fi
        sleep 2
    done
    echo "ERROR: $label did not become ready at $url" >&2
    return 1
}

wait_for_url "http://127.0.0.1:8000/api/products/" "Django API" "$DJANGO_PID"
wait_for_url "http://127.0.0.1:8501/studio/_stcore/health" "Streamlit" "$STREAMLIT_PID"

echo "Starting nginx on port 7860."
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "Deployment is up: / serves Django, /studio/ serves Streamlit."
wait -n "$DJANGO_PID" "$STREAMLIT_PID" "$NGINX_PID"
