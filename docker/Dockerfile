FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    RAGLEMETRY_OUTPUT_DIR=/app/output

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements*.txt ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY src/ /app/src/
COPY mock/ /app/mock/

# Explicitly create output path & configure immutable non-root ownership
RUN groupadd -g 8888 raglemetry && \
    useradd -u 8888 -g raglemetry -s /bin/false raglemetry && \
    mkdir -p /app/output && \
    chown -R raglemetry:raglemetry /app

USER raglemetry:raglemetry

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--log-path", "mock/app.log", "--pattern", "TIMEOUT"]