FROM python:3.11-slim

WORKDIR /app

# Make pip more tolerant to slow connections
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300

COPY requirements.txt .

# Upgrade pip and install with retries/timeouts
RUN pip install --upgrade pip \
    && pip install --retries 10 --timeout 300 -r requirements.txt

COPY . .

# Default command for API (ui overrides this in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
