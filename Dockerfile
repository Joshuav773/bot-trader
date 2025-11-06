# Dockerfile for FastAPI backend
# Optimized for Fly.io deployment - multi-stage build to reduce size

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
# Use CPU-only versions of ML libraries to reduce size (~1-2GB smaller)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user \
    fastapi uvicorn python-dotenv pandas numpy backtrader matplotlib pandas-ta \
    TA-Lib scipy plotly transformers beautifulsoup4 requests \
    alpaca-trade-api sqlmodel SQLAlchemy psycopg[binary] passlib[bcrypt] \
    PyJWT polygon-api-client email-validator && \
    pip install --no-cache-dir --user --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir --user tensorflow-cpu

# Final stage - minimal runtime image
FROM python:3.12-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy only backend code (exclude frontend, docs, etc.)
COPY api/ ./api/
COPY backtester/ ./backtester/
COPY data_ingestion/ ./data_ingestion/
COPY analysis_engine/ ./analysis_engine/
COPY config/ ./config/
COPY ml_models/ ./ml_models/
COPY order_flow/ ./order_flow/
COPY risk_management/ ./risk_management/
COPY start_server.py ./
COPY requirements.txt ./

# Make sure scripts in root are executable
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Run the application using our startup script (handles PORT env var)
CMD ["python", "start_server.py"]

