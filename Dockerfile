# ---- Stage 1: build the React frontend -------------------------------------
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime --------------------------------------------------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOS_DATA_DIR=/data \
    SOS_PORT=8000
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY sawed_off/ ./sawed_off/
COPY find_insta_id.py custom_emails.example.json ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# All persistent state (uploads, saved event, Google token, templates) lives here.
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${SOS_PORT} --proxy-headers --forwarded-allow-ips='*'"]
