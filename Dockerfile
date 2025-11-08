# Dockerfile for FastAPI backend
# Optimized for Fly.io deployment - multi-stage build to reduce size

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python deps
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y build-essential gcc g++ && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY api/ ./api/
COPY backtester/ ./backtester/
COPY data_ingestion/ ./data_ingestion/
COPY analysis_engine/ ./analysis_engine/
COPY config/ ./config/
COPY order_flow/ ./order_flow/
COPY start_server.py ./

EXPOSE 8000

CMD ["python", "start_server.py"]

