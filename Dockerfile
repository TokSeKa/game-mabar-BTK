# Base image bisa diganti, misalnya kalau Docker Hub sedang membatasi pull:
#   docker build --build-arg NODE_IMAGE=mirror.gcr.io/library/node:20-alpine \
#                --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-slim .
ARG NODE_IMAGE=node:20-alpine
ARG PYTHON_IMAGE=python:3.12-slim

# ---------- tahap 1: build frontend ----------
FROM ${NODE_IMAGE} AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- tahap 2: server Python ----------
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static \
    GUIDE_PATH=/app/docs/PANDUAN_BOT_LLM.md
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY docs ./docs
COPY --from=web /web/dist ./static
RUN useradd --create-home --uid 10001 suitbot
USER suitbot
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"
# --workers 1 WAJIB: state room disimpan di memori proses ini.
# Match tetap paralel lewat process pool (MATCH_WORKERS).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
