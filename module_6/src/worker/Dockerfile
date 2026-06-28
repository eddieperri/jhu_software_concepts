FROM python:3.11-slim
WORKDIR /app

# Install Chromium and Chromedriver for Selenium
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# FIX: Give ownership of the files to our non-root user so it can save data
COPY --chown=1000:1000 . .

USER 1000
CMD ["python", "consumer.py"]