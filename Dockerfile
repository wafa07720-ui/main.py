FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ═══ Playwright يثبت Chromium داخلياً (بس مش هنستخدمه) ═══
RUN playwright install-deps chromium || true

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "main.py"]
