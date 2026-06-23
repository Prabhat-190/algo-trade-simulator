FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    WEB_CONCURRENCY=2 \
    GUNICORN_THREADS=4

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --worker-class gthread --threads ${GUNICORN_THREADS} --timeout 120 trading.src.main:server"]
