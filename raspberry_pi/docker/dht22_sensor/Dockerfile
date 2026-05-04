FROM python:3.13-slim
WORKDIR /app


RUN apt-get update && apt-get install -y \
    python3-dev \
    gpiod \
    build-essential \
    swig \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/joan2937/lg.git && \
    cd lg && \
    make && make install && \
    ldconfig && \
    cd .. && \
    rm -rf lg

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import socket, os; host=os.getenv('MQTT_HOST', 'localhost'); port=int(os.getenv('MQTT_PORT', '1883')); socket.create_connection((host, port), timeout=3).close()"

COPY mqtt_publisher.py .

CMD ["python3", "./mqtt_publisher.py"]
