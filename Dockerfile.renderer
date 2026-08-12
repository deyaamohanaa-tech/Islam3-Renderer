FROM python:3.11-slim

# تثبيت الحزم ومكتبات النظام لـ Playwright ودعم الخطوط والإيموجي
RUN apt-get update && apt-get install -y \
    fonts-noto-color-emoji \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ الملفات والمتطلبات
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir fastapi uvicorn pydantic requests

# تثبيت متصفح Chromium الخاص بـ Playwright بكامل مكتباته
RUN python3 -m playwright install --with-deps chromium

COPY . /app

EXPOSE 8080

CMD ["uvicorn", "render_service:app", "--host", "0.0.0.0", "--port", "8080"]
