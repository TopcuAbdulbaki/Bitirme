# ======================================================
# CUA Node — Multi-Stage Dockerfile
# Stage 1: Playwright + Chromium binary hazırlığı
# Stage 2: CUDA runtime + tüm Python bağımlılıkları
# ======================================================

# -------------------------------------------------------
# Stage 1: Browser binary'lerini kur
# python:3.11-slim kullanıyoruz çünkü playwright install
# bu image'da çalışıyor; CUDA stage'e binary kopyalarız
# -------------------------------------------------------
FROM python:3.11-slim AS browser-base

# Sistem bağımlılıkları (Playwright Chromium için)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libexpat1 \
        libxcb1 \
        libxkbcommon0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        fonts-liberation \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Playwright'ı kur ve Chromium binary'sini indir
RUN pip install --no-cache-dir playwright==1.44.0
RUN playwright install chromium --with-deps

# -------------------------------------------------------
# Stage 2: CUDA runtime + Python stack
# -------------------------------------------------------
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS runtime

# Python 3.11 kur
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3-pip \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxcb1 \
        libxkbcommon0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        fonts-liberation \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Playwright browser binary'lerini Stage 1'den kopyala
COPY --from=browser-base /root/.cache/ms-playwright /root/.cache/ms-playwright
COPY --from=browser-base /usr/local/lib/python3.11/dist-packages/playwright \
     /usr/local/lib/python3.11/dist-packages/playwright

# Çalışma dizini
WORKDIR /app

# Önce sadece requirements → Docker layer cache için
COPY cua/requirements.txt /app/cua/requirements.txt
RUN pip install --no-cache-dir -r /app/cua/requirements.txt

# Projenin tamamını kopyala
COPY . /app

# gRPC portunu aç
EXPOSE 50054

# Ortam değişkenleri (docker-compose override eder)
ENV ORCHESTRATOR_HOST=orchestrator \
    ORCHESTRATOR_PORT=50051 \
    RABBITMQ_HOST=rabbitmq \
    RABBITMQ_PORT=5672 \
    MODEL_MODE=local \
    LMSTUDIO_URL=http://host.docker.internal:1234/v1 \
    CUA_GRPC_PORT=50054 \
    CUA_HEALTH_FILE=/tmp/cua_health.json \
    CUA_REQUIRE_ORCHESTRATOR=true \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m cua.healthcheck || exit 1

# Başlat
CMD ["python", "-m", "cua.main"]
