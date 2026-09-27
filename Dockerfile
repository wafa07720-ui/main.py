FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    xz-utils \
    ca-certificates \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN wget -q https://github.com/FlareSolverr/FlareSolverr/releases/download/v3.3.21/flaresolverr_linux_x64.tar.gz \
    && mkdir -p /tmp/fs_extract \
    && tar -xzf flaresolverr_linux_x64.tar.gz -C /tmp/fs_extract \
    && FS_BIN=$(find /tmp/fs_extract -type f -name "flaresolverr" | head -1) \
    && FS_DIR=$(dirname "$FS_BIN") \
    && cp -r "$FS_DIR"/* /app/ \
    && rm -rf /tmp/fs_extract flaresolverr_linux_x64.tar.gz \
    && chmod +x /app/flaresolverr \
    && chmod +x /app/chromedriver 2>/dev/null || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROME_BIN=/app/chrome/chrome
ENV CHROMEDRIVER_PATH=/app/chromedriver
ENV FLARESOLVERR_PATH=/app/flaresolverr
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "start_both.py"]
