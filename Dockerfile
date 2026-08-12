FROM python:3.11-slim

WORKDIR /app

USER root
RUN apt-get update && apt-get install -y \
    fonts-noto-color-emoji \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpangoft2-1.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

EXPOSE 8080

CMD ["uvicorn", "render_service:app", "--host", "0.0.0.0", "--port", "8080"]
