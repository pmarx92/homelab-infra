FROM python:3.13-slim
WORKDIR /home

RUN apt-get update && apt-get install -y \
    python3-dev \
    gpiod \
    build-essential \
    swig \
    git \
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

COPY humidity.py .

CMD ["python", "./humidity.py"]
