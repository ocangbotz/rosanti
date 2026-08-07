FROM python:3.11-slim AS base

# System deps: gcc for any packages that need to compile, curl for the
# healthcheck. No MT5-related packages — MetaTrader5 is Windows-only and
# is expected to run in mock mode inside this container (see docs/SETUP.md
# for how to point a Windows host running MT5 at this backend instead).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data/screenshots \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
