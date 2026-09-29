FROM python:3.11-slim

# ═══ تثبيت الحاجات المطلوبة ═══
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ═══ نسخ requirements وتثبيتها ═══
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ═══ تثبيت Playwright + Chromium + الـ dependencies ═══
RUN playwright install --with-deps chromium

# ═══ نسخ باقي الملفات ═══
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "main.py"]
