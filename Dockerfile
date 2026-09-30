FROM python:3.11-slim

# ═══ تثبيت الحاجات الأساسية + Xvfb + مكتبات Chromium ═══
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    xvfb \
    x11-utils \
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
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ═══ تثبيت المكتبات ═══
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ═══ تثبيت Chromium ═══
RUN playwright install chromium

# ═══ نسخ باقي الملفات ═══
COPY . .

# ═══ إعدادات البيئة ═══
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# ═══ تشغيل Xvfb + البوت ═══
CMD Xvfb :99 -screen 0 1920x1080x24 & sleep 3 && python -u main.py
