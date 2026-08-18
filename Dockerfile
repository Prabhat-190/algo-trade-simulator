FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    WEB_CONCURRENCY=2 \
    GUNICORN_THREADS=4 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies are installed before the source is copied so that code changes do
# not invalidate the (slow) dependency layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY trading/ ./trading/

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['PORT']}/healthz\", timeout=5)" || exit 1

# gthread workers suit this workload: each worker runs background feed threads
# alongside request handling, and the work is I/O bound rather than CPU bound.
CMD ["sh", "-c", "exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers ${WEB_CONCURRENCY} \
    --worker-class gthread \
    --threads ${GUNICORN_THREADS} \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    trading.src.main:server"]
