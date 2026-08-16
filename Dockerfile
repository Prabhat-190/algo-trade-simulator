FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    WEB_CONCURRENCY=2 \
    GUNICORN_THREADS=4 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trading/ ./trading/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/healthz', timeout=5)" || exit 1

# Run with gunicorn
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --worker-class gthread --threads ${GUNICORN_THREADS} --timeout 120 --access-logfile - --error-logfile - src.main:server"]