FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright and Chromium with root user
USER root
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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install chromium

# Copy application files
COPY . .

# Expose port for FastAPI
EXPOSE 8080

# Command to run the FastAPI service using uvicorn
CMD ["uvicorn", "render_service:app", "--host", "0.0.0.0", "--port", "8080"]
