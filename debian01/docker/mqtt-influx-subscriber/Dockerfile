FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /health

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
    test $(($(date +%s) - $(stat -c %Y /health/status 2>/dev/null || echo 0))) -lt 60

COPY subscriber.py .

CMD ["python3", "./subscriber.py"]
