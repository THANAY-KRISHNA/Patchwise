# Python 3.11 Slim Runtime for Patchwise FastAPI Backend
FROM python:3.11-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and configuration
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh .

# Create non-root system user for security and make entrypoint executable
RUN chmod +x docker-entrypoint.sh && \
    useradd -m -u 1001 patchwise && \
    chown -R patchwise:patchwise /app
USER patchwise

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
